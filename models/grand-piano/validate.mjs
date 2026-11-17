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
assert.equal(json.materials.length, 2);
assert.ok(spec.budget.triangles <= 8000 && spec.budget.materials <= 2 && spec.budget.draw_calls <= 6);
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
for (const scene of gltf.scenes) scene.updateMatrixWorld(true);
assert.equal(gltf.scenes.length, 3);
const root = gltf.scene.getObjectByName(spec.root);
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.deepEqual(root.scale.toArray(), [1, 1, 1]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.front_axis, 'Blender -Y / glTF +Z');
assert.equal(gltf.animations.length, 0);
const bench = root.getObjectByName('bench');
const open = root.getObjectByName('lid_open');
const closedScene = gltf.scenes.find(scene => scene.name === 'VARIANT_LidClosed');
const closed = closedScene?.getObjectByName('lid_closed');
const collisionScene = gltf.scenes.find(scene => scene.name === 'COLLISION_ONLY');
assert.ok(bench?.isMesh && open?.isMesh && closed?.isMesh && collisionScene);
assert.equal(bench.parent, root, 'bench can move independently of the piano');
assert.equal(bench.userData.interaction, 'sit');
assert.deepEqual(bench.userData.seat_anchor_local_m, [0, 0.55, 0]);
assert.deepEqual(bench.userData.seat_facing_local, [0, 0, -1]);
assert.equal(root.getObjectByName('lid_closed'), undefined, 'inactive variant is absent from the default scene');
assert.equal(root.getObjectByName('collider_box'), undefined, 'collision meshes are absent from the visual scene');
assert.equal(collisionScene.children.length, 2);
for (const name of ['collider_box', 'collider_box_bench']) {
  const collider = collisionScene.getObjectByName(name);
  assert.ok(collider?.isMesh && collider.userData.collision_only);
  const node = json.nodes.find(node => node.name === name);
  assert.ok(json.meshes[node.mesh].primitives.every(primitive => primitive.material === undefined), 'collider has no material');
}

const positionsByGroup = new Map();
let meshes = 0, primitives = 0, triangles = 0, vertices = 0;
for (const scene of gltf.scenes) scene.traverse(object => {
  if (!object.isMesh) return;
  meshes++;
  const geometry = object.geometry;
  const positions = geometry.attributes.position;
  const normals = geometry.attributes.normal;
  assert.ok(normals);
  assert.ok([...positions.array, ...normals.array].every(Number.isFinite));
  const list = [];
  for (let i = 0; i < positions.count; i++) list.push(new Vector3().fromBufferAttribute(positions, i).applyMatrix4(object.matrixWorld));
  if (!object.userData.collision_only) {
    const group = object.name.startsWith('body_') ? 'piano_body' : object.name;
    const key = group + '/' + object.material.name;
    positionsByGroup.set(key, list);
    if (object.material.name === 'Warm details') {
      assert.ok(geometry.attributes.color, 'ivory and brass use actual vertex colors');
      const colors = geometry.attributes.color;
      assert.ok([...colors.array].every(value => Number.isFinite(value) && value >= 0 && value <= 1));
      assert.ok(new Set(Array.from({ length: colors.count }, (_, i) => colors.getX(i).toFixed(3))).size >= 2, 'distinct ivory and brass tints');
    }
  }
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
assert.equal(meshes, 7);
assert.equal(primitives, 7);
assert.ok(triangles <= spec.budget.triangles, `${triangles} total triangles, including both lids and colliders`);
assert.ok(bytes.length <= spec.budget.bytes);
function visibleStats() {
  let triangles = 0, draws = 0;
  root.traverseVisible(object => {
    if (!object.isMesh) return;
    triangles += (object.geometry.index?.count ?? object.geometry.attributes.position.count) / 3;
    draws += Math.max(object.geometry.groups.length, 1);
  });
  assert.ok(draws <= spec.budget.draw_calls);
  return { triangles, draw_calls: draws };
}
const bounds = new Box3().setFromObject(root, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
assert.ok(Math.abs(bounds.min.y) < 1e-6, 'floor datum');
assert.ok(Math.abs(bounds.min.x + bounds.max.x) < 1e-6, 'width centred on origin');
assert.ok(Math.abs(bounds.min.z + bounds.max.z) < 1e-6, 'complete footprint centred on origin');
assert.ok(Math.abs(dimensions[0] - 1.5) < 1e-5);
assert.ok(dimensions[1] > 1.78 && dimensions[1] < 1.84, 'raised lid clearance');
assert.ok(Math.abs(dimensions[2] - 2.0) < 1e-5);
const openStats = visibleStats();
root.remove(open);
root.add(closed);
root.updateMatrixWorld(true);
const closedBounds = new Box3().setFromObject(root, true);
const closedDimensions = closedBounds.getSize(new Vector3()).toArray();
assert.ok(Math.abs(closedDimensions[1] - 1.031) < 1e-5, 'closed lid and folded music desk fit the 1 m case');
assert.ok(Math.abs(closedDimensions[2] - 2.0) < 1e-5);
const closedStats = visibleStats();
root.remove(closed);
closedScene.add(closed);
root.add(open);
root.updateMatrixWorld(true);
closedScene.updateMatrixWorld(true);
const benchBounds = new Box3().setFromObject(bench, true);
assert.ok(Math.abs(benchBounds.min.y) < 1e-6 && Math.abs(benchBounds.max.y - 0.55) < 1e-6);
assert.ok(Math.abs(bench.position.y) < 1e-6 && Math.abs(bench.position.z - benchBounds.getCenter(new Vector3()).z) < 1e-6, 'bench has its own floor-centre pivot');
const benchColliderBounds = new Box3().setFromObject(collisionScene.getObjectByName('collider_box_bench'), true);
assert.ok(benchColliderBounds.min.distanceTo(benchBounds.min) < 1e-6 && benchColliderBounds.max.distanceTo(benchBounds.max) < 1e-6);

// Match evaluated authoring components to their actual exported semantic nodes.
const buckets = new Map();
for (const [key, positions] of positionsByGroup) {
  const map = new Map();
  for (const p of positions) {
    const key = p.toArray().map(v => Math.round(v * 1e5)).join(',');
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(p);
  }
  buckets.set(key, map);
}
function containsPosition(key, position) {
  const p = new Vector3(...position);
  const cell = position.map(v => Math.round(v * 1e5));
  for (let x = -1; x <= 1; x++) for (let y = -1; y <= 1; y++) for (let z = -1; z <= 1; z++) {
    const candidates = buckets.get(key)?.get([cell[0] + x, cell[1] + y, cell[2] + z].join(',')) ?? [];
    if (candidates.some(candidate => candidate.distanceTo(p) < 2e-6)) return true;
  }
  return false;
}
const featureBounds = {};
for (const part of source.parts) {
  assert.ok(part.positions.every(position => containsPosition(part.group + '/' + part.material, position)), `exported part ${part.name} belongs to ${part.group}`);
  featureBounds[part.name] = new Box3().setFromPoints(part.positions.map(p => new Vector3(...p)));
}
const keyboardParts = source.parts.filter(part => part.name.startsWith('KEY_'));
assert.equal(keyboardParts.length, 2, 'one slab and one flat pattern, no individual key objects');
assert.equal(source.keyboard.pattern_quads, 87);
assert.deepEqual(source.keyboard.white_midi_notes, Array.from({ length: 88 }, (_, i) => 21 + i).filter(midi => [0, 2, 4, 5, 7, 9, 11].includes(midi % 12)));
assert.deepEqual(source.keyboard.black_midi_notes, Array.from({ length: 88 }, (_, i) => 21 + i).filter(midi => ![0, 2, 4, 5, 7, 9, 11].includes(midi % 12)));
const pattern = source.parts.find(part => part.name === 'KEY_FlatPattern');
assert.equal(pattern.positions.length, 87 * 4);
for (let i = 0; i < 51; i++) {
  const x = -0.611 + (i + 1) * 0.0235;
  assert.ok(containsPosition('piano_body/Black lacquer', [x - 0.00045, 0.758, (0.853 - 0.2975) * (2 / 2.345)]), 'white key division faces +Z');
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
assert.equal(source.parts.filter(part => part.name.startsWith('LEG_Tapered_')).length, 3);
assert.equal(source.parts.filter(part => part.name.startsWith('CASTER_Wheel_')).length, 3);
assert.equal(source.parts.filter(part => part.name.startsWith('PEDAL_Paddle_')).length, 3);
assert.equal(source.parts.filter(part => part.name.startsWith('BENCH_Leg_')).length, 4);
const lacquer = json.materials.find(material => material.name === 'Black lacquer');
assert.ok(lacquer.pbrMetallicRoughness.roughnessFactor <= 0.2, 'glossy plain black finish');
const report = {
  result: 'PASS', id: spec.slug, glb_bytes: bytes.length, triangles, vertices, meshes, primitives,
  materials: json.materials.length, textures: 0, animations: 0,
  dimensions_m: dimensions, closed_dimensions_m: closedDimensions,
  bounds_m: { min: bounds.min.toArray(), max: bounds.max.toArray() },
  variants: { lid_open: openStats, lid_closed: closedStats },
  collision_meshes: 2, collider_materials: 0, collision_hidden_from_default_scene: true,
  bench_dimensions_m: benchBounds.getSize(new Vector3()).toArray(),
  bench_pivot_m: bench.position.toArray(), seat_anchor_local_m: bench.userData.seat_anchor_local_m,
  keyboard: { white_keys: 52, black_keys: 36, representation: 'one ivory slab and 87 flat quads', pattern_triangles: 174 },
  sha256: createHash('sha256').update(bytes).digest('hex'), budget: spec.budget, features,
  validation: { errors: validation.issues.numErrors, warnings: validation.issues.numWarnings },
};
fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ result: report.result, triangles, materials: report.materials, variants: report.variants, dimensions_m: dimensions, closed_dimensions_m: closedDimensions }));
