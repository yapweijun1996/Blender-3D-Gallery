import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {loadCatalog} from '../scripts/catalog.mjs';
import {report,geometry} from '../models/mall-escalator-handrail/validate.mjs';
const folder='models/mall-escalator-handrail',id='mall-escalator-handrail';
const sha=b=>createHash('sha256').update(b).digest('hex');
const catalog=loadCatalog(),collection=catalog.collections.find(c=>c.id===id),asset=collection.assets[0];
const meta=JSON.parse(fs.readFileSync(folder+'/metadata/'+id+'.json'));
test('item 430 registers one handrail type, not a full escalator or two mirrored types',()=>{
 assert.deepEqual(collection.assets.map(a=>a.id),[id]);assert.equal(asset.root,'ASSET_MallEscalatorHandrail');assert.equal(asset.downloadable,false);assert.equal(meta.rights,asset.license);assert.match(asset.license,/redistribution terms have not been specified/);
 assert.match(meta.accuracy_notes,/430 only/);assert.match(meta.accuracy_notes,/004 integration is NOT VERIFIED/);assert.equal(meta.status,'validated');
});
test('measured export and metadata hashes match real artifact',()=>{
 const bytes=fs.readFileSync(folder+'/exports/optimized.glb');assert.equal(report.sha256,sha(bytes));assert.equal(meta.metrics.sha256,report.sha256);assert.equal(meta.metrics.glb_bytes,bytes.length);assert.equal(report.validation.errors,0);assert.equal(report.validation.warnings,0);assert.equal(report.primitives,8);assert.equal(report.materials,5);assert.equal(report.animations,0);assert.equal(report.textures,0);assert.ok(report.triangles<8000&&bytes.length<400*1024);
});
test('actual closed belt, slope, clearances, rail seating and reusable pair geometry pass',()=>{
 assert.equal(geometry.status,'PASS');assert.ok(Math.abs(geometry.measuredCentralSlopeDegrees-30)<1e-5);assert.equal(report.parts.MODULE_ContinuousRubberBelt.euler,0);assert.equal(report.parts.MODULE_ContinuousRubberBelt.components,1);assert.equal(geometry.raySamples.length,3);assert.ok(geometry.raySamples.every(s=>s.glassSeatsInBothRails&&s.upperGuideGap_m>.007&&s.lowerReturnGap_m>.024));assert.ok(Math.abs(geometry.pairCasingClearance_m-1.14)<1e-6);assert.equal(geometry.future004Integration,'NOT VERIFIED');
});
test('delivered source reopens, permits real belt edit/reexport and preserves other meshes',()=>{
 const source=JSON.parse(fs.readFileSync(folder+'/reports/sources.json')),edit=JSON.parse(fs.readFileSync(folder+'/reports/source-edit.json'));assert.equal(source.source_reopened,'PASS');assert.equal(source.editable_mesh_parts,8);assert.equal(source.source_sha256,sha(fs.readFileSync(folder+'/sources/'+id+'.blend')));assert.equal(edit.status,'PASS');assert.equal(edit.unchangedOtherMeshes,7);assert.equal(edit.originalGlbSha256,report.sha256);assert.notEqual(edit.editedGlbSha256,report.sha256);assert.equal(edit.shippedSourceHashUnchanged,true);
});
test('six faithful multiangle WebP previews fit gallery budgets',()=>{
 for(const name of [id,'side','reverse','lower-return','underside','pair-context']){const b=fs.readFileSync(folder+'/previews/'+name+'.webp');assert.equal(b.subarray(0,4).toString(),'RIFF');assert.equal(b.subarray(8,12).toString(),'WEBP');assert.ok(b.length<150*1024);assert.ok(fs.statSync(folder+'/previews/'+name+'.png').size>1000);}
});
