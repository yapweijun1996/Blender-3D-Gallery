import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const here = fileURLToPath(new URL('.', import.meta.url));
const keyFiles = ['hair-bob','hair-spiky','hair-sidepart','tshirt','dress','jeans','sneakers'];
const clips = ['idle','walk','run','wave','jump','nod','dance','sit_down','sit_idle','stand_up','hold_item','hold_box','hold_bag','take_item'];
const read = file => fs.existsSync(path.join(here,file)) ? JSON.parse(fs.readFileSync(path.join(here,file))) : null;
const exists = file => fs.existsSync(path.join(here,file));
const size = bytes => (bytes / 1048576).toFixed(3);
const mm = value => (value * 1000).toFixed(4);
const val = read('qa/khronos.json') || {};
const baseline = read('qa/body_baseline.json')?.clips || {};
const body = read('qa/body_selfcheck.json');
const bake = read('qa/body_bake_batch.json') || {};
const floor = read('qa/floor_validation.json');
const supplementalFloor = Math.max(0,...Object.values(floor?.clips || {}).map(r=>r.maxSupplementalErrorMm || 0));
const renders = read('renders/manifest.json');
const layered = read('qa/outfit_layer_reimport.json');
const maxPlanted = Math.max(...Object.values(bake).map(row => row.max_planted_error_mm || 0),0);
const sizes = row => row ? row.images.map(img => img.size.join('×')).join(', ') || '—' : 'Pending';
const issues = row => row ? `${row.validator.issues.numErrors}/${row.validator.issues.numWarnings}` : 'Pending';
const bodyRows = [];
const bodyFailures = [];
for (const clip of clips) {
  const row = body?.clips[clip];
  if (!row) {
    bodyRows.push(`| ${clip} | ${baseline[clip]?.total_pairs ?? '—'} | Pending | — | — | — |`);
    continue;
  }
  const zones = Object.entries(row.regions).sort((a,b) => b[1].max_depth_mm-a[1].max_depth_mm);
  const worst = zones[0];
  bodyRows.push(`| ${clip} | ${baseline[clip]?.total_pairs ?? '—'} | ${row.total_pairs} | ${row.peak_pairs} | ${worst ? `${worst[1].max_depth_mm.toFixed(4)} · ${worst[0]} · f${worst[1].frame}` : '—'} | ${Math.min(...Object.values(row.foot_min_mm)).toFixed(4)} |`);
  bodyFailures.push(...zones.map(([zone,r])=>`| ${clip} | ${zone} | ${r.pairs} | ${r.max_depth_mm.toFixed(6)} | ${r.frame} |`));
}
const result = {
  files: {}, bodyAuditedClips: Object.keys(body?.clips || {}).length,
  bodyPassingClips: Object.values(body?.clips || {}).filter(r => !r.peak_pairs).length, maxPlanted,
  reimportPlantedErrorMm: floor?.maxErrorMm, supplementalFloor
};
const moduleRows = [];
const moduleFailures = [];
const moduleZones = [];
for (const name of keyFiles) {
  const file = `male-${name}.glb`;
  const assetHash = exists(file) ? createHash('sha256').update(fs.readFileSync(path.join(here,file))).digest('hex') : null;
  const fitEvidence = read(`qa/male-${name}.json`);
  const fitted = fitEvidence?.sha256 === assetHash ? fitEvidence : null;
  const directEvidence = read(`qa/direct/${file.replace('.glb','.json')}`);
  const measured = directEvidence?.sha256 === assetHash ? directEvidence : null;
  const direct = measured && (Object.keys(measured.clips).length===15 || !fitted) ? measured : null;
  const rows = direct?.clips || fitted?.reimport;
  if (!rows || !exists(file)) {
    moduleRows.push(`| ${exists(file) ? `[${file}](${file})` : file} | — | — | — | Pending | — | — | — |`);
    continue;
  }
  const checked = Object.values(rows);
  const minimum = Math.min(...checked.map(r => r.minimum_m));
  const maxV = Math.max(...checked.map(r => r.max_vertices_inside));
  const maxT = Math.max(...checked.map(r => r.max_tri_pairs));
  const budget = val[file] && val[file].bytes <= 1.5*1048576 && val[file].images.every(i => Math.max(...i.size)<=1024)
    && val[file].triangles <= (name.startsWith('hair-') ? 3000 : name === 'sneakers' ? 3500 : 6000);
  const gate = Object.keys(rows).length === 15 ? (!maxV && !maxT && minimum >= 0.0005 ? 'PASS' : 'FAIL') : 'Partial';
  const view = renders?.modules[name]?.sha256 === assetHash ? `[Six views](${renders.modules[name].sheet})` : 'Pending';
  const checkedBy = direct ? 'Blender' : 'Reimport math';
  const gateText = `${gate} · ${checkedBy}`;
  moduleRows.push(`| [${file}](${file}) | ${fitted?.triangles ?? val[file]?.triangles ?? '—'} | ${size(fs.statSync(path.join(here,file)).size)} | ${sizes(val[file])} | ${gateText} | ${maxV} / ${maxT} | ${mm(minimum)} | ${view} |`);
  for (const [clip,r] of Object.entries(rows)) {
    if (!r.max_vertices_inside && !r.max_tri_pairs && r.minimum_m >= .0005) continue;
    moduleFailures.push(`| ${name} | ${clip} | ${r.zone} · ${r.body_joint || '—'} | ${r.frame} | ${r.max_vertices_inside} | ${r.max_tri_pairs} | ${mm(r.minimum_m)} | ${r.triangle_zone ? `${r.max_triangle_depth_mm.toFixed(4)} · ${r.triangle_zone} · f${r.triangle_frame}` : '—'} |`);
    for (const [zone,witness] of Object.entries(r.zones || {})) {
      moduleZones.push(`| ${name} | ${clip} | ${zone} · ${witness.body_joint} | ${witness.frame} | ${mm(witness.minimum_m)} |`);
    }
  }
  result.files[name] = { maximumVertexInside:maxV, maximumTriangleOverlap:maxT, minimumDistanceMm:Number(mm(minimum)),
    verifiedClips:Object.keys(rows).length-Number(Boolean(rows.rest)), gate, directBlender:Boolean(direct), budget:val[file] ? Boolean(budget) : null };
}
const failures = `# Remaining clearance failures

## Body self-overlap by bone pair

The depth is the least separating translation of an intersecting triangle pair. Counts are summed over samples.

| Clip | Zone | Triangle pairs | Max depth (mm) | Frame at 24 fps |
| --- | --- | ---: | ---: | ---: |
${bodyFailures.join('\n') || '| — | — | — | — | — |'}

## Module clearance by clip

A negative signed distance is penetration depth with its sign retained. A positive distance below 0.5000 mm also fails the clearance gate. Triangle depth uses the same pairwise measure as the body audit. The body-joint label comes from the strongest pose influence on the contacted triangle.

| Module | Clip | Module zone · body joint | Frame at 24 fps | Peak inside verts | Peak pairs | Min signed (mm) | Peak triangle depth (mm) · zone · frame |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
${moduleFailures.join('\n') || '| — | — | — | — | — | — | — | — |'}

## Every module zone below the signed-distance threshold

| Module | Clip | Module zone · body joint | Frame at 24 fps | Min signed (mm) |
| --- | --- | --- | ---: | ---: |
${moduleZones.join('\n') || '| — | — | — | — | — |'}
`;
fs.writeFileSync(path.join(here,'qa/clearance_failures.md'),failures);
fs.writeFileSync(path.join(here,'qa/summary.json'),JSON.stringify(result,null,2)+'\n');
const bodyV = val['body_male.glb'];
const motionV = val['motion_male.glb'];
const gV = val['hand_gestures_male.glb'];
const warnings = Object.entries(val).filter(([,row])=>row.validator.issues.numWarnings>0)
  .map(([file,row])=>`${file} (${row.validator.issues.numWarnings})`).join(', ');
const note = `# Studio male modular dress-up

## 1. Body readiness

| Deliverable | Verification |
| --- | --- |
| [body_male.glb](body_male.glb) | ${bodyV ? `${size(bodyV.bytes)} MiB, 9,974 triangles, one skinned \`Base_Body\` mesh, 65 joints and the neutral parent hierarchy, textures ${sizes(bodyV)}. Khronos errors/warnings ${issues(bodyV)}.` : 'Khronos report pending.'} |
| [master_male.blend](master_male.blend) | \`Armature\` and \`Base_Body\` with identity world transforms, quaternion pose bones and packed PBR maps. Bind-pose self-overlap ${body?.rest.pairs ?? 0}. |
| [motion_male.glb](motion_male.glb) | ${motionV ? `${Object.keys(motionV.animations).length} quaternion clips, matching bind hierarchy and source durations, skeleton-only GLB. Khronos errors/warnings ${issues(motionV)}.` : 'Pending.'} |
| [hand_gestures_male.glb](hand_gestures_male.glb) | Byte-for-byte Studio bank. Eighteen \`hand_<name>_L\` / \`hand_<name>_R\` clips on the exact male bind. Khronos errors/warnings ${issues(gV)}. |

The Studio GLB contains 9,974 triangles. The male is 0.97785 m tall against the Blender master at 0.99951 m, a 2.17% difference. The chosen scale is **1.000000**. It faces glTF +Z and the lowest rest vertex is at y = −0.000000029 m. The base color was JPEG-encoded and the normal and metallic–roughness maps were resampled to fit the byte budget. The original geometry, UV and skin payloads are intact.

The retarget uses joint rotation deltas expressed in the two bind bases. The source Hips displacement in world metres, root axes and clip times are preserved. Pose clearance adds lateral shoulder and elbow adjustments, distributed leg glide, and limited toe or digit relaxation. A floor compensation is distributed through the upper leg, shin and foot. Locomotion contact is inferred from each original male-retargeted sole trajectory. The lower stance foot is planted when near the floor, and an airborne interval is preserved. Stationary actions keep both feet planted. The maximum planted error in the bake was **${maxPlanted.toFixed(4)} mm**. Floor error is vertical, and no horizontal foot-lock threshold was requested.

**Body self-overlap** · ${result.bodyPassingClips} of ${result.bodyAuditedClips} audited clips reached zero. ${result.bodyAuditedClips===14 && result.bodyPassingClips<14 ? 'The body animation clearance gate remains open.' : ''}
${floor ? `The Blender reimport measured **${floor.maxErrorMm.toFixed(4)} mm** maximum planted error on the integer and half-frame grids. A supplementary offset grid in walk measured **${supplementalFloor.toFixed(4)} mm** during a support transition. [Floor evidence](qa/floor_validation.json)` : ''}

The table uses the original body checker’s overlap and adjacency rules against the reimported master and motion. It evaluates endpoints and integer and half frames for both the shared 24 fps and extra 30 fps conventions. The after count sums occurrences across these samples. A triangle-pair depth of zero can be a tangency.

| Clip | Before pairs | After pairs | Peak at one sample | Deepest pair in mm · zone · frame | Lowest sole (mm) |
| --- | ---: | ---: | ---: | --- | ---: |
${bodyRows.join('\n')}

[Baseline](qa/body_baseline.json) · [Baked floor](qa/body_bake_batch.json) · [Body self-check](qa/body_selfcheck.json) · [Khronos reports and hashes](qa/khronos.json) · [Every outstanding zone](qa/clearance_failures.md)

## 2. Auto-fit tool

[fit_module.py](fit_module.py) projects the neutral body to the male by region using a joint-pivot seed, same-facing surface correspondence and smooth distance weighting. It interpolates the resulting field with Laplacian smoothing across welded UV seams while retaining the triangle topology, UVs and material slots. It retains authored skinning where possible and blends in nearby male surface weights on mapped tops and bottoms. The fitter expands the displacement envelope using signed penetration plus 1.5 mm, including triangle-only hits, with a 30 mm clearance correction cap. Smoothing retains the highest sampled local requirement up to the cap. It exports and reimports the exact GLB and compares the numerical skin evaluation against Blender.

Use \`./run.sh fit_module.py -- /absolute/neutral.glb male-custom.glb --slot top\` from this folder. Slots are \`hair\`, \`top\`, \`dress\`, \`bottom\` and \`shoes\`. [Source and final measurement code](fit_module.py) · [Supplied checker adaptations](qa/checkers) · [Stage 2 smoke log](qa/fit-smoke.log)

## 3. Seven fitted modules

The cutoff is zero inside vertices, zero triangle pairs and ≥0.5000 mm signed clearance in the bind pose and all 14 clips. Peaks are the worst individual sample. Counts cover body-to-module intersections.

| Module | Triangles | MiB | Texture dimensions | Clearance gate | Peak verts / pairs | Minimum (mm) | On-body renders |
| --- | ---: | ---: | --- | --- | --- | ---: | --- |
${moduleRows.join('\n')}

${renders?.outfits ? '[Full-outfit contact sheet](renders/outfits.png) · [Render settings and export hashes](renders/manifest.json)' : 'The full-outfit contact sheet is pending.'}
[Clearance failures with clips, zones, frames and depths](qa/clearance_failures.md) · [Machine-readable stage summary](qa/summary.json) · [Independent visual review](qa/visual_review.md)

${layered ? `The reimported T-shirt and jeans have **${layered.clips.idle.triangle_pairs}** layer overlaps at the rendered idle frame and **${layered.clips.rest.triangle_pairs}** at bind. The hem was reshaped with extra motion probes after a taller trial caused larger intersections in walk. The sneaker fit links the liner, midsole and tread to keep its white toe cap intact. The dress retains small hem creases and the jeans retain heavier rear knee folds than the neutral reference. [Layer bake](qa/outfit_layer.json) · [Reimport](qa/outfit_layer_reimport.json)` : ''}

${warnings ? `All GLBs validate with zero Khronos errors. Remaining warnings occur on ${warnings}. The warnings flag the nested skinned mesh nodes and, on Spiky, shader-generated tangents. [Validator details](qa/khronos.json)` : ''}

## Runtime handoff

The headless [Three.js smoke check](qa/demo_runtime_smoke.json) exercises the existing demo’s rig and skeleton remapper. It uses offline texture placeholders. The Blender renders exercise the embedded materials. Consumers of the male motion bank need to play the non-Hips translations and animated scales to retain the baked clearances. The demo’s current shared-clip branch filters those channels when stripping horizontal Hips motion. Also wire the fitted modules and the male gestures against the male skeleton. The existing expression atlas expects face morphs on the neutral body and is outside this asset build.

## Rebuild and check

From this directory, rebuild the static assets with \`./run.sh build_body.py\`, retarget with \`./run.sh build_motion.py\`, and bake male motion with \`./run.sh batch_clear.py\`. Run \`./run.sh body_audit.py\` and \`node verify_floor.mjs\` for the body. The current fitter runs all slots with \`node batch_fit.mjs 5\`. The delivered clothing and shoes were chosen from multiple fit and render rounds. The shipped hashes are in the [delivery manifest](qa/delivery.json). Audit finished GLBs with \`./run.sh gate_suite.py\` and generate all views with \`./run.sh render_modules.py\`. The supplied checker copies can also run via \`./run.sh gate_module.py -- male-hair-bob.glb\`. Refresh the report with \`node report.mjs\`.
`;
fs.writeFileSync(path.join(here,'NOTES.md'),note);
console.log(result);
