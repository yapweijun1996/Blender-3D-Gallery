// Independently load the controlled source edit without changing delivery files.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { Box3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const report = JSON.parse(fs.readFileSync(dir + 'reports/sources.json'));
const bytes = fs.readFileSync(report.edited_glb);
assert.equal(createHash('sha256').update(bytes).digest('hex'), report.edited_glb_sha256);
const validation = await validator.validateBytes(new Uint8Array(bytes));
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const cans = gltf.scene.getObjectByName('CANS_BatchedDisplay');
const bounds = new Box3().setFromObject(cans, true);
assert.ok(Math.abs(bounds.max.x - .5342) < 1e-6, 'shared mesh edit survives export');
let roughness;
cans.traverse(object => {
  if (object.isMesh && object.material.name === 'Satin tinplate') roughness = object.material.roughness;
});
assert.ok(Math.abs(roughness - .7) < 1e-6, 'material edit survives export');
report.independent_edited_glb_check = {
  result: 'PASS', validator_errors: 0, validator_warnings: 0,
  can_batch_max_x: bounds.max.x, roughness,
};
fs.writeFileSync(dir + 'reports/sources.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report.independent_edited_glb_check));
