import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {createHash} from 'node:crypto';import {loadCatalog} from '../scripts/catalog.mjs';import {report,assemblies} from '../models/mall-glass-partition/validate.mjs';
const root='models/mall-glass-partition',collection=loadCatalog().collections.find(c=>c.id==='mall-glass-partition'),asset=collection.assets[0],m=JSON.parse(fs.readFileSync(asset.metadata));
test('glass partition is one logical original restricted-redistribution static asset',()=>{
 assert.equal(collection.assets.length,1);assert.equal(asset.id,'mall-glass-partition');assert.equal(asset.name,m.name);assert.equal(asset.downloadable,false);assert.equal(asset.license,m.rights);assert.match(asset.license,/redistribution terms have not been specified/);assert.equal(m.display.previewRotationY,0);assert.equal(m.quality_gate.overall,'NEEDS REVIEW');assert.match(m.accuracy_notes,/no runtime interactions/);assert.equal(report.animations,0);assert.equal(report.glassAlpha,.22);
});
test('glass partition source and independent geometry/material edit proof match shipped hashes',()=>{
 const s=JSON.parse(fs.readFileSync(root+'/reports/sources.json'));assert.equal(s.source_reopened,'PASS');assert.equal(s.editable_mesh_parts,15);assert.equal(s.closed_manifold_meshes,15);assert.equal(s.named_materials.length,3);assert.match(s.connector_source_test,/PASS/);
 assert.equal(s.source_sha256,createHash('sha256').update(fs.readFileSync(root+'/'+m.paths.source)).digest('hex'));
 for(const key of ['sha256','glb_bytes','triangles','primitives','materials'])assert.equal(report[key],m.metrics[key]);assert.equal(m.validation.errors,0);assert.equal(m.validation.warnings,0);
 const edit=JSON.parse(fs.readFileSync(root+'/reports/source-edit.json'));assert.equal(edit.status,'PASS');assert.equal(edit.originalSha256,report.sha256);assert.notEqual(edit.originalSha256,edit.editedSha256);assert.equal(edit.shippedSourceUnchanged,true);assert.equal(edit.otherMeshBoundsUnchanged,true);
});
test('glass partition has actual GLB multiangle and assembled preview images within budgets',()=>{
 assert.equal(m.paths.additional_previews.length,4);
 for(const p of [m.paths.preview,...m.paths.additional_previews]){const b=fs.readFileSync(root+'/'+p);assert.equal(b.toString('ascii',0,4),'RIFF');assert.equal(b.toString('ascii',8,12),'WEBP');assert.ok(b.length<150*1024);const png=fs.readFileSync(root+'/'+p.replace('.webp','.png'));assert.equal(png.toString('hex',0,8),'89504e470d0a1a0a');assert.equal(png.readUInt32BE(16),768);assert.equal(png.readUInt32BE(20),768);}
});
test('live GLB straight and both corner directions join without duplicated posts or mesh penetration',()=>{
 assert.equal(assemblies.length,3);assert.deepEqual(assemblies.map(a=>a.name),['straight-three-bay','corner-three-bay','reverse-corner-two-bay']);
 for(const a of assemblies){assert.equal(a.result,'PASS');assert.equal(a.uniquePosts,a.bays+1);assert.equal(a.overlappingMeshPairs,0);assert.ok(a.maxJointErrorMetres<1e-6);assert.ok(a.pairwiseMeshComparisons>400);}
 assert.equal(m.assembly.repeat_pitch_m,1.14);assert.deepEqual(m.assembly.standalone_dimensions_m,[1.2,2.4,.06]);assert.deepEqual(m.display.previewCameraDirection,[.7,.35,1]);
});
