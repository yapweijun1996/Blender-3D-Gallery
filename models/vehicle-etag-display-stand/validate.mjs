import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const spec = JSON.parse(fs.readFileSync(dir + 'backlog.json'));
const bytes = fs.readFileSync(dir + 'exports/optimized.glb');
const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes), { uri: 'optimized.glb', maxIssues: 100 });
fs.writeFileSync(dir + 'reports/khronos.json', JSON.stringify(validation, null, 2) + '\n');
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
assert.ok(json.buffers.every(b => !b.uri));
assert.equal(json.images?.length ?? 0, 0);
assert.equal(json.textures?.length ?? 0, 0);
assert.equal(json.cameras?.length ?? 0, 0);
assert.equal(json.animations?.length ?? 0, 0);
assert.ok(!json.extensions?.KHR_lights_punctual);
assert.ok(json.materials.length <= spec.budget.materials);
assert.ok(json.materials.every(m => (m.alphaMode ?? 'OPAQUE') === 'OPAQUE'));
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName(spec.root);
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.tag_count, 6);
let triangles = 0, vertices = 0, meshes = 0;
const a = new Vector3(), b = new Vector3(), c = new Vector3();
gltf.scene.traverse(obj => {
  if (!obj.isMesh) return;
  meshes++;
  const p = obj.geometry.attributes.position, n = obj.geometry.attributes.normal, index = obj.geometry.index;
  assert.ok(n);
  assert.ok([...p.array, ...n.array].every(Number.isFinite));
  vertices += p.count;
  const count = index?.count ?? p.count;
  triangles += count / 3;
  for (let i = 0; i < count; i += 3) {
    a.fromBufferAttribute(p, index ? index.getX(i) : i);
    b.fromBufferAttribute(p, index ? index.getX(i + 1) : i + 1);
    c.fromBufferAttribute(p, index ? index.getX(i + 2) : i + 2);
    assert.ok(b.sub(a).cross(c.sub(a)).lengthSq() > 1e-18, 'Non-degenerate triangles');
  }
});
const primitives = json.meshes.reduce((n, m) => n + m.primitives.length, 0);
const bounds = new Box3().setFromObject(gltf.scene, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
for (const [i, expected] of [0.5, 0.4, 0.35].entries()) assert.ok(Math.abs(dimensions[i] - expected) < 1e-5);
assert.ok(Math.abs(bounds.min.y) < 1e-6, 'Floor datum');
assert.ok(Math.abs(bounds.min.x + bounds.max.x) < 1e-6, 'Centred X origin');
assert.ok(Math.abs(bounds.min.z + bounds.max.z) < 1e-6, 'Centred Z origin');
assert.ok(bytes.length <= spec.budget.bytes);
assert.ok(triangles <= spec.budget.triangles);
assert.equal(meshes, 3);
assert.equal(primitives, 3);
const report = {
  result: 'PASS', id: spec.slug, glb_bytes: bytes.length, triangles, vertices, meshes, primitives,
  materials: json.materials.length, images: json.images?.length ?? 0, animations: gltf.animations.length,
  dimensions, axis_order: 'glTF X,Y,Z (width,height,depth)', bounds: { min: bounds.min.toArray(), max: bounds.max.toArray() },
  sha256: createHash('sha256').update(bytes).digest('hex'), budget: spec.budget,
  validation: { errors: validation.issues.numErrors, warnings: validation.issues.numWarnings },
  checks: ['Exact metric envelope and floor-centred origin', 'Finite normals and positions', 'Non-degenerate triangles',
    'Three opaque shared materials and three primitives', 'No external resources, textures, cameras, lights or animation'],
};
fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
