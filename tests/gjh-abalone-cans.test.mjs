import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { loadCatalog } from '../scripts/catalog.mjs';

const folder = 'models/gjh-abalone-cans';
const cans = {
  'gjh-can-new-zealand-abalone': ['ASSET_GJHCanNewZealandAbalone', 'New Zealand', '425g'],
  'gjh-can-australia-abalone': ['ASSET_GJHCanAustraliaAbalone', 'Australia', '425g'],
  'gjh-can-south-africa-abalone': ['ASSET_GJHCanSouthAfricaAbalone', 'South Africa', '425g'],
  'gjh-can-mexico-abalone': ['ASSET_GJHCanMexicoAbalone', 'Mexico', '454g'],
};
const catalog = loadCatalog();
const collection = catalog.collections.find(c => c.id === 'gjh-abalone-cans');
const report = JSON.parse(fs.readFileSync(`${folder}/reports/assets.json`));
const parts = ['CanBody', 'TopSeam', 'BottomSeam', 'Lid', 'PullTabPlate', 'PullTabRing', 'Label'];
const readGlb = bytes => JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));

test('four origin variants are registered with unique slugs and no download', () => {
  assert.deepEqual(collection.assets.map(a => a.id), Object.keys(cans));
  for (const asset of collection.assets) {
    assert.equal(asset.downloadable, false);
    assert.equal(asset.root, cans[asset.id][0]);
    assert.match(asset.license, /no independent licence document/i);
  }
});

for (const [id, [rootName, origin, pack]] of Object.entries(cans)) {
  test(`${id}: measured metadata matches the exported GLB`, () => {
    const bytes = fs.readFileSync(`${folder}/exports/${id}.glb`);
    const metadata = JSON.parse(fs.readFileSync(`${folder}/metadata/${id}.json`));
    const measured = report.find(r => r.id === id);
    assert.equal(metadata.metrics.glb_bytes, bytes.length);
    assert.equal(metadata.metrics.sha256, createHash('sha256').update(bytes).digest('hex'));
    assert.equal(measured.sha256, metadata.metrics.sha256);
    assert.deepEqual(metadata.validation, { errors: 0, warnings: 0, validator: metadata.validation.validator });
    assert.equal(metadata.product.origin, origin);
    assert.equal(metadata.product.pack_size, pack);
    assert.ok(metadata.name_zh.endsWith('鲍鱼罐头'));
    assert.equal(Object.keys(metadata.product.source_images).length, 2);
  });

  test(`${id}: self-contained GLB with one embedded JPEG label and the expected parts`, () => {
    const bytes = fs.readFileSync(`${folder}/exports/${id}.glb`);
    const json = readGlb(bytes);
    assert.ok(json.buffers.every(b => !b.uri));
    assert.equal(json.images.length, 1);
    assert.equal(json.images[0].mimeType, 'image/jpeg');
    const names = json.nodes.map(n => n.name);
    assert.ok(names.includes(rootName));
    for (const part of parts) assert.ok(names.includes(part), `${id} missing ${part}`);
    const label = json.meshes[json.nodes.find(n => n.name === 'Label').mesh];
    assert.ok(label.primitives[0].attributes.TEXCOORD_0 !== undefined);
    const position = json.accessors[json.meshes[json.nodes.find(n => n.name === 'CanBody').mesh].primitives[0].attributes.POSITION];
    assert.ok(position.max[1] > 0.1 && position.max[1] < 0.13, 'metre-scale height');
    assert.ok(bytes.length < 600000);
  });
}
