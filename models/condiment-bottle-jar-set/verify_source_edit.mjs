// Independently verify that saved source transforms and material edits survive.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { Box3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const report = JSON.parse(fs.readFileSync(dir + 'reports/sources.json'));
const editedBytes = fs.readFileSync(report.edited_glb);
assert.equal(createHash('sha256').update(editedBytes).digest('hex'), report.edited_glb_sha256);
const validation = await validator.validateBytes(new Uint8Array(editedBytes));
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
async function amberBounds(bytes) {
  const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
  gltf.scene.updateMatrixWorld(true);
  let object;
  gltf.scene.traverse(o => { if (o.isMesh && o.material.name === 'Dark filled amber') object = o; });
  assert.ok(object);
  return { bounds: new Box3().setFromObject(object, true), roughness: object.material.roughness };
}
const original = await amberBounds(fs.readFileSync(dir + 'exports/optimized.glb'));
const edited = await amberBounds(editedBytes);
assert.ok(Math.abs(edited.bounds.min.x - original.bounds.min.x - .01) < 1e-6);
assert.ok(Math.abs(edited.bounds.max.x - original.bounds.max.x - .01) < 1e-6);
assert.ok(Math.abs(edited.roughness - .31) < 1e-6);
report.independent_edited_glb_check = {
  result: 'PASS', validator_errors: 0, validator_warnings: 0,
  measured_translation_x_m: edited.bounds.min.x - original.bounds.min.x,
  measured_roughness: edited.roughness,
};
fs.writeFileSync(dir + 'reports/sources.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report.independent_edited_glb_check));
