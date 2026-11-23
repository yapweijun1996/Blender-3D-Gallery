const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const dir = __dirname;
const read = (file) => JSON.parse(fs.readFileSync(path.join(dir, file), 'utf8'));
const banks = {
  shared: ['rest', 'walk', 'run', 'wave', 'jump', 'idle', 'nod', 'dance'],
  sit: ['sit_down', 'sit_idle', 'stand_up', 'hold_item'],
  carry: ['hold_box', 'hold_bag', 'take_item'],
};
const exportCheck = read('export_check.json');
const rest = read('rest_check.json');
assert.equal(rest.glb_sha256, exportCheck.glb_sha256);

const results = [];
for (const [bank, clips] of Object.entries(banks)) {
  const vertex = read(`checks/${bank}_vertex.json`);
  const triangle = read(`checks/${bank}_triangle.json`);
  assert.equal(vertex.glb_sha256, exportCheck.glb_sha256);
  assert.equal(triangle.glb_sha256, exportCheck.glb_sha256);
  for (const clip of clips) {
    const v = vertex.frames[clip] ?? [{frame: 1, count: vertex.results.rest[0], min_signed_m: vertex.results.rest[1]}];
    const t = triangle.frames[clip] ?? [{frame: 1, count: triangle.results.rest[0], min_signed_m: triangle.results.rest[1]}];
    assert.deepEqual(v.map((row) => row.frame), t.map((row) => row.frame));
    const vc = Math.max(...v.map((row) => row.count));
    const tc = Math.max(...t.map((row) => row.count));
    const deepest = [...v, ...t].reduce((a, b) => a.min_signed_m <= b.min_signed_m ? a : b);
    const failedFrames = v.filter((row, index) => row.count || t[index].count ||
      Math.min(row.min_signed_m, t[index].min_signed_m) < .0005).length;
    results.push({bank, clip, samples: v.length, peak_inside_vertices: vc, peak_overlap_pairs: tc,
      minimum_signed_m: deepest.min_signed_m, minimum_frame: deepest.frame, failed_frames: failedFrames});
  }
}
const samples = results.reduce((total, clip) => total + clip.samples, 0);
const fail = results.some((clip) => clip.failed_frames) || rest.vertex_above_30mm || rest.surface_above_30mm;
const result = {
  glb_sha256: exportCheck.glb_sha256,
  clip_count: results.length - 1,
  poses_including_rest: samples,
  body_clearance_gate: fail ? 'FAIL' : 'PASS',
  minimum_signed_m: Math.min(...results.map((row) => row.minimum_signed_m)),
  clips: results,
};
const table = [
  '| Clip | Samples | Peak inside vertices | Peak overlap pairs | Min signed (mm) | Frame | Failed poses |',
  '| --- | ---: | ---: | ---: | ---: | ---: | ---: |',
  ...results.map((row) => `| \`${row.clip}\` | ${row.samples} | ${row.peak_inside_vertices} | ${row.peak_overlap_pairs} | ${(1000 * row.minimum_signed_m).toFixed(4)} | ${row.minimum_frame} | ${row.failed_frames} |`),
].join('\n');
fs.writeFileSync(path.join(dir, 'checks/summary.json'), JSON.stringify(result, null, 2) + '\n');
fs.writeFileSync(path.join(dir, 'checks/summary.md'), table + '\n');
console.log(table);
if (fail) process.exitCode = 1;
