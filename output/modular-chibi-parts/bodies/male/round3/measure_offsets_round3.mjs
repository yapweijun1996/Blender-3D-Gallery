import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';

const here = new URL('./', import.meta.url);
const path = name => new URL(name, here);
const load = name => readFileSync(path(name));
const sha256 = data => createHash('sha256').update(data).digest('hex');

function mesh(bytes) {
  const end = 20 + bytes.readUInt32LE(12);
  const doc = JSON.parse(bytes.toString('utf8', 20, end));
  assert.equal(doc.meshes.length, 1);
  assert.equal(doc.meshes[0].primitives.length, 1);
  const { attributes } = doc.meshes[0].primitives[0];
  const read = (attribute, width) => {
    const a = doc.accessors[attributes[attribute]];
    const view = doc.bufferViews[a.bufferView];
    assert.equal(a.componentType, 5126);
    const start = end + 8 + (a.byteOffset ?? 0) + (view.byteOffset ?? 0);
    const stride = view.byteStride ?? (width * 4);
    return Array.from({ length: a.count }, (_, i) =>
      Array.from({ length: width }, (_, j) => bytes.readFloatLE(start + i * stride + j * 4)));
  };
  return { points: read('POSITION', 3), uv: read('TEXCOORD_0', 2) };
}
const coordinates = uv => uv.map(value => Math.floor(value * 1e6));
const distance = (left, right) => Math.hypot(...left.map((value, i) => value - right[i]));
const result = {};
for (const key of ['dress', 'jeans']) {
  const filename = `male-${key}-v3.glb`;
  const original = load(`.runtime/initial/${filename}`);
  const current = load(filename);
  const base = mesh(original);
  const final = mesh(current);
  const groups = new Map();
  base.uv.forEach((uv, index) => {
    const id = coordinates(uv).join(',');
    if (!groups.has(id)) groups.set(id, []);
    groups.get(id).push(index);
  });
  let maximum = 0;
  let ambiguous = 0;
  for (const [i, uv] of final.uv.entries()) {
    const [x, y] = coordinates(uv);
    const matching = [];
    for (let dx = -1; dx <= 1; dx++) {
      for (let dy = -1; dy <= 1; dy++) {
        for (const j of groups.get(`${x + dx},${y + dy}`) ?? []) {
          if (distance(uv, base.uv[j]) < 2e-7) matching.push(j);
        }
      }
    }
    assert.ok(matching.length, `${key} source UV unavailable at ${i}`);
    const spread = Math.max(...matching.map(j => distance(base.points[matching[0]], base.points[j])));
    if (spread > .000002) ambiguous++;
    // For a duplicate UV, take the farthest possible bind anchor.
    maximum = Math.max(maximum, ...matching.map(j => distance(final.points[i], base.points[j])));
  }
  const data = { input_sha256: sha256(original), sha256: sha256(current), upper_bound_mm: maximum * 1000,
    verified_position_entries: final.points.length, ambiguous_uv_entries: ambiguous };
  result[key] = data;
  console.log(key, data);
}
writeFileSync(path('qa/offset_measurement.json'), JSON.stringify(result, null, 2) + '\n');
