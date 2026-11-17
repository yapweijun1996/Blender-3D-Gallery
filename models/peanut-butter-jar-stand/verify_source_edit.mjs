import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';
const dir = fileURLToPath(new URL('.', import.meta.url));
const load = async name => {
  const b = fs.readFileSync(dir + name);
  return new GLTFLoader().parseAsync(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength), '');
};
const a = await load('exports/optimized.glb'), b = await load('reports/source-edit/edited.glb');
const name = 'DISPLAY_SharedMatteFixtureAndBlankPaper';
const positions = g => g.scene.getObjectByName(name).geometry.attributes.position.array;
assert.notDeepEqual(positions(a), positions(b));
const cabinetSideMaxX = g => {
  const p = g.scene.getObjectByName(name).geometry.attributes.position;
  let x = -Infinity;
  for (let i = 0; i < p.count; i++) {
    if (p.getY(i) > .071 && p.getY(i) < .59 && Math.abs(p.getZ(i)) < .231) x = Math.max(x, p.getX(i));
  }
  return x;
};
assert.ok(Math.abs(cabinetSideMaxX(a) - .38) < 1e-5);
assert.ok(Math.abs(cabinetSideMaxX(b) - .38 * .92) < 1e-5);
let roughness;
b.scene.traverse(o => { if (o.isMesh && o.material.name === 'SharedPlainTerracottaLid') roughness = o.material.roughness; });
assert.ok(Math.abs(roughness - .77) < 1e-6);
const validation = await validator.validateBytes(new Uint8Array(fs.readFileSync(dir + 'reports/source-edit/edited.glb')));
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
fs.writeFileSync(dir + 'reports/source-edit-verification.json', JSON.stringify({result:'PASS', mesh_edit_persisted:true, material_edit_persisted:true, errors:0, warnings:0}, null, 2) + '\n');
console.log('PASS saved mesh and material edits survive GLB re-export');
