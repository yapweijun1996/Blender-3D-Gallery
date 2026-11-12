import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { loadCatalog } from '../scripts/catalog.mjs';
import { reports } from '../models/mall-glass-railing/validate.mjs';
const folder='models/mall-glass-railing';
const catalog=loadCatalog(),collection=catalog.collections.find(c=>c.id==='mall-glass-railing');
test('glass railing collection has exactly the three distinct reusable modules',()=>{
  assert.deepEqual(collection.assets.map(a=>a.id),['mall-glass-railing-post','mall-glass-railing-1m','mall-glass-railing-2m']);
});
for(const report of reports)test(report.id+' source, rights, metrics and glass contract',()=>{
  const a=collection.assets.find(a=>a.id===report.id),m=JSON.parse(fs.readFileSync(folder+'/metadata/'+report.id+'.json'));
  const source=JSON.parse(fs.readFileSync(folder+'/reports/sources.json')).find(s=>s.id===report.id);
  const bytes=fs.readFileSync(a.file);
  assert.equal(a.downloadable,false);assert.match(a.license,/redistribution terms have not been specified/);
  assert.equal(m.rights,a.license);assert.equal(m.metrics.sha256,createHash('sha256').update(bytes).digest('hex'));
  assert.equal(m.metrics.glb_bytes,bytes.length);assert.equal(m.metrics.sha256,report.sha256);
  assert.equal(m.validation.errors,0);assert.equal(m.validation.warnings,0);
  assert.equal(source.source_reopened,'PASS');assert.ok(source.editable_parts>=16);
  assert.equal(source.source_sha256,createHash('sha256').update(fs.readFileSync(folder+'/'+m.paths.source)).digest('hex'));
  assert.equal(m.display.previewRotationY,0);assert.ok(Math.abs(report.bounds.min[1])<1e-5);
  const webp=fs.readFileSync(a.thumbnail);assert.equal(webp.toString('ascii',0,4),'RIFF');assert.equal(webp.toString('ascii',8,12),'WEBP');assert.ok(webp.length<150*1024);
  assert.equal(fs.readFileSync(folder+'/'+m.paths.render).toString('hex',0,8),'89504e470d0a1a0a');
  if(report.spacing){assert.equal(report.glass.alphaMode,'BLEND');assert.ok(report.glass.alpha>.2&&report.glass.alpha<.4);assert.equal(report.glass.doubleSided,true);assert.equal(source.glass_panels,1);}
});
test('real exported components pass repeated and orthogonal assembly clearance checks',()=>{
  const assembly=JSON.parse(fs.readFileSync(folder+'/reports/assembly.json'));
  assert.deepEqual(assembly.map(a=>a.name),['repeated-1m','mixed-right-angle']);
  for(const a of assembly){assert.equal(a.result,'PASS');assert.ok(a.actualExportedConnectedPiecePairsTested>3000);assert.ok(a.maxConnectorErrorMetres<1e-5);assert.ok(a.maxIntermoduleAabbPenetrationMetres<=a.allowanceMetres);}
});
