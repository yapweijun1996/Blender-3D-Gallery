import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import validator from 'gltf-validator';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

const report=JSON.parse(fs.readFileSync(new URL('reports/sources.json',import.meta.url)));
const original=fs.readFileSync(new URL('exports/optimized.glb',import.meta.url));
const edited=fs.readFileSync(report.edited_glb);
const v=await validator.validateBytes(new Uint8Array(edited));
assert.equal(v.issues.numErrors,0);assert.equal(v.issues.numWarnings,0);
const load=b=>new GLTFLoader().parseAsync(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),'');
const [a,b]=await Promise.all([load(original),load(edited)]);
const position=(g,n)=>[...g.scene.getObjectByName(n).geometry.attributes.position.array];
assert.notDeepEqual(position(a,'FRAME_Chandelier'),position(b,'FRAME_Chandelier'));
for(const name of ['LIGHT_Ring','CRYSTAL_Pendants']) assert.deepEqual(position(a,name),position(b,name));
assert.ok(Math.abs(b.scene.getObjectByName('FRAME_Chandelier').material.roughness-.77)<1e-5);
const result={result:'PASS',edited_glb_sha256:createHash('sha256').update(edited).digest('hex'),
  geometry_edit_survives_export:true,material_edit_survives_export:true,
  light_and_pendant_geometry_unchanged:true,khronos:{errors:v.issues.numErrors,warnings:v.issues.numWarnings}};
fs.writeFileSync(new URL('reports/source-edit.json',import.meta.url),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result));
