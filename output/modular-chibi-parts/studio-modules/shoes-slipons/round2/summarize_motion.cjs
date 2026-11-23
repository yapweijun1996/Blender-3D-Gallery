const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const qa = path.join(__dirname, 'qa');
const sha = crypto.createHash('sha256')
  .update(fs.readFileSync(path.join(__dirname, 'shoes_slipons_v2.glb'))).digest('hex');
const read = (...parts) => fs.readFileSync(path.join(qa, ...parts), 'utf8');
const floor = .0005;
const groups = {
  shared: ['rest', 'walk', 'run', 'wave', 'jump', 'idle', 'nod', 'dance'],
  'sit-hold': ['sit_down', 'sit_idle', 'stand_up', 'hold_item'],
  carry: ['hold_box', 'hold_bag', 'take_item'],
};
const dense = JSON.parse(read('motion_gate.json'));
assert.equal(dense.glb_sha256, sha);
assert.equal(Object.keys(dense.results).length, 15);
const clips = {};
for (const [group, names] of Object.entries(groups)) {
  const native = {};
  for (const [mode, stem] of [['vertex', 'motion_check'], ['triangle', 'motion_check_tri']]) {
    const dir = ['checkers', group, mode];
    const log = read(...dir, 'RESULT.txt');
    assert(log.includes('CHECKED_GLTF_SHA256 ' + sha));
    for (const file of ['walk.png', 'run.png', 'wave.png', 'jump.png']) {
      const bytes = fs.readFileSync(path.join(qa, ...dir, file));
      assert.equal(bytes.readUInt32BE(0), 0x89504e47);
    }
    native[mode] = JSON.parse(read(...dir, stem + '.json'));
    const entries = Object.entries(native[mode]);
    assert.equal(entries.length, group === 'shared' ? 8 : group === 'sit-hold' ? 12 : 11);
    for (const [clip, [count, distance]] of entries) {
      assert.equal(count, 0, group + ' ' + mode + ' ' + clip);
      assert(distance >= floor, group + ' ' + mode + ' ' + clip + ' clearance');
    }
  }
  for (const name of names) {
    const [vertices, vertexMin] = native.vertex[name];
    const [pairs, triMin] = native.triangle[name];
    const scan = dense.results[name];
    assert(scan && scan.samples > 0);
    assert.equal(scan.max_vertices_inside, 0);
    assert.equal(scan.max_triangle_pairs, 0);
    assert(scan.min_signed_m >= floor);
    clips[name] = {native_vertices_inside: vertices, native_triangle_pairs: pairs,
      native_vertex_min_m: vertexMin, native_triangle_min_m: triMin, dense: scan};
  }
}
assert.equal(Object.keys(clips).length, 15);
const sampleCount = Object.values(clips).reduce((count, {dense}) => count + dense.samples, 0);
const report = {glb_sha256: sha, min_signed_distance_gate_m: floor,
  samples_including_rest: sampleCount, clips};
fs.writeFileSync(path.join(qa, 'motion_summary.json'), JSON.stringify(report, null, 2) + '\n');
console.table(Object.fromEntries(Object.entries(clips).map(([name, c]) => [name, {
  inside: c.native_vertices_inside, overlap: c.native_triangle_pairs,
  native_vertex_mm: (c.native_vertex_min_m * 1000).toFixed(3),
  native_triangle_mm: (c.native_triangle_min_m * 1000).toFixed(3),
  dense_mm: (c.dense.min_signed_m * 1000).toFixed(3), samples: c.dense.samples,
}])));
console.log(sampleCount + ' dense poses including rest for ' + sha);
