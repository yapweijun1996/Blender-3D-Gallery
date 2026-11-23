import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { validateBytes } from 'gltf-validator';

const id = 'wooden-mooncake-mould-workboard';
const load = name => readFile(new URL(name, import.meta.url));
const [buffer, source, webp] = await Promise.all([
  load('exports/' + id + '.glb'), load(id + '.blend'), load('previews/studio.webp')
]);
const sha = b => createHash('sha256').update(b).digest('hex');
const report = await validateBytes(buffer, {uri: id + '.glb'});
assert.equal(report.issues.messages.length, 0, JSON.stringify(report.issues));
const g = JSON.parse(buffer.subarray(20, 20 + buffer.readUInt32LE(12)));
assert.equal(g.asset.version, '2.0');
assert.ok(g.buffers.every(buf => !buf.uri));
for (const key of ['animations', 'images', 'cameras', 'lights', 'skins']) {
  assert.equal(g[key]?.length ?? 0, 0, key);
}
for (const name of ['WORKBOARD', 'HAND MOULD', 'STAMPED CAKE', 'COTTON', 'DUST BRUSH',
                    'Hardwood body with scalloped wall', 'Fluted pastry with X-mirrored']) {
  assert.ok(g.nodes.some(node => node.name?.startsWith(name)), name);
}
assert.equal(webp.toString('ascii', 0, 4), 'RIFF');
assert.equal(webp.toString('ascii', 8, 12), 'WEBP');
const measured = {
  glb_bytes: buffer.length,
  glb_sha256: sha(buffer),
  source_sha256: sha(source),
  preview_sha256: sha(webp),
  preview_bytes: webp.length,
  triangles: report.info.totalTriangleCount,
  vertices: report.info.totalVertexCount,
  meshes: g.meshes.length,
  materials: g.materials.length,
  draw_calls: report.info.drawCallCount,
  animations: 0,
  maximum_texture_dimension_px: 0,
};
assert.ok(measured.triangles < 35000 && measured.glb_bytes < 650000);
if (!process.argv.includes('--measure')) {
  const metadata = JSON.parse(await load('metadata.json'));
  assert.deepEqual(measured, Object.fromEntries(Object.keys(measured).map(k => [k,metadata.metrics[k]])));
  assert.equal(metadata.id, id);
}
console.log(JSON.stringify({id,...measured,issues:report.issues}));
