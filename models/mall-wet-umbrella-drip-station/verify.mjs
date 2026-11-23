import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
const load=n=>readFile(new URL(n, import.meta.url));
const id='mall-wet-umbrella-drip-station';
const [b,src,img,raw]=await Promise.all([load('exports/'+id+'.glb'),load(id+'.blend'),load('previews/studio.webp'),load('metadata.json')]);
const m=JSON.parse(raw),digest=x=>createHash('sha256').update(x).digest('hex');
const r=await validateBytes(b,{uri:m.export});
assert.equal(r.issues.messages.length,0,JSON.stringify(r.issues));
const d=JSON.parse(b.subarray(20,20+b.readUInt32LE(12)));
assert.equal(d.asset.version,'2.0');
assert.ok(d.buffers.every(b=>!b.uri));
for(const k of ['animations','images','cameras','skins'])assert.equal(d[k]?.length??0,0,k);
for(const prefix of ['Open rounded long guide ','Open rounded compact guide ','Slatted tip cradle ']){
 const set=d.nodes.filter(n=>n.name.startsWith(prefix));
 assert.equal(set.length,4);
 assert.equal(new Set(set.map(n=>n.mesh)).size,1);
}
assert.equal(img.toString('ascii',0,4),'RIFF');
assert.equal(img.toString('ascii',8,12),'WEBP');
const actual={glb_bytes:b.length,glb_sha256:digest(b),source_sha256:digest(src),preview_sha256:digest(img),preview_bytes:img.length,
 triangles:r.info.totalTriangleCount,vertices:r.info.totalVertexCount,meshes:d.meshes.length,materials:d.materials.length,
 draw_calls:r.info.drawCallCount,animations:0,maximum_texture_dimension_px:0};
assert.deepEqual(actual,Object.fromEntries(Object.keys(actual).map(k=>[k,m.metrics[k]])));
console.log(JSON.stringify({id,...actual,guides:12,issues:r.issues}));
