// Independently load a controlled source edit and measure the exported change.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const source = JSON.parse(fs.readFileSync(dir + 'reports/sources.json'));
async function load(path) {
  const bytes = fs.readFileSync(path);
  return new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
}
const original = await load(dir + 'exports/optimized.glb');
const edited = await load(source.edited_glb);
const validation = await validator.validateBytes(new Uint8Array(fs.readFileSync(source.edited_glb)));
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
let shifted = 0, unchanged = 0;
original.scene.traverse(object => {
  if (!object.isMesh) return;
  const other = edited.scene.getObjectByName(object.name);
  assert.ok(other?.isMesh);
  const a = object.geometry.attributes.position, b = other.geometry.attributes.position;
  assert.equal(a.count, b.count);
  for (let i = 0; i < a.count; i++) {
    assert.ok(Math.abs(a.getY(i) - b.getY(i)) < 1e-6);
    assert.ok(Math.abs(a.getZ(i) - b.getZ(i)) < 1e-6);
    const dx = b.getX(i) - a.getX(i);
    if (Math.abs(dx - .005) < 1e-6) shifted++;
    else { assert.ok(Math.abs(dx) < 1e-6); unchanged++; }
  }
});
assert.ok(shifted > 100 && unchanged > shifted);
source.controlled_edit_verification = {result: 'PASS', shifted_vertices: shifted, unchanged_vertices: unchanged,
  translation_gltf_xyz_m: [.005, 0, 0], khronos_errors: 0, khronos_warnings: 0};
fs.writeFileSync(dir + 'reports/sources.json', JSON.stringify(source, null, 2) + '\n');
console.log(source.controlled_edit_verification);
