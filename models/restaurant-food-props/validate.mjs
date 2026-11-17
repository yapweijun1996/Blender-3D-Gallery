import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const spec = JSON.parse(fs.readFileSync(dir + 'backlog.json'));
const bytes = fs.readFileSync(process.argv[2] ?? dir + 'exports/optimized.glb');
const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes), { uri: 'optimized.glb', maxIssues: 100 });
if (!process.argv[2]) fs.writeFileSync(dir + 'reports/khronos.json', JSON.stringify(validation, null, 2) + '\n');
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
assert.ok(json.buffers.every(b => !b.uri));
for (const field of ['images', 'textures', 'cameras', 'animations', 'skins']) assert.equal(json[field]?.length ?? 0, 0, field);
assert.ok(!json.extensions?.KHR_lights_punctual);
assert.ok(json.materials.length <= spec.budget.materials);
assert.ok(json.materials.every(m => (m.alphaMode ?? 'OPAQUE') === 'OPAQUE'));
assert.ok(json.meshes.every(m => m.primitives.every(p => p.attributes.COLOR_0 !== undefined)));
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName(spec.root);
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.service_items, 10);
assert.equal(root.userData.front_axis, 'Blender -Y / glTF +Z');
let triangles = 0, vertices = 0, meshes = 0;
const a = new Vector3(), b = new Vector3(), c = new Vector3();
const parts = {};
gltf.scene.traverse(obj => {
  if (!obj.isMesh) return;
  meshes++;
  const p = obj.geometry.attributes.position, n = obj.geometry.attributes.normal, index = obj.geometry.index;
  assert.ok(n && obj.geometry.attributes.color);
  assert.ok([...p.array, ...n.array].every(Number.isFinite));
  assert.ok([...obj.geometry.attributes.color.array].every(value => Number.isFinite(value) && value >= 0 && value <= 1));
  vertices += p.count;
  const count = index?.count ?? p.count;
  triangles += count / 3;
  for (let i = 0; i < count; i += 3) {
    a.fromBufferAttribute(p, index ? index.getX(i) : i);
    b.fromBufferAttribute(p, index ? index.getX(i + 1) : i + 1);
    c.fromBufferAttribute(p, index ? index.getX(i + 2) : i + 2);
    assert.ok(b.sub(a).cross(c.sub(a)).lengthSq() > 1e-20, `${obj.name}: degenerate triangle`);
  }
  const bounds = new Box3().setFromObject(obj, true);
  parts[obj.name] = { triangles: count / 3, pivot: obj.position.toArray(), min: bounds.min.toArray(), max: bounds.max.toArray() };
  if (obj.name !== 'TRAY_Serving') {
    assert.ok(bounds.min.x > -.478 && bounds.max.x < .478, `${obj.name}: tray X containment`);
    assert.ok(bounds.min.z > -.278 && bounds.max.z < .278, `${obj.name}: tray Z containment`);
    assert.ok(bounds.min.y >= .0129, `${obj.name}: tray deck contact`);
  }
});
const primitives = json.meshes.reduce((n, m) => n + m.primitives.length, 0);
const bounds = new Box3().setFromObject(gltf.scene, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
assert.ok(Math.abs(dimensions[0] - 1) < 1e-6);
assert.ok(Math.abs(dimensions[2] - .6) < 1e-6);
assert.ok(Math.abs(bounds.min.y) < 1e-6);
assert.ok(Math.abs(bounds.min.x + bounds.max.x) < 1e-6);
assert.ok(Math.abs(bounds.min.z + bounds.max.z) < 1e-6);
assert.ok(bytes.length <= spec.budget.bytes);
assert.ok(triangles <= spec.budget.triangles);
assert.equal(meshes, 11);
assert.equal(primitives, 11);
for (const name of spec.features) assert.ok(parts[name], `Required service component: ${name}`);
const report = {
  result: 'PASS', id: spec.slug, glb_bytes: bytes.length, triangles, vertices, meshes, primitives,
  materials: json.materials.length, images: 0, animations: 0, dimensions,
  axis_order: 'glTF X,Y,Z (width,height,depth)', bounds: { min: bounds.min.toArray(), max: bounds.max.toArray() },
  sha256: createHash('sha256').update(bytes).digest('hex'), budget: spec.budget,
  validation: { errors: validation.issues.numErrors, warnings: validation.issues.numWarnings }, parts,
  checks: ['Floor-centred 1.0 x 0.6 metre tray', 'Ten named independently movable service meshes',
    'Finite vertex colours and normals; no degenerate triangles', 'All dishes contained by tray deck',
    'Shared opaque vertex-colour material; no images, external resources, cameras, lights or animation'],
};
if (!process.argv[2]) {
  fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
} else {
  const original = JSON.parse(fs.readFileSync(dir + 'reports/assets.json'));
  assert.notEqual(report.sha256, original.sha256, 'Saved source edit changes exported bytes');
  const width = part => part.max[0] - part.min[0];
  const ratio = width(parts.DISH_Sauce_Ramekin) / width(original.parts.DISH_Sauce_Ramekin);
  assert.ok(Math.abs(ratio - .92) < 1e-5, 'Reopened source retains actual mesh edit');
  assert.ok(json.materials.every(m => Math.abs(m.pbrMetallicRoughness.roughnessFactor - .77) < 1e-5));
  for (const [name, part] of Object.entries(parts)) {
    if (name === 'DISH_Sauce_Ramekin') continue;
    for (const field of ['min', 'max']) part[field].forEach((v, i) =>
      assert.ok(Math.abs(v - original.parts[name][field][i]) < 1e-6, `Unrelated geometry unchanged: ${name}`));
  }
  fs.writeFileSync(dir + 'reports/source-edit.json', JSON.stringify({ result: 'PASS',
    source_sha256: original.sha256, edited_sha256: report.sha256, ramekin_width_ratio: ratio,
    roughness: json.materials[0].pbrMetallicRoughness.roughnessFactor,
    unrelated_components_unchanged: 10, validation: report.validation }, null, 2) + '\n');
}
console.log(JSON.stringify(report));
