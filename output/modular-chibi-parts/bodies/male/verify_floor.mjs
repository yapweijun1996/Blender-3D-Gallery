import fs from 'node:fs';

const read = name => JSON.parse(fs.readFileSync(new URL(name,import.meta.url)));
const baseline = read('qa/body_baseline.json');
const fitted = read('qa/body_selfcheck.json');
const staticClips = new Set(['idle','wave','nod','hold_item','hold_box','hold_bag','take_item']);
const seated = new Set(['sit_down','sit_idle','stand_up']);
const results = {};
for (const [clip, row] of Object.entries(fitted.clips)) {
  const reference = new Map(baseline.clips[clip].foot_samples.map(([frame,...z]) => [frame,z]));
  const result = {groundContacts:0, maxAbsoluteGroundErrorMm:0, maxSupplementalErrorMm:0,
    lowestAnySoleMm:Math.min(...Object.values(row.foot_min_mm)), unmatchedFrames:0};
  for (const [frame,...z] of row.foot_samples) {
    const prior = reference.get(frame);
    if (!prior) {
      result.unmatchedFrames++;
      continue;
    }
    const low = Math.min(...prior);
    for (const [i, height] of prior.entries()) {
      const planted = staticClips.has(clip) || (seated.has(clip) ? height < Math.max(13,low+10)
        : height <= 2 || (low <= 3 && height-low < 4));
      if (!planted) continue;
      const onGrid = [frame*2,frame*2.5].some(value => Math.abs(value-Math.round(value))<1e-4);
      if (!onGrid) {
        result.maxSupplementalErrorMm = Math.max(result.maxSupplementalErrorMm,Math.abs(z[i]));
        continue;
      }
      result.groundContacts++;
      if (Math.abs(z[i]) > result.maxAbsoluteGroundErrorMm) {
        result.maxAbsoluteGroundErrorMm = Math.abs(z[i]);
        result.worstFrame = frame;
        result.worstSide = i===0 ? 'Left' : 'Right';
      }
    }
  }
  results[clip] = result;
}
const report = { baseFps:24, clipCount:Object.keys(results).length,
  maxErrorMm:Math.max(0,...Object.values(results).map(r=>r.maxAbsoluteGroundErrorMm)), clips:results };
fs.writeFileSync(new URL('qa/floor_validation.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
console.log('Blender reimport floor max error',report.maxErrorMm,'mm across',
  Object.keys(report.clips).length,'clips');
