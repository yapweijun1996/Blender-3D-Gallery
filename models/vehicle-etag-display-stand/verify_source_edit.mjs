import assert from 'node:assert/strict';
import fs from 'node:fs';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = new URL('.', import.meta.url);
const report = JSON.parse(fs.readFileSync(new URL('reports/sources.json', dir)));
const original = fs.readFileSync(new URL('exports/optimized.glb', dir));
const edited = fs.readFileSync((process.env.ETAG_EDIT_DIR ?? '/tmp/vehicle-etag-display-stand-source-edit') + '/edited.glb');
assert.notDeepEqual(original, edited);
const validation = await validator.validateBytes(new Uint8Array(edited));
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
const load = bytes => new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
const [a, b] = await Promise.all([load(original), load(edited)]);
const positions = gltf => {
  const values = [];
  gltf.scene.traverse(o => { if (o.isMesh) values.push(...o.geometry.attributes.position.array); });
  return values;
};
assert.notDeepEqual(positions(a), positions(b));
const json = JSON.parse(edited.subarray(20, 20 + edited.readUInt32LE(12)));
assert.ok(json.materials.some(m => Math.abs(m.pbrMetallicRoughness.roughnessFactor - .77) < 1e-5));
report.exported_edit_verified = 'PASS';
fs.writeFileSync(new URL('reports/sources.json', dir), JSON.stringify(report, null, 2) + '\n');
console.log('PASS saved geometry and material edits survive the source-only export');
