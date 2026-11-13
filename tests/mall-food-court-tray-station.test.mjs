import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {loadCatalog} from '../scripts/catalog.mjs';
import {report,geometry,sha} from '../models/mall-food-court-tray-station/validate.mjs';
const id='mall-food-court-tray-station',folder='models/'+id,read=n=>JSON.parse(fs.readFileSync(folder+'/reports/'+n+'.json')),meta=JSON.parse(fs.readFileSync(folder+'/metadata/'+id+'.json')),c=loadCatalog().collections.find(x=>x.id===id),asset=c.assets[0];
test('439 exact tray return station, original rights and disabled downloads',()=>{
 assert.deepEqual(c.assets.map(a=>a.id),[id]);assert.equal(asset.root,'ASSET_MallFoodCourtTrayStation');assert.equal(asset.downloadable,false);assert.equal(meta.rights,asset.license);assert.match(meta.accuracy_notes,/439 only/);assert.match(meta.accuracy_notes,/No hygiene, safety/);assert.match(meta.accuracy_notes,/Android\/iOS hardware is NOT TESTED/);assert.equal(meta.status,'validated');assert.deepEqual(Object.keys(meta.display).sort(),['front_axis','origin','previewRotationY','units','up_axis']);
});
test('exact optimized bytes, Khronos 0 errors and warnings, bounded geometry and no textures',()=>{
 const b=fs.readFileSync(folder+'/exports/optimized.glb');assert.equal(sha(b),report.sha256);for(const key of ['sha256','glb_bytes','triangles','vertices','primitives','materials','textures','animations'])assert.equal(meta.metrics[key],report[key]);assert.equal(report.primitives,15);assert.equal(report.materials,8);assert.equal(report.textures,0);assert.equal(report.animations,0);assert.deepEqual(report.validation,{errors:0,warnings:0,validator:'2.0.0-dev.3.10'});assert.ok(report.triangles<12000&&b.length<600000);
});
test('floor origin, practical metric scale, supported counter and real shelf openings',()=>{
 assert.equal(geometry.status,'PASS');for(const [i,v] of [1.5,1.49,.66].entries())assert.ok(Math.abs(geometry.dimensions_glTF_m[i]-v)<1e-6);assert.equal(geometry.floorPlane_glTF_Y_m,0);assert.equal(geometry.independentModules.length,13);assert.equal(geometry.clearOpeningWidth_m,1.36);assert.deepEqual(geometry.shelfVerticalClearances_m,[.33,.33]);assert.equal(geometry.apertureRays.length,2);for(const ray of geometry.apertureRays)assert.match(ray.firstHit,/CabinetBack/);
});
test('four hollow independent trays have real shelf clearance and a free removal sweep',()=>{
 assert.equal(geometry.trays.length,4);for(const t of geometry.trays)assert.ok(Math.abs(t.hollowFloorThickness_m-.006)<1e-6);assert.equal(geometry.stackGap_m,.005);assert.equal(geometry.trayRemoval.status,'PASS');assert.equal(geometry.trayRemoval.distance_m,.62);assert.ok(geometry.trayRemoval.sweptBoxNoFixedModuleCollision&&geometry.trayRemoval.fullyOutsideCounter);assert.ok(geometry.staticProp);
});
test('self-contained source reopens with editable labels and closed evaluated meshes',()=>{
 const s=read('sources');assert.equal(s.source_reopened,'PASS');assert.equal(s.source_sha256,sha(fs.readFileSync(folder+'/sources/'+id+'.blend')));assert.ok(s.selfContained);assert.equal(s.source_units,'metres');assert.equal(s.source_scales,'UNIT');assert.equal(s.editableTextObjects,2);assert.equal(s.topology.status,'PASS');assert.equal(s.topology.nonmanifoldEdges,0);assert.equal(s.topology.degenerateFaces,0);assert.equal(s.textFit.status,'PASS');assert.equal(s.textFit.labels.ReturnLabel.body,'TRAY RETURN');
});
test('saved real mesh, material and label edits survive reopen and reexport without regeneration',()=>{
 const e=read('source-edit');assert.equal(e.status,'PASS');assert.deepEqual(e.changedModules,['Counter','SignText','Tray04']);assert.equal(e.unchangedModuleCount,10);assert.ok(e.allModuleTransformsPreserved&&e.shippedSourceHashUnchanged);assert.equal(e.originalGlbSha256,report.sha256);assert.notEqual(e.editedGlbSha256,report.sha256);assert.deepEqual(e.validation,{errors:0,warnings:0});
});
test('six PNG/WebP views include rear, interior and source-only tray removal',()=>{
 for(const n of [id,'front','rear','side','interior','tray-removal']){const b=fs.readFileSync(folder+'/previews/'+n+'.webp');assert.equal(b.subarray(0,4).toString(),'RIFF');assert.equal(b.subarray(8,12).toString(),'WEBP');assert.ok(b.length<150*1024);const p=fs.readFileSync(folder+'/previews/'+n+'.png');assert.equal(p.subarray(0,8).toString('hex'),'89504e470d0a1a0a');assert.equal(p.readUInt32BE(16),768);assert.equal(p.readUInt32BE(20),768);}
});
