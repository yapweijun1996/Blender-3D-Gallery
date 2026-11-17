import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
import validator from 'gltf-validator';

const bytes = await readFile(new URL('./character-motion.glb', import.meta.url));
const report = await validator.validateBytes(new Uint8Array(bytes));
assert.equal(report.issues.numErrors, 0, 'GLB must have no validation errors');
assert.equal(report.issues.numWarnings, 0, 'GLB must have no validation warnings');
assert.equal(report.info.hasSkins, true);
const length = bytes.readUInt32LE(12);
const doc = JSON.parse(bytes.subarray(20, 20 + length));
assert.equal(doc.skins.length, 1);
assert.equal(doc.skins[0].joints.length, 65);
assert.deepEqual(doc.animations.map(a => a.name).sort(), ['Idle', 'Jump', 'Run_InPlace', 'Sit', 'Walk_InPlace', 'Wave']);
console.log('GLB validation passed: one 65-joint skin and six named clips');

const chairBytes = await readFile(new URL('./fitted-chair.glb', import.meta.url));
const chairReport = await validator.validateBytes(new Uint8Array(chairBytes));
assert.equal(chairReport.issues.numErrors, 0, 'Chair GLB must have no validation errors');
assert.equal(chairReport.issues.numWarnings, 0, 'Chair GLB must have no validation warnings');
assert.ok(chairReport.info.totalTriangleCount > 0, 'Chair must have geometry');
console.log('Fitted chair GLB validation passed');
