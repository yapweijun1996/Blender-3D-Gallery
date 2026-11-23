import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, renameSync, unlinkSync, writeFileSync } from 'node:fs';

const here = new URL('./', import.meta.url);
const location = path => new URL(path, here);
const load = path => readFileSync(location(path));
const hash = input => createHash('sha256').update(input).digest('hex');
const toGltf = ([x, y, z]) => [x, z, -y].map(Math.fround);
const id = values => values.map(v => Math.round(v * 1e7)).join(',');
const gap = (a, b) => Math.hypot(...a.map((value, i) => value - b[i]));

for (const key of process.argv.slice(2)) {
  const editPath = location(`.runtime/${key}-positions.json`);
  if (!existsSync(editPath)) continue;
  const file = `male-${key}-v3.glb`;
  const bytes = load(file);
  const changes = JSON.parse(readFileSync(editPath, 'utf8'));
  assert.equal(hash(bytes), changes.input);
  assert.ok(changes.rows.length > 0);
  const jsonEnd = 20 + bytes.readUInt32LE(12);
  const json = JSON.parse(bytes.toString('utf8', 20, jsonEnd));
  const binChunk = bytes.subarray(jsonEnd);
  const data = binChunk.subarray(8);
  const changesByPosition = new Map();
  for (const [a, b] of changes.rows) {
    const before = toGltf(a);
    const after = toGltf(b);
    const tag = id(before);
    const record = changesByPosition.get(tag);
    if (record) assert.ok(gap(record.after, after) < 1e-7);
    changesByPosition.set(tag, { before, after, covered: false });
  }
  const accessors = new Set(json.meshes.flatMap(m => m.primitives.map(p => p.attributes.POSITION)));
  let affected = 0;
  for (const index of accessors) {
    const accessor = json.accessors[index];
    const view = json.bufferViews[accessor.bufferView];
    assert.equal(accessor.componentType, 5126);
    assert.equal(accessor.type, 'VEC3');
    const offset = (accessor.byteOffset ?? 0) + (view.byteOffset ?? 0);
    const lo = [Infinity, Infinity, Infinity];
    const hi = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < accessor.count; i++) {
      const position = offset + i * (view.byteStride ?? 12);
      let values = [0, 4, 8].map(j => data.readFloatLE(position + j));
      let record = changesByPosition.get(id(values));
      if (!record) {
        record = [...changesByPosition.values()].find(item => gap(values, item.before) < 2e-7);
      }
      if (record) {
        affected++;
        record.covered = true;
        values = values.map((value, j) => Math.fround(value + record.after[j] - record.before[j]));
        values.forEach((value, j) => data.writeFloatLE(value, position + j * 4));
      }
      for (let j = 0; j < 3; j++) {
        lo[j] = Math.min(lo[j], values[j]);
        hi[j] = Math.max(hi[j], values[j]);
      }
    }
    accessor.min = lo;
    accessor.max = hi;
  }
  assert.ok([...changesByPosition.values()].every(item => item.covered), `${key} position lookup`);
  const jsonBuffer = Buffer.from(JSON.stringify(json));
  const padded = Buffer.alloc(Math.ceil(jsonBuffer.length / 4) * 4, 0x20);
  jsonBuffer.copy(padded);
  const header = Buffer.from(bytes.subarray(0, 20));
  header.writeUInt32LE(padded.length, 12);
  header.writeUInt32LE(20 + padded.length + binChunk.length, 8);
  const output = Buffer.concat([header, padded, binChunk]);
  const stage = location(`.runtime/${key}-positions.glb`);
  writeFileSync(stage, output);
  renameSync(stage, location(file));
  const qa = `qa/fit-${key}.json`;
  const history = JSON.parse(load(qa));
  history.sha256 = hash(output);
  history.vertex_displacement_max_mm += changes.offset_mm;
  history.vertex_polish ??= [];
  history.vertex_polish.push({ input_sha256: changes.input, patches: changes.history,
    changed_position_entries: affected, preserved_skin_attributes: true });
  writeFileSync(location(qa), JSON.stringify(history, null, 2) + '\n');
  unlinkSync(editPath);
  console.log(file, affected, 'position entries updated', 'maximum step (mm)', changes.offset_mm);
}
