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
assert.equal(json.materials.length, 3);
assert.ok(json.materials.every(m => (m.alphaMode ?? 'OPAQUE') === 'OPAQUE' && !m.doubleSided));
assert.ok(!json.images?.length && !json.textures?.length && !json.cameras?.length);
assert.ok(!json.animations?.length && !json.extensionsRequired?.length && !json.extensions?.KHR_lights_punctual);
assert.ok(json.buffers.every(b => !b.uri));
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName('ASSET_PeanutButterJarStand');
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(gltf.scene.children.length, 1);
let triangles = 0, meshes = 0, vertices = 0, degenerateTriangles = 0;
const materialUse = new Set();
const a = new Vector3(), b = new Vector3(), c = new Vector3();
gltf.scene.traverse(o => {
  if (!o.isMesh) return;
  meshes++;
  const g = o.geometry, p = g.attributes.position, n = g.attributes.normal;
  assert.ok(n);
  assert.ok([...p.array, ...n.array].every(Number.isFinite));
  assert.ok(Array.from({length:n.count}, (_, i) => Math.hypot(n.getX(i), n.getY(i), n.getZ(i))).every(x => Math.abs(x - 1) < 1e-4));
  vertices += p.count;
  const index = g.index;
  const count = index?.count ?? p.count;
  triangles += count / 3;
  materialUse.add(o.material.uuid);
  for (let i = 0; i < count; i += 3) {
    a.fromBufferAttribute(p, index ? index.getX(i) : i);
    b.fromBufferAttribute(p, index ? index.getX(i + 1) : i + 1);
    c.fromBufferAttribute(p, index ? index.getX(i + 2) : i + 2);
    if (b.sub(a).cross(c.sub(a)).lengthSq() < 1e-20) degenerateTriangles++;
  }
});
const bounds = new Box3().setFromObject(gltf.scene, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
assert.equal(meshes, 3);
assert.equal(materialUse.size, 3);
assert.equal(degenerateTriangles, 0);
assert.ok(triangles < 18000);
assert.ok(bytes.length < 1.5 * 1024 * 1024);
for (const [i, expected] of [0.8, 1.02, 0.5].entries()) assert.ok(Math.abs(dimensions[i] - expected) < 1e-5);
assert.ok(Math.abs(bounds.min.y) < 1e-6);
assert.ok(Math.abs(bounds.min.x + bounds.max.x) < 1e-6);
assert.ok(Math.abs(bounds.min.z + bounds.max.z) < 1e-6);
const report = {
  result: 'PASS', id: 'peanut-butter-jar-stand', bytes: bytes.length, triangles, vertices,
  meshes, mesh_primitives: json.meshes.reduce((s, m) => s + m.primitives.length, 0),
  materials: json.materials.length, textures: 0, animations: 0, degenerate_triangles: degenerateTriangles,
  dimensions_m: {width: dimensions[0], height: dimensions[1], depth: dimensions[2]},
  bounds: {min: bounds.min.toArray(), max: bounds.max.toArray()},
  sha256: createHash('sha256').update(bytes).digest('hex'),
  validation: {errors: validation.issues.numErrors, warnings: validation.issues.numWarnings, infos: validation.issues.numInfos},
  budget: {triangles_exclusive: 18000, bytes_exclusive: 1572864, materials_max: 3, mesh_primitives_max: 3},
};
fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
