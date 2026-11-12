import assert from 'node:assert/strict';import fs from 'node:fs';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';
import {Box3,Vector3,Group} from 'three';import validator from 'gltf-validator';import {readGlb,near} from './glb.mjs';
const root=fileURLToPath(new URL('.',import.meta.url)),layouts=JSON.parse(fs.readFileSync(root+'layouts.json'));
const {bytes,json,scene}=await readGlb(root+'exports/mall-glass-partition.glb');
const v=await validator.validateBytes(new Uint8Array(bytes));assert.equal(v.issues.numErrors,0);assert.equal(v.issues.numWarnings,0);
assert.ok(!json.images?.length&&!json.textures?.length&&!json.animations?.length&&!json.cameras?.length&&!json.extensions?.KHR_lights_punctual);
assert.ok(json.buffers.every(b=>!b.uri));
const asset=scene.getObjectByName('ASSET_MallGlassPartition');assert.deepEqual(asset.position.toArray(),[0,0,0]);near(asset.userData.pitch_m,1.14);
let triangles=0,vertices=0,primitives=0;const parts={};
scene.traverse(o=>{if(o.isMesh){primitives++;vertices+=o.geometry.attributes.position.count;triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;const b=new Box3().setFromObject(o);parts[o.name]={min:b.min.toArray(),max:b.max.toArray()};}});
assert.equal(primitives,15);assert.equal(json.materials.length,3);assert.ok(bytes.length<150*1024&&triangles<3000);
const bounds=new Box3().setFromObject(scene),dimensions=bounds.getSize(new Vector3()).toArray();dimensions.forEach((x,i)=>near(x,[1.2,2.4,.06][i]));near(bounds.min.y,0);
const gm=json.materials.find(m=>m.name.startsWith('GLASS '));assert.equal(gm.alphaMode,'BLEND');near(gm.pbrMetallicRoughness.baseColorFactor[3],.22);
for(const [side,x] of [['Left',-.57],['Right',.57]]){const c=asset.getObjectByName('CONNECTOR_'+side);c.position.toArray().forEach((n,i)=>near(n,[x,0,0][i]));near(c.userData.height_m,2.4);}
const overlap=(a,b)=>['x','y','z'].map(k=>Math.min(a.max[k],b.max[k])-Math.max(a.min[k],b.min[k]));
export const assemblies=[];
for(const example of layouts.examples){
 const group=new Group(),bays=[];
 for(const [i,placement] of example.bays.entries()){
  const bay=asset.clone(true);bay.position.fromArray(placement.position);bay.rotation.y=placement.rotationY;
  if(placement.remove_left_post){const post=bay.getObjectByName('POST_Left');assert.ok(post);post.removeFromParent();}
  group.add(bay);bays.push(bay);
 }
 group.updateMatrixWorld(true);let postCount=0,meshCount=0;const meshes=[];
 group.traverse(o=>{if(o.isMesh){meshes.push(o);meshCount++;if(o.name.startsWith('POST_'))postCount++;}});
 assert.equal(postCount,bays.length+1);assert.equal(meshCount,15*bays.length-(bays.length-1));
 let comparisons=0;for(let i=0;i<meshes.length;i++)for(let j=i+1;j<meshes.length;j++){
  comparisons++;assert.ok(!overlap(new Box3().setFromObject(meshes[i]),new Box3().setFromObject(meshes[j])).every(x=>x>1e-6),example.name+': '+meshes[i].name+' overlaps '+meshes[j].name);
 }
 let maxJointError=0;
 for(let i=1;i<bays.length;i++){
  const a=bays[i-1].getObjectByName('CONNECTOR_Right').getWorldPosition(new Vector3()),b=bays[i].getObjectByName('CONNECTOR_Left').getWorldPosition(new Vector3());
  const d=a.distanceTo(b);assert.ok(d<1e-6);maxJointError=Math.max(d,maxJointError);assert.equal(bays[i].getObjectByName('POST_Left'),undefined);
  const shared=bays[i-1].getObjectByName('POST_Right');assert.ok(shared);const centre=new Box3().setFromObject(shared).getCenter(new Vector3());near(centre.x,a.x);near(centre.z,a.z);
 }
 const b=new Box3().setFromObject(group),dims=b.getSize(new Vector3()).toArray();dims.forEach((n,i)=>near(n,example.expected_dimensions[i]));near(b.min.y,0);
 assemblies.push({name:example.name,bays:bays.length,uniquePosts:postCount,meshes:meshCount,dimensions:dims,maxJointErrorMetres:maxJointError,pairwiseMeshComparisons:comparisons,overlappingMeshPairs:0,result:'PASS'});
}
export const report={id:'mall-glass-partition',glb_bytes:bytes.length,triangles,vertices,primitives,materials:json.materials.length,textures:0,animations:0,dimensions,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},parts,glassAlpha:.22,sha256:createHash('sha256').update(bytes).digest('hex'),validation:{errors:0,warnings:0,validator:v.validatorVersion}};
fs.writeFileSync(root+'reports/assets.json',JSON.stringify(report,null,2)+'\n');fs.writeFileSync(root+'reports/assemblies.json',JSON.stringify(assemblies,null,2)+'\n');console.log(JSON.stringify({asset:report,assemblies},null,2));
