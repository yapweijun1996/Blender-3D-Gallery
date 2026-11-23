import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { validateBytes } from 'gltf-validator';

const load = (name) => readFile(new URL(name, import.meta.url));
const [source, glb, preview, json] = await Promise.all([
  load('mall-claw-prize-machine.blend'),
  load('exports/mall-claw-prize-machine.glb'),
  load('previews/studio.webp'),
  load('metadata.json'),
]);
const metadata = JSON.parse(json);
const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');
const report = await validateBytes(new Uint8Array(glb), { uri: 'mall-claw-prize-machine.glb' });
assert.equal(report.issues.numErrors, 0, JSON.stringify(report.issues));
assert.equal(report.issues.numWarnings, 0, JSON.stringify(report.issues));
assert.equal(glb.length, metadata.metrics.glb_bytes);
assert.ok(glb.length <= 5 * 1024 * 1024);
assert.equal(digest(glb), metadata.metrics.glb_sha256);
assert.equal(digest(source), metadata.metrics.source_sha256);
assert.equal(digest(preview), metadata.metrics.preview_sha256);
assert.ok(preview.length <= 150 * 1024 && preview.toString('ascii', 8, 12) === 'WEBP');
assert.equal(report.info.totalTriangleCount, metadata.metrics.triangles);
assert.ok(report.info.totalTriangleCount <= 100000);
assert.equal(report.info.totalVertexCount, metadata.metrics.vertices);
assert.equal(report.info.drawCallCount, metadata.metrics.meshes);
assert.equal(report.info.materialCount, metadata.metrics.materials);
assert.equal(report.info.animationCount, 0);
assert.equal(report.info.hasTextures, false);
console.log(JSON.stringify({ asset: metadata.id, issues: report.issues, info: report.info }, null, 2));
