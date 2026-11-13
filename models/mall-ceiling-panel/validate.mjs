import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {Box3,Vector3,Raycaster} from 'three';
import validator from 'gltf-validator';
import {readGlb,near} from './glb.mjs';
const root=fileURLToPath(new URL('.',import.meta.url));
const {bytes,json,scene}=await readGlb(root+'exports/mall-ceiling-panel-module.glb');
const result=await validator.validateBytes(new Uint8Array(bytes));
assert.equal(result.issues.numErrors,0);assert.equal(result.issues.numWarnings,0);
assert.equal(json.images.length,1);assert.ok(json.images.every(i=>i.bufferView!==undefined&&!i.uri));
assert.ok(json.buffers.every(b=>!b.uri));assert.ok(!json.animations?.length&&!json.cameras?.length&&!json.extensions?.KHR_lights_punctual);
let triangles=0,vertices=0,primitives=0;
scene.traverse(o=>{if(o.isMesh){primitives++;vertices+=o.geometry.attributes.position.count;triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;}});
const bounds=new Box3().setFromObject(scene),dimensions=bounds.getSize(new Vector3()).toArray();
dimensions.forEach((v,i)=>near(v,[1.2,.36,1.2][i]));near(bounds.min.y,0);
assert.ok(bytes.length<512*1024&&triangles<5000&&primitives<=32);
const parts={};
for(const o of scene.getObjectByName('ASSET_MallCeilingPanel').children){
 if(o.name.startsWith('CONNECTOR_'))continue;
 const b=new Box3().setFromObject(o);parts[o.name]={min:b.min.toArray(),max:b.max.toArray(),dimensions:b.getSize(new Vector3()).toArray()};
 if(o.name.startsWith('PANEL_')){near(b.min.y,.008);near(b.max.y,.024);near(b.getSize(new Vector3()).x,.576);near(b.getSize(new Vector3()).z,.576);}
}
assert.equal(Object.keys(parts).length,25);
const connectors={};
for(const [name,position] of Object.entries({XP:[.6,.018,0],XN:[-.6,.018,0],YP:[0,.018,-.6],YN:[0,.018,.6]})){
 const o=scene.getObjectByName('CONNECTOR_'+name);assert.ok(o);const p=o.getWorldPosition(new Vector3()).toArray();p.forEach((v,i)=>near(v,position[i]));connectors[name]=p;
}
const surfaceChecks=[];
for(const [x,z,height] of [[0,0,0],[.3,0,0],[0,.3,0],[.594,0,0],[.3,.3,.008],[-.3,-.3,.008]]){
 const hits=new Raycaster(new Vector3(x,-1,z),new Vector3(0,1,0)).intersectObject(scene,true);assert.ok(hits.length);near(hits[0].point.y,height);surfaceChecks.push({x,z,expectedUndersideHeight:height,measuredHeight:hits[0].point.y});
}
export const report={id:'mall-ceiling-panel-module',surfaceChecks,connectors,glb_bytes:bytes.length,triangles,vertices,primitives,materials:json.materials.length,textures:1,texture_dimensions:[256,256],animations:0,dimensions,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},parts,sha256:createHash('sha256').update(bytes).digest('hex'),validation:{errors:0,warnings:0,validator:result.validatorVersion}};
export const assembly=[];
for(const rotated of [false,true]){
 const modules=[],panels=[],roots=[];
 for(let x=0;x<3;x++)for(let z=0;z<3;z++){
  const copy=scene.clone(true);copy.position.set(x*1.2,0,z*1.2);copy.rotation.y=rotated?((x+z)%4)*Math.PI/2:0;copy.updateMatrixWorld(true);roots.push(copy);modules.push(new Box3().setFromObject(copy));
  for(let i=1;i<=4;i++)panels.push(new Box3().setFromObject(copy.getObjectByName('PANEL_'+i)));
 }
 let maxOverlap=0,seams=0,maxConnectorError=0;
 for(let i=0;i<modules.length;i++)for(let j=i+1;j<modules.length;j++){
  const a=modules[i],b=modules[j],overlap=[0,1,2].map(k=>Math.min(a.max.getComponent(k),b.max.getComponent(k))-Math.max(a.min.getComponent(k),b.min.getComponent(k)));
  if(overlap.every(v=>v>0)){const depth=Math.min(...overlap);maxOverlap=Math.max(maxOverlap,depth);assert.ok(depth<1e-6);}
  const delta=a.getCenter(new Vector3()).sub(b.getCenter(new Vector3()));
  if(Math.abs(delta.length()-1.2)<1e-6){
   let nearest=Infinity;
   for(const n of ['XP','XN','YP','YN'])for(const m of ['XP','XN','YP','YN'])nearest=Math.min(nearest,roots[i].getObjectByName('CONNECTOR_'+n).getWorldPosition(new Vector3()).distanceTo(roots[j].getObjectByName('CONNECTOR_'+m).getWorldPosition(new Vector3())));
   assert.ok(nearest<1e-6);maxConnectorError=Math.max(maxConnectorError,nearest);seams++;
  }
 }
 let joints=0,maxGapError=0;
 for(let i=0;i<panels.length;i++)for(let j=i+1;j<panels.length;j++){
  const a=panels[i],b=panels[j],ac=a.getCenter(new Vector3()),bc=b.getCenter(new Vector3());near(ac.y,bc.y);
  for(const [axis,other] of [['x','z'],['z','x']])if(Math.abs(ac[other]-bc[other])<1e-6&&Math.abs(Math.abs(ac[axis]-bc[axis])-.6)<1e-6){
   const gap=ac[axis]<bc[axis]?b.min[axis]-a.max[axis]:a.min[axis]-b.max[axis];near(gap,.024);maxGapError=Math.max(maxGapError,Math.abs(gap-.024));joints++;
  }
  const overlap=[0,1,2].map(k=>Math.min(a.max.getComponent(k),b.max.getComponent(k))-Math.max(a.min.getComponent(k),b.min.getComponent(k)));assert.ok(overlap.some(v=>v<=1e-6),'Panels overlap');
 }
 assert.equal(joints,60);assert.equal(seams,12);const total=new Box3();modules.forEach(b=>total.union(b));near(total.getSize(new Vector3()).x,3.6);near(total.getSize(new Vector3()).z,3.6);
 assembly.push({name:rotated?'3x3-alternating-quarter-turns':'3x3-repeat',modules:9,panels:36,panelGapsMeasured:joints,matchedConnectorSeams:seams,nominalGridWidthMetres:.024,maxGridGapErrorMetres:maxGapError,maxConnectorErrorMetres:maxConnectorError,maxModuleAabbOverlapMetres:maxOverlap,dimensions:total.getSize(new Vector3()).toArray(),result:'PASS'});
}
fs.writeFileSync(root+'reports/assets.json',JSON.stringify(report,null,2)+'\n');
fs.writeFileSync(root+'reports/assembly.json',JSON.stringify(assembly,null,2)+'\n');
console.log(JSON.stringify({asset:report,assembly},null,2));
