import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {validateBytes} from 'gltf-validator';
import {Raycaster,DoubleSide,Vector3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const id='funicular-cable-guide-roller-section';
const raw=await readFile(new URL('./exports/'+id+'.glb',import.meta.url));
const K=await validateBytes(raw,{uri:id+'.glb',maxIssues:1000});
assert.deepEqual([K.issues.numErrors,K.issues.numWarnings,K.issues.numInfos],[0,0,0],JSON.stringify(K.issues));
const j=JSON.parse(raw.subarray(20,20+raw.readUInt32LE(12)));
assert.equal(j.asset.version,'2.0');assert.deepEqual(j.buffers.map(b=>b.uri),[undefined]);assert.equal(j.textures?.length??0,0);assert.equal(j.animations?.length??0,0);
const {scene,animations}=await new GLTFLoader().parseAsync(raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength),'');
assert.equal(animations.length,0);scene.updateMatrixWorld(true);
const inclined=scene.getObjectByName('INCLINED_SECTION_ORIGIN');assert.ok(inclined);
const INV=inclined.matrixWorld.clone().invert();
const V=(x,y,z)=>new Vector3(x,z,-y);
const local=p=>p.clone().applyMatrix4(INV);
function inModel(label){
 const root=scene.getObjectByName(label);assert.ok(root,label);
 const m=[];root.traverse(x=>{if(x.isMesh){m.push(x);x.material.side=DoubleSide;}});
 assert.ok(m.length);return m;
}
const rays=(o,d,L,objs)=>new Raycaster(V(...o).applyMatrix4(inclined.matrixWorld),V(...d).transformDirection(inclined.matrixWorld),0,L).intersectObjects(objs,false)[0];
const down=[0,0,-1],ro=inModel('One_unbroken_sculpted_centre_haul_rope'),
  left=inModel('Continuous_left_section_rail_head_web_and_foot'),right=inModel('Continuous_right_section_rail_head_web_and_foot');
let rope=0,rails=0,bore=0,profile=0;
const centered=[],gaps=[],height=[];
const sz=Math.acos(V(0,1,0).transformDirection(inclined.matrixWorld).dot(V(0,1,0)))*180/Math.PI;
assert.ok(sz>12.9999&&sz<13.0001);
for(let j=-43;j<=43;j++){
 const y=j*.0202;
 for(const x of [-.011,0,.011]){
  const h=rays([x,y,.395],down,.070,ro);
  assert.ok(h&&local(h.point).y>.367&&local(h.point).y<.3741);rope++;
 }
 for(const [x,track] of [[-.472,left],[.472,right]]){
  const h=rays([x,y,.434],down,.09,track);
  assert.ok(h&&Math.abs(local(h.point).y-.395)<.000003);rails++;
 }
}
for(const [index,Y] of [-.605,0,.605].entries()){
 const sh=inModel('CONCAVE_GUIDE_ROLLER_'+(index+1));
 for(const h of [-.012,0,.012])for(let m=-10;m<=10;m++){
  const v=[m*.00195,Y+h,.35111];
  const a=rays(v,down,.056,ro),b=rays(v,down,.056,sh);
  assert.ok(a&&b);
  const gap=(b.distance-a.distance)*1000;
  assert.ok(gap>.05&&gap<3.1,[index, h,m,gap]);gaps.push(gap);profile++;
  if(h===0&&m===0){assert.ok(gap<.5);centered.push(gap);}
 }
 const c=rays([0,Y,.41],down,.165,sh);
 for(const x of [-.046,.046]){
  const h=rays([x,Y,.41],down,.165,sh);
  const d=(c.distance-h.distance)*1000;assert.ok(d>32);height.push(d);
 }
 for(const dy of [-.013,0,.013])for(const dz of [-.013,0,.013])for(const u of [-1,1]){
  assert.equal(rays([u*.071,Y+dy,.216+dz],[-u,0,0],.143,sh),undefined);bore++;
 }
}
console.log(JSON.stringify({sha256:createHash('sha256').update(raw).digest('hex'),bytes:raw.length,
 triangles:K.info.totalTriangleCount,vertices:K.info.totalVertexCount,drawCalls:K.info.drawCallCount,
 meshes:j.meshes.length,materials:j.materials.length,animations:0,issues:K.issues,rope,rails,bore,profile,centredTangencyMm:centered,
 withinTroughMm:[Math.min(...gaps),Math.max(...gaps)],shoulderDepthMm:[Math.min(...height),Math.max(...height)]},null,2));
