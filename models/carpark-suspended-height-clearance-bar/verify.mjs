import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Box3,Raycaster,Vector3} from 'three';
const id='carpark-suspended-height-clearance-bar';
const bytes=await readFile(process.argv[2]??new URL('./exports/'+id+'.glb',import.meta.url));
const gltf=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const k=await validateBytes(new Uint8Array(bytes),{uri:id+'.glb'});
for(const key of ['numErrors','numWarnings','numInfos','numHints'])assert.equal(k.issues[key],0,JSON.stringify(k.issues));
assert.deepEqual(gltf.buffers.map(x=>x.uri),[undefined]);
for(const key of ['images','animations','cameras'])assert.equal(gltf[key]?.length??0,0);
const {scene:model}=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
model.updateMatrixWorld(true);
for(const name of ['CARPARK_SUSPENDED_HEIGHT_CLEARANCE_BAR_EXHIBIT','INDEPENDENT_CONCRETE_ENTRANCE_CROSS_SECTION','BAR_AND_SEPARATE_ANCHOR_PLATE_ASSEMBLIES','TWO_GENUINELY_INTERLOCKED_CHAINS'])assert.ok(model.getObjectByName(name),name);
const matches=(prefix)=>{const a=[];model.traverse(n=>{if(n.isMesh&&n.name.startsWith(prefix))a.push(n)});return a;};
const cast=(at,v,mesh,far)=>new Raycaster(at,v,0,far).intersectObject(mesh,false)[0];
let actualInterlocks=0,through=0;
for(const [side,x] of [['LEFT',-1.135],['RIGHT',1.135]]){
 const rings=Array.from({length:6},(_,i)=>{
   const m=matches(side+'_'+i+'_CLOSED_');assert.equal(m.length,1);
   return m[0];
 });
 const bb=rings.map(m=>new Box3().setFromObject(m,true));
 for(let i=0;i<6;i++){
   const b=bb[i],c=b.getCenter(new Vector3()),d=b.getSize(new Vector3());
   assert.ok(d.y>.153&&d.y<.155);
   assert.ok(i%2===0?d.x>.100&&d.z<.026:d.z>.100&&d.x<.026);
   const from=(dy,u)=>i%2===0?new Vector3(x+u,c.y+dy,.602):new Vector3(x-.135,c.y+dy,.467+u);
   const direction=new Vector3(i%2===0?0:1,0,i%2===0?-1:0);
   for(const off of [-.012,0,.012]){
     assert.equal(cast(from(0,off),direction,rings[i],.27),undefined);
     through++;
   }
   if(i<5){
     const q=bb[i+1].min.y+.012-c.y;
     assert.ok(q>.04&&q<.042);
     assert.equal(cast(from(q,0),direction,rings[i],.27),undefined);
     assert.ok(cast(from(q,0),direction,rings[i+1],.27));
     actualInterlocks++;
   }
 }
}
assert.equal(matches('Roof_bolted_anchor_plate').length,2);
assert.equal(matches('Bar_bolted_eye_seat_plate').length,2);
assert.equal(matches('Real_overhead_concrete_anchorage_lintel').length,1);
const bbox=new Box3().setFromObject(model,true),info=k.info;
console.log(JSON.stringify({sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,issues:k.issues,triangles:info.totalTriangleCount,vertices:info.totalVertexCount,drawCalls:info.drawCallCount,meshes:gltf.meshes.length,materials:gltf.materials.length,actualInterlocks,openEyeRays:through,bounds:[bbox.min.toArray(),bbox.max.toArray()]},null,2));
