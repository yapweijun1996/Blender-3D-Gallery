import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {loadCatalog} from '../scripts/catalog.mjs';
// Import reruns Khronos and all 53 pose/clearance checks against shipped GLB
// bytes. These contracts do not pass merely because an old report says PASS.
import {report,articulation} from '../models/mall-shopfront-roller-shutter/validate.mjs';
const root='models/mall-shopfront-roller-shutter';
const collection=loadCatalog().collections.find(c=>c.id==='mall-shopfront-roller-shutter');
const asset=collection.assets[0],m=JSON.parse(fs.readFileSync(asset.metadata));
test('roller shutter is one logical original asset with disabled public download',()=>{
 assert.equal(collection.assets.length,1);
 assert.equal(asset.id,'mall-shopfront-roller-shutter');
 assert.equal(asset.name,m.name);
 assert.equal(asset.downloadable,false);
 assert.equal(asset.license,m.rights);
 assert.match(m.rights,/redistribution terms have not been specified/);
 assert.equal(m.quality_gate.overall,'NEEDS REVIEW');
 assert.match(m.quality_gate.scope,/physical Android\/iOS remain untested/);
 assert.equal(m.display.units,'metres');
 assert.deepEqual(m.display.previewCameraDirection,[.7,.35,1]);
});
test('roller shutter metadata matches live GLB and hashed editable source proof',()=>{
 for(const key of ['sha256','glb_bytes','triangles','vertices','primitives','materials','textures','animations'])assert.equal(report[key],m.metrics[key]);
 assert.equal(report.validation.errors,0);assert.equal(report.validation.warnings,0);
 const source=JSON.parse(fs.readFileSync(root+'/reports/sources.json'));
 assert.equal(source.source_reopened,'PASS');assert.equal(source.editable_mesh_parts,44);
 assert.equal(source.closed_manifold_meshes,44);assert.equal(source.named_materials.length,4);
 assert.equal(source.source_sha256,createHash('sha256').update(fs.readFileSync(root+'/'+m.paths.source)).digest('hex'));
 const edit=JSON.parse(fs.readFileSync(root+'/reports/source-edit.json'));
 assert.equal(edit.status,'PASS');assert.equal(edit.originalSha256,report.sha256);
 assert.notEqual(edit.originalSha256,edit.editedSha256);
 assert.equal(edit.shippedSourceUnchanged,true);assert.equal(edit.otherMeshBoundsUnchanged,true);
});
test('real separate shutter slats clear fixed guides, hood and roller across 53 poses',()=>{
 assert.equal(report.primitives,44);assert.equal(m.assembly.slat_count,28);
 for(let i=1;i<=28;i++)assert.ok(report.parts['SLAT_'+String(i).padStart(2,'0')]);
 for(const name of ['TRACK_Left_Web','TRACK_Right_Web','HOOD_Front','HOOD_Rear','HOOD_Top','ROLLER_Drum','BOTTOM_Rail','BOTTOM_Seal'])assert.ok(report.parts[name]);
 assert.equal(articulation.length,53);assert.equal(articulation[0].liftMetres,0);
 assert.equal(articulation.at(-1).liftMetres,2.6);
 for(const pose of articulation){assert.equal(pose.status,'PASS');assert.equal(pose.fixedUnchanged,true);assert.equal(pose.slatSlatAndFrameCollisions,false);assert.ok(pose.minRollerClearanceMetres>0);assert.ok(Math.abs(pose.clearHeightMetres-pose.liftMetres)<1e-6);}
 assert.ok(Math.abs(report.clearOpeningMetres[0]-2.92)<1e-6);
 assert.equal(report.animations,0);assert.match(m.accuracy_notes,/no runtime click interaction/);
});
test('shutter closed, part-open, open and cutaway previews exist within image budgets',()=>{
 assert.equal(m.paths.additional_previews.length,5);
 for(const name of ['part-open','open','mechanism-cutaway'])assert.ok(m.paths.additional_previews.includes('previews/'+name+'.webp'));
 for(const path of [m.paths.preview,...m.paths.additional_previews]){
  const b=fs.readFileSync(root+'/'+path);assert.equal(b.toString('ascii',0,4),'RIFF');assert.equal(b.toString('ascii',8,12),'WEBP');assert.ok(b.length<150*1024);
 }
 assert.equal(fs.readFileSync(root+'/'+m.paths.render).toString('hex',0,8),'89504e470d0a1a0a');
});
