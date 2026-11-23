import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
const id='ramadan-bazaar-air-balang-stall',load=n=>readFile(new URL(n,import.meta.url));
const [b,src,img,json]=await Promise.all([load('exports/'+id+'.glb'),load(id+'.blend'),load('previews/studio.webp'),load('metadata.json')]);
const m=JSON.parse(json),sha=x=>createHash('sha256').update(x).digest('hex');
const r=await validateBytes(b,{uri:m.export});assert.equal(r.issues.messages.length,0,JSON.stringify(r.issues));
const jsonEnd=20+b.readUInt32LE(12),g=JSON.parse(b.subarray(20,jsonEnd));
assert.equal(g.asset.version,'2.0');assert.ok(g.buffers.every(v=>!v.uri));
for(const k of ['images','cameras','lights','skins'])assert.equal(g[k]?.length??0,0,k);
assert.equal(g.animations.length,1);
const clip=g.animations[0];assert.equal(clip.name,'AIR_BALANG_POUR');
assert.equal(clip.channels.length,3);
const snap=v=>Number(v.toFixed(5));
const actual={};
function rows(id,n){
 const a=g.accessors[id],w=g.bufferViews[a.bufferView], off=jsonEnd+8+(w.byteOffset??0)+(a.byteOffset??0);
 assert.equal(a.componentType,5126);assert.equal(a.type,['','SCALAR','','VEC3','VEC4'][n]);
 return Array.from({length:a.count},(_,i)=>Array.from({length:n},(_,j)=>b.readFloatLE(off+i*(w.byteStride??n*4)+4*j)));
}
for(const ch of clip.channels){
 const n=g.nodes[ch.target.node],s=clip.samplers[ch.sampler], ts=rows(s.input,1).map(t=>t[0]);
 const v=rows(s.output,ch.target.path==='rotation'?4:3);
 assert.equal(ts[0],0);assert.equal(ts.at(-1),2.25);assert.equal(v.length,ts.length);
 const ar=v.map(t=>snap(ch.target.path==='rotation'?t[0]:t[1]));
 const near=ts.findIndex(t=>Math.abs(t-1.25)<1e-5);
 const mid=near===-1?null:ar[near];
 actual[n.name]={target:ch.target.path,anchor:n.translation.map(snap),start:ar[0],middle:mid,end:ar.at(-1),max:Math.max(...ar)};
}
assert.equal(actual.AIR_BALANG_TAP_LEVER.target,'rotation');
assert.deepEqual(actual.AIR_BALANG_TAP_LEVER.anchor,[-.6,1.27,.303]);
assert.equal(actual.AIR_BALANG_TAP_LEVER.start,0);assert.equal(actual.AIR_BALANG_TAP_LEVER.end,0);
assert.ok(Math.abs(actual.AIR_BALANG_TAP_LEVER.max-Math.sin(.87/2))<.00002);
assert.deepEqual(actual.AIR_BALANG_STREAM,{target:'scale',anchor:[-.6,1.159,.329],start:.001,middle:actual.AIR_BALANG_STREAM.middle,end:.001,max:1});
assert.ok(actual.AIR_BALANG_STREAM.middle===null||actual.AIR_BALANG_STREAM.middle===1);
assert.deepEqual(actual.AIR_BALANG_CUP_FILL,{target:'scale',anchor:[-.6,.996,.329],start:.01,middle:.57,end:.96,max:.96});
assert.equal(img.toString('ascii',0,4),'RIFF');assert.equal(img.toString('ascii',8,12),'WEBP');
const info=r.info, measured={glb_bytes:b.length,glb_sha256:sha(b),source_sha256:sha(src),preview_sha256:sha(img),preview_bytes:img.length,triangles:info.totalTriangleCount,vertices:info.totalVertexCount,meshes:g.meshes.length,materials:g.materials.length,draw_calls:info.drawCallCount,animations:1,maximum_texture_dimension_px:0};
assert.deepEqual(measured,Object.fromEntries(Object.keys(measured).map(k=>[k,m.metrics[k]])));
console.log(JSON.stringify({id,...measured,clip:clip.name,actual,issues:r.issues}));
