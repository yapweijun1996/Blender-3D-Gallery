import assert from 'node:assert/strict';import fs from 'node:fs';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';import {Box3} from 'three';import validator from 'gltf-validator';import {readGlb,near} from './glb.mjs';
const root=fileURLToPath(new URL('.',import.meta.url)),out=process.argv[2];assert.ok(out);
const a=await readGlb(root+'exports/mall-ceiling-light-module.glb'),b=await readGlb(out+'/exports/mall-ceiling-light-module.glb');
const val=await validator.validateBytes(new Uint8Array(b.bytes));assert.equal(val.issues.numErrors,0);assert.equal(val.issues.numWarnings,0);
const sha=v=>createHash('sha256').update(v).digest('hex');
assert.equal(JSON.parse(fs.readFileSync(root+'reports/sources.json')).source_sha256,sha(fs.readFileSync(root+'sources/mall-ceiling-light-module.blend')));
for(const o of a.scene.getObjectByName('ASSET_MallCeilingLight').children){
 const other=b.scene.getObjectByName(o.name);assert.ok(other);
 const ba=new Box3().setFromObject(o),bb=new Box3().setFromObject(other);
 near(bb.min.y,ba.min.y-(o.name==='DIFFUSER_Opal'?.001:0));near(bb.max.y,ba.max.y);
 for(const dim of ['x','z']){near(ba.min[dim],bb.min[dim]);near(ba.max[dim],bb.max[dim]);}
}
const mat=j=>j.materials.find(m=>m.name==='Warm opal emissive diffuser');
mat(a.json).emissiveFactor.forEach((v,i)=>near(v,[.8,.73,.55][i]));mat(b.json).emissiveFactor.forEach((v,i)=>near(v,[.3,.25,.18][i]));
const report={status:'PASS',method:'Reopened shipped .blend, isolated copy, diffuser underside vertices lowered 1 mm, emission RGB changed from (0.8,0.73,0.55) to (0.3,0.25,0.18), saved and re-exported with --export-source',otherMeshBoundsUnchanged:true,shippedSourceUnchanged:true,originalSha256:sha(a.bytes),editedSha256:sha(b.bytes),editedValidation:{errors:0,warnings:0}};
assert.notEqual(report.originalSha256,report.editedSha256);fs.writeFileSync(root+'reports/source-edit.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
