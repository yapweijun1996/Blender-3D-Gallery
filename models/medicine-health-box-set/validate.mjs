// Adapted from the self-checkout-machine quality gate for a three-draw static prop.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const bytes = fs.readFileSync(dir + 'exports/optimized.glb');
const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes), { maxIssues: 100 });
fs.writeFileSync(dir + 'reports/khronos.json', JSON.stringify(validation, null, 2) + '\n');
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
assert.ok(json.buffers.every(buffer => !buffer.uri));
assert.ok(!json.images?.length && !json.textures?.length && !json.cameras?.length);
assert.ok(!json.extensions?.KHR_lights_punctual);
assert.equal(json.materials.length, 3);
assert.ok(json.materials.every(m => (m.alphaMode ?? 'OPAQUE') === 'OPAQUE' && !m.doubleSided));
const loader = new GLTFLoader();
const load = data => loader.parseAsync(data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength), '');
const gltf = await load(bytes);
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName('ASSET_MedicineHealthBoxSet');
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.carton_count, 20);
assert.equal(root.userData.bottle_count, 6);
assert.equal(root.userData.tier_count, 5);
assert.equal(gltf.animations.length, 0);
let triangles = 0, vertices = 0, primitives = 0;
const parts = {};
gltf.scene.traverse(object => {
  if (!object.isMesh) return;
  const geometry = object.geometry, position = geometry.attributes.position, index = geometry.index;
  assert.ok(geometry.attributes.normal && geometry.attributes.color);
  assert.ok([...position.array, ...geometry.attributes.normal.array].every(Number.isFinite));
  const count = index?.count ?? position.count;
  assert.equal(count % 3, 0);
  const a = new Vector3(), b = new Vector3(), c = new Vector3();
  for (let i = 0; i < count; i += 3) {
    a.fromBufferAttribute(position, index ? index.getX(i) : i);
    b.fromBufferAttribute(position, index ? index.getX(i + 1) : i + 1);
    c.fromBufferAttribute(position, index ? index.getX(i + 2) : i + 2);
    assert.ok(b.sub(a).cross(c.sub(a)).lengthSq() > 1e-20, 'nondegenerate triangle');
  }
  triangles += count / 3;
  vertices += position.count;
  primitives += Math.max(1, geometry.groups.length);
  const bounds = new Box3().setFromObject(object, true);
  parts[object.name] = { min: bounds.min.toArray(), max: bounds.max.toArray(), triangles: count / 3 };
});
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-5, `${a} != ${b}`);
const bounds = new Box3().setFromObject(root, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
for (const [axis, expected] of [.6, 1.7, .35].entries()) near(dimensions[axis], expected);
near(bounds.min.y, 0);
near(bounds.min.x + bounds.max.x, 0);
near(bounds.min.z + bounds.max.z, 0);
for (const name of ['BATCH_Powdercoat', 'BATCH_Plaincartonpaper', 'BATCH_Opaquebottlepolymer']) assert.ok(gltf.scene.getObjectByName(name));
assert.ok(triangles < 18000);
assert.ok(bytes.length < 1.5 * 1024 * 1024);
assert.equal(primitives, 3);
const source = JSON.parse(fs.readFileSync(dir + 'reports/sources.json'));
assert.equal(source.result, 'PASS');
assert.equal(source.carton_count, 20);
assert.equal(source.bottle_count, 6);
assert.deepEqual(source.cartons_bottom_to_top, [4, 4, 4, 4, 4]);
assert.deepEqual(source.bottles_bottom_to_top, [0, 0, 2, 2, 2]);
// An independent runtime loader confirms that a saved source edit survives batching.
const editedBytes = fs.readFileSync(source.edited_glb);
const editedValidation = await validator.validateBytes(new Uint8Array(editedBytes));
assert.equal(editedValidation.issues.numErrors + editedValidation.issues.numWarnings, 0);
const edited = await load(editedBytes);
let movedVertices = 0;
gltf.scene.traverse(object => {
  if (!object.isMesh) return;
  const before = object.geometry.attributes.position;
  const after = edited.scene.getObjectByName(object.name).geometry.attributes.position;
  assert.equal(before.count, after.count);
  for (let i = 0; i < before.count; i++) {
    const dx = after.getX(i) - before.getX(i);
    near(after.getY(i), before.getY(i));
    near(after.getZ(i), before.getZ(i));
    if (Math.abs(dx) > 1e-6) {
      assert.equal(object.name, 'BATCH_Plaincartonpaper');
      near(dx, .005);
      movedVertices++;
    }
  }
});
assert.ok(movedVertices > 0);
const report = {
  result: 'PASS', id: 'medicine-health-box-set', glb_bytes: bytes.length,
  triangles, vertices, meshes: json.meshes.length, primitives,
  materials: json.materials.length, images: json.images?.length ?? 0,
  animations: gltf.animations.length, dimensions,
  dimensions_order: 'width, height, depth (glTF X,Y,Z)',
  bounds: { min: bounds.min.toArray(), max: bounds.max.toArray() },
  sha256: createHash('sha256').update(bytes).digest('hex'),
  validation: { errors: validation.issues.numErrors, warnings: validation.issues.numWarnings },
  source_edit: { result: 'PASS', moved_vertices: movedVertices, delta_x_m: .005 }, parts,
};
fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
if (process.argv.includes('--update-metadata')) {
  const metadataPath = dir + 'metadata/medicine-health-box-set.json';
  const metadata = JSON.parse(fs.readFileSync(metadataPath));
  metadata.dimensions = { units: 'metres', axis_order: report.dimensions_order, size: dimensions, bounds: report.bounds };
  metadata.statistics = Object.fromEntries(['glb_bytes', 'triangles', 'vertices', 'meshes', 'primitives', 'materials', 'images', 'animations', 'sha256'].map(key => [key, report[key]]));
  Object.assign(metadata.statistics, {
    carton_count: source.carton_count, bottle_count: source.bottle_count, tier_count: source.tier_count,
    cartons_bottom_to_top: source.cartons_bottom_to_top, bottles_bottom_to_top: source.bottles_bottom_to_top,
    editable_mesh_parts: source.closed_manifold_parts,
  });
  fs.writeFileSync(metadataPath, JSON.stringify(metadata, null, 2) + '\n');
}
