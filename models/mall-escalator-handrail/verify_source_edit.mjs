import fs from 'node:fs';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {Box3,Vector3} from 'three';
import validator from 'gltf-validator';
import {readGlb,near} from './glb.mjs';
const root=fileURLToPath(new URL('.',import.meta.url)),sha=b=>createHash('sha256').update(b).digest('hex');
assert.ok(process.argv[2],'pass isolated edited GLB path');
const original=await readGlb(root+'exports/optimized.glb'),edited=await readGlb(process.argv[2]);
const val=await validator.validateBytes(new Uint8Array(edited.bytes));assert.equal(val.issues.numErrors,0);assert.equal(val.issues.numWarnings,0);
const names=[];original.scene.traverse(o=>{if(o.isMesh)names.push(o.name)});let unchanged=0;
for(const name of names){
 const a=original.scene.getObjectByName(name),b=edited.scene.getObjectByName(name);assert.ok(b);
 if(name==='MODULE_ContinuousRubberBelt'){
  near(new Box3().setFromObject(a).getSize(new Vector3()).z,.08);near(new Box3().setFromObject(b).getSize(new Vector3()).z,.09);
  near(a.material.roughness,.48);near(b.material.roughness,.62);
  assert.notDeepEqual(a.geometry.attributes.position.array,b.geometry.attributes.position.array);
  for(const key of ['x','y'])near(new Box3().setFromObject(a).getSize(new Vector3())[key],new Box3().setFromObject(b).getSize(new Vector3())[key]);
 }else{
  assert.deepEqual(a.geometry.attributes.position.array,b.geometry.attributes.position.array);
  assert.deepEqual(a.geometry.index.array,b.geometry.index.array);
  assert.deepEqual(a.geometry.attributes.normal.array,b.geometry.attributes.normal.array);
  assert.deepEqual(a.material.color.toArray(),b.material.color.toArray());near(a.material.roughness,b.material.roughness);unchanged++;
 }
}
assert.equal(unchanged,7);
const unchangedMaterials=original.json.materials.filter(m=>m.name!=='Black elastomer handrail belt');
for(const m of unchangedMaterials)assert.deepEqual(edited.json.materials.find(x=>x.name===m.name),m);
assert.equal(unchangedMaterials.length,4);assert.notEqual(sha(original.bytes),sha(edited.bytes));
const inspection=JSON.parse(fs.readFileSync(root+'reports/sources.json'));
assert.equal(sha(fs.readFileSync(root+'sources/mall-escalator-handrail.blend')),inspection.source_sha256);
const report={status:'PASS',originalGlbSha256:sha(original.bytes),editedGlbSha256:sha(edited.bytes),edit:'Reopened isolated .blend copy: belt width 80 to 90 mm and rubber roughness 0.48 to 0.62; reexported using copied self-contained generator --export-source',unchangedOtherMeshes:unchanged,unchangedOtherMaterials:unchangedMaterials.length,shippedSourceHashUnchanged:true,khronos:{errors:0,warnings:0}};
fs.writeFileSync(root+'reports/source-edit.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
