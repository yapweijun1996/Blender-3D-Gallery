import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
const id='shophouse-retractable-fabric-awning';
const read=k=>readFile(new URL(k,import.meta.url));
const [glb,blend,webp]=await Promise.all([read('exports/'+id+'.glb'),read(id+'.blend'),read('previews/studio.webp')]);
const sha=b=>createHash('sha256').update(b).digest('hex');
const rep=await validateBytes(glb,{uri:id+'.glb'});
assert.equal(rep.issues.messages.length,0,JSON.stringify(rep.issues));
const len=glb.readUInt32LE(12),j=JSON.parse(glb.subarray(20,20+len)), bin=glb.subarray(28+len);
assert.equal(j.asset.version,'2.0');assert.ok(j.buffers.every(x=>!x.uri));
for(const k of ['images','cameras','skins','textures'])assert.equal(j[k]?.length??0,0,k);
assert.equal(j.animations.length,1); const clip=j.animations[0];
assert.equal(clip.name,'AWNING_FOLD_IN');
assert.equal(clip.channels.length,9);
const expected={
 AWNING_FRONT_BAR:['translation'],
 AWNING_FABRIC:['scale'],
 AWNING_ROLLER:['rotation'],
 AWNING_L_PROXIMAL:['rotation'],
 AWNING_L_DISTAL:['rotation','translation'],
 AWNING_R_PROXIMAL:['rotation'],
 AWNING_R_DISTAL:['rotation','translation'],
};
const actual={};
function values(acc){
 const a=j.accessors[acc],v=j.bufferViews[a.bufferView],stride={SCALAR:1,VEC3:3,VEC4:4}[a.type]*4;
 assert.equal(a.componentType,5126);assert.ok(!v.byteStride||v.byteStride===stride);
 return Array.from({length:a.count},(_,k)=>Array.from({length:stride/4},(_,i)=>bin.readFloatLE((v.byteOffset||0)+(a.byteOffset||0)+k*stride+i*4)));
}
for(const {sampler,target} of clip.channels){
 const n=j.nodes[target.node],p=target.path,s=clip.samplers[sampler];
 assert.ok(Number.isInteger(n.mesh));
 const times=values(s.input).flat();assert.ok(Math.abs(times.at(-1)-2.4)<2e-6&&times[0]===0);
 assert.ok(times.every((t,i)=>!i||times[i-1]<t));
 const data=values(s.output);assert.equal(data.length,times.length);
 if(n.name==='AWNING_FABRIC'){
  assert.equal(p,'scale');assert.ok(Math.abs(data.at(-1)[2]-.102/.777)<2e-6);
  for(const v of data){assert.equal(v[0],1);assert.equal(v[1],1);}
 }
 if(n.name==='AWNING_FRONT_BAR')assert.ok(Math.abs(Math.hypot(...data[0].map((v,i)=>v-data.at(-1)[i]))-.675)<2e-6);
 (actual[n.name]??=[]).push(p);
}
for(const value of Object.values(actual))value.sort();
assert.deepEqual(actual,expected);
assert.equal(webp.toString('ascii',0,4),'RIFF');assert.equal(webp.toString('ascii',8,12),'WEBP');
const m={glb_bytes:glb.length,glb_sha256:sha(glb),source_sha256:sha(blend),preview_sha256:sha(webp),preview_bytes:webp.length,
 triangles:rep.info.totalTriangleCount,vertices:rep.info.totalVertexCount,draw_calls:rep.info.drawCallCount,meshes:j.meshes.length,
 materials:j.materials.length,animations:1,maximum_texture_dimension_px:0};
assert.ok(m.glb_bytes<210000&&m.triangles<12000);
if(!process.argv.includes('--measure')){
 const md=JSON.parse(await read('metadata.json'));
 assert.deepEqual(m,Object.fromEntries(Object.keys(m).map(k=>[k,md.metrics[k]])));
 assert.equal(md.id,id);
}
console.log(JSON.stringify({id,metrics:m,channels:actual,issues:rep.issues}));
