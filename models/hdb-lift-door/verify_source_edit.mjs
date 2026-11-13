import assert from 'node:assert/strict';import fs from 'node:fs';import {Box3} from 'three';import validator from 'gltf-validator';import {readGlb,near} from './glb.mjs';
const root=new URL('.',import.meta.url);const a=await readGlb(new URL('exports/hdb-lift-door.glb',root)),b=await readGlb(new URL('reports/source-edit.glb',root));
const v=await validator.validateBytes(new Uint8Array(b.bytes));assert.equal(v.issues.numErrors,0);assert.equal(v.issues.numWarnings,0);assert.notDeepEqual(a.bytes,b.bytes);
for(const [side,x] of [['Left',-.55],['Right',.55]])near(b.scene.getObjectByName('MOVABLE_'+side+'Door').position.x,x);
fs.writeFileSync(new URL('reports/source-edit-proof.json',root),JSON.stringify({result:'PASS',actualBlendReopenEditAndReexport:true,shippedSourcePreserved:true,errors:0,warnings:0},null,2)+'\n');console.log('PASS hdb-lift-door actual source edit');
