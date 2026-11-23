import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
const load=n=>readFile(new URL(n,import.meta.url)), id='mall-carpark-help-point';
const [b,src,img,raw]=await Promise.all([load('exports/'+id+'.glb'),load(id+'.blend'),load('previews/studio.webp'),load('metadata.json')]);
const m=JSON.parse(raw);
const digest=x=>createHash('sha256').update(x).digest('hex');
const kr=await validateBytes(b,{uri:m.export}); assert.equal(kr.issues.messages.length,0,JSON.stringify(kr.issues));
assert.equal(img.toString('ascii',0,4),'RIFF'); assert.equal(img.toString('ascii',8,12),'WEBP');
const jsonEnd=20+b.readUInt32LE(12),d=JSON.parse(b.subarray(20,jsonEnd));
assert.equal(d.asset.version,'2.0'); assert.ok(d.buffers.every(b=>!b.uri));
for(const p of ['images','cameras','skins'])assert.equal(d[p]?.length??0,0,p);
assert.equal(d.animations.length,1);
const [clip]=d.animations; assert.equal(clip.name,'CARPARK_HELP_PRESS');
assert.equal(clip.channels.length,2);
const animation={};
const precision=v=>Number(v.toFixed(5));
function floats(aid,width){
 const a=d.accessors[aid],vw=d.bufferViews[a.bufferView];
 assert.equal(a.componentType,5126);
 assert.equal(a.type,width===1?'SCALAR':'VEC3');
 return Array.from({length:a.count},(_,i)=>Array.from({length:width},(_,j)=>b.readFloatLE(jsonEnd+8+(vw.byteOffset??0)+(a.byteOffset??0)+i*(vw.byteStride??width*4)+4*j)));
}
for(const ch of clip.channels){
 const n=d.nodes[ch.target.node], s=clip.samplers[ch.sampler];
 assert.equal(ch.target.path,'translation');
 const times=floats(s.input,1).map(t=>t[0]);
 const values=floats(s.output,3);
 assert.equal(times[0],0); assert.equal(times.at(-1),1.5);
 assert.equal(times.length,values.length);
 animation[n.name]={start:values[0].map(precision),finish:values.at(-1).map(precision),minz:precision(Math.min(...values.map(v=>v[2]))),maxz:precision(Math.max(...values.map(v=>v[2])))};
 if(n.name==='CARPARK_HELP_BUTTON') assert.deepEqual(n.children.map(i=>d.nodes[i].name).sort(),['English key print','Malay key print']);
}
assert.deepEqual(animation,{
 CARPARK_HELP_BUTTON:{start:[0,.841,.223],finish:[0,.841,.223],minz:.211,maxz:.223},
 CARPARK_HELP_INDICATOR:{start:[0,.963,.171],finish:[0,.963,.197],minz:.171,maxz:.197},
});
const actual={glb_bytes:b.length,glb_sha256:digest(b),source_sha256:digest(src),preview_sha256:digest(img),preview_bytes:img.length,triangles:kr.info.totalTriangleCount,
 vertices:kr.info.totalVertexCount,meshes:d.meshes.length,materials:d.materials.length,draw_calls:kr.info.drawCallCount,animations:1,maximum_texture_dimension_px:0};
assert.deepEqual(actual,Object.fromEntries(Object.keys(actual).map(k=>[k,m.metrics[k]])));
console.log(JSON.stringify({id,...actual,clip:clip.name,animation,issues:kr.issues}));
