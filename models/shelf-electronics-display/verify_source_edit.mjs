import assert from 'node:assert/strict';
import fs from 'node:fs';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = new URL('.', import.meta.url);
const report = JSON.parse(fs.readFileSync(new URL('reports/sources.json', dir)));
const originalBytes = fs.readFileSync(new URL('exports/optimized.glb', dir));
const editedBytes = fs.readFileSync(report.edited_glb);
const parse = bytes => new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
const original = await parse(originalBytes), edited = await parse(editedBytes);
const originalMesh = original.scene.getObjectByName('BATCH_Graphite');
const editedMesh = edited.scene.getObjectByName('BATCH_Graphite');
assert.ok(Math.abs(editedMesh.material.roughness - .77) < 1e-6);
const a = originalMesh.geometry, b = editedMesh.geometry;
assert.equal(a.index.count, b.index.count);
let changedX = 0;
// Expand indexed positions: edits can change normal splits and unique vertex counts.
for (let i = 0; i < a.index.count; i++) {
  const ai = a.index.getX(i), bi = b.index.getX(i);
  const x = a.attributes.position.getX(ai), editedX = b.attributes.position.getX(bi);
  assert.ok(Math.abs(a.attributes.position.getY(ai) - b.attributes.position.getY(bi)) < 1e-6);
  assert.ok(Math.abs(a.attributes.position.getZ(ai) - b.attributes.position.getZ(bi)) < 1e-6);
  if (Math.abs(x - editedX) > 1e-6) {
    assert.ok(Math.abs(editedX - (-.253 + (x + .253) * .92)) < 1e-6, 'intended tablet-local X edit');
    changedX++;
  }
}
assert.ok(changedX > 0);
const validation = await validator.validateBytes(new Uint8Array(editedBytes));
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
report.independent_edited_glb_load = { result: 'PASS', changed_triangle_vertex_x_values: changedX,
  unaffected_y_z_values: true, roughness: .77, khronos_errors: 0, khronos_warnings: 0 };
fs.writeFileSync(new URL('reports/sources.json', dir), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report.independent_edited_glb_load));
