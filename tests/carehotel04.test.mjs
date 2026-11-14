import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {createHash} from 'node:crypto';
const specs=JSON.parse(fs.readFileSync('scripts/batchcarehotel04.json')),catalog=JSON.parse(fs.readFileSync('models/catalog.json')),sha=f=>createHash('sha256').update(fs.readFileSync(f)).digest('hex');
for(const s of specs)test(s.id+' '+s.title+' source, GLB, metadata, previews and catalog evidence',()=>{
 const p='models/'+s.slug+'/',m=JSON.parse(fs.readFileSync(p+'metadata/'+s.slug+'.json')),r=JSON.parse(fs.readFileSync(p+'reports/assets.json')),source=JSON.parse(fs.readFileSync(p+'reports/source.json'));
 assert.equal(catalog.collections.flatMap(c=>c.assets).filter(a=>a.id===s.slug).length,1);
 assert.equal(m.backlog_id,s.id);assert.equal(m.metrics.sha256,r.sha256);assert.equal(sha(p+'exports/'+s.slug+'.glb'),r.sha256);assert.equal(r.validation.errors,0);assert.equal(r.validation.warnings,0);assert.ok(r.triangles<s.budget_triangles&&r.glb_bytes<s.budget_bytes);
 assert.equal(sha(p+'sources/'+s.slug+'.blend'),source.source_sha256);assert.equal(source.edit_proof.result,'PASS');assert.equal(source.units,'metres');
 for(const name of ['hero','front','rear']){const b=fs.readFileSync(p+'previews/'+name+'.webp');assert.equal(b.toString('ascii',0,4),'RIFF');assert.equal(b.toString('ascii',8,12),'WEBP');}
 if(s.animation_nodes){const a=JSON.parse(fs.readFileSync(p+'reports/animation.json'));assert.equal(a.result,'PASS');assert.ok(a.clips.length>0);assert.notDeepEqual(a.open,a.closed);}
 const visual=JSON.parse(fs.readFileSync(p+'reports/visual-review.json'));assert.equal(visual.result,'PASS');assert.equal(visual.glb_sha256,r.sha256);assert.equal(visual.source_sha256,source.source_sha256);assert.equal(source.edit_proof.material_roughness_survived_save_reopen_export,true);
 assert.equal(m.status,'draft');assert.equal(m.quality_gate.android,'NOT TESTED');assert.equal(m.quality_gate.ios,'NOT TESTED');
});
