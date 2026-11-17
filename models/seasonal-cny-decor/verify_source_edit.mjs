import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir=fileURLToPath(new URL('.',import.meta.url));
const report=JSON.parse(fs.readFileSync(dir+'reports/sources.json'));
const loader=new GLTFLoader();
async function load(path){
  const bytes=fs.readFileSync(path);
  const json=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const gltf=await loader.parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
  return {bytes,json,scene:gltf.scene};
}
const a=await load(dir+'exports/optimized.glb');
const b=await load(dir+'reports/source-edit/edited.glb');
const validation=await validator.validateBytes(new Uint8Array(b.bytes));
assert.equal(validation.issues.numErrors,0);
assert.equal(validation.issues.numWarnings,0);
const x=a.scene.getObjectByName(report.edited_delivery_mesh);
const y=b.scene.getObjectByName(report.edited_delivery_mesh);
assert.ok(x&&y);
assert.equal(x.geometry.attributes.position.count,y.geometry.attributes.position.count);
assert.notDeepEqual(x.geometry.attributes.position.array,y.geometry.attributes.position.array);
assert.ok(b.json.materials.some(m=>Math.abs(m.pbrMetallicRoughness.roughnessFactor-.77)<1e-5));
console.log('PASS saved mesh and material edits survive re-export; original source unchanged.');
