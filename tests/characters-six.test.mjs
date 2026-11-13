import fs from 'node:fs';import assert from 'node:assert/strict';import test from 'node:test';import {createHash} from 'node:crypto';
const ids=['cashier','security-guard','delivery-rider','chef','teacher','warehouse-worker'];
const catalog=JSON.parse(fs.readFileSync('models/catalog.json'));
for(const id of ids){
test(id+' preserves fixed budgets and role-specific motion proof',()=>{
const h='models/'+id+'/',c=JSON.parse(fs.readFileSync(h+'contract.json')),r=JSON.parse(fs.readFileSync(h+'reports/assets.json')),b=JSON.parse(fs.readFileSync(h+'budget.json'));
assert.equal(r.status,'PASS');assert.equal(b.max_triangles,15000);assert.equal(b.max_glb_bytes,2000000);assert.equal(b.max_primitives,120);assert.ok(r.triangles<=b.max_triangles&&r.glb_bytes<=b.max_glb_bytes&&r.primitives<=b.max_primitives);assert.equal(r.sha256,createHash('sha256').update(fs.readFileSync(h+'exports/'+id+'.glb')).digest('hex'));
assert.deepEqual(r.clips.map(x=>x.clip).sort(),['Idle',c.action].sort());for(const clip of r.clips){assert.equal(clip.sample_count,41);assert.ok(clip.transformed_foot_vertex_drift<1e-5&&clip.grip_error<1e-5&&clip.root_drift<1e-5);}assert.equal(r.clip_switching,'PASS');assert.ok(r.clips.find(x=>x.clip===c.action).effector_travel>c.minimum_travel);
});
test(id+' is one independent editable registration with retained source proof',()=>{
const h='models/'+id+'/',s=JSON.parse(fs.readFileSync(h+'reports/sources.json')),m=JSON.parse(fs.readFileSync(h+'metadata/'+id+'.json'));assert.equal(catalog.collections.flatMap(c=>c.assets).filter(a=>a.id===id).length,1);assert.ok(s.canonical_unchanged&&s.saved_reopened&&s.export_without_regeneration&&s.exported_mesh_change);assert.equal(s.canonical_sha256,createHash('sha256').update(fs.readFileSync(h+'sources/'+id+'.blend')).digest('hex'));assert.match(m.description,/Not skinned/);
});
}
