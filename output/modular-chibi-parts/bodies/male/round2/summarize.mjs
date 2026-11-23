import { readFileSync, writeFileSync } from 'node:fs';

const root = new URL('./', import.meta.url);
const read = name => JSON.parse(readFileSync(new URL(name, root)));
const body = read('qa/body.json');
const neutral = read('qa/neutral_rest_pairs.json');
const validation = read('qa/gltf_validation.json');
const keys = ['tshirt','dress','jeans','hair-bob','hair-spiky','hair-sidepart','sneakers'];
const modules = Object.fromEntries(keys.map(key => [key,read(`qa/modules/${key}.json`)]));
const names = Object.keys(body.clips);
const renders = read('renders/manifest.json');
const motionRenders = read('renders/motion/manifest.json');
const motionSHA = validation['motion_male_fixed.glb'].sha256;
if (body.sha256 !== motionSHA || motionRenders.bank_after !== motionSHA || renders.motion_sha256 !== motionSHA ||
    Object.values(modules).some(r => r.motion_sha256 !== motionSHA)) {
  throw Error('Body, renders and module QA must reference the emitted motion bank');
}
for (const [name,m] of Object.entries(modules)) {
  if (validation[m.file] && validation[m.file].sha256!==m.sha256) throw Error('Package/audit hash mismatch: '+name);
  const view = renders.modules[name];
  if (view.sha256 !== m.sha256) throw Error('Module render/audit hash mismatch: '+name);
  if (new Set(view.views).size!==6) throw Error('Six render views are required for '+name);
  for (const path of [view.sheet,...view.views]) {
    if (readFileSync(new URL(path,root)).readUInt32BE(0)!==0x89504e47) throw Error('Invalid PNG '+path);
  }
}
const poseCount = Object.values(body.clips).reduce((n,r)=>n+r.samples,0);
const poseNames = ['walk','wave','run','sit_idle','hold_box','take_item'];
for (const name of poseNames) {
  const png = motionRenders.clips[name].file;
  if (readFileSync(new URL(png,root)).readUInt32BE(0)!==0x89504e47) throw Error('Invalid PNG '+png);
}
if (readFileSync(new URL(renders.outfits,root)).readUInt32BE(0)!==0x89504e47) throw Error('Invalid outfit PNG');
const mm = n => Number(n).toFixed(4);
const sum = (a,f) => a.reduce((total,row)=>total+f(row),0);
const max = (a,f) => Math.max(...a.map(f));
const min = (a,f) => Math.min(...a.map(f));
const motionPass = names.length === 14 && Object.values(body.clips).every(c =>
  c.target_pairs === 0 && c.planted_height_mm <= 1 && c.hip_height_change_mm <= 2);
const modulePass = Object.values(modules).every(m => Object.keys(m.clips).length === 15 &&
  Object.values(m.clips).every(c => c.shortfall_samples === 0));
const tshirt = Object.values(modules.tshirt.clips);
const tspenetration = tshirt.reduce((n,r) => n+r.total_inside,0);
const tsbelow = tshirt.flatMap(r=>r.frames).filter(f=>f.min_signed_m<.0005);
const tshirtException = tspenetration>0 && tspenetration<=21 &&
  Math.min(...tshirt.map(r=>r.min_signed_m))>=-.0014 &&
  tshirt.every(r=>r.total_triangle_pairs===0) && tsbelow.every(f=>f.inside>0);
const exceptionText = tshirtException
  ? 'The T-shirt qualifies for the requested vertex allowance. The tested offset, weight, topology and local search passes left '+tspenetration+' inside vertex occurrence with zero triangle contacts. The exact frame and depth are listed below.'
  : '';
const packagePass = Object.values(validation).every(a => a.errors === 0);
const modRows = [];
const exceptions = [];
const bodyRows = [];
const bodyExceptions = [];
for (const [name,c] of Object.entries(body.clips)) {
  const deepest = max([{max_depth_mm:0},...Object.values(c.regions)], r=>r.max_depth_mm);
  bodyRows.push(`| ${name} | ${c.samples} | ${c.target_pairs} | ${c.total_pairs} | ${c.peak_pairs} | ${mm(deepest)} | ${mm(c.planted_height_mm)} | ${mm(c.planted_height_change_mm)} | ${mm(c.planted_ankle_horizontal_change_mm)} | ${mm(c.hip_height_change_mm)} |`);
  for (const [zone,r] of Object.entries(c.regions)) {
    bodyExceptions.push(`| ${name} | ${zone} | ${r.frames} | ${r.pairs} | ${mm(r.max_depth_mm)} | ${r.frame} |`);
  }
}
for (const [key,m] of Object.entries(modules)) {
  const rows = Object.values(m.clips);
  const best = min(rows,r=>r.min_signed_m);
  const peakVerts = max(rows,r=>r.peak_inside);
  const peakPairs = max(rows,r=>r.peak_triangle_pairs);
  const gate = rows.length===15 && rows.every(r=>!r.shortfall_samples);
  modRows.push(`| ${m.file} | ${m.triangles} | ${peakVerts} | ${peakPairs} | ${mm(best*1000)} | ${sum(rows,r=>r.shortfall_samples)} | ${gate?'PASS':key==='tshirt'&&tshirtException?'VERTEX ALLOWANCE':'FAIL'} | [JSON](qa/modules/${key}.json) | [Six views](renders/${key}/six-views.png) |`);
  for (const [clip,r] of Object.entries(m.clips)) {
    if (!r.shortfall_samples) continue;
    exceptions.push(`| ${m.file} | ${clip} | ${r.minimum_frame} | ${r.shortfall_samples} | ${r.peak_inside} | ${r.peak_triangle_pairs} | ${mm(r.min_signed_m*1000)} | ${mm(r.peak_triangle_depth_mm)} |`);
  }
}
const outfit = Object.entries(renders.outfit_pairs ?? {}).flatMap(([pose,pairs]) =>
  Object.entries(pairs).map(([pair,count]) => '| '+pose+' | '+pair+' | '+count+' |'));
const fitRows = ['tshirt','dress','jeans'].map(key => {
  const fit=read('qa/fit-'+key+'.json');
  return '| '+fit.file+' | '+fit.triangles+' | '+mm(fit.max_baked_offset_mm)+' | [Fit history](qa/fit-'+key+'.json) |';
});
const packageRows = Object.entries(validation).map(([path,r]) =>
  '| '+path+' | '+r.bytes+' | '+r.joints+' | '+r.errors+' | '+r.warnings+' |');
const output = `# Male body and garment fit · Round 2

**Motion gate ${motionPass?'PASS':'FAIL'}. Module gate ${modulePass?'PASS':'FAIL'}. GLB validation ${packagePass?'PASS':'FAIL'}.**

## Motion

[motion_male_fixed.glb](motion_male_fixed.glb) carries the same 14 clip names, input time bounds, 65 joints, and bind hierarchy as round 1. The verification counts unordered epsilon-zero triangle pairs from the reimported male body. It excludes adjacent triangles across welded rest positions and any exact pair already present in that mesh's bind pose. The male bind had ${Object.keys(body.rest_pairs).length?sum(Object.values(body.rest_pairs),r=>r.count):0} such pairs. The neutral reference master has ${neutral.pairs} non-adjacent bind pairs across ${Object.keys(neutral.region_pairs).length} zones. Its triangle IDs belong to a different mesh. [Male body replay](qa/body.json) · [Neutral rest pair IDs and depths](qa/neutral_rest_pairs.json) · [Package validation](qa/gltf_validation.json)

Target regions cover arms, hands and fingers against the torso, head and legs, and shins against thighs. The target count also includes elbow and wrist folds, shoulder overlaps and foot-to-shin contacts. The Blender replay checked ${poseCount} pose samples. The reported floor error is the absolute vertical distance from the ground at reference-derived support samples. Sole and horizontal ankle changes are measured against round 1 at the same support samples. Hip change compares the maximum absolute vertical difference in Hips position. Each clip includes endpoints and integer and half frames at 24 and 30 fps. Walk also includes the offset 30 fps grid measured from its first key. The render sheets align sample phase across the neutral reference, round-one male and round-two male. The male wave raises its hand higher in the round-one retarget. The pose is carried through in round two. The take-item elbow opens enough to move the right hand outward. The walk edit also releases the left thumb locally where it touched the skirt. The other 13 animation definitions and their sampled data remain byte-identical to the previously audited bank. [Walk channel audit](qa/walk_motion_proof.json)

| Clip | Samples | Target pairs | All pairs | Peak at one sample | Deepest (mm) | Planted error (mm) | Sole change (mm) | Ankle drift (mm) | Hip change (mm) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
${bodyRows.join('\n')}

[Walk](renders/motion/walk-before-after.png) · [Wave](renders/motion/wave-before-after.png) · [Run](renders/motion/run-before-after.png) · [Sit idle](renders/motion/sit_idle-before-after.png) · [Hold box](renders/motion/hold_box-before-after.png) · [Take item](renders/motion/take_item-before-after.png)

## Modules

The three v2 exports start from the round 1 male garments. Long edges were split with UV/material interpolation and new skin weights were smoothed across welded seams. The bind-space offset bake samples signed distance and interior probes on crossed triangles. Each violated clearance requests the limiting penetration plus 1.5 mm. The Laplacian passes preserve the selected correction along its direction. The bake caps displacement at 30 mm from the subdivided source and tests the result against the posed surface. Trials that introduced new crossings were rejected or reduced. Residual entries below show any clearance the tested solutions could not reach. The reported gate independently reimports the exported GLBs and replays both round 1 predicates at every sampled frame. The gate requires no negative signed vertices, no body/garment triangle contacts and at least 0.5 mm signed clearance.

| Asset | Triangles | Peak inside vertices | Peak triangle pairs | Min clearance (mm) | Failed samples | Gate | Audit | Renders |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
${modRows.join('\n')}

[T-shirt](male-tshirt-v2.glb) · [Dress](male-dress-v2.glb) · [Jeans](male-jeans-v2.glb) · [Outfits](renders/outfits.png) · [Render manifest](renders/manifest.json)

| Fit export | Triangles | Maximum bind offset (mm) | Search evidence |
| --- | ---: | ---: | --- |
${fitRows.join('\n')}

### Outfit layer checks

| Pose | Garment pair | Triangle pairs |
| --- | --- | ---: |
${outfit.join('\n')}

### GLB packages

| File | Bytes | Joints | Errors | Warnings |
| --- | ---: | ---: | ---: | ---: |
${packageRows.join('\n')}

## Residual body overlaps

| Clip | Dominant joint pair | Samples | Triangle pair occurrences | Deepest (mm) | Frame |
| --- | --- | ---: | ---: | ---: | ---: |
${bodyExceptions.join('\n') || '| — | — | 0 | 0 | — | — |'}

## Module clearance shortfalls

${exceptionText}

| Asset | Clip | Minimum frame | Failed samples | Peak inside vertices | Peak triangle pairs | Min signed (mm) | Max pair depth (mm) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
${exceptions.join('\n') || '| — | — | — | 0 | 0 | 0 | — | — |'}

## Reproduction

The vertex and triangle results use the same signed-nearest-normal and triangle-overlap predicates as the round 1 copies in ../qa/checkers. Both predicates run on a shared Blender-evaluated pose. The per-clip and per-frame evidence is in qa/modules/.

Run Blender jobs with sh run.sh. The wrapper configures the guard, the scratch directory and two threads. The motion passes are motion_repair.py, leg_polish.py, floor_polish.py and shoe_guard.py following the sneaker replay. The fit history records the guarded displacement, local shape and weight trials, exact vertex search, triangle patch trials and witness subdivision. verify.py replays the body and modules. render_round2.py generates the Cycles sheets. The structural and Khronos report is generated by node validate.mjs. node summarize.mjs regenerates these tables. The round-one checker drivers also checked the sneakers before the thumb polish. The final Blender replay includes the amended walk. [Original checker replay](qa/supplied/sneakers)
`;
writeFileSync(new URL('NOTES.md',root),output);
console.log({motionPass,modulePass,packagePass,bodyRegions:bodyExceptions.length,moduleExceptions:exceptions.length});
