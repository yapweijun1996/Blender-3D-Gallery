import assert from 'node:assert/strict';import fs from 'node:fs';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';import {Box3} from 'three';import validator from 'gltf-validator';import {readGlb,near} from './glb.mjs';
const root=fileURLToPath(new URL('.',import.meta.url)),out=process.argv[2];assert.ok(out);
const a=await readGlb(root+'exports/mall-structural-column.glb'),b=await readGlb(out+'/exports/mall-structural-column.glb');
const val=await validator.validateBytes(new Uint8Array(b.bytes));assert.equal(val.issues.numErrors,0);assert.equal(val.issues.numWarnings,0);
const sha=v=>createHash('sha256').update(v).digest('hex');
assert.equal(JSON.parse(fs.readFileSync(root+'reports/sources.json')).source_sha256,sha(fs.readFileSync(root+'sources/mall-structural-column.blend')));
let unchanged=0;
a.scene.traverse(o=>{if(o.isMesh){const other=b.scene.getObjectByName(o.name);assert.ok(other);const ba=new Box3().setFromObject(o),bb=new Box3().setFromObject(other);
 if(o.name==='CLADDING_Front_Lower'){near(bb.min.x,ba.min.x+.01);near(bb.max.x,ba.max.x-.01);}
 else{assert.deepEqual(Array.from(o.geometry.attributes.position.array),Array.from(other.geometry.attributes.position.array));near(ba.min.x,bb.min.x);near(ba.max.x,bb.max.x);unchanged++;}
 for(const dim of ['y','z']){near(ba.min[dim],bb.min[dim]);near(ba.max[dim],bb.max[dim]);}
}});
assert.equal(unchanged,12);
const mat=j=>j.materials.find(m=>m.name==='Honed warm ivory cladding').pbrMetallicRoughness;
near(mat(a.json).roughnessFactor,.58);near(mat(b.json).roughnessFactor,.72);
for(const m of a.json.materials)if(m.name!=='Honed warm ivory cladding')assert.deepEqual(m,b.json.materials.find(x=>x.name===m.name));
const report={status:'PASS',method:'Reopened shipped .blend; isolated copy narrows front lower cladding from 0.50 to 0.48 m and changes ivory finish roughness 0.58 to 0.72. Saved and re-exported with --export-source.',unrelatedMeshGeometryUnchanged:unchanged,otherMeshBoundsUnchanged:true,otherMaterialsUnchanged:true,shippedSourceUnchanged:true,originalSha256:sha(a.bytes),editedSha256:sha(b.bytes),editedValidation:{errors:0,warnings:0}};
assert.notEqual(report.originalSha256,report.editedSha256);fs.writeFileSync(root+'reports/source-edit.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
