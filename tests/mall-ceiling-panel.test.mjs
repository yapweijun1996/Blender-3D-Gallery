import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {createHash} from 'node:crypto';import {loadCatalog} from '../scripts/catalog.mjs';import {report,assembly} from '../models/mall-ceiling-panel/validate.mjs';
const root='models/mall-ceiling-panel',collection=loadCatalog().collections.find(c=>c.id==='mall-ceiling-panel'),asset=collection.assets[0],m=JSON.parse(fs.readFileSync(asset.metadata));
test('ceiling is one logical kit and preserves redistribution restriction',()=>{
 assert.equal(collection.assets.length,1);assert.equal(asset.id,'mall-ceiling-panel-module');assert.equal(asset.downloadable,false);assert.equal(asset.license,m.rights);assert.match(asset.license,/redistribution terms have not been specified/);assert.equal(m.display.previewRotationY,0);assert.equal(m.quality_gate.overall,'NEEDS REVIEW');
});
test('ceiling source is genuinely editable with independent panels, grid and hangers',()=>{
 const s=JSON.parse(fs.readFileSync(root+'/reports/sources.json'));assert.equal(s.source_reopened,'PASS');assert.equal(s.editable_mesh_parts,25);assert.equal(s.closed_manifold_meshes,25);assert.equal(s.connector_empties,4);assert.equal(s.packed_original_textures,1);
 assert.equal(s.source_sha256,createHash('sha256').update(fs.readFileSync(root+'/'+m.paths.source)).digest('hex'));
 assert.equal(report.sha256,m.metrics.sha256);assert.equal(report.glb_bytes,m.metrics.glb_bytes);assert.equal(m.validation.errors,0);assert.equal(m.validation.warnings,0);assert.ok(report.triangles<5000);assert.ok(report.glb_bytes<512*1024);
 const edit=JSON.parse(fs.readFileSync(root+'/reports/source-edit.json'));assert.equal(edit.status,'PASS');assert.equal(edit.originalSha256,report.sha256);assert.notEqual(edit.originalSha256,edit.editedSha256);assert.equal(edit.shippedSourceUnchanged,true);assert.equal(edit.otherMeshBoundsUnchanged,true);
});
test('ceiling previews include actual-GLB underside, rear, edge and repeat assembly',()=>{
 for(const p of [m.paths.preview,...m.paths.additional_previews]){const b=fs.readFileSync(root+'/'+p);assert.equal(b.toString('ascii',0,4),'RIFF');assert.equal(b.toString('ascii',8,12),'WEBP');assert.ok(b.length<150*1024);}
 assert.equal(fs.readFileSync(root+'/'+m.paths.render).toString('hex',0,8),'89504e470d0a1a0a');
});
test('ceiling repeat and quarter-turn assembly preserve every grid gap and connector seam',()=>{
 assert.equal(assembly.length,2);
 for(const a of assembly){assert.equal(a.result,'PASS');assert.equal(a.panels,36);assert.equal(a.panelGapsMeasured,60);assert.equal(a.matchedConnectorSeams,12);assert.ok(a.maxGridGapErrorMetres<1e-6);assert.ok(a.maxConnectorErrorMetres<1e-6);assert.ok(a.maxModuleAabbOverlapMetres<1e-6);}
});
