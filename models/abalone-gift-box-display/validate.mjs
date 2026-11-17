// Independent delivered-GLB quality gate, based on self-checkout-machine.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const here = fileURLToPath(new URL('.', import.meta.url));
const bytes = fs.readFileSync(here + 'exports/optimized.glb');
const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes), { maxIssues: 200 });
fs.writeFileSync(here + 'reports/khronos.json', JSON.stringify(validation, null, 2) + '\n');
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName('ASSET_AbaloneGiftBoxDisplay');
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.gift_boxes, 12);
assert.equal(root.userData.plain_cans, 24);
assert.equal(gltf.animations.length, 0);
assert.equal(json.materials.length, 3);
assert.ok(!json.images?.length && !json.textures?.length && !json.cameras?.length && !json.extensions?.KHR_lights_punctual);
assert.ok(json.buffers.every(b => !b.uri));
assert.ok(json.materials.every(m => !m.doubleSided));
const clear = json.materials.find(m => m.name === 'SharedClearLid');
assert.equal(clear.alphaMode, 'BLEND');
assert.ok(clear.pbrMetallicRoughness.baseColorFactor[3] <= .15);
let triangles = 0, vertices = 0, primitives = 0, degenerates = 0;
const a = new Vector3(), b = new Vector3(), c = new Vector3();
gltf.scene.traverse(o => {
  if (!o.isMesh) return;
  primitives++;
  const geometry = o.geometry, position = geometry.attributes.position;
  assert.ok(geometry.attributes.normal);
  assert.ok([...position.array].every(Number.isFinite));
  assert.ok([...geometry.attributes.normal.array].every(Number.isFinite));
  vertices += position.count;
  const count = geometry.index?.count ?? position.count;
  triangles += count / 3;
  for (let i = 0; i < count; i += 3) {
    const at = j => geometry.index ? geometry.index.getX(j) : j;
    a.fromBufferAttribute(position, at(i));
    b.fromBufferAttribute(position, at(i + 1));
    c.fromBufferAttribute(position, at(i + 2));
    if (b.sub(a).cross(c.sub(a)).lengthSq() < 1e-18) degenerates++;
  }
  if (o.material.name === 'SharedLacquer') {
    assert.ok(geometry.attributes.color, 'lacquer variants retain vertex colors');
    const colors = new Set();
    for (let i = 0; i < geometry.attributes.color.count; i++) {
      colors.add([0, 1, 2].map(k => geometry.attributes.color.array[i * geometry.attributes.color.itemSize + k].toFixed(3)).join(','));
    }
    assert.equal(colors.size, 4, 'red, gold, black, blank ivory card');
  }
});
assert.equal(primitives, 3);
assert.equal(degenerates, 0);
assert.ok(triangles < 20000);
assert.ok(bytes.length < 1.5 * 1024 * 1024);
const bounds = new Box3().setFromObject(gltf.scene, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
for (const [i, expected] of [1, .9, .5].entries()) assert.ok(Math.abs(dimensions[i] - expected) < .0001);
assert.ok(Math.abs(bounds.min.y) < 1e-6);
assert.ok(Math.abs(bounds.min.x + bounds.max.x) < 1e-6);
assert.ok(Math.abs(bounds.min.z + bounds.max.z) < 1e-6);
const metrics = { glb_bytes: bytes.length, triangles, vertices, primitives, draw_calls: primitives,
  materials: json.materials.length, textures: 0, animations: gltf.animations.length, degenerates,
  dimensions, bounds: { min: bounds.min.toArray(), max: bounds.max.toArray() },
  sha256: createHash('sha256').update(bytes).digest('hex') };
const source = JSON.parse(fs.readFileSync(here + 'reports/source.json'));
assert.equal(source.result, 'PASS');
const report = { result: 'PASS', id: 'abalone-gift-box-display', ...metrics,
  source_features: { boxes: source.editable_gift_boxes, cans: source.plain_cans,
    clear_lids: source.clear_lids, blank_gift_cards: source.blank_gift_cards, blank_signs: source.blank_signs },
  validation: { errors: validation.issues.numErrors, warnings: validation.issues.numWarnings, validator: validation.validatorVersion } };
fs.writeFileSync(here + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
const metadataPath = here + 'metadata/abalone-gift-box-display.json';
if (fs.existsSync(metadataPath)) {
  const metadata = JSON.parse(fs.readFileSync(metadataPath));
  metadata.metrics = metrics;
  metadata.validation = report.validation;
  fs.writeFileSync(metadataPath, JSON.stringify(metadata, null, 2) + '\n');
}
console.log(JSON.stringify(report, null, 2));
