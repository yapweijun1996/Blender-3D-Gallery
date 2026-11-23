import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
const id='mall-wheelchair-loan-station', load=n=>readFile(new URL(n,import.meta.url));
const [b,src,img,json]=await Promise.all([load('exports/'+id+'.glb'),load(id+'.blend'),load('previews/studio.webp'),load('metadata.json')]);
const m=JSON.parse(json),digest=x=>createHash('sha256').update(x).digest('hex');
const khronos=await validateBytes(b,{uri:m.export});
assert.equal(khronos.issues.messages.length,0,JSON.stringify(khronos.issues));
const g=JSON.parse(b.subarray(20,20+b.readUInt32LE(12)));
assert.equal(g.asset.version,'2.0');
assert.ok(g.buffers.every(v=>!v.uri));
for(const p of ['animations','images','cameras','skins','lights'])assert.equal(g[p]?.length??0,0,p);
for(const part of ['Low-profile docking bay','Bilingual loan and return sign','Collapsed chair frame','Upholstery and padded grips','Main and caster wheels','Cup tray and docking bumper']){
 assert.ok(g.nodes.some(n=>n.name.startsWith(part)),part);
}
assert.equal(img.toString('ascii',0,4),'RIFF');assert.equal(img.toString('ascii',8,12),'WEBP');
const info=khronos.info;
const actual={glb_bytes:b.length,glb_sha256:digest(b),source_sha256:digest(src),preview_sha256:digest(img),preview_bytes:img.length,triangles:info.totalTriangleCount,
 vertices:info.totalVertexCount,meshes:g.meshes.length,materials:g.materials.length,draw_calls:info.drawCallCount,animations:0,maximum_texture_dimension_px:0};
assert.deepEqual(actual,Object.fromEntries(Object.keys(actual).map(k=>[k,m.metrics[k]])));
console.log(JSON.stringify({id,...actual,issues:khronos.issues}));
