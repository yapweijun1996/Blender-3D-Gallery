import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { validateBytes } from 'gltf-validator';

const load = name => readFile(new URL(name, import.meta.url));
const [source, glb, preview, json] = await Promise.all([
  load('malaysia-rail-reload-counter.blend'), load('exports/malaysia-rail-reload-counter.glb'),
  load('previews/studio.webp'), load('metadata.json'),
]);
const meta = JSON.parse(json);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const report = await validateBytes(new Uint8Array(glb), { uri: meta.export });
assert.equal(report.issues.messages.length, 0, JSON.stringify(report.issues));
assert.equal(glb.length, meta.metrics.glb_bytes);
assert.ok(glb.length <= 280 * 1024);
assert.equal(hash(glb), meta.metrics.glb_sha256);
assert.equal(hash(source), meta.metrics.source_sha256);
assert.equal(hash(preview), meta.metrics.preview_sha256);
assert.equal(report.info.totalTriangleCount, meta.metrics.triangles);
assert.equal(report.info.totalVertexCount, meta.metrics.vertices);
assert.equal(report.info.drawCallCount, meta.metrics.draw_calls);
assert.equal(report.info.hasTextures, false);
const document = JSON.parse(glb.subarray(20, 20 + glb.readUInt32LE(12)));
assert.ok(document.buffers.every(buffer => !buffer.uri), 'no external resources');
assert.equal(document.animations.length, 1);
const [clip] = document.animations;
assert.equal(clip.name, 'RAIL_CARD_TAP');
assert.deepEqual(clip.channels.map(({target}) => [document.nodes[target.node].name, target.path])
  .map(([name,path]) => name+':'+path).sort(), [
    'RAIL_DEMO_CARD:rotation', 'RAIL_DEMO_CARD:translation', 'RAIL_READER_INDICATOR:translation',
  ]);
assert.equal(Math.min(...clip.samplers.map(s => document.accessors[s.input].min[0])), 0);
assert.equal(Math.max(...clip.samplers.map(s => document.accessors[s.input].max[0])), 2);
console.log(JSON.stringify({
  id: meta.id, clip: clip.name, seconds: 2, animatedChannels: clip.channels.length,
  bytes: glb.length, triangles: report.info.totalTriangleCount, issues: report.issues,
}, null, 2));
