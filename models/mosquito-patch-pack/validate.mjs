// Adapted from the self-checkout-machine gate; actual geometry drives all statistics.
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
assert.equal(json.materials.filter(m => m.alphaMode === 'BLEND').length, 1);
assert.ok(json.materials.every(m => !m.doubleSided && !m.extensions?.KHR_materials_transmission));
const loader = new GLTFLoader();
const load = data => loader.parseAsync(data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength), '');
const gltf = await load(bytes);
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName('ASSET_MosquitoPatchPack');
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(gltf.animations.length, 0);
let triangles = 0, vertices = 0, primitives = 0;
const parts = {};
gltf.scene.traverse(object => {
  if (!object.isMesh) return;
  const geometry = object.geometry, position = geometry.attributes.position, index = geometry.index;
  assert.ok(geometry.attributes.normal);
  assert.ok([...position.array, ...geometry.attributes.normal.array].every(Number.isFinite));
  const count = index?.count ?? position.count;
  assert.equal(count % 3, 0);
  const a = new Vector3(), b = new Vector3(), c = new Vector3();
  for (let i = 0; i < count; i += 3) {
    a.fromBufferAttribute(position, index ? index.getX(i) : i);
    b.fromBufferAttribute(position, index ? index.getX(i + 1) : i + 1);
    c.fromBufferAttribute(position, index ? index.getX(i + 2) : i + 2);
    assert.ok(b.sub(a).cross(c.sub(a)).lengthSq() > 1e-22, 'nondegenerate triangle');
  }
  triangles += count / 3;
  vertices += position.count;
  primitives += Math.max(1, geometry.groups.length);
  const bounds = new Box3().setFromObject(object, true);
  parts[object.name] = { min: bounds.min.toArray(), max: bounds.max.toArray(), triangles: count / 3 };
});
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-6, `${a} != ${b}`);
const bounds = new Box3().setFromObject(root, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
for (const [axis, expected] of [.5, .35, .3].entries()) near(dimensions[axis], expected);
near(bounds.min.y, 0);
near(bounds.min.x + bounds.max.x, 0);
near(bounds.min.z + bounds.max.z, 0);
assert.ok(triangles < 12000);
assert.ok(bytes.length < 1.5 * 1024 * 1024);
assert.equal(primitives, 3);
const source = JSON.parse(fs.readFileSync(dir + 'reports/sources.json'));
assert.equal(source.result, 'PASS');
assert.equal(source.regular_pack_count, 16);
assert.equal(source.hero_pack_count, 1);
assert.equal(source.patch_count, 102);
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
    near(after.getY(i), before.getY(i));
    near(after.getZ(i), before.getZ(i));
    const dx = after.getX(i) - before.getX(i);
    if (Math.abs(dx) > 1e-6) { near(dx, .004); movedVertices++; }
  }
});
assert.ok(movedVertices > 0);
const report = {
  result: 'PASS', id: 'mosquito-patch-pack', glb_bytes: bytes.length,
  triangles, vertices, meshes: json.meshes.length, primitives,
  materials: json.materials.length, images: json.images?.length ?? 0,
  animations: gltf.animations.length, dimensions,
  dimensions_order: 'width, height, depth (glTF X,Y,Z)',
  bounds: { min: bounds.min.toArray(), max: bounds.max.toArray() },
  sha256: createHash('sha256').update(bytes).digest('hex'),
  validation: { errors: validation.issues.numErrors, warnings: validation.issues.numWarnings },
  zero_area_triangles: 0, source_edit: { result: 'PASS', moved_vertices: movedVertices, delta_x_m: .004 }, parts,
};
fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
if (process.argv.includes('--update-metadata')) {
  const metadataPath = dir + 'metadata/mosquito-patch-pack.json';
  const metadata = JSON.parse(fs.readFileSync(metadataPath));
  metadata.dimensions = { units: 'metres', axis_order: report.dimensions_order, size: dimensions, bounds: report.bounds };
  metadata.statistics = Object.fromEntries(['glb_bytes', 'triangles', 'vertices', 'meshes', 'primitives', 'materials', 'images', 'animations', 'sha256', 'zero_area_triangles'].map(key => [key, report[key]]));
  Object.assign(metadata.statistics, {
    regular_pack_count: source.regular_pack_count, hero_pack_count: source.hero_pack_count,
    patch_count: source.patch_count, editable_mesh_parts: source.closed_manifold_parts,
    regular_card_width_height_m: source.items[0].card_width_height_m,
    hero_card_width_height_m: source.items.at(-1).card_width_height_m,
  });
  fs.writeFileSync(metadataPath, JSON.stringify(metadata, null, 2) + '\n');
}
