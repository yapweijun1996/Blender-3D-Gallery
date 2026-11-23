import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { validateBytes } from 'gltf-validator';

const load = name => readFile(new URL(name, import.meta.url));
const [source, glb, preview, raw] = await Promise.all([
  load('market-restock-mini-lorry.blend'), load('exports/market-restock-mini-lorry.glb'),
  load('previews/studio.webp'), load('metadata.json'),
]);
const meta=JSON.parse(raw), hash=b=>createHash('sha256').update(b).digest('hex');
const report=await validateBytes(glb,{uri:meta.export});
assert.equal(report.issues.messages.length,0,JSON.stringify(report.issues));
const d=JSON.parse(glb.subarray(20,20+glb.readUInt32LE(12)));
assert.equal(d.asset.version,'2.0');
assert.ok(d.buffers.every(b=>!b.uri), 'no external resources');
for (const key of ['animations','images','cameras','skins']) assert.equal(d[key]?.length??0,0,key);
assert.equal(d.nodes.filter(n=>n.name.startsWith('Slatted crate ')).length,6);
assert.equal(new Set(d.nodes.filter(n=>n.name.startsWith('Slatted crate ')).map(n=>n.mesh)).size,2);
const tyreNodes=d.nodes.filter(n=>/^(?:Front|Rear) (?:Left|Right) \| Rubber tyres/.test(n.name));
assert.equal(tyreNodes.length,4);
assert.equal(new Set(tyreNodes.map(n=>n.mesh)).size,1);
assert.equal(preview.toString('ascii',0,4),'RIFF');
assert.equal(preview.toString('ascii',8,12),'WEBP');
const result={
  glb_bytes:glb.length, glb_sha256:hash(glb), source_sha256:hash(source),
  preview_sha256:hash(preview),preview_bytes:preview.length, triangles:report.info.totalTriangleCount,
  vertices:report.info.totalVertexCount, meshes:d.meshes.length,
  draw_calls:report.info.drawCallCount,materials:d.materials.length, animations:0,
  maximum_texture_dimension_px:0,
};
assert.deepEqual(result, Object.fromEntries(Object.keys(result).map(k=>[k,meta.metrics[k]])));
console.log(JSON.stringify({id:meta.id,...result,issues:report.issues}));
