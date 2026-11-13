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
const parts = ['GoldRim', 'SilverMetal', 'Label'];
const accessor_ = (json, prim, key) => json.accessors[prim.attributes[key]];
const readGlb = bytes => JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
// Decode a float accessor (VEC2/VEC3) from the GLB binary chunk; UV and normal accessors carry no min/max.
function readFloats(bytes, json, accessor) {
  const comps = { VEC2: 2, VEC3: 3 }[accessor.type];
  const jsonLength = bytes.readUInt32LE(12);
  const bin = bytes.subarray(20 + jsonLength + 8);
  const view = json.bufferViews[accessor.bufferView];
  const stride = view.byteStride ?? comps * 4;
  const base = view.byteOffset + (accessor.byteOffset ?? 0);
  const values = [];
  for (let i = 0; i < accessor.count; i++)
    values.push(Array.from({ length: comps }, (_, k) => bin.readFloatLE(base + i * stride + k * 4)));
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
    assert.equal(Object.keys(metadata.product.source_images).length, id.endsWith('mexico-abalone') ? 2 : 3);
    assert.ok(Object.values(metadata.product.source_images).every(h => /^[0-9a-f]{64}$/.test(h)), 'source packshot hashes recorded');
    const layout = metadata.label_layout;
    assert.match(layout.status, /estimates, not verified/);
    const centres = Object.values(layout.panels_degrees_from_front);
    assert.ok(centres.every(p => p.usable_from >= -74 && p.usable_to <= 74), 'only the reliable centre of each packshot is used');
    if (id.endsWith('mexico-abalone')) {
      assert.ok(layout.unprinted_gap_degrees > 90 && /no artwork, text or marks were invented/i.test(layout.gap_note), 'missing panel is disclosed, not invented');
    } else {
      assert.equal(layout.unprinted_gap_degrees, 0);
      const ordered = layout.order_around_can.map(n => layout.panels_degrees_from_front[n]);
      assert.equal(ordered.length, 3);
    }
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
    const position = json.accessors[json.meshes[json.nodes.find(n => n.name === 'SilverMetal').mesh].primitives[0].attributes.POSITION];
    assert.ok(position.max[1] > 0.1 && position.max[1] < 0.13, 'metre-scale height');
    assert.ok(bytes.length <= 500 * 1024, 'GLB size target');
  });
}

for (const [id, [rootName]] of Object.entries(cans)) {
  const bytes = fs.readFileSync(`${folder}/exports/${id}.glb`);
  const json = readGlb(bytes);
  const nodeMesh = name => json.meshes[json.nodes.find(n => n.name === name).mesh].primitives[0];
  const accessor = (primitive, key) => json.accessors[primitive.attributes[key]];

  test(`${id}: rolled seams are thin, the lid and base have relief, normals point outward, UVs wrap exactly once`, () => {
    const heightOf = json.accessors[nodeMesh('SilverMetal').attributes.POSITION].max[1];
    const gold = readFloats(bytes, json, accessor(nodeMesh('GoldRim'), 'POSITION'));
    const ys = gold.map(p => p[1]);
    assert.ok(Math.max(...gold.map(p => Math.hypot(p[0], p[2]))) < 0.03675 + 0.0030, 'seams bulge less than 3 mm past the body');
    assert.ok(ys.every(y => y < 0.0055 || y > heightOf - 0.0055), 'gold exists only in two seams under 5.5 mm tall');
    const silver = readFloats(bytes, json, accessor(nodeMesh('SilverMetal'), 'POSITION'));
    const levels = (lo, hi) => new Set(silver.map(p => Math.round(p[1] * 1e5)).filter(v => v >= lo * 1e5 && v <= hi * 1e5));
    assert.ok(levels(heightOf - 0.0045, heightOf).size >= 5, 'lid keeps rim, recessed panel and pressed rings');
    assert.ok(levels(0, 0.0035).size >= 5, 'base keeps a standing ring and recess');
    assert.ok(Math.min(...silver.map(p => p[1])) >= -0.0005 && Math.min(...ys) >= -0.0005, 'floor-centre origin');
    const label = nodeMesh('Label');
    const positions = readFloats(bytes, json, accessor(label, 'POSITION'));
    const normals = readFloats(bytes, json, accessor(label, 'NORMAL'));
    positions.forEach((p, i) => {
      const n = normals[i];
      if (Math.abs(n[1]) < 0.5) assert.ok((n[0] * p[0] + n[2] * p[2]) / Math.hypot(p[0], p[2]) > 0.9, 'label wall normals face outward');
    });
    const uv = readFloats(bytes, json, accessor(label, 'TEXCOORD_0'));
    const us = uv.map(p => p[0]), vs = uv.map(p => p[1]);
    assert.ok(Math.min(...us) >= -0.001 && Math.max(...us) <= 1.001 && Math.max(...us) - Math.min(...us) > 0.99, 'u covers exactly one wrap');
    assert.ok(Math.min(...vs) > -0.1 && Math.max(...vs) < 1.1, 'v only overshoots under the seams');
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
    assert.ok(primitives <= 3 && primitives === lod.draw_calls);
    assert.ok(lod.triangles < metadata.metrics.triangles);
    assert.ok(lod.texture_memory_bytes < metadata.metrics.texture_memory_bytes / 3);
    assert.ok(metadata.metrics.draw_calls <= 3 && metadata.metrics.materials <= 3, 'draw-call and material targets');
    assert.ok(metadata.metrics.triangles <= 5000 && metadata.metrics.glb_bytes <= 500 * 1024, 'triangle and size targets');
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

for (const [id] of Object.entries(cans)) {
  test(`${id}: label texture is isotropic on the mesh (circles stay round), with mipmapped filtering and opt-in anisotropy`, () => {
    const bytes = fs.readFileSync(`${folder}/exports/${id}.glb`);
    const json = readGlb(bytes);
    const prim = json.meshes[json.nodes.find(n => n.name === 'Label').mesh].primitives[0];
    const jl = bytes.readUInt32LE(12);
    const view = json.bufferViews[json.images[0].bufferView];
    const jpg = bytes.subarray(20 + jl + 8 + view.byteOffset, 20 + jl + 8 + view.byteOffset + view.byteLength);
    let w = 0, h = 0;
    for (let i = 2; i < jpg.length;) { if (jpg[i] !== 0xFF) { i++; continue; } const m = jpg[i + 1]; if (m >= 0xC0 && m <= 0xC3) { h = jpg.readUInt16BE(i + 5); w = jpg.readUInt16BE(i + 7); break; } i += 2 + jpg.readUInt16BE(i + 2); }
    const P = readFloats(bytes, json, accessor_(json, prim, 'POSITION', 3));
    const UV = readFloats(bytes, json, accessor_(json, prim, 'TEXCOORD_0', 2));
    const wall = P.map((p, i) => i).filter(i => Math.hypot(P[i][0], P[i][2]) > 0.0369);
    const radius = wall.reduce((a, i) => a + Math.hypot(P[i][0], P[i][2]), 0) / wall.length;
    const ys = wall.map(i => P[i][1]), vs = wall.map(i => UV[i][1]);
    const labelHeight = (Math.max(...ys) - Math.min(...ys)) / (Math.max(...vs) - Math.min(...vs));
    const horizontal = w / (2 * Math.PI * radius), vertical = h / labelHeight;
    assert.ok(Math.abs(vertical / horizontal - 1) < 0.005, `texel density v/h ${vertical / horizontal}`);
    assert.deepEqual([json.samplers[0].minFilter, json.samplers[0].magFilter], [9987, 9729], 'mipmapped minification, linear magnification');
    const metadata = JSON.parse(fs.readFileSync(`${folder}/metadata/${id}.json`));
    assert.equal(metadata.display.textureAnisotropy, 8);
    assert.throws(() => validateMetadata({ ...metadata, display: { ...metadata.display, textureAnisotropy: 99 } }, id), /textureAnisotropy/);
  });
}

test('flat Wild Caught badges are fixed and disclosed, printed logos are left alone', () => {
  for (const id of ['gjh-can-australia-abalone', 'gjh-can-new-zealand-abalone', 'gjh-can-mexico-abalone']) {
    const fix = JSON.parse(fs.readFileSync(`${folder}/metadata/${id}.json`)).label_layout.flat_badge_fix;
    assert.ok(fix.face_on_width_over_height.before_computed > 1.3, 'distortion before the fix was measured');
    assert.ok(Math.abs(fix.face_on_width_over_height.after_rendered_approx - 1) < 0.06, 'round after the fix');
    assert.match(fix.fix, /no pixel is redrawn/i);
  }
  const sa = JSON.parse(fs.readFileSync(`${folder}/metadata/gjh-can-south-africa-abalone.json`)).label_layout;
  assert.equal(sa.flat_badge_fix, null);
});
