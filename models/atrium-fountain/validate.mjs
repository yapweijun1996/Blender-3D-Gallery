// Independent exported-asset gate, following self-checkout-machine/validate.mjs.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {Box3, Vector3, Triangle} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const spec = JSON.parse(fs.readFileSync(dir + 'backlog.json'));
const bytes = fs.readFileSync(dir + 'exports/optimized.glb');
const doc = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const khronos = await validator.validateBytes(new Uint8Array(bytes), {uri: 'optimized.glb'});
fs.writeFileSync(dir + 'reports/khronos.json', JSON.stringify(khronos, null, 2) + '\n');
assert.equal(khronos.issues.numErrors, 0);
assert.equal(khronos.issues.numWarnings, 0);
assert.ok(doc.buffers.every(b => !b.uri));
assert.ok(!doc.images?.length && !doc.textures?.length && !doc.cameras?.length);
assert.ok(!doc.extensionsUsed?.includes('KHR_lights_punctual'));
assert.ok(!doc.extensionsUsed?.includes('KHR_materials_transmission'));
assert.equal(doc.materials.length, 3);
assert.equal(doc.meshes.length, 5);
assert.deepEqual(doc.meshes.map(m => m.name).sort(), [...spec.features].sort(), 'exact exported mesh data names');
const primitiveCount = doc.meshes.reduce((sum, m) => sum + m.primitives.length, 0);
assert.equal(primitiveCount, 5);
const water = doc.materials.find(m => m.name === 'Translucent aqua water');
assert.equal(water.alphaMode, 'BLEND');
assert.ok(water.pbrMetallicRoughness.baseColorFactor[3] > 0 && water.pbrMetallicRoughness.baseColorFactor[3] < 1);
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName(spec.root);
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.front_axis, 'Blender -Y / glTF +Z');
assert.equal(gltf.animations.length, 0, 'static water shapes, no fabricated clips');
const bounds = new Box3().setFromObject(root, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
for (const [axis, expected] of [5, 2.15, 5].entries())
  assert.ok(Math.abs(dimensions[axis] - expected) < 1e-5, `metre envelope ${axis}: ${dimensions[axis]}`);
assert.ok(Math.abs(bounds.min.y) < 1e-7);
assert.ok(Math.abs(bounds.min.x + bounds.max.x) < 1e-7 && Math.abs(bounds.min.z + bounds.max.z) < 1e-7);
let triangles = 0, vertices = 0, minArea = Infinity, basinHeight = 0;
const parts = {};
const meshes = [];
root.traverse(o => {if (o.isMesh) meshes.push(o);});
for (const o of meshes) {
  assert.ok(spec.features.includes(o.name), 'named runtime mesh: ' + o.name);
  const geo = o.geometry, pos = geo.attributes.position, index = geo.index;
  assert.ok(geo.attributes.normal);
  assert.ok([...pos.array, ...geo.attributes.normal.array].every(Number.isFinite));
  const count = index?.count ?? pos.count;
  assert.equal(count % 3, 0);
  triangles += count / 3;
  vertices += pos.count;
  const points = Array.from({length: pos.count}, (_, i) => new Vector3().fromBufferAttribute(pos, i).applyMatrix4(o.matrixWorld));
  for (let i = 0; i < count; i += 3) {
    const tri = new Triangle(...[0, 1, 2].map(j => points[index ? index.getX(i + j) : i + j]));
    const area = tri.getArea();
    assert.ok(area > 1e-12, `nondegenerate ${o.name}/${i / 3}`);
    minArea = Math.min(minArea, area);
  }
  if (o.name === 'STONE_BasinAndBowls') {
    assert.ok(geo.attributes.color, 'original stone palette');
    basinHeight = Math.max(...points.filter(p => Math.hypot(p.x, p.z) > 2).map(p => p.y));
    assert.ok(Math.abs(basinHeight - .8) < 1e-6, 'basin coping height');
  }
  const b = new Box3().setFromObject(o, true);
  parts[o.name] = {min: b.min.toArray(), max: b.max.toArray(), triangles: count / 3};
}
for (const name of spec.features) assert.ok(root.getObjectByName(name)?.isMesh, name);
assert.ok(triangles < spec.budget.triangles);
assert.ok(bytes.length < spec.budget.bytes);

// Weld attribute seams geometrically, then count actual disconnected jet tubes.
const jets = root.getObjectByName('WATER_Jets');
const pos = jets.geometry.attributes.position, index = jets.geometry.index;
const points = Array.from({length: pos.count}, (_, i) => new Vector3().fromBufferAttribute(pos, i).applyMatrix4(jets.matrixWorld));
const keys = points.map(p => p.toArray().map(v => Math.round(v * 1e6)).join(','));
const graph = new Map(keys.map(k => [k, new Set()]));
for (let i = 0; i < index.count; i += 3) {
  const ids = [0, 1, 2].map(j => keys[index.getX(i + j)]);
  for (let j = 0; j < 3; j++) {
    graph.get(ids[j]).add(ids[(j + 1) % 3]);
    graph.get(ids[(j + 1) % 3]).add(ids[j]);
  }
}
const visited = new Set(), jetBounds = [];
for (const key of graph.keys()) {
  if (visited.has(key)) continue;
  const stack = [key], component = new Set();
  while (stack.length) {
    const next = stack.pop();
    if (visited.has(next)) continue;
    visited.add(next); component.add(next);
    for (const neighbor of graph.get(next)) if (!visited.has(neighbor)) stack.push(neighbor);
  }
  const componentPoints = points.filter((p, i) => component.has(keys[i]));
  const b = new Box3().setFromPoints(componentPoints);
  assert.ok(b.min.y < .72 && b.max.y > 1.86, 'arc rises from basin and arches above lower bowl');
  assert.ok(Math.min(...componentPoints.map(p => Math.hypot(p.x, p.z))) < .73, 'jet reaches bowl water');
  assert.ok(Math.max(...componentPoints.map(p => Math.hypot(p.x, p.z))) < 2.0, 'jet stays inside basin');
  jetBounds.push({min: b.min.toArray(), max: b.max.toArray()});
}
assert.equal(jetBounds.length, 8, 'eight actual disconnected arc tubes');
const surface = new Box3().setFromObject(root.getObjectByName('WATER_Surface'), true);
assert.ok(Math.abs(surface.getSize(new Vector3()).y - .006) < 1e-6);
assert.ok(Math.abs(surface.max.y - .638) < 1e-6);
assert.ok(surface.max.x < 2.17 && surface.max.z < 2.17, 'water disc inside basin wall');

let sourceEdit = 'NOT RUN';
if (process.argv.includes('--source-edit')) {
  const editedBytes = fs.readFileSync('/tmp/atrium-fountain-source-edit.glb');
  const edited = await new GLTFLoader().parseAsync(editedBytes.buffer.slice(editedBytes.byteOffset, editedBytes.byteOffset + editedBytes.byteLength), '');
  edited.scene.updateMatrixWorld(true);
  const moved = new Box3().setFromObject(edited.scene.getObjectByName('WATER_Jets'), true);
  const original = new Box3().setFromObject(jets, true);
  for (const edge of ['min', 'max']) assert.ok(Math.abs(moved[edge].y - original[edge].y - .02) < 1e-6);
  const same = new Box3().setFromObject(edited.scene.getObjectByName('WATER_Surface'), true);
  assert.ok(same.min.distanceTo(surface.min) < 1e-7 && same.max.distanceTo(surface.max) < 1e-7);
  sourceEdit = 'PASS: independently loaded saved-source edit; jets moved 20 mm, surface unchanged';
}

const report = {result: 'PASS', id: spec.slug, triangles, vertices, glb_bytes: bytes.length,
  meshes: doc.meshes.length, primitives: primitiveCount, materials: doc.materials.length,
  textures: 0, animations: 0, dimensions_metres: dimensions,
  basin_height_metres: basinHeight, water_surface_thickness_metres: surface.getSize(new Vector3()).y,
  bounds: {min: bounds.min.toArray(), max: bounds.max.toArray()},
  jet_components: jetBounds.length, jet_bounds: jetBounds, min_triangle_area_m2: minArea,
  sha256: createHash('sha256').update(bytes).digest('hex'),
  validation: {errors: khronos.issues.numErrors, warnings: khronos.issues.numWarnings},
  budget: spec.budget, source_edit: sourceEdit, parts};
fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
