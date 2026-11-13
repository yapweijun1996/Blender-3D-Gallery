import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {Box3,Vector3,Raycaster} from 'three';
import validator from 'gltf-validator';
import {readGlb,near} from './glb.mjs';
const root=fileURLToPath(new URL('.',import.meta.url)),sha=b=>createHash('sha256').update(b).digest('hex');
const {bytes,json,scene}=await readGlb(root+'exports/optimized.glb');
const val=await validator.validateBytes(new Uint8Array(bytes));
assert.equal(val.issues.numErrors,0);assert.equal(val.issues.numWarnings,0);
assert.ok(!json.animations?.length&&!json.cameras?.length&&!json.extensions?.KHR_lights_punctual);
assert.ok(json.buffers.every(b=>!b.uri)&&!(json.images??[]).length);
const asset=scene.getObjectByName('ASSET_MallEscalatorLanding');assert.deepEqual(asset.position.toArray(),[0,0,0]);near(asset.userData.floor_surface_height_m,.03);
const meshesOf=o=>{const a=[];o.traverse(x=>{if(x.isMesh)a.push(x)});return a;};
let triangles=0,vertices=0,primitives=0;const parts={};
for(const o of meshesOf(scene)){primitives++;vertices+=o.geometry.attributes.position.count;triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;const b=new Box3().setFromObject(o);parts[o.name]={min:b.min.toArray(),max:b.max.toArray()};}
const bounds=new Box3().setFromObject(scene),dimensions=bounds.getSize(new Vector3()).toArray();
dimensions.forEach((x,i)=>near(x,[1.2,.03,1.2][i]));near(bounds.min.y,0);
assert.ok(bytes.length<200*1024&&triangles<3000);assert.equal(primitives,8);assert.equal(json.materials.length,5);
for(const [name,pos] of [['FloorSide',[0,.03,.6]],['FutureEscalator',[0,.03,-.6]],['Underside',[0,0,0]],['LeftEdge',[-.6,.03,0]],['RightEdge',[.6,.03,0]]])asset.getObjectByName('CONNECTOR_'+name).getWorldPosition(new Vector3()).toArray().forEach((x,i)=>near(x,pos[i]));
for(const name of ['MODULE_AccessPlate_Front','MODULE_AccessPlate_Rear']){
 const b=new Box3().setFromObject(asset.getObjectByName(name));near(b.min.y,.012);near(b.max.y,.03);
 const o=asset.getObjectByName(name),a=o.geometry.attributes.position,xs=new Set();
 for(let i=0;i<a.count;i++){const p=new Vector3().fromBufferAttribute(a,i).applyMatrix4(o.matrixWorld);if(Math.abs(p.y-.03)<1e-6)xs.add(p.x.toFixed(6));}
 assert.equal(xs.size,50,'25 ribs with distinct left/right upper edges');
}
const front=new Box3().setFromObject(asset.getObjectByName('MODULE_AccessPlate_Front'));
const rear=new Box3().setFromObject(asset.getObjectByName('MODULE_AccessPlate_Rear'));
near(front.min.z-rear.max.z,.002);
const comb=asset.getObjectByName('MODULE_CombTransition'),combBox=new Box3().setFromObject(comb);
near(combBox.min.z,-.6);near(combBox.max.y,.029);
const toothXs=new Set(),ca=comb.geometry.attributes.position;
for(let i=0;i<ca.count;i++){const p=new Vector3().fromBufferAttribute(ca,i).applyMatrix4(comb.matrixWorld);if(Math.abs(p.z+.6)<1e-6)toothXs.add(p.x.toFixed(6));}
assert.equal(toothXs.size,54,'27 coarse comb fingers');
const floor=await readGlb(root+'../mall-floor-tile/exports/mall-floor-tile-module.glb');
const layouts=JSON.parse(fs.readFileSync(root+'layouts.json')),assemblies=[];
const overlap=(a,b)=>['x','y','z'].map(k=>Math.min(a.max[k],b.max[k])-Math.max(a.min[k],b.min[k]));
const rayHeight=(object,x,z)=>{const ray=new Raycaster(new Vector3(x,1,z),new Vector3(0,-1,0));const hits=ray.intersectObject(object,true);assert.ok(hits.length,'actual surface missing at '+x+','+z);return hits[0].point.y;};
for(const layout of layouts.floor_connections){
 const tile=floor.scene.clone(true);tile.position.fromArray(layout.translation_m);tile.updateMatrixWorld(true);
 const tb=new Box3().setFromObject(tile),axis=layout.axis,s=layout.sign;
 const landingEdge=s===1?bounds.max[axis]:bounds.min[axis],floorEdge=s===1?tb.min[axis]:tb.max[axis];
 near(landingEdge,floorEdge);near(tb.max.y,.03);near(tb.min.y,0);
 let pairChecks=0;for(const a of meshesOf(asset))for(const b of meshesOf(tile)){
  assert.ok(!overlap(new Box3().setFromObject(a),new Box3().setFromObject(b)).every(v=>v>1e-6),'floor and landing volume overlap');pairChecks++;
 }
 const heights=[];
 for(const lateral of [-.45,-.15,.15,.45]){
  const pLanding=axis==='z'?[lateral,.595]:[s*.595,lateral];
  const pFloor=axis==='z'?[lateral,.605]:[s*.605,lateral];
  const a=rayHeight(asset,...pLanding),b=rayHeight(tile,...pFloor);near(a,.03);near(b,.03);heights.push({landing:a,floor:b});
 }
 const gp=axis==='z'?[.15,.601]:[s*.601,.15];const grout=rayHeight(tile,...gp);near(grout,.029);
 assemblies.push({name:layout.name,status:'PASS',floor_sha256:sha(floor.bytes),translation_m:layout.translation_m,edge_gap_m:Math.abs(landingEdge-floorEdge),positiveVolumeIntersections:0,meshPairChecks:pairChecks,actualRayHeightSamples:heights,groutSurface_m:grout,nominalTop_m:.03});
}
const provenance=JSON.parse(fs.readFileSync(root+'provenance.json'));for(const item of provenance.inputs)assert.equal(sha(fs.readFileSync(root+'../'+item.path)),item.sha256);
export const report={id:'mall-escalator-landing',glb_bytes:bytes.length,triangles,vertices,primitives,materials:json.materials.length,textures:0,animations:0,dimensions,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},parts,ribs_per_plate:25,comb_teeth:27,source_parts:8,sha256:sha(bytes),validation:{errors:0,warnings:0,validator:val.validatorVersion}};
export {assemblies};
fs.writeFileSync(root+'reports/assets.json',JSON.stringify(report,null,2)+'\n');fs.writeFileSync(root+'reports/assemblies.json',JSON.stringify(assemblies,null,2)+'\n');
console.log(JSON.stringify({metrics:{...report,parts:undefined},assemblies},null,2));
