import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { validateMetadata, loadCatalog } from '../scripts/catalog.mjs';
const source = JSON.parse(fs.readFileSync('models/solar-system/metadata/earth.json','utf8'));
function metadata(display) {return {...structuredClone(source), display:{previewRotationY:0,...display}};}
const validate = display => validateMetadata(metadata(display),'earth');

test('omitted and partial preview settings retain metadata without inserting defaults', () => {
  for (const display of [{}, {previewLighting:{}}, {previewCameraDirection:[1,-1.4,1]},
    {previewLighting:{directionalPosition:[4,-7,5]}},
    {previewLighting:{hemisphereIntensity:0,directionalIntensity:10}}]) {
    const input=metadata(display), before=structuredClone(input);
    assert.equal(validateMetadata(input,'earth'),input);
    assert.deepEqual(input,before,'validation neither normalizes nor inserts override values');
  }
  assert.equal(validate({}).display.previewCameraDirection,undefined);
  assert.equal(validate({}).display.previewLighting,undefined);
});

test('preview vectors reject malformed, non-finite, excessive and degenerate values', () => {
  const invalid=[null,false,'1,2,3',{},[],[1,2],[1,2,3,4],[1,'2',3],[NaN,1,1],
    [Infinity,1,1],[-Infinity,1,1],[101,1,1],[-101,1,1],[0,0,0],[0.00000001,0,0],new Array(3)];
  for (const vector of invalid) {
    assert.throws(()=>validate({previewCameraDirection:vector}),/metadata previewCameraDirection/);
    assert.throws(()=>validate({previewLighting:{directionalPosition:vector}}),/metadata previewLighting.directionalPosition/);
  }
  for (const vector of [[0,1,0],[0,-1,0]]) {
    assert.throws(()=>validate({previewCameraDirection:vector}),/previewCameraDirection/,'camera must avoid vertical poles');
    assert.doesNotThrow(()=>validate({previewLighting:{directionalPosition:vector}}));
  }
  for (const vector of [[100,-100,100],[-100,0,-100],[0.000001,0,0]])
    assert.doesNotThrow(()=>validate({previewCameraDirection:vector,previewLighting:{directionalPosition:vector}}));
});

test('known invalid preview fields fail authoring validation, never silently fall back', () => {
  for (const value of [null,[],false,0,'default']) assert.throws(()=>validate({previewLighting:value}),/metadata previewLighting/);
  for (const field of ['hemisphereIntensity','directionalIntensity']) {
    for (const value of [null,false,'2',NaN,Infinity,-Infinity,-0.01,10.01])
      assert.throws(()=>validate({previewLighting:{[field]:value}}),new RegExp('previewLighting.'+field));
    for (const value of [0,2,10]) assert.doesNotThrow(()=>validate({previewLighting:{[field]:value}}));
  }
  assert.throws(()=>validate({previewRotationY:'0'}),/metadata display/,'existing required rotation validation stays intact');
});

test('unknown metadata conventions and source objects remain unchanged', () => {
  const input=metadata({futureDisplay:{anything:true},previewLighting:{futureLighting:['preserved']}});
  input.futureMetadata={anything:true}; const before=structuredClone(input);
  assert.equal(validateMetadata(input,'earth'),input); assert.deepEqual(input,before);
});

test('ceiling opts into underside presentation without geometry, rotation or rights changes', () => {
  const asset=loadCatalog().collections.flatMap(c=>c.assets).find(a=>a.id==='mall-ceiling-panel-module');
  assert.deepEqual(asset.details.display.previewCameraDirection,[1,-1.4,1]);
  assert.deepEqual(asset.details.display.previewLighting,{directionalPosition:[4,-7,5]});
  assert.equal(asset.details.display.previewRotationY,0); assert.equal(asset.downloadable,false);
  assert.equal(asset.details.metrics.sha256,'40f7e02cc5f4db5fa3556ddda90c69ea128c98848707106433c25d1018b1d7ef');
});
