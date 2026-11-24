import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Box3,Raycaster,Vector3} from 'three';
const id='five-foot-way-cobbler-repair-stand';
const bytes=await readFile(process.argv[2]??new URL('./exports/'+id+'.glb',import.meta.url));
const gltf=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const k=await validateBytes(new Uint8Array(bytes),{uri:id+'.glb'});
for(const key of ['numErrors','numWarnings','numInfos','numHints'])assert.equal(k.issues[key],0,JSON.stringify(k.issues));
assert.deepEqual(gltf.buffers.map(x=>x.uri),[undefined]);
for(const key of ['images','animations','cameras'])assert.equal(gltf[key]?.length??0,0);
const {scene:model}=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
model.updateMatrixWorld(true);
for(const name of ['FIVE_FOOT_WAY_COBBLER_EXHIBIT','CAST_SHOE_LAST_MODULE','LOOSE_SHOE_FORM_SOLE','ROUNDED_PARKED_MALLET'])assert.ok(model.getObjectByName(name),name);
const matches=(prefix)=>{const a=[];model.traverse(n=>{if(n.isMesh&&n.name.startsWith(prefix))a.push(n)});return a;};
const cast=(at,vector,meshes,far=1.5)=>new Raycaster(at,vector,0,far).intersectObjects(meshes,false)[0];
const down=new Vector3(0,-1,0);
const fore=matches('Actual_raised_forefoot_tread');
const heel=matches('Actual_raised_heel_tread');
const field=matches('Dark_full_continuous_recessed_tread_field');
assert.equal(fore.length,16);assert.equal(heel.length,8);assert.ok(field.length);
function sole(x,y){
 // Same documented original sculpture pose, independent of the loader's axis adapter.
 const a=-22*Math.PI/180;
 const h=cast(new Vector3(.181+x*Math.cos(a)-y*Math.sin(a),.466,.065-x*Math.sin(a)-y*Math.cos(a)),down,[...fore,...heel,...field],.14);
 assert.ok(h,[x,y]);return h.point.y;
}
const relief=[];
for(const [offset,inc,rows,dy,target] of [[.010,.0142,8,.019,.0034],[-.117,.013,4,.014,.0031]]){
 for(let i=0;i<rows;i++)for(const sign of [-1,1]){
   const x=offset+inc*i;const r=sole(x,sign*dy)-sole(x,0);
   assert.ok(Math.abs(r-target)<.00005,[x,sign,r]);relief.push(r);
 }
}
const saddle=matches('True_open_square_saddle_socket');
assert.ok(saddle.length);
let open=0;
for(const dx of [-.014,0,.014])for(const dz of [-.014,0,.014]){
 assert.equal(cast(new Vector3(-.224+dx,.559,.051+dz),down,saddle,.076),undefined);open++;
}
const last=matches('Sculpted_closed_asymmetric_toe_heel_cast_shoe_last');
assert.ok(last.length&&last.some(n=>n.geometry.hasAttribute('color')));
const lastBox=last.reduce((box,n)=>box.union(new Box3().setFromObject(n,true)),new Box3());
assert.ok(Math.abs(lastBox.max.x-lastBox.min.x-.288)<.00015);
const bbox=new Box3().setFromObject(model,true);
const info=k.info;
console.log(JSON.stringify({sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,issues:k.issues,triangles:info.totalTriangleCount,vertices:info.totalVertexCount,drawCalls:info.drawCallCount,meshes:gltf.meshes.length,materials:gltf.materials.length,openSaddleRays:open,treadRays:relief.length,treadReliefMm:[Math.min(...relief)*1000,Math.max(...relief)*1000],bounds:[bbox.min.toArray(),bbox.max.toArray()]},null,2));
