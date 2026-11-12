import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { loadCatalog } from '../scripts/catalog.mjs';
const folder = 'models/mall-queue-stanchions';
const expected = ['mall-queue-post', 'mall-queue-short', 'mall-queue-long'];
const catalog = loadCatalog();
const collection = catalog.collections.find(item => item.id === 'mall-queue-stanchions');
test('queue kit registers independent post and short/long bays', () => {
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
    assert.ok(source.editable_parts >= 10);
    assert.ok(fs.statSync(folder + '/' + metadata.paths.source).size > 10000);
    const thumbnail = fs.readFileSync(folder + '/' + metadata.paths.preview);
    assert.equal(thumbnail.subarray(0,4).toString(), 'RIFF');
    assert.equal(thumbnail.subarray(8,12).toString(), 'WEBP');
    assert.ok(thumbnail.length < 150 * 1024);
  });
}
test('short, long and turned layouts align measured belt endpoints with post sockets', () => {
  const reports = JSON.parse(fs.readFileSync(folder + '/reports/assets.json'));
  const layouts = JSON.parse(fs.readFileSync(folder + '/layouts.json'));
  for (const example of layouts.examples) {
    assert.equal(new Set(example.posts.map(p => p.join(','))).size, example.posts.length);
    for (const link of example.belts) {
      const report = reports.find(r => r.id === link.variant);
      const [a,b] = link.posts.map(i => example.posts[i]);
      const dx=b[0]-a[0], dz=b[2]-a[2], length=Math.hypot(dx,dz);
      assert.ok(Math.abs(length-report.spacing)<1e-6);
      for (const [index,x] of [report.modules.MODULE_Belt.min[0],report.modules.MODULE_Belt.max[0]].entries()) {
        const endpoint=[link.position[0]+Math.cos(link.rotationY)*x, .905, link.position[2]-Math.sin(link.rotationY)*x];
        const post=index===0?a:b, sign=index===0?1:-1;
        assert.ok(Math.abs(endpoint[0]-(post[0]+sign*dx/length*.073))<1e-5);
        assert.ok(Math.abs(endpoint[2]-(post[2]+sign*dz/length*.073))<1e-5);
      }
      assert.ok(Math.abs(report.modules.MODULE_Post_Right.origin[0]-report.modules.MODULE_Post_Left.origin[0]-length)<1e-5);
    }
  }
});
