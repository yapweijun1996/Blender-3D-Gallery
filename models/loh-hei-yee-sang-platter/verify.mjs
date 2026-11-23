import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { validateBytes } from 'gltf-validator';

const load = name => readFile(new URL(name, import.meta.url));
const [source, glb, preview, metaBytes] = await Promise.all([
  load('loh-hei-yee-sang-platter.blend'),
  load('exports/loh-hei-yee-sang-platter.glb'),
  load('previews/studio.webp'),
  load('metadata.json'),
]);
const meta = JSON.parse(metaBytes);
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const report = await validateBytes(new Uint8Array(glb), { uri: meta.export });
assert.equal(report.issues.messages.length, 0, JSON.stringify(report.issues));
assert.equal(glb.length, meta.metrics.glb_bytes);
assert.ok(glb.length <= 800 * 1024);
assert.equal(digest(glb), meta.metrics.glb_sha256);
assert.equal(digest(source), meta.metrics.source_sha256);
assert.equal(digest(preview), meta.metrics.preview_sha256);
assert.ok(preview.length < 60 * 1024 && preview.toString('ascii', 8, 12) === 'WEBP');
assert.equal(report.info.totalTriangleCount, meta.metrics.triangles);
assert.ok(report.info.totalTriangleCount < 20000);
assert.equal(report.info.totalVertexCount, meta.metrics.vertices);
assert.equal(report.info.animationCount, 1);
assert.equal(report.info.hasTextures, false);

const document = JSON.parse(glb.subarray(20, 20 + glb.readUInt32LE(12)));
assert.ok(document.buffers.every(buffer => !buffer.uri), 'no external buffers');
assert.equal(document.animations.length, 1);
assert.equal(document.meshes.length, meta.metrics.meshes);
const [clip] = document.animations;
assert.equal(clip.name, 'LOH_HEI_TOSS');
assert.equal(clip.channels.length, 46);
const groups = new Map();
for (const {target} of clip.channels) {
  const name = document.nodes[target.node].name;
  const paths = groups.get(name) ?? [];
  paths.push(target.path);
  groups.set(name, paths);
}
const ingredients = ['Carrot','Cucumber','Fish_slices','Pickled_ginger','Pillow_cracker','Pomelo','White_radish'];
assert.deepEqual([...groups.keys()].sort(), [...ingredients.flatMap(k => [k+'_parcel_1',k+'_parcel_2',k+'_parcel_3']), 'Left_paired_chopsticks', 'Right_paired_chopsticks'].sort());
assert.ok([...groups.values()].every(paths => paths.sort().join(',') === 'rotation,translation'));
assert.equal(Math.min(...clip.samplers.map(s => document.accessors[s.input].min[0])), 0);
assert.ok(Math.abs(Math.max(...clip.samplers.map(s => document.accessors[s.input].max[0])) - 50/24) < 1e-5);
console.log(JSON.stringify({
  model: meta.id, triangles: report.info.totalTriangleCount, fileBytes: glb.length,
  clip: clip.name, animatedNodes: groups.size, animationSeconds: 50/24,
  embeddedBuffers: document.buffers.length, issues: report.issues
}, null, 2));
