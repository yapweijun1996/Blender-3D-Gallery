import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {loadCatalog} from '../scripts/catalog.mjs';
const id='mall-retail-pop-up-cart',base='models/'+id+'/';
test('retail cart is unique, bounded and editable',()=>{const a=loadCatalog().collections.flatMap(c=>c.assets).filter(a=>a.id===id);assert.equal(a.length,1);assert.ok(a[0].triangles<16000);assert.ok(a[0].bytes<800000);assert.equal(a[0].downloadable,false);const s=JSON.parse(fs.readFileSync(base+'reports/sources.json'));assert.equal(s.source_reopened,'PASS');assert.equal(s.independentModules.length,13);assert.equal(s.topology.nonmanifoldEdges,0);assert.equal(s.topology.degenerateFaces,0);assert.equal(s.textFit.status,'PASS');assert.ok(fs.statSync(base+'sources/'+id+'.blend').size>10000);});
test('retail cart source edits persist without changing delivered source',()=>{const r=JSON.parse(fs.readFileSync(base+'reports/source-edit.json'));assert.equal(r.status,'PASS');assert.equal(r.originalSourceUnchanged,true);assert.equal(r.edits.length,3);});
test('retail cart has honest native mobile limitations',()=>{const m=JSON.parse(fs.readFileSync(base+'metadata.json'));assert.match(m.accuracy_notes,/Android\/iOS NOT TESTED/);assert.equal(m.paths.additional_previews.length,3);});
