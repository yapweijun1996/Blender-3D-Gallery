// Asset-specific adaptation of the self-checkout-machine quality gate.
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
assert.ok(json.materials.every(m => !m.alphaMode || m.alphaMode === 'OPAQUE'));
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName('ASSET_FashionClothingRack');
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.front_axis, 'Blender -Y / glTF +Z');
assert.equal(gltf.animations.length, 0);
let triangles = 0, vertices = 0, primitives = 0;
const parts = {};
gltf.scene.traverse(object => {
  if (!object.isMesh) return;
  const geometry = object.geometry, position = geometry.attributes.position, index = geometry.index;
  assert.ok(geometry.attributes.normal);
  assert.ok([...position.array, ...geometry.attributes.normal.array].every(Number.isFinite));
  if (object.name !== 'BATCH_BrushedMetal') assert.ok(geometry.attributes.color);
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
assert.ok(dimensions[0] > 2.6 && dimensions[0] < 3);
near(dimensions[1], 1.6);
assert.ok(dimensions[2] > .95 && dimensions[2] < 1.15);
near(bounds.min.y, 0);
near(bounds.min.x + bounds.max.x, 0);
near(bounds.min.z + bounds.max.z, 0);
for (const name of ['BATCH_Cotton', 'BATCH_MatteSurface', 'BATCH_BrushedMetal']) assert.ok(parts[name]);
assert.equal(json.meshes.length, 3);
assert.ok(triangles < 20000 && bytes.length < 1572864 && primitives === 3);
const report = { result: 'PASS', id: 'fashion-clothing-rack',
  glb_bytes: bytes.length, triangles, vertices, meshes: json.meshes.length, primitives,
  materials: json.materials.length, images: json.images?.length ?? 0, animations: gltf.animations.length,
  dimensions, bounds: { min: bounds.min.toArray(), max: bounds.max.toArray() },
  sha256: createHash('sha256').update(bytes).digest('hex'),
  validation: { errors: validation.issues.numErrors, warnings: validation.issues.numWarnings }, parts };
fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
const metadataPath = dir + 'metadata/fashion-clothing-rack.json';
if (fs.existsSync(metadataPath)) {
  const metadata = JSON.parse(fs.readFileSync(metadataPath));
  metadata.dimensions = { units: 'metres', axis_order: 'glTF X,Y,Z (width,height,depth)', size: dimensions, bounds: report.bounds };
  metadata.statistics = Object.fromEntries(['glb_bytes', 'triangles', 'vertices', 'meshes', 'primitives', 'materials', 'images', 'animations', 'sha256'].map(key => [key, report[key]]));
  fs.writeFileSync(metadataPath, JSON.stringify(metadata, null, 2) + '\n');
}
console.log(JSON.stringify(report, null, 2));
