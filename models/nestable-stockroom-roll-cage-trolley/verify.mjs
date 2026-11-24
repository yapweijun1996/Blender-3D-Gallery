import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Box3,Raycaster,Vector3} from 'three';
const id='nestable-stockroom-roll-cage-trolley';
const bytes=await readFile(process.argv[2]??new URL('./exports/'+id+'.glb',import.meta.url));
const raw=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const k=await validateBytes(new Uint8Array(bytes),{uri:id+'.glb'});
for(const key of ['numErrors','numWarnings','numInfos','numHints'])assert.equal(k.issues[key],0,JSON.stringify(k.issues));
assert.deepEqual(raw.buffers.map(x=>x.uri),[undefined]);
for(const key of ['images','animations','cameras'])assert.equal(raw[key]?.length??0,0);
const {scene:model}=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
model.updateMatrixWorld(true);
const receiver=model.getObjectByName('RECEIVER_CAGE_SAME_SKU');
const nested=model.getObjectByName('NESTED_CAGE_SAME_SKU');
const exhibit=model.getObjectByName('NESTABLE_STOCKROOM_ROLL_CAGE_DISPLAY');
assert.ok(exhibit&&receiver&&nested&&receiver.parent===nested.parent);
const box=o=>new Box3().setFromObject(o,true);
const matches=(root,p)=>{const a=[];root.traverse(n=>{if(n.isMesh&&n.name.replace(/^NESTED_COPY_/,'').startsWith(p))a.push(n)});return a;};
const cast=(at,v,obj,far)=>new Raycaster(at,v,0,far).intersectObjects(obj,false)[0];
const a=box(receiver),b=box(nested);
const overlap=Math.min(a.max.z,b.max.z)-Math.max(a.min.z,b.min.z);
assert.ok(Math.abs(overlap-.439)<.0002);
const physical=(root)=>{
 const x=new Map();
 root.traverse(o=>{if(o.isMesh)x.set(o.geometry.uuid,(x.get(o.geometry.uuid)??0)+1)});
 return [...x].sort(([a],[b])=>a.localeCompare(b));
};
assert.deepEqual(physical(receiver),physical(nested));
const ground=matches(model,'Quiet_textured_stockroom_exhibit_plinth');
assert.equal(ground.length,1);
let holes=0;const wheel=[];
for(const [root,off] of [[receiver,.274],[nested,-.111]]){
 const tires=matches(root,'Seated_black_tire_on_independent_caster');
 const casters=tires.map(t=>box(t));assert.equal(tires.length,4);
 for(const w of casters){
   const c=w.getCenter(new Vector3());
   const h=cast(new Vector3(c.x,.099,c.z),new Vector3(0,-1,0),ground,.09);
   assert.ok(h&&Math.abs(h.point.y-w.min.y)<2.5e-5);
   wheel.push((w.min.y-h.point.y)*1000);
 }
 const grid=matches(root,'Open_side_grid');assert.equal(grid.length,50);
 for(const i of [1,3,5,8,10])for(const j of [2,5,8,11])for(const s of [-1,1]){
   const y=-.398+(i+.5)*(.388+.398)/12,z=.282+(j+.5)*1.218/15;
   const c=cast(new Vector3(s*(.237-.19*y+.038),z,-y-off),new Vector3(-s,0,0),grid,.087);
   assert.equal(c,undefined);holes++;
 }
 assert.equal(matches(root,'Upper_deck_keeper').length,2);
 assert.equal(matches(root,'Rested_platform_inner_eye').length,2);
 assert.equal(matches(root,'Continuous_fixed_common_pin').length,1);
}
const bbox=box(model),info=k.info;
console.log(JSON.stringify({sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,issues:k.issues,triangles:info.totalTriangleCount,vertices:info.totalVertexCount,drawCalls:info.drawCallCount,meshes:raw.meshes.length,materials:raw.materials.length,sharedMeshIdentity:true,overlapM:overlap,latticeRays:holes,groundedWheels:wheel,bounds:[bbox.min.toArray(),bbox.max.toArray()]},null,2));
