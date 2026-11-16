import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { Box3 } from 'three';
import validator from 'gltf-validator';
import { readGlb } from './glb.mjs';

const dir = fileURLToPath(new URL('.', import.meta.url));
const report = JSON.parse(fs.readFileSync(dir + 'reports/sources.json'));
const original = await readGlb(dir + 'exports/optimized.glb');
const edited = await readGlb(dir + 'reports/source-edit/edited.glb');
assert.notDeepEqual(original.bytes, edited.bytes);
const validation = await validator.validateBytes(new Uint8Array(edited.bytes));
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
const before = new Box3().setFromObject(original.scene.getObjectByName(report.edited_mesh), true);
const after = new Box3().setFromObject(edited.scene.getObjectByName(report.edited_mesh), true);
assert.ok(Math.abs(before.max.x - .5) < 1e-6);
assert.ok(Math.abs(after.max.x - .491) < 1e-6, 'Cabinet end panel becomes widest after platform edit');
assert.ok(Math.abs(after.min.x + .491) < 1e-6);
assert.ok(edited.json.materials.some(material => material.name === 'Soft surfaces' &&
  Math.abs(material.pbrMetallicRoughness.roughnessFactor - .77) < 1e-5));
for (const name of ['BATCH_Hardware', 'BATCH_Glass']) {
  assert.deepEqual(original.scene.getObjectByName(name).geometry.attributes.position.array,
    edited.scene.getObjectByName(name).geometry.attributes.position.array, 'Unedited geometry remains identical');
}
console.log('PASS saved source platform edit and surface roughness survive GLB export');
