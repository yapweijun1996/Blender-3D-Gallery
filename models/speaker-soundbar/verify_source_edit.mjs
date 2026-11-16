import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import validator from 'gltf-validator';
import { load } from './validate.mjs';

const dir = fileURLToPath(new URL('.', import.meta.url));
const evidence = JSON.parse(fs.readFileSync(dir + 'reports/sources.json'));
const original = fs.readFileSync(dir + 'exports/optimized.glb');
const reexport = fs.readFileSync(path.join(os.tmpdir(), 'speaker-soundbar-source-edit/source-reexport.glb'));
const edited = fs.readFileSync(path.join(os.tmpdir(), 'speaker-soundbar-source-edit/edited.glb'));
assert.equal(createHash('sha256').update(edited).digest('hex'), evidence.edited_glb_sha256);
const validation = await validator.validateBytes(new Uint8Array(edited));
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
const a = await load(original), b = await load(edited);
const reopened = await load(reexport);
const json = bytes => JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
assert.deepEqual(json(original), json(reexport), 'unchanged source preserves the full exported contract');
const repeatedValidation = await validator.validateBytes(new Uint8Array(reexport));
assert.equal(repeatedValidation.issues.numErrors, 0);
assert.equal(repeatedValidation.issues.numWarnings, 0);
let largestUvDifference = 0, largestTangentDifference = 0;
a.scene.traverse(object => {
  if (!object.isMesh) return;
  const other = reopened.scene.getObjectByName(object.name);
  assert.ok(other?.isMesh);
  assert.deepEqual(object.geometry.index.array, other.geometry.index.array);
  for (const [name, attribute] of Object.entries(object.geometry.attributes)) {
    const actual = other.geometry.attributes[name];
    assert.equal(actual.count, attribute.count);
    const tolerance = name === 'tangent' ? .001 : 1e-6;
    for (let i = 0; i < attribute.array.length; i++) {
      const difference = Math.abs(attribute.array[i] - actual.array[i]);
      assert.ok(difference <= tolerance, `reopened ${object.name} ${name} within ${tolerance}`);
      if (name === 'uv') largestUvDifference = Math.max(largestUvDifference, difference);
      if (name === 'tangent') largestTangentDifference = Math.max(largestTangentDifference, difference);
    }
  }
});
for (const gltf of [a, b]) gltf.scene.updateMatrixWorld(true);
const width = (gltf, name) => new Box3().setFromObject(gltf.scene.getObjectByName(name), true).getSize(new Vector3()).x;
assert.ok(Math.abs(width(a, 'SOUNDBAR') - .9) < 1e-5);
assert.ok(Math.abs(width(b, 'SOUNDBAR') - .828) < 1e-5, 'saved mesh edit changed real exported geometry');
assert.ok(Math.abs(width(a, 'FLOOR_SPEAKER') - width(b, 'FLOOR_SPEAKER')) < 1e-6);
let found = false;
b.scene.traverse(object => {
  if (object.material?.name === 'Graphite enclosure and rubber') {
    assert.ok(Math.abs(object.material.roughness - .77) < 1e-5);
    found = true;
  }
});
assert.ok(found);
evidence.saved_edit_reexport = 'PASS: measured bar width changed from 0.9 to 0.828 m; saved roughness is 0.77';
evidence.unchanged_source_semantic_reexport = { result: 'PASS', largest_uv_difference: largestUvDifference,
  largest_tangent_difference: largestTangentDifference, uv_tolerance: 1e-6, tangent_tolerance: .001,
  note: 'Saved/reopened evaluated bevel UVs round slightly; clean generator rebuilds remain byte-identical' };
fs.writeFileSync(dir + 'reports/sources.json', JSON.stringify(evidence, null, 2) + '\n');
console.log(evidence.saved_edit_reexport);
