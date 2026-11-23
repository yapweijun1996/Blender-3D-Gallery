import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';

const base = new URL('./', import.meta.url);
const read = path => readFileSync(new URL(path, base));
const json = path => JSON.parse(read(path));
const hash = path => createHash('sha256').update(read(path)).digest('hex');
const pkg = json('qa/gltf_validation.json');
const render = json('renders/manifest.json');
const outfit = json('qa/outfit_layers.json');
const offsetMeasurement = json('qa/offset_measurement.json');
const fixed = '../round2/motion_male_fixed.glb';
const keys = ['dress', 'jeans'];
const filenames = Object.fromEntries(keys.map(key => [key, `male-${key}-v3.glb`]));
const fail = row => row.inside || row.triangle_pairs || row.min_signed_m < .0005;
const mm = meters => (meters * 1000).toFixed(4);
const file = (label, url) => `[${label}](${url})`;
const joint = value => value?.split(':').at(-1) ?? '—';
const audit = {};
const metrics = {};
const exceptions = [];
const motionHash = hash(fixed);

for (const item of json('qa/source_inventory.json')) {
  if (!item.path.startsWith('../sockets/') && !item.path.split('/').includes('.runtime')) assert.equal(hash(item.path), item.sha256, item.path);
}
assert.equal(render.motion_sha256, motionHash);
assert.equal(outfit.motion_sha256, motionHash);
assert.equal(render.body_master_sha256, hash('../master_male.blend'));
assert.deepEqual(render.assets, outfit.assets);
assert.deepEqual(render.outfit_layers, outfit.pairs);
assert.equal(hash(render.outfits.sheet), render.outfits.sha256);

for (const key of keys) {
  const name = filenames[key];
  const current = json(`qa/modules/${key}.json`);
  const old = json(`../round2/qa/modules/${key}.json`);
  assert.equal(current.file, name);
  assert.equal(current.sha256, hash(name));
  assert.equal(current.sha256, pkg[name].sha256);
  assert.equal(current.sha256, render.assets[key]);
  assert.equal(current.motion_sha256, motionHash);
  assert.deepEqual(Object.keys(current.clips), Object.keys(old.clips));
  assert.equal(current.triangles, pkg[name].triangles);
  const views = render.views[key];
  assert.equal(hash(views.sheet), views.sheet_sha256);
  assert.equal(Object.keys(views.panels).length, 6);
  for (const [path, sha] of Object.entries(views.panels)) {
    assert.equal(hash(path), sha);
    const png = read(path);
    assert.deepEqual([png.readUInt32BE(16), png.readUInt32BE(20)], render.resolution_per_view);
  }
  const summary = [];
  for (const [clip, rows] of Object.entries(current.clips)) {
    assert.deepEqual(rows.frames.map(f => f.frame), old.clips[clip].frames.map(f => f.frame), clip);
    for (const frame of rows.frames.filter(fail)) {
      exceptions.push({ key, clip, ...frame });
    }
    summary.push(rows);
  }
  const samples = summary.reduce((sum, r) => sum + r.samples, 0);
  assert.equal(samples, 3027);
  audit[key] = current.clips;
  metrics[key] = {
    samples, peakInside: Math.max(...summary.map(r => r.peak_inside)),
    peakPairs: Math.max(...summary.map(r => r.peak_triangle_pairs)),
    minimumM: Math.min(...summary.map(r => r.min_signed_m)),
    failed: summary.reduce((sum, r) => sum + r.shortfall_samples, 0),
  };
}
for (const [key, path] of Object.entries({
  'hair-bob': '../male-hair-bob.glb',
  'hair-spiky': '../male-hair-spiky.glb',
  tshirt: '../round2/male-tshirt-v2.glb',
  sneakers: '../male-sneakers.glb',
})) assert.equal(hash(path), render.assets[key]);

const body = json('../round2/qa/body.json');
assert.equal(body.sha256, motionHash);
const bodyTotal = Object.values(body.clips).reduce((sum, r) => sum + r.total_pairs, 0);
const bodyTargets = Object.values(body.clips).reduce((sum, r) => sum + r.target_pairs, 0);
const tshirt = json('../round2/qa/modules/tshirt.json');
assert.equal(tshirt.motion_sha256, motionHash);
assert.equal(tshirt.sha256, render.assets.tshirt);
const shirtRun = tshirt.clips.run.frames.find(f => f.inside);
const beforeLayers = json('../round2/renders/manifest.json').outfit_pairs;
const afterLayers = outfit.pairs;

let notes = '# Male dress and jeans · Round 3\n\n';
const layerClear = Object.values(afterLayers).every(pose => Object.values(pose).every(count => count === 0));
const shallow = exceptions.every(row => Math.max(-row.min_signed_m * 1000, row.triangle_depth_mm ?? 0) < 1.5);
const gate = exceptions.length > 0 ? (shallow ? 'Exception recorded' : 'Open') : 'Pass';
notes += `**Garment/body gates ${gate}. Outfit layer check ${layerClear ? 'Pass' : 'Open'}.** The Blender replay covered 3,026 samples across fourteen clips plus the bind pose. Sampling includes endpoints and integer and half frames on the round-two 24 and 30 fps grids.\n\n`;
notes += '| Export | Peak inside | Peak pairs | Min signed (mm) | Failed samples | Triangles | MiB | Max texture | Khronos E/W |\n';
notes += '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n';
for (const key of keys) {
  const name = filenames[key];
  const p = pkg[name];
  const t = metrics[key];
  notes += `| ${file(name, name)} | ${t.peakInside} | ${t.peakPairs} | ${mm(t.minimumM)} | ${t.failed} | ${p.triangles} | ${(p.bytes / 1048576).toFixed(3)} | ${Math.max(...p.images.flat())} px | ${p.errors}/${p.warnings} |\n`;
}
notes += '\n[Per-frame dress replay](qa/modules/dress.json) · [Per-frame jeans replay](qa/modules/jeans.json) · [Khronos and rig validation](qa/gltf_validation.json)\n\n';
notes += '## Clip results\n\n';
notes += '| Clip | Samples | Dress inside / pairs | Dress min (mm) | Jeans inside / pairs | Jeans min (mm) |\n';
notes += '| --- | ---: | ---: | ---: | ---: | ---: |\n';
for (const [clip, d] of Object.entries(audit.dress)) {
  const j = audit.jeans[clip];
  notes += `| ${clip} | ${d.samples} | ${d.peak_inside}/${d.peak_triangle_pairs} | ${mm(d.min_signed_m)} | ${j.peak_inside}/${j.peak_triangle_pairs} | ${mm(j.min_signed_m)} |\n`;
}
notes += '\n## Dress and jeans exceptions\n\n';
if (!exceptions.length) {
  notes += 'None. Every sample met the 0.5000 mm signed-distance floor and both zero-contact predicates.\n';
} else {
  notes += '| Garment | Clip | Frame | Vertex body zone | Inside | Signed min (mm) | Pair body zone | Pairs | Pair depth (mm) |\n';
  notes += '| --- | --- | ---: | --- | ---: | ---: | --- | ---: | ---: |\n';
  for (const row of exceptions) {
    notes += `| ${row.key} | ${row.clip} | ${row.frame} | ${joint(row.body_joint)} | ${row.inside} | ${mm(row.min_signed_m)} | ${joint(row.triangle_body_joint)} | ${row.triangle_pairs} | ${row.triangle_depth_mm?.toFixed(4) ?? '—'} |\n`;
  }
}
notes += '\n## Outfit fit\n\n';
notes += '| Pose | Pair | Round 2 | Round 3 |\n| --- | --- | ---: | ---: |\n';
for (const [pose, pairs] of Object.entries(afterLayers)) {
  for (const [pair, count] of Object.entries(pairs)) {
    notes += `| ${pose} | ${pair} | ${beforeLayers[pose][pair]} | ${count} |\n`;
  }
}
notes += '\nThe original cuff is shortened to clear the sneaker opening, leaving a small visible ankle gap. The jeans waistband is inset locally by 2 mm. The final idle renders were visually checked from all six views and in both outfits.\n';
notes += '\n[Dress six views](renders/dress/six-views.png) · [Jeans six views](renders/jeans/six-views.png) · [Both outfits](renders/outfits.png) · [Render hashes](renders/manifest.json)\n\n';
notes += '## Fit and reproduction\n\n';
notes += 'The fit starts from the v2 exports, subdivides long edges on reported contact faces and clips the cuffs at 0.121 m in bind space. The offset bake converts each sampled limiting nearest-surface direction to bind space, adds a 2 mm margin and caps the displacement at 30 mm. The Laplacian pass preserves the required directional projection before capped trial selection. Local lofts and skin-weight blends are checked on the moving rig. The smallest positional edits preserve the GLB skin attributes. The final search also tests the normals of equally near triangles at shared body corners. The final audit reimports the delivered files and runs the round-two checker functions unchanged.\n\n';
for (const key of keys) {
  const fit = json(`qa/fit-${key}.json`);
  assert.equal(fit.sha256, pkg[filenames[key]].sha256);
  assert.equal(offsetMeasurement[key].sha256, fit.sha256);
  const bound = offsetMeasurement[key].upper_bound_mm;
  assert.ok(bound <= 30.001, key);
  notes += `- ${key} displacement bound ${bound.toFixed(3)} mm. ${file('Fit history', `qa/fit-${key}.json`)}\n`;
}
notes += '\nReplay with `sh blender.sh verify_round3.py --` and render with `sh blender.sh render_round3.py --`. Run `node package_round3.mjs` before replay to normalize the GLB roots and check the deliverable packages. [Bind offset measurements](qa/offset_measurement.json)\n\n';
notes += '## Round-two carryovers\n\n';
notes += `The accepted T-shirt has ${shirtRun.inside} inside vertex at run frame ${shirtRun.frame}, ${mm(shirtRun.min_signed_m)} mm signed, and ${shirtRun.triangle_pairs} triangle pairs at that frame. The reused motion bank has ${bodyTargets} targeted body self-contact pairs in the round-two replay. The broader self-overlap diagnostic counted ${bodyTotal.toLocaleString('en-US')} pair occurrences. [T-shirt replay](../round2/qa/modules/tshirt.json) · [Body replay](../round2/qa/body.json)\n`;
writeFileSync(new URL('NOTES.md', base), notes);
console.log(JSON.stringify({ gate, layerClear, metrics, exceptions, outfit: afterLayers }, null, 2));
