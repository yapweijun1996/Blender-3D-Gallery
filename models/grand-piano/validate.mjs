import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const spec = JSON.parse(fs.readFileSync(dir + 'backlog.json'));
const source = JSON.parse(fs.readFileSync(dir + 'reports/source-geometry.json'));
const bytes = fs.readFileSync(dir + 'exports/optimized.glb');
const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes), { maxIssues: 100 });
fs.writeFileSync(dir + 'reports/khronos.json', JSON.stringify(validation, null, 2) + '\n');
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
assert.ok(!json.images?.length && !json.textures?.length && !json.cameras?.length);
assert.ok(!json.extensions?.KHR_lights_punctual);
assert.ok(json.buffers.every(buffer => buffer.uri === undefined));
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName(spec.root);
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.front_axis, 'Blender -Y / glTF +Z');
assert.equal(gltf.animations.length, 0);

const positionsByMaterial = new Map();
let meshes = 0, primitives = 0, triangles = 0, vertices = 0;
gltf.scene.traverse(object => {
  if (!object.isMesh) return;
  meshes++;
  const geometry = object.geometry;
  const positions = geometry.attributes.position;
  const normals = geometry.attributes.normal;
  assert.ok(normals);
  assert.ok([...positions.array, ...normals.array].every(Number.isFinite));
  const list = [];
  for (let i = 0; i < positions.count; i++) list.push(new Vector3().fromBufferAttribute(positions, i).applyMatrix4(object.matrixWorld));
  positionsByMaterial.set(object.material.name, list);
  const index = geometry.index;
  const count = index?.count ?? positions.count;
  triangles += count / 3;
  vertices += positions.count;
  primitives += Math.max(geometry.groups.length, 1);
  const edgeA = new Vector3(), edgeB = new Vector3();
  for (let i = 0; i < count; i += 3) {
    const a = list[index ? index.getX(i) : i];
    const b = list[index ? index.getX(i + 1) : i + 1];
    const c = list[index ? index.getX(i + 2) : i + 2];
    assert.ok(edgeA.subVectors(b, a).cross(edgeB.subVectors(c, a)).lengthSq() > 1e-20, 'nondegenerate triangle');
  }
});
assert.equal(meshes, 3);
assert.equal(primitives, 3);
assert.equal(json.materials.length, 3);
assert.ok(triangles <= spec.budget.triangles);
assert.ok(bytes.length <= spec.budget.bytes);
const bounds = new Box3().setFromObject(gltf.scene, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
assert.ok(Math.abs(bounds.min.y) < 1e-6, 'floor datum');
assert.ok(Math.abs(bounds.min.x + bounds.max.x) < 1e-6, 'width centred on origin');
assert.ok(Math.abs(bounds.min.z + bounds.max.z) < 1e-6, 'footprint centred on origin');
assert.ok(Math.abs(dimensions[0] - 1.5) < 1e-5);
assert.ok(dimensions[1] > 1.78 && dimensions[1] < 1.84, 'raised lid envelope');
assert.ok(Math.abs(dimensions[2] - 2.345) < 1e-5, 'piano plus matching bench');

// Check every evaluated key vertex against the real merged GLB, allowing float32 rounding.
const buckets = new Map();
for (const [name, positions] of positionsByMaterial) {
  const map = new Map();
  for (const p of positions) {
    const key = p.toArray().map(v => Math.round(v * 1e5)).join(',');
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(p);
  }
  buckets.set(name, map);
}
function containsPosition(material, position) {
  const p = new Vector3(...position);
  const cell = position.map(v => Math.round(v * 1e5));
  for (let x = -1; x <= 1; x++) for (let y = -1; y <= 1; y++) for (let z = -1; z <= 1; z++) {
    const candidates = buckets.get(material).get([cell[0] + x, cell[1] + y, cell[2] + z].join(',')) ?? [];
    if (candidates.some(candidate => candidate.distanceTo(p) < 2e-6)) return true;
  }
  return false;
}
const notes = source.keys.slice().sort((a, b) => a.midi - b.midi);
assert.equal(notes.length, 88);
assert.deepEqual(notes.map(key => key.midi), Array.from({ length: 88 }, (_, i) => 21 + i));
const white = notes.filter(key => key.color === 'white');
const black = notes.filter(key => key.color === 'black');
assert.equal(white.length, 52);
assert.equal(black.length, 36);
const keyBounds = new Map();
for (const key of notes) {
  const expectedColor = [0, 2, 4, 5, 7, 9, 11].includes(key.midi % 12) ? 'white' : 'black';
  assert.equal(key.color, expectedColor, 'chromatic key layout');
  const material = key.color === 'white' ? 'Ivory keys' : 'Black lacquer';
  assert.ok(key.positions.every(position => containsPosition(material, position)), `exported geometry for MIDI ${key.midi}`);
  const box = new Box3().setFromPoints(key.positions.map(p => new Vector3(...p)));
  keyBounds.set(key.midi, box);
  assert.ok(Math.abs(box.max.y - (key.color === 'white' ? 0.755 : 0.771)) < 1e-5, 'key playing height');
  assert.ok(Math.abs(box.max.z - (key.color === 'white' ? 0.5555 : 0.4405)) < 1e-5, 'keys face +Z');
}
for (let i = 1; i < white.length; i++) {
  const previous = keyBounds.get(white[i - 1].midi), current = keyBounds.get(white[i].midi);
  assert.ok(current.min.x > previous.max.x, 'separate white key fronts');
  assert.ok(Math.abs(current.min.x - previous.min.x - 0.0235) < 1e-6, 'uniform white-key pitch');
}
for (const key of black) {
  const box = keyBounds.get(key.midi);
  const previous = keyBounds.get(key.midi - 1), next = keyBounds.get(key.midi + 1);
  assert.ok(Math.abs((box.min.x + box.max.x) / 2 - (previous.max.x + next.min.x) / 2) < 1e-6, 'black key between adjacent naturals');
  // White key vertices at rear depth must remain outside the black key envelope.
  for (const natural of notes.filter(note => note.midi === key.midi - 1 || note.midi === key.midi + 1)) {
    const rear = natural.positions.filter(p => p[2] < box.max.z - 0.002);
    assert.ok(rear.every(p => p[0] < box.min.x || p[0] > box.max.x), 'notched white-key clearance');
  }
}
const featureBounds = {};
for (const part of source.parts) {
  assert.ok(part.positions.every(position => containsPosition(part.material, position)), `exported part ${part.name}`);
  const bounds = new Box3().setFromPoints(part.positions.map(p => new Vector3(...p)));
  featureBounds[part.name] = bounds;
}
const groupedBounds = prefix => {
  const bounds = new Box3();
  const parts = source.parts.filter(part => part.name.startsWith(prefix));
  assert.ok(parts.length, prefix);
  for (const part of parts) bounds.union(featureBounds[part.name]);
  return { count: parts.length, dimensions_m: bounds.getSize(new Vector3()).toArray(),
    bounds_m: { min: bounds.min.toArray(), max: bounds.max.toArray() } };
};
const features = Object.fromEntries(spec.features.map(prefix => [prefix, groupedBounds(prefix)]));
const pianoBounds = new Box3();
for (const part of source.parts.filter(part => !part.name.startsWith('BENCH_'))) pianoBounds.union(featureBounds[part.name]);
assert.ok(Math.abs(pianoBounds.getSize(new Vector3()).z - 1.75) < 1e-5);
assert.equal(source.parts.filter(part => part.name.startsWith('LEG_Tapered_')).length, 3);
assert.equal(source.parts.filter(part => part.name.startsWith('CASTER_Wheel_')).length, 3);
assert.equal(source.parts.filter(part => part.name.startsWith('PEDAL_Paddle_')).length, 3);
assert.equal(source.parts.filter(part => part.name.startsWith('BENCH_Leg_')).length, 4);
assert.ok(features.LID_.bounds_m.max[1] > features.CASE_.bounds_m.max[1] + 0.7);
const sourceMaterial = json.materials.find(material => material.name === 'Black lacquer');
assert.ok(sourceMaterial.pbrMetallicRoughness.roughnessFactor <= 0.2, 'glossy plain black finish');
const report = {

  result: 'PASS', id: spec.slug, glb_bytes: bytes.length, triangles, vertices, meshes, primitives,
  materials: json.materials.length, textures: json.textures?.length ?? 0, animations: gltf.animations.length,
  dimensions_m: dimensions, bounds_m: { min: bounds.min.toArray(), max: bounds.max.toArray() },
  key_count: notes.length, white_keys: white.length, black_keys: black.length,
  white_key_top_m: keyBounds.get(21).max.y, black_key_top_m: keyBounds.get(22).max.y,
  key_layout: 'A0-C8 inclusive; seven complete octaves plus low A/B and high C; notched white keys; all key vertices matched to GLB',
  sha256: createHash('sha256').update(bytes).digest('hex'), budget: spec.budget,
  piano_dimensions_m: pianoBounds.getSize(new Vector3()).toArray(), features,
  validation: { errors: validation.issues.numErrors, warnings: validation.issues.numWarnings },
};
fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
