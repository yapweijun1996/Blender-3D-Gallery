/** Verify the final bytes and complete checker coverage before reporting. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const dir = __dirname;
const parts = path.resolve(dir, '../../..');
const scratch = process.env.HAIR_CHECKER_DIR || '/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular';
const read = f => JSON.parse(fs.readFileSync(path.resolve(dir,f)));
const sha = f => crypto.createHash('sha256').update(fs.readFileSync(path.resolve(dir,f))).digest('hex');
const glb = 'hair_ponytail_v1.glb';
const id = sha(glb);
const geo = read('geometry_check.json');
const val = read('khronos_validation.json');
const visual = read('pixels_v1.json');
assert.equal(geo.asset_sha256,id);
assert.equal(val.asset_sha256,id);
assert.equal(visual.asset_sha256,id);
assert.equal(sha('fit_views_v1.png'),visual.sheet_sha256);
for (const [file,hash] of Object.entries(visual.closeups)) assert.equal(sha(file),hash);
assert.equal(geo.bytes,fs.statSync(path.join(dir,glb)).size);
assert(geo.bytes <= 1.2*1024**2 && geo.triangles >= 1500 && geo.triangles <= 3000);
assert(geo.has_uv && geo.hierarchy_matches && geo.editable_reopened);
assert.deepEqual(geo.textures,[[1024,1024]]);
assert.deepEqual(geo.weighted_bones,['mixamorig:Head']);
assert.equal(geo.joints,65);
assert.equal(geo.max_influences,1);
assert.equal(geo.max_inverse_bind_difference,0);
assert.equal(geo.components,1);
assert(geo.volume_m3>0 && geo.min_triangle_area>0);
for (const field of ['bad_edges','inconsistent_edges','nonadjacent_self_intersections','weight_sum_error']) assert.equal(geo[field],0);
assert.equal(val.issues.numErrors+val.issues.numWarnings,0);
const master=path.join(parts,'master/GJH_Chibi_Master_rigged.blend');
const banks = [
  ['shared','body-fix/motion_fixed.glb',['walk','run','wave','jump','idle','nod','dance']],
  ['act','actions-fix/actions_fixed.glb',['sit_down','sit_idle','stand_up','hold_item']],
  ['act2','actions-hold2/hold_actions.glb',['hold_box','hold_bag','take_item']]
];
const rows=[];
for (const [bank,file,clips] of banks) {
  const data = {};
  for (const stem of ['motion_check','motion_check_tri']) {
    const prefix='checks/'+bank+'/'+stem;
    const provenance=read(prefix+'_provenance.json');
    assert.equal(provenance.glb_sha256,id);
    assert.equal(provenance.master_sha256,sha(master));
    assert.equal(provenance.clips_sha256,sha(path.join(parts,file)));
    assert.equal(provenance.driver_sha256,sha('check_motion.py'));
    for (const [name,hash] of Object.entries(provenance.scripts)) {
      const base=bank==='shared'?scratch:path.join(parts,'body-fix',bank);
      assert.equal(hash,sha(path.join(base,name)));
    }
    const frames=read(prefix+'_frames.json'), summary=read(prefix+'.json');
    assert.deepEqual(Object.keys(frames).sort(),[...clips].sort());
    assert(summary.rest[0]===0 && summary.rest[1]>=.0005);
    for(const n of clips) {
      const fs=frames[n];
      assert(Number.isInteger(fs[0].frame)&&Number.isInteger(fs.at(-1).frame));
      assert(fs.every((r,i)=>!i||r.frame===fs[i-1].frame+.5));
      assert.equal(Math.max(...fs.map(r=>r.count)),summary[n][0]);
      assert.equal(Math.min(...fs.map(r=>r.min_signed_m)),summary[n][1]);
    }
    data[stem]=frames;
  }
  for (const name of clips) {
    const v=data.motion_check[name], t=data.motion_check_tri[name];
    assert.equal(v.length,t.length);
    assert(v.every((r,i)=>r.frame===t[i].frame));
    const worst=v.concat(t).reduce((a,b)=>a.min_signed_m<b.min_signed_m?a:b);
    const row={name,first:v[0].frame,last:v.at(-1).frame,samples:v.length,
      inside:Math.max(...v.map(r=>r.count)),overlap_pairs:Math.max(...t.map(r=>r.count)),
      min_signed_m:worst.min_signed_m,minimum_frame:worst.frame};
    assert(row.inside===0&&row.overlap_pairs===0&&row.min_signed_m>=.0005,JSON.stringify(row));
    rows.push(row);
  }
}
const eyes=read('eyes_check.json');assert.equal(eyes.asset_sha256,id);
for(const e of Object.values(eyes.eyes))assert(e.eye_samples>0&&e.occluded===0&&e.min_projected_margin_m>0);
const review=read('checks/visual_review.json');assert.equal(review.asset_sha256,id);assert.equal(review.decision,'PASS');
const report={asset_sha256:id,geometry:geo,khronos:val.issues,eyes:eyes.eyes,visual_review:review.decision,clips:rows,
  samples_per_checker:rows.reduce((s,r)=>s+r.samples,0),
  minimum_signed_m:Math.min(...rows.map(r=>r.min_signed_m)),visible_hair:visual.views,
  source_sha256:sha('../source_studio_segmented.glb'),master_sha256:sha(master),
  reference_sha256:sha(path.join(parts,'generated3/hair-05-ponytail-tpose.png')),blend_sha256:sha('hair_ponytail_v1.blend')};
fs.writeFileSync(path.join(dir,'checks/acceptance.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
