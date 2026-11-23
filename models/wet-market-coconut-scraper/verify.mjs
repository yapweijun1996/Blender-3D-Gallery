import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
const id='wet-market-coconut-scraper',load=n=>readFile(new URL(n,import.meta.url));
const [b,src,img,json]=await Promise.all([load('exports/'+id+'.glb'),load(id+'.blend'),load('previews/studio.webp'),load('metadata.json')]);
const m=JSON.parse(json),sha=x=>createHash('sha256').update(x).digest('hex');
const r=await validateBytes(b,{uri:m.export});assert.equal(r.issues.messages.length,0,JSON.stringify(r.issues));
const end=20+b.readUInt32LE(12),g=JSON.parse(b.subarray(20,end));assert.equal(g.asset.version,'2.0');assert.ok(g.buffers.every(v=>!v.uri));
for(const k of ['images','cameras','lights','skins'])assert.equal(g[k]?.length??0,0,k);
assert.equal(g.animations.length,1);const c=g.animations[0];assert.equal(c.name,'KELAPA_CRANK_TURN');assert.equal(c.channels.length,2);
const round=x=>Number(x.toFixed(5));
function values(id,n){
 const a=g.accessors[id],v=g.bufferViews[a.bufferView];assert.equal(a.componentType,5126);assert.equal(a.type,n===1?'SCALAR':'VEC4');
 return Array.from({length:a.count},(_,i)=>Array.from({length:n},(_,j)=>b.readFloatLE(end+8+(v.byteOffset??0)+(a.byteOffset??0)+i*(v.byteStride??n*4)+4*j)));
}
const samples={};
for(const ch of c.channels){
 assert.equal(ch.target.path,'rotation'); const node=g.nodes[ch.target.node],p=c.samplers[ch.sampler];
 const t=values(p.input,1).map(v=>v[0]), data=values(p.output,4);assert.equal(t[0],0);assert.equal(t.at(-1),2);assert.equal(t.length,data.length);
 assert.ok(data.every(q=>Math.abs(q[1])<1e-6&&Math.abs(q[2])<1e-6));
 let last=0;
 const a=data.map(q=>{let angle=2*Math.atan2(q[0],q[3]);while(angle-last>Math.PI)angle-=2*Math.PI;while(angle-last< -Math.PI)angle+=2*Math.PI;last=angle;return angle});
 assert.ok(Math.abs(a[0])<1e-6);
 const mid=t.findIndex(v=>Math.abs(v-23/24)<1e-5);assert.notEqual(mid,-1);
 samples[node.name]={anchor:node.translation.map(round),midDeg:Number((a[mid]*180/Math.PI).toFixed(3)),endDeg:Number((a.at(-1)*180/Math.PI).toFixed(3))};
}
assert.deepEqual(samples,{KELAPA_CRANK_HANDLE:{anchor:[.214,.235,-.074],midDeg:121.5,endDeg:270},KELAPA_SCRAPER_ROTOR:{anchor:[.097,.373,-.074],midDeg:-243,endDeg:-540}});
assert.equal(img.toString('ascii',0,4),'RIFF');assert.equal(img.toString('ascii',8,12),'WEBP');
const info=r.info,measured={glb_bytes:b.length,glb_sha256:sha(b),source_sha256:sha(src),preview_sha256:sha(img),preview_bytes:img.length,triangles:info.totalTriangleCount,vertices:info.totalVertexCount,meshes:g.meshes.length,materials:g.materials.length,draw_calls:info.drawCallCount,animations:1,maximum_texture_dimension_px:0};
assert.deepEqual(measured,Object.fromEntries(Object.keys(measured).map(k=>[k,m.metrics[k]])));
console.log(JSON.stringify({id,...measured,clip:c.name,samples,issues:r.issues}));
