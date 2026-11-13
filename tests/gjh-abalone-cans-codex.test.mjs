import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { loadCatalog } from '../scripts/catalog.mjs';

// Comparison set: the same four cans with an AI-generated flat label (Codex). Disclosure and geometry parity are tested.
const folder = 'models/gjh-abalone-cans';
const skus = ['new-zealand', 'australia', 'south-africa', 'mexico'];
const catalog = loadCatalog();
const collection = catalog.collections.find(c => c.id === 'gjh-abalone-cans-codex');
const all = catalog.collections.flatMap(c => c.assets);
const readGlb = bytes => JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const floats = (bytes, json, acc) => {
  const comps = { VEC2: 2, VEC3: 3 }[acc.type];
  const bin = bytes.subarray(20 + bytes.readUInt32LE(12) + 8);
  const view = json.bufferViews[acc.bufferView];
  const stride = view.byteStride ?? comps * 4;
  const base = view.byteOffset + (acc.byteOffset ?? 0);
  return Array.from({ length: acc.count }, (_, i) => Array.from({ length: comps }, (_, k) => bin.readFloatLE(base + i * stride + k * 4)));
};
const sha = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');

test('codex comparison set is registered, not downloadable, and labelled as AI-generated', () => {
  assert.deepEqual(collection.assets.map(a => a.id), skus.map(s => `gjh-can-${s}-abalone-codex`));
  for (const asset of collection.assets) {
    assert.equal(asset.downloadable, false);
    assert.match(asset.license, /AI-generated/);
    assert.ok(asset.tags.includes('ai-generated-label'));
    assert.match(asset.name, /Codex flat label/);
  }
});

for (const sku of skus) {
  const id = `gjh-can-${sku}-abalone-codex`, photoId = `gjh-can-${sku}-abalone`;
  test(`${id}: metadata discloses the AI label, lists known differences and ties to the photo version`, () => {
    const metadata = JSON.parse(fs.readFileSync(`${folder}/metadata/${id}.json`));
    assert.match(metadata.label_source.status, /Not official artwork/);
    assert.ok(metadata.label_source.known_discrepancies_from_official.length >= 2);
    assert.equal(metadata.label_source.comparison_with, photoId);
    assert.ok(all.some(a => a.id === photoId), 'the photo version it is compared with exists');
    assert.equal(metadata.label_source.file_sha256, sha(`${folder}/${metadata.label_source.file}`), 'flat label file hash recorded');
    assert.match(metadata.rights, /AI-generated/);
    assert.equal(metadata.display.textureAnisotropy, 8);
    const bytes = fs.readFileSync(`${folder}/exports/codex/${id}.glb`);
    assert.equal(metadata.metrics.glb_bytes, bytes.length);
    assert.equal(metadata.metrics.sha256, sha(`${folder}/exports/codex/${id}.glb`));
    assert.deepEqual([metadata.validation.errors, metadata.validation.warnings], [0, 0]);
  });

  test(`${id}: same budgets and geometry as the photo version, isotropic label, one embedded JPEG`, () => {
    const bytes = fs.readFileSync(`${folder}/exports/codex/${id}.glb`);
    const json = readGlb(bytes);
    assert.ok(json.buffers.every(b => !b.uri));
    assert.equal(json.images.length, 1);
    assert.equal(json.images[0].mimeType, 'image/jpeg');
    assert.equal(json.materials.length, 3);
    assert.equal(json.meshes.reduce((n, m) => n + m.primitives.length, 0), 3);
    assert.ok(bytes.length <= 500 * 1024, 'GLB size target');
    const names = json.nodes.map(n => n.name);
    for (const n of [`ASSET_GJHCan${sku.split('-').map(w => w[0].toUpperCase() + w.slice(1)).join('')}AbaloneCodex`, 'GoldRim', 'SilverMetal', 'Label']) assert.ok(names.includes(n), `${id} missing ${n}`);
    const photo = readGlb(fs.readFileSync(`${folder}/exports/${photoId}.glb`));
    const bounds = j => ['GoldRim', 'SilverMetal'].map(n => j.accessors[j.meshes[j.nodes.find(x => x.name === n).mesh].primitives[0].attributes.POSITION]).map(a => [a.min, a.max]);
    // Heights differ by the sub-millimetre rounding of each photo's measured label rows; radii are identical.
    const near = (x, y) => x.every((box, i) => box.every((v, k) => v.every((c, j) => Math.abs(c - y[i][k][j]) < 0.0005)));
    assert.ok(near(bounds(json), bounds(photo)), 'same can geometry within 0.5 mm');
    // label texel density: horizontal and vertical agree
    const prim = json.meshes[json.nodes.find(n => n.name === 'Label').mesh].primitives[0];
    const jl = bytes.readUInt32LE(12), view = json.bufferViews[json.images[0].bufferView];
    const jpg = bytes.subarray(20 + jl + 8 + view.byteOffset, 20 + jl + 8 + view.byteOffset + view.byteLength);
    let w = 0, h = 0;
    for (let i = 2; i < jpg.length;) { if (jpg[i] !== 0xFF) { i++; continue; } const m = jpg[i + 1]; if (m >= 0xC0 && m <= 0xC3) { h = jpg.readUInt16BE(i + 5); w = jpg.readUInt16BE(i + 7); break; } i += 2 + jpg.readUInt16BE(i + 2); }
    const P = floats(bytes, json, json.accessors[prim.attributes.POSITION]), UV = floats(bytes, json, json.accessors[prim.attributes.TEXCOORD_0]);
    const wall = P.map((_, i) => i).filter(i => Math.hypot(P[i][0], P[i][2]) > 0.0369);
    const radius = wall.reduce((a, i) => a + Math.hypot(P[i][0], P[i][2]), 0) / wall.length;
    const ys = wall.map(i => P[i][1]), vs = wall.map(i => UV[i][1]);
    const labelHeight = (Math.max(...ys) - Math.min(...ys)) / (Math.max(...vs) - Math.min(...vs));
    assert.ok(Math.abs((h / labelHeight) / (w / (2 * Math.PI * radius)) - 1) < 0.005, 'texel density isotropic');
    assert.ok(w >= 1500, 'texture is at least 1500 px around the can');
  });
}
