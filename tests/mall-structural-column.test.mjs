
import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {createHash} from 'node:crypto';import {loadCatalog} from '../scripts/catalog.mjs';import {report,assemblies} from '../models/mall-structural-column/validate.mjs';
const root='models/mall-structural-column',collection=loadCatalog().collections.find(c=>c.id==='mall-structural-column'),asset=collection.assets[0],m=JSON.parse(fs.readFileSync(asset.metadata));
test('column is one logical original restricted-redistribution visual architecture asset',()=>{
 assert.equal(collection.assets.length,1);assert.equal(asset.id,'mall-structural-column');assert.equal(asset.name,m.name);assert.equal(asset.downloadable,false);assert.equal(asset.license,m.rights);assert.match(asset.license,/redistribution terms have not been specified/);assert.equal(m.display.previewRotationY,0);assert.equal(m.quality_gate.overall,'NEEDS REVIEW');assert.match(m.accuracy_notes,/No structural load/);assert.equal(report.animations,0);
});
test('column live geometry is a ground-origin 3 m closed-part model with no internal penetration',()=>{
 assert.equal(report.primitives,13);assert.equal(report.materials,3);assert.equal(report.internalMeshPairChecks,78);assert.equal(report.textures,0);
 for(const key of ['sha256','glb_bytes','triangles','primitives','materials'])assert.equal(report[key],m.metrics[key]);
 assert.equal(m.validation.errors,0);assert.equal(m.validation.warnings,0);
 for(const [i,want] of [.6,3,.6].entries())assert.ok(Math.abs(report.dimensions[i]-want)<1e-6);
 assert.equal(report.bounds.min[1],0);assert.ok(report.glb_bytes<100*1024);assert.ok(report.triangles<2000);
});
test('column source reopens with independent panels and real edit/re-export proof',()=>{
 const s=JSON.parse(fs.readFileSync(root+'/reports/sources.json'));assert.equal(s.source_reopened,'PASS');assert.equal(s.editable_mesh_parts,13);assert.equal(s.closed_manifold_meshes,13);assert.equal(s.cladding_panels,8);assert.equal(s.named_materials.length,3);
 assert.equal(s.source_sha256,createHash('sha256').update(fs.readFileSync(root+'/'+m.paths.source)).digest('hex'));
 const edit=JSON.parse(fs.readFileSync(root+'/reports/source-edit.json'));assert.equal(edit.status,'PASS');assert.equal(edit.originalSha256,report.sha256);assert.notEqual(edit.originalSha256,edit.editedSha256);assert.equal(edit.shippedSourceUnchanged,true);assert.equal(edit.otherMeshBoundsUnchanged,true);assert.equal(edit.unrelatedMeshGeometryUnchanged,12);assert.equal(edit.otherMaterialsUnchanged,true);
});
test('column multiview and placement images have actual PNG/WebP signatures and budgets',()=>{
 assert.equal(m.paths.additional_previews.length,4);
 for(const p of [m.paths.preview,...m.paths.additional_previews]){const b=fs.readFileSync(root+'/'+p);assert.equal(b.toString('ascii',0,4),'RIFF');assert.equal(b.toString('ascii',8,12),'WEBP');assert.ok(b.length<150*1024);const png=fs.readFileSync(root+'/'+p.replace('.webp','.png'));assert.equal(png.toString('hex',0,8),'89504e470d0a1a0a');assert.equal(png.readUInt32BE(16),768);assert.equal(png.readUInt32BE(20),768);}
});
test('live GLB column placement against unchanged actual floor/ceiling modules is clear and supported',()=>{
 assert.equal(assemblies.length,2);assert.deepEqual(assemblies.map(a=>a.name),['placement-grid','assembly-two-columns']);
 for(const a of assemblies){assert.equal(a.result,'PASS');assert.equal(a.floorModules,a.columns*9);assert.equal(a.ceilingModules,a.columns*8);assert.equal(a.penetrations,0);assert.ok(a.columnContextMeshComparisons>=4069);assert.equal(a.floorContactHeight_m,0);assert.equal(a.ceilingUndersideHeight_m,3);assert.ok(Math.abs(a.minimumCapToCeilingClearance_m-.3)<1e-6);}
 assert.equal(assemblies[1].interColumnBaseClearance_m,3);
 for(const [name,file] of [['floor','mall-floor-tile/exports/mall-floor-tile-module.glb'],['ceiling','mall-ceiling-panel/exports/mall-ceiling-panel-module.glb']])assert.equal(assemblies[0].sourceHashes[name],createHash('sha256').update(fs.readFileSync('models/'+file)).digest('hex'));
 assert.deepEqual(m.assembly.standalone_dimensions_m,[.6,3,.6]);assert.deepEqual(m.display.previewCameraDirection,[.7,.35,1]);
});
