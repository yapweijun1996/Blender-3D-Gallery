// Template: self-checkout-machine/validate.mjs; adds exact grid seam checks.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {Box3, Vector3} from 'three';
import validator from 'gltf-validator';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

const dir = fileURLToPath(new URL('.', import.meta.url));
const spec = JSON.parse(fs.readFileSync(dir + 'backlog.json'));
const bytes = fs.readFileSync(dir + 'exports/optimized.glb');
const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const v = await validator.validateBytes(new Uint8Array(bytes), {uri: 'optimized.glb'});
fs.writeFileSync(dir + 'reports/khronos.json', JSON.stringify(v, null, 2) + '\n');
assert.equal(v.issues.numErrors, 0, 'Khronos errors');
assert.equal(v.issues.numWarnings, 0, 'Khronos warnings');
assert.ok(json.buffers.every(b => !b.uri));
assert.ok(!json.images?.length && !json.textures?.length && !json.cameras?.length);
assert.ok(!json.extensions?.KHR_lights_punctual);
assert.equal(json.materials.length, 3);
assert.equal(json.meshes.length, 3);
assert.equal(json.meshes.reduce((n, m) => n + m.primitives.length, 0), 3);
const glass = json.materials.find(m => m.name === 'Pale aqua glass');
assert.equal(glass.alphaMode, 'BLEND');
assert.ok(glass.doubleSided);
assert.ok(glass.pbrMetallicRoughness.baseColorFactor[3] > .1 && glass.pbrMetallicRoughness.baseColorFactor[3] < .5);
assert.ok(!json.extensionsUsed?.includes('KHR_materials_transmission'));
const g = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
g.scene.updateMatrixWorld(true);
const root = g.scene.getObjectByName(spec.root);
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(g.animations.length, 0);
const bounds = new Box3().setFromObject(g.scene, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
const expected = [spec.dimensions[0], spec.dimensions[2], spec.dimensions[1]];
for (let i = 0; i < 3; i++) assert.ok(Math.abs(dimensions[i] - expected[i]) < 1e-6, `exact metre envelope ${i}`);
assert.ok(Math.abs(bounds.min.y) < 1e-7, 'floor datum');
assert.ok(Math.abs(bounds.min.x + bounds.max.x) < 1e-7);
assert.ok(Math.abs(bounds.min.z + bounds.max.z) < 1e-7);
let triangles = 0, vertices = 0, minTriangleArea = Infinity;
const parts = {}, seams = {};
g.scene.traverse(o => {
  if (!o.isMesh) return;
  const geo = o.geometry, pos = geo.attributes.position, normal = geo.attributes.normal;
  assert.ok(normal && [...pos.array, ...normal.array].every(Number.isFinite));
  const index = geo.index;
  const count = index?.count ?? pos.count;
  triangles += count / 3;
  vertices += pos.count;
  const points = [];
  for (let i = 0; i < pos.count; i++) points.push(new Vector3().fromBufferAttribute(pos, i).applyMatrix4(o.matrixWorld));
  for (let i = 0; i < count; i += 3) {
    const [a, b, c] = [0, 1, 2].map(j => points[index ? index.getX(i + j) : i + j]);
    const area = b.clone().sub(a).cross(c.clone().sub(a)).length() / 2;
    assert.ok(area > 1e-13, `nondegenerate triangle ${o.name}/${i / 3}`);
    minTriangleArea = Math.min(minTriangleArea, area);
  }
  const b = new Box3().setFromObject(o, true);
  parts[o.name] = {min: b.min.toArray(), max: b.max.toArray(), triangles: count / 3};
  for (const axis of [0, 2]) {
    const profile = sign => [...new Set(points.filter(p => Math.abs(p.getComponent(axis) - sign * 2) < 1e-6)
      .map(p => p.toArray().filter((_, i) => i !== axis).map(v => Math.round(v * 1e6)).join(',')))].sort();
    assert.deepEqual(profile(-1), profile(1), `matching opposite frame profiles ${o.name} axis ${axis}`);
    seams[`${o.name}/${axis === 0 ? 'X' : 'Z'}`] = {matching: true, profile_vertices: profile(1).length};
  }
});
for (const prefix of spec.features) assert.ok(Object.keys(parts).some(name => name.startsWith(prefix)));
assert.equal(Object.keys(parts).length, 3);
assert.ok(triangles < spec.budget.triangles);
assert.ok(bytes.length < spec.budget.bytes);
for (const [name, expected] of Object.entries({X_NEG: [-2, 0, 0], X_POS: [2, 0, 0], Z_NEG: [0, 0, -2], Z_POS: [0, 0, 2]})) {
  const c = root.getObjectByName('CONNECTOR_' + name);
  assert.ok(c);
  assert.ok(c.getWorldPosition(new Vector3()).distanceTo(new Vector3(...expected)) < 1e-6);
}
// Actual-export placement: all nine modules stay within disjoint 4 m cells.
const assembly = [];
for (let x = -1; x <= 1; x++) for (let z = -1; z <= 1; z++) {
  const clone = g.scene.clone(true);
  clone.position.set(x * 4, 0, z * 4);
  clone.updateMatrixWorld(true);
  assembly.push(new Box3().setFromObject(clone, true));
}
let touchingPairs = 0;
for (let i = 0; i < assembly.length; i++) for (let j = i + 1; j < assembly.length; j++) {
  const overlap = assembly[i].clone().intersect(assembly[j]);
  if (overlap.isEmpty()) continue;
  const d = overlap.getSize(new Vector3());
  assert.ok(d.x < 1e-6 || d.z < 1e-6, 'no positive-volume overlap across tile cells');
  if ((d.x < 1e-6 && d.z > 3.99) || (d.z < 1e-6 && d.x > 3.99)) touchingPairs++;
}
assert.equal(touchingPairs, 12, 'all twelve 3 x 3 seams touch');
const report = {
  result: 'PASS', id: spec.slug, glb_bytes: bytes.length, triangles, vertices,
  meshes: 3, primitives: 3, materials: 3, textures: 0, animations: 0,
  dimensions, bounds: {min: bounds.min.toArray(), max: bounds.max.toArray()},
  min_triangle_area_m2: minTriangleArea,
  sha256: createHash('sha256').update(bytes).digest('hex'),
  budget: spec.budget, validation: {errors: v.issues.numErrors, warnings: v.issues.numWarnings},
  tile_test: {grid: [3, 3], pitch_metres: 4, matching_seams: touchingPairs, profiles: seams}, parts
};
fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
