import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

const here = path.dirname(fileURLToPath(import.meta.url));
const read = file => JSON.parse(fs.readFileSync(path.join(here, file), 'utf8'));
const digest = createHash('sha256').update(fs.readFileSync(path.join(here, 'pants_v6.glb'))).digest('hex');
const banks = {
  shared: ['rest', 'walk', 'run', 'wave', 'jump', 'idle', 'nod', 'dance'],
  actions: ['sit_down', 'sit_idle', 'stand_up', 'hold_item'],
  carry: ['hold_box', 'hold_bag', 'take_item'],
};
const peaks = samples => samples.length ? Math.max(...samples.map(row => row.count)) : null;
const group = (rows, half) => rows.filter(row => Number.isInteger(row.frame) !== half);
const results = {};
for (const [bank, clips] of Object.entries(banks)) {
  const base = `checkers/${bank}`;
  const vertex = read(`${base}/vertex/motion_check.json`);
  const triangle = read(`${base}/triangle/motion_check_tri.json`);
  const vertexFrames = read(`${base}/vertex/motion_check_frames.json`);
  const triangleFrames = read(`${base}/triangle/motion_check_tri_frames.json`);
  for (const kind of ['vertex', 'triangle']) {
    if (read(`${base}/${kind}/provenance.json`).glb_sha256 !== digest) throw new Error('Stale motion result');
  }
  for (const clip of clips) {
    const v = clip === 'rest' ? [{ frame: 1, count: vertex.rest[0], min_signed_m: vertex.rest[1] }] : vertexFrames[clip];
    const t = clip === 'rest' ? [{ frame: 1, count: triangle.rest[0], min_signed_m: triangle.rest[1] }] : triangleFrames[clip];
    if (v.length !== t.length || v.some((row, index) => row.frame !== t[index].frame)) {
      throw new Error(`Sample mismatch for ${clip}`);
    }
    if (clip !== 'rest' && v.some((row, i) => i > 0 && i < v.length - 1 && row.frame - v[i - 1].frame > .5)) {
      throw new Error(`Incomplete frame coverage for ${clip}`);
    }
    const minimum = [...v, ...t].reduce((a, b) => b.min_signed_m < a.min_signed_m ? b : a);
    const row = {
      samples: v.length,
      integer_samples: group(v, false).length,
      half_samples: group(v, true).length,
      max_vertices_inside_integer: peaks(group(v, false)),
      max_vertices_inside_half: peaks(group(v, true)),
      max_triangle_pairs_integer: peaks(group(t, false)),
      max_triangle_pairs_half: peaks(group(t, true)),
      minimum_signed_m: minimum.min_signed_m,
      minimum_frame: minimum.frame,
    };
    row.pass = Math.max(peaks(v), peaks(t)) === 0 && row.minimum_signed_m >= .0005;
    results[clip] = row;
  }
}
const report = {
  glb_sha256: digest,
  motion_clip_count: Object.values(banks).flat().length - 1,
  poses_including_rest: Object.values(results).reduce((sum, row) => sum + row.samples, 0),
  pass: Object.values(results).every(row => row.pass),
  results,
};
const carry = banks.carry;
const nativeBase = 'checkers/carry_native';
const native = {};
for (const kind of ['vertex', 'triangle']) {
  if (read(`${nativeBase}/${kind}/provenance.json`).glb_sha256 !== digest) throw new Error('Stale native carry result');
  native[kind] = read(`${nativeBase}/${kind}/${kind === 'vertex' ? 'motion_check' : 'motion_check_tri'}_frames.json`);
}
report.native_carry = Object.fromEntries(carry.map(clip => {
  const v = native.vertex[clip];
  const t = native.triangle[clip];
  if (v.length !== 97 || t.length !== 97 || v.some((row, i) => row.frame !== i / 2 || t[i].frame !== row.frame)) {
    throw new Error(`Incomplete native carry frame coverage for ${clip}`);
  }
  const min = [...v, ...t].reduce((a, b) => b.min_signed_m < a.min_signed_m ? b : a);
  return [clip, { samples: v.length, peak_inside: peaks(v), peak_pairs: peaks(t),
    minimum_signed_m: min.min_signed_m, minimum_frame: min.frame,
    pass: peaks(v) === 0 && peaks(t) === 0 && min.min_signed_m >= .0005 }];
}));
report.pass &&= Object.values(report.native_carry).every(row => row.pass);
fs.writeFileSync(path.join(here, 'motion_summary.json'), JSON.stringify(report, null, 2) + '\n');
console.table(results);
if (!report.pass) process.exitCode = 1;
