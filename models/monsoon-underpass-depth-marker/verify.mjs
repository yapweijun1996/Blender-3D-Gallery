import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
const id='monsoon-underpass-depth-marker',load=n=>readFile(new URL(n,import.meta.url));
const [b,src,img,json]=await Promise.all([load('exports/'+id+'.glb'),load(id+'.blend'),load('previews/studio.webp'),load('metadata.json')]);
const m=JSON.parse(json),sha=x=>createHash('sha256').update(x).digest('hex');
const report=await validateBytes(b,{uri:m.export});assert.equal(report.issues.messages.length,0,JSON.stringify(report.issues));
const g=JSON.parse(b.subarray(20,20+b.readUInt32LE(12)));
assert.equal(g.asset.version,'2.0');assert.ok(g.buffers.every(v=>!v.uri));
for(const p of ['animations','images','cameras','lights','skins'])assert.equal(g[p]?.length??0,0,p);
for(const key of ['Cropped underpass roadway','Open recessed drain','Removable ruler housing','Bilingual labels']){
 assert.ok(g.nodes.some(x=>x.name.startsWith(key)),key);
}
assert.equal(img.toString('ascii',0,4),'RIFF');assert.equal(img.toString('ascii',8,12),'WEBP');
const info=report.info,measured={glb_bytes:b.length,glb_sha256:sha(b),source_sha256:sha(src),preview_sha256:sha(img),preview_bytes:img.length,triangles:info.totalTriangleCount,
 vertices:info.totalVertexCount,meshes:g.meshes.length,materials:g.materials.length,draw_calls:info.drawCallCount,animations:0,maximum_texture_dimension_px:0};
assert.deepEqual(measured,Object.fromEntries(Object.keys(measured).map(k=>[k,m.metrics[k]])));
console.log(JSON.stringify({id,...measured,issues:report.issues}));
