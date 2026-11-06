import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import validator from 'gltf-validator';
const path=new URL('./exports/proton-saga-1985.glb',import.meta.url), bytes=fs.readFileSync(path);
const report=await validator.validateBytes(new Uint8Array(bytes),{uri:'proton-saga-1985.glb',maxIssues:100});
assert.equal(report.issues.numErrors,0);assert.equal(report.issues.numWarnings,0);
const size=bytes.readUInt32LE(12),gltf=JSON.parse(bytes.subarray(20,20+size));
const names=new Map(gltf.nodes.map((n,i)=>[n.name,i]));
const root=names.get('ASSET_Proton_Saga_1985');assert.notEqual(root,undefined);
for(const code of ['FL','FR','RL','RR']){
 const roll=names.get(`Wheel_${code}_Roll`);assert.notEqual(roll,undefined);assert.ok(gltf.nodes[roll].children?.length);
 if(code.startsWith('F')){const steer=names.get(`Wheel_${code}_Steer`);assert.notEqual(steer,undefined);assert.ok(gltf.nodes[steer].children.includes(roll));assert.ok(gltf.nodes[root].children.includes(steer))}
 else assert.ok(gltf.nodes[root].children.includes(roll));
}
assert.equal((gltf.animations??[]).length,0);
console.log(JSON.stringify({sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,nodes:gltf.nodes.length,meshes:gltf.meshes.length,materials:gltf.materials.length,animations:0,validator:{errors:0,warnings:0},wheel_pivots:'PASS'},null,2));
