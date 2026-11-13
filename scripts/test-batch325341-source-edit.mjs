import fs from 'node:fs';import assert from 'node:assert/strict';import {pathToFileURL,fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
const {PropertyBinding}=await import(pathToFileURL(root+'node_modules/three/build/three.module.js'));
for(const s of JSON.parse(fs.readFileSync(root+'scripts/batch325341.json'))){
 const p=root+'models/'+s.slug+'/',r=JSON.parse(fs.readFileSync(p+'reports/source.json'));
 const {readGlb}=await import(pathToFileURL(p+'glb.mjs'));const a=await readGlb(p+'exports/'+s.slug+'.glb'),b=await readGlb(p+'reports/source-edit.glb');
 const name=r.edit_proof.node,na=a.scene.getObjectByName(PropertyBinding.sanitizeNodeName(name)),nb=b.scene.getObjectByName(PropertyBinding.sanitizeNodeName(name));assert.ok(na&&nb);
 assert.ok(Math.abs(nb.position.x-na.position.x-.123)<1e-5);
 r.edit_proof.result='PASS';r.edit_proof.glb_node_delta_x=nb.position.x-na.position.x;fs.writeFileSync(p+'reports/source.json',JSON.stringify(r,null,2)+'\n');console.log('EDIT_PASS',s.id);
}
