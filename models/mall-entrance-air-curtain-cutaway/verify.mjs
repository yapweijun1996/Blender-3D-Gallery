import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {validateBytes} from 'gltf-validator';
import {Raycaster,Vector3,DoubleSide} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const id='mall-entrance-air-curtain-cutaway';
const data=await readFile(new URL('./exports/'+id+'.glb',import.meta.url));
const K=await validateBytes(data,{uri:id+'.glb',maxIssues:1000});
assert.deepEqual([K.issues.numErrors,K.issues.numWarnings,K.issues.numInfos],[0,0,0],JSON.stringify(K.issues));
const j=JSON.parse(data.subarray(20,20+data.readUInt32LE(12)));
assert.equal(j.asset.version,'2.0');assert.deepEqual(j.buffers.map(x=>x.uri),[undefined]);assert.equal(j.textures?.length??0,0);
const {scene,animations}=await new GLTFLoader().parseAsync(data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength),'');
assert.equal(animations.length,0);scene.updateMatrixWorld(true);
const ALL=[];
scene.traverse(o=>{if(o.isMesh){ALL.push(o);o.material.side=DoubleSide;}});
const V=(x,y,z)=>new Vector3(x,z,-y);
const ray=(p,q,d,obs=ALL)=>new Raycaster(V(...p),V(...q),0,d).intersectObjects(obs,false)[0];
const find=p=>ALL.filter(m=>m.name.startsWith(p));
const one=p=>{const k=find(p);assert.equal(k.length,1,p);return k;};
const dirZ=[0,0,1], backZ=[0,0,-1], dirY=[0,1,0];
const a=one('Continuous_front_outlet_lip'),b=one('Connected_rear_curved_plenum');
let outlet=0,lips=0,intake=0,tines=0,openCage=0,realBlade=0;
for(let i=-18;i<=18;i++){
 const x=i*.032;
 for(const y of [-.030,-.018,0,.019,.031]){
  assert.equal(ray([x,y,.202],dirZ,.129),undefined);
  assert.equal(ray([x,y,.331],backZ,.129),undefined);outlet+=2;
 }
 for(const [y,mesh] of [[-.058,a],[.058,b]]){
  const hit=ray([x,y,.223],dirZ,.090,mesh);
  assert.ok(hit&&hit.point.y>.245&&hit.point.y<.267);lips++;
 }
}
assert.equal(find('Genuinely_separated_front_intake_slat').length,11);
for(let n=0;n<11;n++){
 for(let i=0;i<7;i++){
  const x=-.610+.081*i;
  assert.ok(ray([x,-.197,.335+n*.0184],dirY,.088,ALL.filter(o=>o.name==='Genuinely_separated_front_intake_slat_'+n)));
  tines++;
  if(n<10){
   const z=.335+(n+.5)*.0184;
   assert.equal(ray([x,-.197,z],dirY,.088),undefined);
   assert.equal(ray([x,-.109,z],[0,-1,0],.088),undefined);intake+=2;
  }
 }
}
for(const [d,cx] of [['LEFT',-.336],['RIGHT',.336]]){
 const fan=one('Actual_separate_curved_blade_surfaces_'+d);
 const ann=['Captured_outer_annular_end_ring_','Matching_true_bored_sleeve_end_ring_','Sparse_center_annular_support_band_'].flatMap(n=>one(n+d));
 const v=scene.getObjectByName('OPEN_BLOWER_CAGE_'+d).getWorldPosition(new Vector3());
 assert.ok(v.distanceTo(V(cx,-.018,.425))<1e-6);
 for(const u of [-.207,-.146,-.039,.048,.112,.207])for(let i=0;i<22;i++){
  const p=(i+.5)*Math.PI/11, y=Math.cos(p),z=Math.sin(p);
  assert.equal(ray([cx+u,-.018+.097*y,.425+.097*z],[0,-y,-z],.079,fan.concat(ann)),undefined);
  assert.equal(ray([cx+u,-.018+.019*y,.425+.019*z],[0,y,z],.077,fan.concat(ann)),undefined);
  openCage+=2;
  const p2=i*Math.PI/11, yy=Math.cos(p2),zz=Math.sin(p2);
  assert.ok(ray([cx+u,-.018+.105*yy,.425+.105*zz],[0,-yy,-zz],.06,fan));
  realBlade++;
 }
}
console.log(JSON.stringify({sha256:createHash('sha256').update(data).digest('hex'),bytes:data.length,
 triangles:K.info.totalTriangleCount,vertices:K.info.totalVertexCount,drawCalls:K.info.drawCallCount,
 meshes:j.meshes.length,materials:j.materials.length,animations:0,issues:K.issues,outlet,lips,intake,tines,openCage,realBlade},null,2));
