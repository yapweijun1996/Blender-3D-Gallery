import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Box3,Raycaster,Vector3} from 'three';
const id='traditional-congkak-board-display';
const bytes=await readFile(process.argv[2]??new URL('./exports/'+id+'.glb',import.meta.url));
const raw=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const v=await validateBytes(new Uint8Array(bytes),{uri:id+'.glb'});
for(const k of ['numErrors','numWarnings','numInfos','numHints'])assert.equal(v.issues[k],0,JSON.stringify(v.issues));
assert.deepEqual(raw.buffers.map(x=>x.uri),[undefined]);
for(const k of ['images','animations','cameras'])assert.equal(raw[k]?.length??0,0);
const {scene}=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
scene.updateMatrixWorld(true);
const board=scene.getObjectByName('CONGKAK_ORIGINAL_SOLID_BOARD'),
 plinth=scene.getObjectByName('SEPARATE_INTERPRETIVE_EXHIBIT_PLINTH'),
 seeds=scene.getObjectByName('STAGED_SPARSE_COUNTERS');
assert.ok(board&&plinth&&seeds);assert.equal(board.children.length,1);assert.equal(seeds.children.length,9);
const hit=(x,y,z=.188,d=new Vector3(0,-1,0),dist=.15)=>new Raycaster(new Vector3(x,z,-y),d,0,dist).intersectObject(board,true)[0]?.point.y;
const stats={village:0,house:0,wallRays:0,bottomRays:0};
const entries=[];
for(const x of [-.046,.046])for(const y of [-.276,-.184,-.092,0,.092,.184,.276])entries.push(['village',x,y,.0355,.042]);
for(const y of [-.404,.404])entries.push(['house',0,y,.068,.059]);
for(const [k,x,y,r,d] of entries){
 stats[k]++;
 const f=hit(x,y);assert.ok(Math.abs(f-(.168-d))<2e-6,[k,x,y,f].join());
 for(let q=0;q<12;q++){
  const a=q*Math.PI/6;
  const rr=k==='village'?[.43,.75]:[.43,.75,.94];
  for(const u of rr){
   const s=hit(x+u*r*Math.cos(a),y+u*r*Math.sin(a));
   assert.ok(s&&s>f&&s<.1678,[k,x,y,q,u,s].join());
   stats.wallRays++;
  }
 }
 const z=hit(x,y,.062,new Vector3(0,1,0),.020);
 assert.ok(Math.abs(z-.074)<2e-6);stats.bottomRays++;
}
const seat=[];
for(const item of seeds.children){
 const v=new Box3().setFromObject(item,true);
 const p=v.getCenter(new Vector3());const f=hit(p.x,-p.z);
 assert.ok(f&&f<v.max.y&&Math.abs(v.min.y-f)<.010);
 seat.push(v.min.y);
}
assert.equal(raw.images,undefined);assert.equal(raw.materials.some(x=>x.pbrMetallicRoughness?.baseColorTexture),false);
const bbox=new Box3().setFromObject(scene,true),i=v.info;
console.log(JSON.stringify({sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,issues:v.issues,triangles:i.totalTriangleCount,vertices:i.totalVertexCount,drawCalls:i.drawCallCount,meshes:raw.meshes.length,materials:raw.materials.length,stats,seedCount:seat.length,bounds:[bbox.min.toArray(),bbox.max.toArray()]},null,2));
