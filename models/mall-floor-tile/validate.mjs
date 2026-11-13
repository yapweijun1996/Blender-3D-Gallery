import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3,Vector3,Raycaster } from 'three';
import validator from 'gltf-validator';
import {readGlb,near} from './glb.mjs';
const root=fileURLToPath(new URL('.',import.meta.url));
const {bytes,json,scene}=await readGlb(root+'exports/mall-floor-tile-module.glb');
const result=await validator.validateBytes(new Uint8Array(bytes));
assert.equal(result.issues.numErrors,0);assert.equal(result.issues.numWarnings,0);
assert.equal(json.images.length,1);assert.ok(json.images.every(i=>i.bufferView!==undefined&&!i.uri));
assert.ok(json.buffers.every(b=>!b.uri));assert.ok(!json.animations?.length&&!json.cameras?.length&&!json.extensions?.KHR_lights_punctual);
let triangles=0,vertices=0,primitives=0;
scene.traverse(o=>{if(o.isMesh){primitives++;vertices+=o.geometry.attributes.position.count;triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;}});
const bounds=new Box3().setFromObject(scene),dimensions=bounds.getSize(new Vector3()).toArray();
for(const [a,b] of dimensions.map((v,i)=>[v,[1.2,.03,1.2][i]]))near(a,b);
near(bounds.min.y,0);assert.ok(bytes.length<1024*1024&&triangles<1000&&primitives<=10);
const parts={};
for(const name of ['MODULE_GroutBed',...Array.from({length:4},(_,i)=>'MODULE_Tile_'+(i+1))]){
 const o=scene.getObjectByName(name);assert.ok(o,name);const b=new Box3().setFromObject(o);
 parts[name]={min:b.min.toArray(),max:b.max.toArray(),dimensions:b.getSize(new Vector3()).toArray()};
 if(name.includes('Tile')){near(b.min.y,.012);near(b.max.y,.03);near(b.getSize(new Vector3()).x,.596);near(b.getSize(new Vector3()).z,.596);}
}
const surfaceChecks=[];
for(const [x,z,height] of [[0,0,.029],[.3,0,.029],[0,.3,.029],[.599,0,.029],[.3,.3,.03],[-.3,-.3,.03]]){
 const hits=new Raycaster(new Vector3(x,1,z),new Vector3(0,-1,0)).intersectObject(scene,true);assert.ok(hits.length);near(hits[0].point.y,height);surfaceChecks.push({x,z,expectedHeight:height,measuredHeight:hits[0].point.y});
}
export const report={id:'mall-floor-tile-module',surfaceChecks,glb_bytes:bytes.length,triangles,vertices,primitives,materials:json.materials.length,textures:1,texture_dimensions:[512,512],animations:0,dimensions,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},parts,sha256:createHash('sha256').update(bytes).digest('hex'),validation:{errors:0,warnings:0,validator:result.validatorVersion}};
export const assembly=[];
for(const rotated of [false,true]){
 const modules=[],tiles=[];
 for(let x=0;x<3;x++)for(let z=0;z<3;z++){
  const copy=scene.clone(true);copy.position.set(x*1.2,0,z*1.2);copy.rotation.y=rotated?((x+z)%4)*Math.PI/2:0;copy.updateMatrixWorld(true);
  modules.push(new Box3().setFromObject(copy));
  for(let i=1;i<=4;i++)tiles.push(new Box3().setFromObject(copy.getObjectByName('MODULE_Tile_'+i)));
 }
 let pairs=0,maxOverlap=0;
 for(let i=0;i<modules.length;i++)for(let j=i+1;j<modules.length;j++){
  pairs++;const a=modules[i],b=modules[j];const overlap=[0,1,2].map(k=>Math.min(a.max.getComponent(k),b.max.getComponent(k))-Math.max(a.min.getComponent(k),b.min.getComponent(k)));
  if(overlap.every(v=>v>0)){const depth=Math.min(...overlap);maxOverlap=Math.max(maxOverlap,depth);assert.ok(depth<1e-6);}
 }
 let joints=0,maxGapError=0;
 for(let i=0;i<tiles.length;i++)for(let j=i+1;j<tiles.length;j++){
  const a=tiles[i],b=tiles[j],ac=a.getCenter(new Vector3()),bc=b.getCenter(new Vector3());near(ac.y,bc.y);
  for(const [axis,other] of [['x','z'],['z','x']])if(Math.abs(ac[other]-bc[other])<1e-6&&Math.abs(Math.abs(ac[axis]-bc[axis])-.6)<1e-6){
   const gap=ac[axis]<bc[axis]?b.min[axis]-a.max[axis]:a.min[axis]-b.max[axis];near(gap,.004);maxGapError=Math.max(maxGapError,Math.abs(gap-.004));joints++;
  }
  const overlap=[0,1,2].map(k=>Math.min(a.max.getComponent(k),b.max.getComponent(k))-Math.max(a.min.getComponent(k),b.min.getComponent(k)));
  assert.ok(overlap.some(v=>v<=1e-6),'Stone slabs overlap');
 }
 assert.equal(joints,60);const total=new Box3();modules.forEach(b=>total.union(b));near(total.getSize(new Vector3()).x,3.6);near(total.getSize(new Vector3()).z,3.6);
 assembly.push({name:rotated?'3x3-alternating-quarter-turns':'3x3-repeat',modules:9,tiles:36,modulePairs: pairs,jointsMeasured:joints,nominalGroutMetres:.004,maxGroutErrorMetres:maxGapError,maxModuleAabbOverlapMetres:maxOverlap,dimensions:total.getSize(new Vector3()).toArray(),result:'PASS'});
}
fs.writeFileSync(root+'reports/assets.json',JSON.stringify(report,null,2)+'\n');
fs.writeFileSync(root+'reports/assembly.json',JSON.stringify(assembly,null,2)+'\n');
console.log(JSON.stringify({asset:report,assembly},null,2));
