import fs from 'node:fs';import assert from 'node:assert/strict';import {pathToFileURL,fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';
const root=fileURLToPath(new URL('../',import.meta.url));const sha=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const {PropertyBinding}=await import(pathToFileURL(root+'node_modules/three/build/three.module.js'));
for(const s of JSON.parse(fs.readFileSync(root+'scripts/batchcityshells05.json'))){
 const p=root+'models/'+s.slug+'/',r=JSON.parse(fs.readFileSync(p+'reports/source.json'));
 const {readGlb}=await import(pathToFileURL(p+'glb.mjs'));const a=await readGlb(p+'exports/'+s.slug+'.glb'),b=await readGlb(p+'reports/source-edit.glb');
 const name=r.edit_proof.node,na=a.scene.getObjectByName(PropertyBinding.sanitizeNodeName(name)),nb=b.scene.getObjectByName(PropertyBinding.sanitizeNodeName(name));assert.ok(na&&nb);assert.ok(Math.abs(nb.position.x-na.position.x-.123)<1e-5);
 const ma=a.json.materials.find(m=>m.name===r.edit_proof.material),mb=b.json.materials.find(m=>m.name===r.edit_proof.material);assert.ok(ma&&mb);assert.ok(Math.abs(ma.pbrMetallicRoughness.roughnessFactor-r.edit_proof.roughness_before)<1e-5);assert.ok(Math.abs(mb.pbrMetallicRoughness.roughnessFactor-r.edit_proof.roughness_after)<1e-5);
 assert.equal(sha(p+'sources/'+s.slug+'.blend'),r.source_sha256);assert.equal(sha(p+r.edit_proof.saved_copy),r.edit_proof.copy_sha256);
 r.edit_proof.result='PASS';r.edit_proof.glb_node_delta_x=nb.position.x-na.position.x;r.edit_proof.material_roughness_survived_save_reopen_export=true;fs.writeFileSync(p+'reports/source.json',JSON.stringify(r,null,2)+'\n');console.log('EDIT_PASS',s.id);
}
