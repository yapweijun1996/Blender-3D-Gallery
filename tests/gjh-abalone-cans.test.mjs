import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { loadCatalog, validateMetadata } from '../scripts/catalog.mjs';

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
// Decode a float VEC2 accessor from the GLB binary chunk (UV accessors carry no min/max).
function readVec2(bytes, json, accessor) {
  const jsonLength = bytes.readUInt32LE(12);
  const bin = bytes.subarray(20 + jsonLength + 8);
  const view = json.bufferViews[accessor.bufferView];
  const stride = view.byteStride ?? 8;
  const values = [];
  for (let i = 0; i < accessor.count; i++)
    values.push([bin.readFloatLE(view.byteOffset + (accessor.byteOffset ?? 0) + i * stride), bin.readFloatLE(view.byteOffset + (accessor.byteOffset ?? 0) + i * stride + 4)]);
  return values;
}

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

for (const [id, [rootName]] of Object.entries(cans)) {
  const bytes = fs.readFileSync(`${folder}/exports/${id}.glb`);
  const json = readGlb(bytes);
  const nodeMesh = name => json.meshes[json.nodes.find(n => n.name === name).mesh].primitives[0];
  const accessor = (primitive, key) => json.accessors[primitive.attributes[key]];

  test(`${id}: rolled seams are thin, proportionate and the label UVs stay near 0..1 without stretching`, () => {
    for (const name of ['TopSeam', 'BottomSeam']) {
      const position = accessor(nodeMesh(name), 'POSITION');
      assert.ok(position.max[1] - position.min[1] < 0.0055, `${name} height must stay under 5.5 mm`);
      assert.ok(position.max[0] < 0.0375 + 0.0030, `${name} must not bulge more than 3 mm past the body`);
    }
    const uv = readVec2(bytes, json, accessor(nodeMesh('Label'), 'TEXCOORD_0'));
    const us = uv.map(p => p[0]), vs = uv.map(p => p[1]);
    assert.ok(Math.min(...us) >= -0.001 && Math.max(...us) <= 1.001, 'u spans exactly one wrap');
    assert.ok(Math.max(...us) - Math.min(...us) > 0.99, 'u covers the whole circumference');
    assert.ok(Math.min(...vs) > -0.1 && Math.max(...vs) < 1.1, 'v only overshoots under the seams');
    const lid = accessor(nodeMesh('Lid'), 'POSITION');
    assert.ok(lid.max[1] - lid.min[1] > 0.0020 && lid.max[1] - lid.min[1] < 0.006, 'lid keeps a recessed centre and pressed rings (about 2-3 mm of relief)');
  });

  test(`${id}: LOD1 is a lighter, validated, texture-embedded variant with fewer draw calls`, () => {
    const metadata = JSON.parse(fs.readFileSync(`${folder}/metadata/${id}.json`));
    const file = fs.readFileSync(`${folder}/exports/lod1/${id}-lod1.glb`);
    const lod1 = readGlb(file);
    const lod = metadata.metrics.lod1;
    assert.equal(createHash('sha256').update(file).digest('hex'), lod.sha256);
    assert.equal(lod.validation.errors + lod.validation.warnings, 0);
    assert.equal(lod1.images.length, 1);
    assert.ok(lod1.buffers.every(b => !b.uri));
    const primitives = lod1.meshes.reduce((n, m) => n + m.primitives.length, 0);
    assert.ok(primitives <= 4 && primitives === lod.draw_calls);
    assert.ok(lod.triangles < metadata.metrics.triangles);
    assert.ok(lod.texture_memory_bytes < metadata.metrics.texture_memory_bytes / 3);
    assert.ok(!lod1.nodes.some(n => n.name === 'CanBody'), 'LOD1 drops the hidden body shell');
    assert.ok(metadata.metrics.draw_calls <= 7);
  });

  test(`${id}: viewer display settings use the opt-in studio environment and validate`, () => {
    const metadata = JSON.parse(fs.readFileSync(`${folder}/metadata/${id}.json`));
    assert.equal(metadata.display.studioEnvironment, true);
    assert.ok(metadata.display.environmentIntensity > 0 && metadata.display.environmentIntensity <= 3);
    assert.doesNotThrow(() => validateMetadata(metadata, id));
  });
}

test('metadata validation rejects malformed studio environment settings', () => {
  const metadata = JSON.parse(fs.readFileSync(`${folder}/metadata/gjh-can-mexico-abalone.json`));
  const id = 'gjh-can-mexico-abalone';
  assert.throws(() => validateMetadata({ ...metadata, display: { ...metadata.display, studioEnvironment: 'yes' } }, id), /studioEnvironment/);
  assert.throws(() => validateMetadata({ ...metadata, display: { ...metadata.display, environmentIntensity: 9 } }, id), /environmentIntensity/);
});
