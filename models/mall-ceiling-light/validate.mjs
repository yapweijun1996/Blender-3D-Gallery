import assert from 'node:assert/strict';
import fs from 'node:fs';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';
import {Box3,Vector3,Raycaster,Group} from 'three';import validator from 'gltf-validator';import {readGlb,near} from './glb.mjs';
const root=fileURLToPath(new URL('.',import.meta.url));
const {bytes,json,scene}=await readGlb(root+'exports/mall-ceiling-light-module.glb');
const result=await validator.validateBytes(new Uint8Array(bytes));assert.equal(result.issues.numErrors,0);assert.equal(result.issues.numWarnings,0);
assert.ok(!json.images?.length&&!json.textures?.length);assert.ok(json.buffers.every(b=>!b.uri));
assert.ok(!json.animations?.length&&!json.cameras?.length&&!json.extensions?.KHR_lights_punctual);
let triangles=0,vertices=0,primitives=0;
scene.traverse(o=>{if(o.isMesh){primitives++;vertices+=o.geometry.attributes.position.count;triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;}});
const bounds=new Box3().setFromObject(scene),dimensions=bounds.getSize(new Vector3()).toArray();
dimensions.forEach((v,i)=>near(v,[.576,.065,.576][i]));near(bounds.min.y,-.001);
assert.ok(bytes.length<256*1024&&triangles<5000&&primitives<=16);
const parts={};
for(const o of scene.getObjectByName('ASSET_MallCeilingLight').children){
 const b=new Box3().setFromObject(o);parts[o.name]={min:b.min.toArray(),max:b.max.toArray(),dimensions:b.getSize(new Vector3()).toArray()};
}
assert.equal(Object.keys(parts).length,11);assert.equal(json.materials.length,4);
const emissive=json.materials.find(m=>m.name==='Warm opal emissive diffuser').emissiveFactor;emissive.forEach((v,i)=>near(v,[.8,.73,.55][i]));
const surfaceChecks=[];
for(const [x,z,height] of [[0,0,.003],[.28,0,0],[-.274,.274,-.001]]){
 const hits=new Raycaster(new Vector3(x,-1,z),new Vector3(0,1,0)).intersectObject(scene,true);assert.ok(hits.length);near(hits[0].point.y,height);surfaceChecks.push({x,z,expectedUndersideHeight:height,measuredHeight:hits[0].point.y});
}
export const report={id:'mall-ceiling-light-module',surfaceChecks,glb_bytes:bytes.length,triangles,vertices,primitives,materials:json.materials.length,textures:0,animations:0,emissiveFactor:emissive,dimensions,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},parts,sha256:createHash('sha256').update(bytes).digest('hex'),validation:{errors:0,warnings:0,validator:result.validatorVersion}};
// Test each of four actual panel bays, with and without quarter-turn rotation.
export const assembly=[];
for(let panelIndex=1;panelIndex<=4;panelIndex++)for(const rotated of [false,true]){
 const ceiling=(await readGlb(root+'../mall-ceiling-panel/exports/mall-ceiling-panel-module.glb')).scene;
 const kit=ceiling.getObjectByName('ASSET_MallCeilingPanel'),removed=ceiling.getObjectByName('PANEL_'+panelIndex);
 const removedBounds=new Box3().setFromObject(removed),centre=removedBounds.getCenter(new Vector3());
 const retained=Object.fromEntries(kit.children.filter(o=>o!==removed).map(o=>[o.name,o.matrixWorld.toArray()]));
 removed.removeFromParent();assert.equal(kit.children.filter(o=>o.name.startsWith('PANEL_')).length,3);
 const light=scene.clone(true);light.position.set(centre.x,.008,centre.z);light.rotation.y=rotated?Math.PI/2:0;light.updateMatrixWorld(true);
 const lb=new Box3().setFromObject(light);near(lb.min.x,removedBounds.min.x);near(lb.max.x,removedBounds.max.x);near(lb.min.z,removedBounds.min.z);near(lb.max.z,removedBounds.max.z);
 near(lb.min.y,.007);near(lb.max.y,.072);
 let maxOverlap=0,retainedMeshCount=0;
 for(const o of kit.children){
  assert.deepEqual(o.matrixWorld.toArray(),retained[o.name]);
  if(o.name.startsWith('CONNECTOR_'))continue;
  retainedMeshCount++;
  const b=new Box3().setFromObject(o),overlap=['x','y','z'].map(k=>Math.min(lb.max[k],b.max[k])-Math.max(lb.min[k],b.min[k]));
  if(overlap.every(v=>v>0)){maxOverlap=Math.max(maxOverlap,Math.min(...overlap));assert.ok(Math.min(...overlap)<1e-6,'Light overlaps retained '+o.name);}
 }
 assert.equal(retainedMeshCount,24);
 const combined=new Group();combined.add(ceiling,light);combined.updateMatrixWorld(true);
 const hits=new Raycaster(new Vector3(centre.x,-1,centre.z),new Vector3(0,1,0)).intersectObject(combined,true);
 assert.ok(hits[0].object.name.startsWith('DIFFUSER_Opal'));near(hits[0].point.y,.011);
 for(const o of kit.children.filter(o=>o.name.startsWith('PANEL_'))){
  const p=new Box3().setFromObject(o).getCenter(new Vector3());
  const hit=new Raycaster(new Vector3(p.x,-1,p.z),new Vector3(0,1,0)).intersectObject(combined,true)[0];near(hit.point.y,.008);
 }
 assembly.push({removedPanel:'PANEL_'+panelIndex,quarterTurn:rotated,retainedPanels:3,retainedMeshes:retainedMeshCount,retainedTransformsUnchanged:true,fixturePosition:light.position.toArray(),maxAabbOverlapMetres:maxOverlap,undersideVisible:true,result:'PASS'});
}
fs.writeFileSync(root+'reports/assets.json',JSON.stringify(report,null,2)+'\n');
fs.writeFileSync(root+'reports/assembly.json',JSON.stringify(assembly,null,2)+'\n');console.log(JSON.stringify({asset:report,assembly},null,2));
