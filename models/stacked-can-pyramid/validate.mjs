// Preserve the existing Khronos/loader gates and enforce the owner's P1 budget.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';
import { loadCatalog } from '../../scripts/catalog.mjs';

const dir = fileURLToPath(new URL('.', import.meta.url));
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-5, `${a} != ${b}`);
const variants = [];
let referenceGeometry;
const catalog = loadCatalog();
for (const [variant, filename, id] of [
  ['variant_a', 'optimized.glb', 'stacked-can-pyramid'],
  ['variant_b', 'optimized-variant-b.glb', 'stacked-can-pyramid-variant-b'],
]) {
  const bytes = fs.readFileSync(dir + 'exports/' + filename);
  const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
  const validation = await validator.validateBytes(new Uint8Array(bytes), { maxIssues: 100 });
  fs.writeFileSync(dir + `reports/khronos${variant === 'variant_a' ? '' : '-variant-b'}.json`, JSON.stringify(validation, null, 2) + '\n');
  assert.equal(validation.issues.numErrors, 0);
  assert.equal(validation.issues.numWarnings, 0);
  assert.ok(json.buffers.every(buffer => !buffer.uri));
  assert.ok(!json.images?.length && !json.textures?.length && !json.cameras?.length);
  assert.ok(!json.extensions?.KHR_lights_punctual);
  assert.equal(json.materials.length, 2);
  assert.ok(json.materials.some(m => m.name === variant));
  assert.ok(json.materials.every(m => (m.alphaMode ?? 'OPAQUE') === 'OPAQUE' && !m.doubleSided));
  assert.equal(json.meshes.length, 2, 'one merged display and one hidden collider');
  const geometryBytes = bytes.subarray(28 + bytes.readUInt32LE(12));
  const geometryHash = createHash('sha256').update(geometryBytes).digest('hex');
  if (referenceGeometry) assert.equal(geometryHash, referenceGeometry, 'variants share identical geometry');
  referenceGeometry = geometryHash;
  const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
  gltf.scene.updateMatrixWorld(true);
  const root = gltf.scene.getObjectByName('ASSET_StackedCanPyramid');
  assert.ok(root);
  assert.deepEqual(root.position.toArray(), [0, 0, 0]);
  assert.equal(root.userData.units, 'metres');
  assert.equal(root.userData.can_count, 91);
  assert.equal(root.userData.radial_segments, 8);
  assert.equal(root.userData.variant, variant);
  assert.equal(gltf.animations.length, 0);
  assert.equal(gltf.scenes.length, 2);
  assert.equal(gltf.scene.getObjectByName('collider_box'), undefined, 'collider hidden from default scene');
  const colliderNode = json.nodes.find(n => n.name === 'collider_box');
  assert.ok(colliderNode.extras.collision_only && colliderNode.extras.visible === false);
  assert.ok(json.meshes[colliderNode.mesh].primitives.every(p => p.material === undefined), 'collider has no material');
  const collisionScene = gltf.scenes[1];
  collisionScene.updateMatrixWorld(true);
  const collider = collisionScene.getObjectByName('collider_box');
  assert.ok(collider);
  const colliderBounds = new Box3().setFromObject(collider, true);
  for (const [i, expected] of [1, 1.4, 1].entries()) near(colliderBounds.getSize(new Vector3()).getComponent(i), expected);
  near(colliderBounds.min.y, 0);
  assert.ok(root.getObjectByName('DISPLAY_MergedCansAndPlinth'));
  let triangles = 0, vertices = 0, primitives = 0, visibleTriangles = 0, visiblePrimitives = 0;
  const parts = {}, geometry = new Set();
  for (const scene of gltf.scenes) scene.traverse(object => {
    if (!object.isMesh || geometry.has(object.geometry)) return;
    geometry.add(object.geometry);
    const g = object.geometry, position = g.attributes.position, index = g.index;
    assert.ok(g.attributes.normal);
    assert.ok([...position.array, ...g.attributes.normal.array].every(Number.isFinite));
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
    primitives += Math.max(1, g.groups.length);
    if (scene === gltf.scene) {
      visibleTriangles += count / 3;
      visiblePrimitives += Math.max(1, g.groups.length);
    }
    const partBounds = new Box3().setFromObject(object, true);
    parts[object.name] = { min: partBounds.min.toArray(), max: partBounds.max.toArray(), triangles: count / 3 };
  });
  const bounds = new Box3().setFromObject(root, true);
  const dimensions = bounds.getSize(new Vector3()).toArray();
  for (const [axis, expected] of [1, 1.4, 1].entries()) near(dimensions[axis], expected);
  near(bounds.min.y, 0);
  near(bounds.min.x + bounds.max.x, 0);
  near(bounds.min.z + bounds.max.z, 0);
  assert.ok(triangles <= 8000, 'whole GLB including collider');
  assert.ok(bytes.length < 1.5 * 1024 * 1024);
  assert.equal(visiblePrimitives, 2);
  assert.ok(visiblePrimitives <= 6);
  const asset = catalog.collections.flatMap(c => c.assets).find(a => a.id === id);
  assert.ok(asset && asset.file.endsWith('/' + filename));
  assert.equal(asset.triangles, triangles);
  assert.equal(asset.materials, 2);
  assert.equal(asset.details.statistics.triangles, triangles);
  const label = json.materials.find(m => m.name === variant).pbrMetallicRoughness.baseColorFactor;
  variants.push({ variant, id, file: 'exports/' + filename, glb_bytes: bytes.length,
    triangles, visible_triangles: visibleTriangles, vertices, meshes: json.meshes.length, primitives,
    visible_primitives: visiblePrimitives, materials: json.materials.length, images: 0,
    animations: gltf.animations.length, dimensions,
    dimensions_order: 'width, height, depth (glTF X,Y,Z)',
    bounds: { min: bounds.min.toArray(), max: bounds.max.toArray() },
    sha256: createHash('sha256').update(bytes).digest('hex'),
    geometry_sha256: geometryHash, label_color_linear: label,
    validation: { errors: validation.issues.numErrors, warnings: validation.issues.numWarnings }, parts,
    collider: { name: 'collider_box', scene: 1, hidden_from_default: true, material: null, triangles: 12 },
  });
}
assert.notDeepEqual(variants[0].label_color_linear, variants[1].label_color_linear);
const report = { result: 'PASS', id: 'stacked-can-pyramid', spec: 'Owner P1 override 2026-11-17', variants };
fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
