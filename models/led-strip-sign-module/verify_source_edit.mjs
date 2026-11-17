import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
async function load(relative) {
  const bytes = fs.readFileSync(dir + relative);
  const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
  gltf.scene.updateMatrixWorld(true);
  return { bytes, scene: gltf.scene };
}
const original = await load('exports/optimized.glb');
const edited = await load('reports/source-edit/edited.glb');
const validation = await validator.validateBytes(new Uint8Array(edited.bytes));
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
const box = (scene, name) => new Box3().setFromObject(scene.getObjectByName(name), true);
const before = box(original.scene, 'SIGN_BlankFace'), after = box(edited.scene, 'SIGN_BlankFace');
const displacement = after.min.x - before.min.x;
assert.ok(Math.abs(displacement - .02) < 2e-6);
const strength = edited.scene.getObjectByName('SIGN_LedStrip').material.emissiveIntensity;
assert.equal(strength, 2);
assert.equal(original.scene.getObjectByName('SIGN_LedStrip').material.emissiveIntensity, 4);
for (const name of ['SIGN_Housing', 'SIGN_WallBracket', 'SIGN_LedStrip']) assert.deepEqual(box(edited.scene, name), box(original.scene, name));
const report = { result: 'PASS', method: 'Reopen source, move blank face +20 mm X, change LED strength 4 to 2, save and reopen a copy, export and independently load GLB',
  measured_face_displacement_m: displacement, measured_edited_emissive_strength: strength,
  original_sha256: createHash('sha256').update(original.bytes).digest('hex'),
  edited_sha256: createHash('sha256').update(edited.bytes).digest('hex'), validation: { errors: 0, warnings: 0 } };
fs.writeFileSync(dir + 'reports/source-edit.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
