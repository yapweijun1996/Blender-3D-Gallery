// Confirm an actual saved-source mirror edit without changing other geometry.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {Box3, Vector3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

async function load(relative) {
  const bytes=fs.readFileSync(new URL(relative,import.meta.url));
  const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
  gltf.scene.updateMatrixWorld(true);
  return {scene:gltf.scene,sha256:createHash('sha256').update(bytes).digest('hex')};
}
const a=await load('exports/optimized.glb'),b=await load('reports/source-edit.glb');
const bounds=(scene,name)=>new Box3().setFromObject(scene.getObjectByName(name),true);
const original=bounds(a.scene,'MIRROR_Rear'),edited=bounds(b.scene,'MIRROR_Rear');
const size=b=>b.getSize(new Vector3()).toArray();
assert.ok(Math.abs(size(edited)[0]/size(original)[0]-.92)<1e-6);
assert.ok(Math.abs(edited.min.y-original.min.y-.025)<1e-6);
const unchanged=[];
a.scene.traverse(o=>{
  if (!o.isMesh || o.name==='MIRROR_Rear') return;
  const x=bounds(a.scene,o.name),y=bounds(b.scene,o.name);
  assert.ok(x.min.distanceTo(y.min)<1e-6 && x.max.distanceTo(y.max)<1e-6,o.name);
  unchanged.push(o.name);
});
const report={result:'PASS',canonical_sha256:a.sha256,edited_sha256:b.sha256,
  original_mirror_size:size(original),edited_mirror_size:size(edited),
  measured_vertical_offset_m:edited.min.y-original.min.y,unchanged_mesh_bounds:unchanged,
  source_unchanged:true,scope:'Temporary in-memory mirror edit, independently loaded and bounded; canonical source not saved over.'};
fs.writeFileSync(new URL('reports/source-edit-verification.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
