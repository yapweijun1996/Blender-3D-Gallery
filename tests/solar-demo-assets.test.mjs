import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import validator from 'gltf-validator';
import { loadCatalog } from '../scripts/catalog.mjs';
import { solarSceneAssets } from '../src/solar/assets.js';

const hash = b => crypto.createHash('sha256').update(b).digest('hex');
function parse(bytes) {
  assert.equal(bytes.toString('ascii', 0, 4), 'glTF');
  const size = bytes.readUInt32LE(12), json = JSON.parse(bytes.subarray(20, 20 + size));
  return {json, bin: bytes.subarray(28 + size)};
}

test('optimized solar GLBs match current sources and retain every non-image buffer', async () => {
  const manifest = JSON.parse(fs.readFileSync('models/solar-demo/manifest.json'));
  const assets = solarSceneAssets(loadCatalog().collections.flatMap(c => c.assets));
  assert.equal(manifest.length, assets.length);
  assert.equal(new Set(manifest.map(a => a.id)).size, assets.length);
  let sourceTotal = 0, optimizedTotal = 0;
  for (const asset of assets) {
    const entry = manifest.find(a => a.id === asset.id);
    assert.ok(entry, asset.id);
    assert.equal(entry.source, asset.file);
    assert.equal(entry.file, `models/solar-demo/${asset.id}.glb`);
    const source = fs.readFileSync(entry.source), output = fs.readFileSync(entry.file);
    assert.equal(hash(source), entry.sourceSha256, `stale source for ${asset.id}`);
    assert.equal(hash(output), entry.sha256, `changed optimized file for ${asset.id}`);
    assert.equal(source.length, entry.originalBytes);
    assert.equal(output.length, entry.bytes);
    const report = await validator.validateBytes(new Uint8Array(output));
    assert.equal(report.issues.numErrors, 0, asset.id);
    assert.equal(report.issues.numWarnings, 0, asset.id);
    for (const resource of report.info.resources ?? []) {
      if (resource.image) assert.ok(resource.image.width <= 1024 && resource.image.height <= 1024, `${asset.id} texture exceeds 1K`);
    }
    const a = parse(source), b = parse(output);
    assert.equal(a.json.bufferViews.length, b.json.bufferViews.length);
    const images = new Set((a.json.images ?? []).map(i => i.bufferView));
    for (let i = 0; i < a.json.bufferViews.length; i++) {
      if (images.has(i)) continue;
      const x = a.json.bufferViews[i], y = b.json.bufferViews[i];
      assert.deepEqual(a.bin.subarray(x.byteOffset ?? 0, (x.byteOffset ?? 0) + x.byteLength), b.bin.subarray(y.byteOffset ?? 0, (y.byteOffset ?? 0) + y.byteLength), `${asset.id} buffer ${i}`);
    }
    for (const key of ['nodes','meshes','accessors','materials','textures','samplers','scenes','animations']) assert.deepEqual(b.json[key], a.json[key], `${asset.id} ${key}`);
    sourceTotal += source.length; optimizedTotal += output.length;
  }
  assert.ok(optimizedTotal < sourceTotal * 0.3, 'optimized set remains substantially smaller');
});
