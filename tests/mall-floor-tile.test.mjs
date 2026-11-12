import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {createHash} from 'node:crypto';import {loadCatalog} from '../scripts/catalog.mjs';import {report,assembly} from '../models/mall-floor-tile/validate.mjs';
const root='models/mall-floor-tile',catalog=loadCatalog(),collection=catalog.collections.find(c=>c.id==='mall-floor-tile'),asset=collection.assets[0],m=JSON.parse(fs.readFileSync(asset.metadata));
test('mall tile is one logical repeat module, with unchanged public download restriction',()=>{
 assert.equal(collection.assets.length,1);assert.equal(asset.id,'mall-floor-tile-module');assert.equal(asset.downloadable,false);assert.equal(asset.license,m.rights);assert.match(asset.license,/redistribution terms have not been specified/);assert.equal(m.display.previewRotationY,0);
});
test('mall tile source remains editable, packed and correctly measured',()=>{
 const s=JSON.parse(fs.readFileSync(root+'/reports/sources.json'));assert.equal(s.source_reopened,'PASS');assert.equal(s.editable_mesh_parts,5);assert.equal(s.packed_original_textures,1);
 assert.equal(s.source_sha256,createHash('sha256').update(fs.readFileSync(root+'/'+m.paths.source)).digest('hex'));
 assert.equal(report.sha256,m.metrics.sha256);assert.equal(report.glb_bytes,m.metrics.glb_bytes);assert.equal(m.validation.errors,0);assert.equal(m.validation.warnings,0);
 assert.ok(report.triangles<1000);assert.ok(report.glb_bytes<1024*1024);assert.equal(m.assembly.repeat_pitch_m,1.2);assert.equal(m.assembly.grout_joint_m,.004);
 const edit=JSON.parse(fs.readFileSync(root+'/reports/source-edit.json'));assert.equal(edit.status,'PASS');assert.equal(edit.originalSha256,report.sha256);assert.equal(edit.shippedSourceUnchanged,true);
});
test('mall tile previews include perspective, top, edge and actual-GLB repeat assembly',()=>{
 for(const p of [m.paths.preview,...m.paths.additional_previews]){const b=fs.readFileSync(root+'/'+p);assert.equal(b.toString('ascii',0,4),'RIFF');assert.equal(b.toString('ascii',8,12),'WEBP');assert.ok(b.length<150*1024);}
 assert.equal(fs.readFileSync(root+'/'+m.paths.render).toString('hex',0,8),'89504e470d0a1a0a');
});
test('mall tile actual exported repeated and quarter-turned modules keep every joint',()=>{
 assert.equal(assembly.length,2);for(const a of assembly){assert.equal(a.result,'PASS');assert.equal(a.tiles,36);assert.equal(a.jointsMeasured,60);assert.ok(a.maxGroutErrorMetres<1e-6);assert.ok(a.maxModuleAabbOverlapMetres<1e-6);}
});
