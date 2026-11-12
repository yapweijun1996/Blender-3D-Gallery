import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {createHash} from 'node:crypto';import {loadCatalog} from '../scripts/catalog.mjs';import {report,articulation} from '../models/mall-shopfront-door/validate.mjs';
const root='models/mall-shopfront-door',collection=loadCatalog().collections.find(c=>c.id==='mall-shopfront-door'),asset=collection.assets[0],m=JSON.parse(fs.readFileSync(asset.metadata));
test('shopfront door is one logical original restricted-redistribution asset',()=>{
 assert.equal(collection.assets.length,1);assert.equal(asset.id,'mall-shopfront-door');assert.equal(asset.name,m.name);assert.equal(asset.downloadable,false);assert.equal(asset.license,m.rights);assert.match(asset.license,/redistribution terms have not been specified/);assert.equal(m.display.previewRotationY,0);assert.equal(m.quality_gate.overall,'NEEDS REVIEW');
});
test('shopfront source is editable with real mesh and material source reexport proof',()=>{
 const s=JSON.parse(fs.readFileSync(root+'/reports/sources.json'));assert.equal(s.source_reopened,'PASS');assert.equal(s.editable_mesh_parts,33);assert.equal(s.closed_manifold_meshes,33);assert.equal(s.named_materials.length,4);assert.match(s.hinge_source_test,/PASS/);
 assert.equal(s.source_sha256,createHash('sha256').update(fs.readFileSync(root+'/'+m.paths.source)).digest('hex'));
 for(const key of ['sha256','glb_bytes','triangles','primitives','materials'])assert.equal(report[key],m.metrics[key]);
 assert.equal(m.validation.errors,0);assert.equal(m.validation.warnings,0);
 const edit=JSON.parse(fs.readFileSync(root+'/reports/source-edit.json'));assert.equal(edit.status,'PASS');assert.equal(edit.originalSha256,report.sha256);assert.notEqual(edit.originalSha256,edit.editedSha256);assert.equal(edit.shippedSourceUnchanged,true);assert.equal(edit.otherMeshBoundsUnchanged,true);
});
test('shopfront includes actual GLB closed front rear and open previews',()=>{
 assert.equal(m.paths.additional_previews.length,3);
 for(const p of [m.paths.preview,...m.paths.additional_previews]){const b=fs.readFileSync(root+'/'+p);assert.equal(b.toString('ascii',0,4),'RIFF');assert.equal(b.toString('ascii',8,12),'WEBP');assert.ok(b.length<150*1024);}
 assert.equal(fs.readFileSync(root+'/'+m.paths.render).toString('hex',0,8),'89504e470d0a1a0a');
});
test('actual named GLB hinges articulate independently without moving frame or colliding',()=>{
 assert.equal(articulation.length,21);
 for(const a of articulation){assert.equal(a.result,'PASS');assert.equal(a.fixedFrameUnchanged,true);assert.equal(a.leafLocalPartsUnchanged,true);assert.equal(a.frameAndOppositeLeafCollision,false);}
 assert.ok(report.openClearWidthIncludingHardwareMetres>1.73);assert.equal(report.animations,0);assert.equal(report.glassAlpha,.22);assert.match(m.accuracy_notes,/no runtime click-to-open/);assert.deepEqual(m.display.previewCameraDirection,[.7,.35,1]);
});
