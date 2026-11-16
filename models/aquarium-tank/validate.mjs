// Asset gate based on self-checkout-machine/validate.mjs.
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
const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes), {uri: 'optimized.glb'});
fs.writeFileSync(dir + 'reports/khronos.json', JSON.stringify(validation, null, 2) + '\n');
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
assert.ok(json.buffers.every(b => !b.uri));
assert.ok(!json.images?.length && !json.textures?.length && !json.cameras?.length);
assert.ok(!json.extensions?.KHR_lights_punctual);
assert.equal(json.materials.length, 3);
assert.equal(json.meshes.length, 3);
const primitives = json.meshes.reduce((n, m) => n + m.primitives.length, 0);
assert.equal(primitives, 3);
const opaque = json.materials.find(m => m.name === 'Opaque vertex palette');
assert.ok(opaque && (opaque.alphaMode ?? 'OPAQUE') === 'OPAQUE');
assert.ok(json.meshes.find(m => m.name === 'DETAILS_Opaque').primitives[0].attributes.COLOR_0 !== undefined);
for (const name of ['Clear pale glass', 'Transparent aqua water']) {
  const m = json.materials.find(m => m.name === name);
  assert.equal(m.alphaMode, 'BLEND');
  assert.ok(m.pbrMetallicRoughness.baseColorFactor[3] > 0 && m.pbrMetallicRoughness.baseColorFactor[3] < .15);
}
assert.ok(!json.extensionsUsed?.includes('KHR_materials_transmission'));
const loader = new GLTFLoader();
const g = await loader.parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
g.scene.updateMatrixWorld(true);
const root = g.scene.getObjectByName(spec.root);
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.front_axis, 'Blender -Y / glTF +Z');
assert.equal(g.animations.length, 0);
const bounds = new Box3().setFromObject(root, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
const expected = [spec.dimensions[0], spec.dimensions[2], spec.dimensions[1]];
for (let i = 0; i < 3; i++) assert.ok(Math.abs(dimensions[i] - expected[i]) < 1e-6, `metre envelope axis ${i}: ${dimensions[i]}`);
assert.ok(Math.abs(bounds.min.y) < 1e-7);
for (const axis of ['x', 'z']) assert.ok(Math.abs(bounds.min[axis] + bounds.max[axis]) < 1e-7, 'floor centre');
const anchor = root.getObjectByName('ANCHOR_Fish').getWorldPosition(new Vector3());
assert.ok(anchor.distanceTo(new Vector3(0, .98, .05)) < 1e-6);
const swim = new Box3(root.getObjectByName('SWIM_Min').getWorldPosition(new Vector3()),
  root.getObjectByName('SWIM_Max').getWorldPosition(new Vector3()));
assert.ok(swim.containsPoint(anchor));
let triangles = 0, vertices = 0, minArea = Infinity, swimIntersections = 0;
const parts = {};
root.traverse(o => {
  if (!o.isMesh) return;
  const geo = o.geometry, pos = geo.attributes.position, index = geo.index;
  assert.ok(geo.attributes.normal);
  assert.ok([...pos.array, ...geo.attributes.normal.array].every(Number.isFinite));
  const count = index?.count ?? pos.count;
  vertices += pos.count;
  triangles += count / 3;
  const points = Array.from({length: pos.count}, (_, i) => new Vector3().fromBufferAttribute(pos, i).applyMatrix4(o.matrixWorld));
  for (let i = 0; i < count; i += 3) {
    const tri = new Triangle(...[0, 1, 2].map(j => points[index ? index.getX(i + j) : i + j]));
    const area = tri.getArea();
    assert.ok(area > 1e-13, `nondegenerate triangle ${o.name}/${i / 3}`);
    minArea = Math.min(minArea, area);
    if (o.name.startsWith('EXPORT_DETAILS') && swim.intersectsTriangle(tri)) swimIntersections++;
  }
  const b = new Box3().setFromObject(o, true);
  parts[o.name] = {min: b.min.toArray(), max: b.max.toArray(), triangles: count / 3};
});
assert.equal(swimIntersections, 0, 'reserved swim volume is clear of opaque geometry');
for (const feature of spec.features) assert.ok(Object.keys(parts).some(name => name.startsWith('EXPORT_' + feature)));
assert.ok(triangles < spec.budget.triangles);
assert.ok(bytes.length < spec.budget.bytes);
let sourceEdit = 'NOT RUN';
if (process.argv.includes('--source-edit')) {
  const editedBytes = fs.readFileSync('/tmp/aquarium-tank-source-edit.glb');
  const edited = await loader.parseAsync(editedBytes.buffer.slice(editedBytes.byteOffset, editedBytes.byteOffset + editedBytes.byteLength), '');
  edited.scene.updateMatrixWorld(true);
  const editedBounds = new Box3().setFromObject(edited.scene, true);
  assert.ok(editedBounds.max.z > bounds.max.z + .03, 'saved-source door edit reaches the GLB');
  assert.ok(edited.scene.getObjectByName('ANCHOR_Fish').getWorldPosition(new Vector3()).distanceTo(anchor) < 1e-6);
  sourceEdit = 'PASS: reopened source, moved a door outward 40 mm, re-exported and independently loaded; original preserved';
}
const report = {
  result: 'PASS', id: spec.slug, glb_bytes: bytes.length, triangles, vertices,
  meshes: json.meshes.length, primitives, materials: json.materials.length,
  textures: 0, animations: 0, dimensions,
  bounds: {min: bounds.min.toArray(), max: bounds.max.toArray()},
  fish_anchor_metres: anchor.toArray(),
  reserved_swim_bounds: {min: swim.min.toArray(), max: swim.max.toArray()},
  opaque_swim_intersections: swimIntersections, min_triangle_area_m2: minArea,
  sha256: createHash('sha256').update(bytes).digest('hex'),
  validation: {errors: validation.issues.numErrors, warnings: validation.issues.numWarnings},
  budget: spec.budget, source_edit: sourceEdit, parts
};
fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
