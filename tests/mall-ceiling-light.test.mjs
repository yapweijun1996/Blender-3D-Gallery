import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {createHash} from 'node:crypto';import {loadCatalog} from '../scripts/catalog.mjs';import {report,assembly} from '../models/mall-ceiling-light/validate.mjs';
const root='models/mall-ceiling-light',collection=loadCatalog().collections.find(c=>c.id==='mall-ceiling-light'),asset=collection.assets[0],m=JSON.parse(fs.readFileSync(asset.metadata));
test('ceiling light is one logical asset with original restricted redistribution',()=>{
 assert.equal(collection.assets.length,1);assert.equal(asset.id,'mall-ceiling-light-module');assert.equal(asset.name,m.name);assert.equal(asset.downloadable,false);assert.equal(asset.license,m.rights);assert.match(asset.license,/redistribution terms have not been specified/);assert.equal(m.display.previewRotationY,0);assert.equal(m.quality_gate.overall,'NEEDS REVIEW');
});
test('ceiling light source is genuinely editable and reexports actual mesh and emission edits',()=>{
 const s=JSON.parse(fs.readFileSync(root+'/reports/sources.json'));assert.equal(s.source_reopened,'PASS');assert.equal(s.editable_mesh_parts,11);assert.equal(s.closed_manifold_meshes,11);assert.equal(s.named_materials.length,4);
 assert.equal(s.source_sha256,createHash('sha256').update(fs.readFileSync(root+'/'+m.paths.source)).digest('hex'));
 assert.equal(report.sha256,m.metrics.sha256);assert.equal(report.glb_bytes,m.metrics.glb_bytes);assert.equal(m.validation.errors,0);assert.equal(m.validation.warnings,0);assert.ok(report.triangles<5000);assert.ok(report.glb_bytes<256*1024);
 const edit=JSON.parse(fs.readFileSync(root+'/reports/source-edit.json'));assert.equal(edit.status,'PASS');assert.equal(edit.originalSha256,report.sha256);assert.notEqual(edit.originalSha256,edit.editedSha256);assert.equal(edit.shippedSourceUnchanged,true);assert.equal(edit.otherMeshBoundsUnchanged,true);
});
test('ceiling light includes actual GLB underside rear edge and ceiling assembly previews',()=>{
 assert.equal(m.paths.additional_previews.length,4);
 for(const p of [m.paths.preview,...m.paths.additional_previews]){const b=fs.readFileSync(root+'/'+p);assert.equal(b.toString('ascii',0,4),'RIFF');assert.equal(b.toString('ascii',8,12),'WEBP');assert.ok(b.length<150*1024);}
 assert.equal(fs.readFileSync(root+'/'+m.paths.render).toString('hex',0,8),'89504e470d0a1a0a');
});
test('light fits every real ceiling bay and quarter-turn without erasing other panels or hardware',()=>{
 assert.equal(assembly.length,8);
 for(const a of assembly){assert.equal(a.result,'PASS');assert.equal(a.retainedPanels,3);assert.equal(a.retainedMeshes,24);assert.equal(a.retainedTransformsUnchanged,true);assert.equal(a.undersideVisible,true);assert.ok(a.maxAabbOverlapMetres<1e-6);}
 assert.equal(report.textures,0);assert.equal(report.animations,0);assert.deepEqual(report.emissiveFactor.map(v=>Number(v.toFixed(2))),[.8,.73,.55]);assert.match(m.accuracy_notes,/does not illuminate/);
});

test('ceiling light opts into approved underside preview without changing geometry or emission',()=>{
 assert.deepEqual(m.display.previewCameraDirection,[1,-1.4,1]);
 assert.deepEqual(m.display.previewLighting,{directionalPosition:[4,-7,5]});
 assert.equal(report.sha256,'b8b0b31c7657028dff44f8c04ba7e65b07feac892b4849b81bb0a1fd78432cf8');
 assert.equal(JSON.parse(fs.readFileSync(root+'/reports/sources.json')).source_sha256,'881ff73ec593c8c96bc19e3eebf0a7f4f085fe43655304cd0788abdf977e68bd');
 assert.deepEqual(report.emissiveFactor.map(v=>Number(v.toFixed(2))),[.8,.73,.55]);assert.equal(asset.downloadable,false);
});
