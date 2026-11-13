import assert from 'node:assert/strict';
import fs from 'node:fs';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';
import {Box3,Vector3} from 'three';import validator from 'gltf-validator';import {readGlb,near} from './glb.mjs';
const root=fileURLToPath(new URL('.',import.meta.url));
const {bytes,json,scene}=await readGlb(root+'exports/mall-shopfront-door.glb');
const v=await validator.validateBytes(new Uint8Array(bytes));assert.equal(v.issues.numErrors,0);assert.equal(v.issues.numWarnings,0);
assert.ok(!json.images?.length&&!json.textures?.length&&!json.animations?.length&&!json.cameras?.length&&!json.extensions?.KHR_lights_punctual);
assert.ok(json.buffers.every(b=>!b.uri));
const asset=scene.getObjectByName('ASSET_MallShopfrontDoor'),fixed=scene.getObjectByName('FRAME_Fixed');
assert.equal(asset.children.length,3);assert.deepEqual(asset.position.toArray(),[0,0,0]);
let triangles=0,vertices=0,primitives=0;const parts={};
scene.traverse(o=>{if(o.isMesh){primitives++;vertices+=o.geometry.attributes.position.count;triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;const b=new Box3().setFromObject(o);parts[o.name]={min:b.min.toArray(),max:b.max.toArray()};}});
assert.equal(primitives,33);assert.equal(json.materials.length,4);
assert.ok(bytes.length<350*1024&&triangles<8000);
const bounds=new Box3().setFromObject(scene),dimensions=bounds.getSize(new Vector3()).toArray();
dimensions.forEach((x,i)=>near(x,[2.1,2.4,.183][i]));near(bounds.min.y,0);
const gm=json.materials.find(m=>m.name.startsWith('GLASS '));assert.equal(gm.alphaMode,'BLEND');near(gm.pbrMetallicRoughness.baseColorFactor[3],.22);
const fixedTransforms=Object.fromEntries(fixed.children.map(o=>[o.name,o.matrixWorld.toArray()]));
const left=scene.getObjectByName('HINGE_Left'),right=scene.getObjectByName('HINGE_Right');
for(const [pivot,x] of [[left,-.95],[right,.95]]){near(pivot.position.x,x);near(pivot.position.y,0);near(pivot.position.z,.04);assert.equal(pivot.children.length,13);}
const leftGlass=scene.getObjectByName('GLASS_Left'),rightGlass=scene.getObjectByName('GLASS_Right');
const leftRelative=leftGlass.position.toArray(),rightRelative=rightGlass.position.toArray();
const overlap=(a,b)=>['x','y','z'].map(k=>Math.min(a.max[k],b.max[k])-Math.max(a.min[k],b.min[k]));
const stationaryFrame=fixed.children.filter(o=>o.name.startsWith('FRAME_'));
const closedScene=Object.fromEntries(asset.children.map(o=>[o.name,o.matrixWorld.toArray()]));
export const articulation=[];
for(const mode of ['left-only','right-only','both'])for(const degrees of [0,15,30,45,60,75,90]){
 left.rotation.y=mode==='right-only'?0:-degrees*Math.PI/180;right.rotation.y=mode==='left-only'?0:degrees*Math.PI/180;scene.updateMatrixWorld(true);
 for(const o of fixed.children)assert.deepEqual(o.matrixWorld.toArray(),fixedTransforms[o.name],'Fixed frame moved');
 assert.deepEqual(leftGlass.position.toArray(),leftRelative);assert.deepEqual(rightGlass.position.toArray(),rightRelative);
 // Conservative AABB separation across distinct assemblies. Leaf/handle attachment
 // overlaps within a leaf and the coaxial hinge bearing interfaces are intentional.
 for(const pivot of [left,right])for(const part of pivot.children)for(const frame of stationaryFrame){
   const overlaps=overlap(new Box3().setFromObject(part),new Box3().setFromObject(frame));
   assert.ok(!overlaps.every(x=>x>1e-6),part.name+' intersects '+frame.name);
 }
 const lb=new Box3().setFromObject(left),rb=new Box3().setFromObject(right);
 assert.ok(!overlap(lb,rb).every(x=>x>1e-6),'Leaf assemblies collide');
 if(degrees>0&&mode!=='right-only')assert.ok(new Box3().setFromObject(leftGlass).getCenter(new Vector3()).z>.04);
 if(degrees>0&&mode!=='left-only')assert.ok(new Box3().setFromObject(rightGlass).getCenter(new Vector3()).z>.04);
 const gap=rb.min.x-lb.max.x;
 articulation.push({mode,degrees,fixedFrameUnchanged:true,leafLocalPartsUnchanged:true,frameAndOppositeLeafCollision:false,projectedGapMetres:gap,result:'PASS'});
 if(mode==='both'&&degrees===90)assert.ok(gap>1.73&&gap<1.75,'Usable open gap includes pull handles');
}
left.rotation.y=right.rotation.y=0;scene.updateMatrixWorld(true);
for(const o of asset.children)assert.deepEqual(o.matrixWorld.toArray(),closedScene[o.name]);
const open=articulation.find(a=>a.mode==='both'&&a.degrees===90);
export const report={id:'mall-shopfront-door',glb_bytes:bytes.length,triangles,vertices,primitives,materials:json.materials.length,textures:0,animations:0,dimensions,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},parts,frameApertureMetres:[1.94,2.32],openClearWidthIncludingHardwareMetres:open.projectedGapMetres,glassAlpha:.22,sha256:createHash('sha256').update(bytes).digest('hex'),validation:{errors:0,warnings:0,validator:v.validatorVersion}};
fs.writeFileSync(root+'reports/assets.json',JSON.stringify(report,null,2)+'\n');
fs.writeFileSync(root+'reports/articulation.json',JSON.stringify(articulation,null,2)+'\n');
console.log(JSON.stringify({asset:report,articulationCases:articulation.length},null,2));
