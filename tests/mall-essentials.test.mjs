import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { loadCatalog } from '../scripts/catalog.mjs';
const folder = 'models/mall-essentials';
const expected = ['mall-directory-kiosk', 'mall-advertising-lightbox', 'mall-trash-bin', 'mall-display-shelf'];
const catalog = loadCatalog();
const collection = catalog.collections.find(item => item.id === 'mall-essentials');
test('mall essentials registers exactly the four requested fixtures', () => {
  assert.ok(collection);
  assert.deepEqual(collection.assets.map(asset => asset.id), expected);
});
for (const id of expected) {
  test(id + ' preserves provenance, measured export, source and thumbnail', () => {
    const asset = collection.assets.find(asset => asset.id === id);
    const metadata = JSON.parse(fs.readFileSync(folder + '/metadata/' + id + '.json'));
    const bytes = fs.readFileSync(folder + '/exports/' + id + '.glb');
    const gltf = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
    const report = JSON.parse(fs.readFileSync(folder + '/reports/assets.json')).find(r => r.id === id);
    const source = JSON.parse(fs.readFileSync(folder + '/reports/sources.json')).find(r => r.id === id);
    assert.equal(asset.downloadable, false);
    assert.match(asset.license, /redistribution terms have not been specified/);
    assert.equal(metadata.rights, asset.license);
    assert.equal(metadata.metrics.sha256, createHash('sha256').update(bytes).digest('hex'));
    assert.equal(metadata.metrics.glb_bytes, bytes.length);
    assert.equal(metadata.metrics.sha256, report.sha256);
    assert.equal(metadata.validation.errors, 0);
    assert.equal(metadata.validation.warnings, 0);
    assert.equal(metadata.status, 'validated');
    assert.ok(report.triangles > 0 && report.triangles <= 20000);
    assert.ok(bytes.length <= 700000 && report.primitives <= 8);
    assert.ok(Math.abs(report.bounds.min[1]) <= .001);
    assert.ok(gltf.nodes.some(node => node.name === asset.root));
    assert.equal(gltf.images?.length ?? 0, 0);
    assert.ok(gltf.buffers.every(buffer => !buffer.uri));
    assert.equal(gltf.cameras?.length ?? 0, 0);
    assert.equal(gltf.animations?.length ?? 0, 0);
    assert.equal(source.source_reopened, 'PASS');
    assert.ok(source.editable_parts > 10);
    assert.ok(fs.statSync(folder + '/' + metadata.paths.source).size > 10000);
    const thumbnail = fs.readFileSync(folder + '/' + metadata.paths.preview);
    assert.equal(thumbnail.subarray(0,4).toString(), 'RIFF');
    assert.equal(thumbnail.subarray(8,12).toString(), 'WEBP');
    assert.ok(thumbnail.length < 150 * 1024);
  });
}
