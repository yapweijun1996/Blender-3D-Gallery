import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import validator from 'gltf-validator';

const bytes = await readFile(new URL('./character.glb', import.meta.url));
const report = await validator.validateBytes(new Uint8Array(bytes));
assert.equal(report.issues.numErrors, 0, JSON.stringify(report.issues));
assert.equal(report.issues.numWarnings, 0, JSON.stringify(report.issues));
assert.equal(report.info.totalTriangleCount, 39214);
assert.equal(report.info.hasSkins, true);

const doc = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
assert.deepEqual(doc.animations.map(animation => animation.name), ['walk']);
assert.equal(doc.meshes.length, 1);
assert.equal(doc.skins.length, 1);
assert.equal(doc.skins[0].joints.length, 65);
const meshNode = doc.nodes.findIndex(node => node.mesh === 0 && node.skin === 0);
assert.ok(doc.scenes[doc.scene].nodes.includes(meshNode), 'Skinned mesh must be a scene root');
assert.equal(doc.images.length, 1);
assert.equal(doc.images[0].mimeType, 'image/jpeg');
assert.ok(doc.materials[0].pbrMetallicRoughness.baseColorTexture, 'Missing source texture');
console.log('PASS: zero glTF errors and warnings; 65 joints, 39,214 triangles, textured skin and walk');
