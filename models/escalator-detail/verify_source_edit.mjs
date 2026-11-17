// Independently confirm that real saved mesh and material edits reached the GLB.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {Box3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

async function read(relative) {
  const bytes=fs.readFileSync(new URL(relative,import.meta.url));
  const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
  gltf.scene.updateMatrixWorld(true);
  return {gltf,sha256:createHash('sha256').update(bytes).digest('hex')};
}
const original=await read('exports/optimized.glb');
const edited=await read('reports/source-edit.glb');
const a=new Box3().setFromObject(original.gltf.scene.getObjectByName('SIGNAGE_BlankPost'),true);
const b=new Box3().setFromObject(edited.gltf.scene.getObjectByName('SIGNAGE_BlankPost'),true);
assert.ok(a.max.y-b.max.y>.018,'saved sign panel height edit is visible in export bounds');
let steel=0;
edited.gltf.scene.traverse(o=>{
  if(o.isMesh && o.material.name==='Satin stainless steel') {
    assert.ok(Math.abs(o.material.roughness-.77)<1e-6);
    steel++;
  }
});
assert.ok(steel>0);
const source=JSON.parse(fs.readFileSync(new URL('reports/sources.json',import.meta.url)));
assert.equal(original.sha256,source.unchanged_source_reexport_sha256);
assert.notEqual(edited.sha256,original.sha256);
const sourceHash=createHash('sha256').update(fs.readFileSync(new URL('sources/escalator-detail.blend',import.meta.url))).digest('hex');
assert.equal(sourceHash,source.source_sha256);
const report={result:'PASS',original_sign_bounds:{min:a.min.toArray(),max:a.max.toArray()},
  edited_sign_bounds:{min:b.min.toArray(),max:b.max.toArray()},steel_primitives_with_saved_roughness:steel,
  measured_roughness:.77,original_glb_sha256:original.sha256,edited_glb_sha256:edited.sha256,
  canonical_source_unchanged:true};
fs.writeFileSync(new URL('reports/source-edit.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
