const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const root = __dirname;
const read = relative => JSON.parse(fs.readFileSync(path.join(root, relative), "utf8"));
const sha = relative => createHash("sha256").update(fs.readFileSync(path.join(root, relative))).digest("hex");
const changed = ["tshirt", "dress", "jeans"];
const controls = ["hair-bob", "hair-spiky", "hair-sidepart", "sneakers"];
const names = [...changed, ...controls];
const assets = read("assets.json");
const layers = read("layering.json");
const offset = Object.fromEntries(changed.map(name => [name, read(`female-${name}-v2.fit.json`)]));
const report = Object.fromEntries(names.map(name => [name, read(`checks/${name}/gate.json`)]));
const clips = ["rest", "walk", "run", "wave", "jump", "idle", "nod", "dance", "sit_down",
  "sit_idle", "stand_up", "hold_item", "hold_box", "hold_bag", "take_item"];
const motion = sha("../motion_female.glb");
const master = sha("../master_female.blend");
const mm = value => (1000 * value).toFixed(3);
const byModule = {};
const exceptions = [];

for (const name of names) {
  const garment = changed.includes(name);
  const file = garment ? `female-${name}-v2.glb` : `../female-${name}.glb`;
  const validator = read(file.replace(".glb", ".validator.json"));
  const gate = report[name];
  assert.equal(sha(file), gate.module_sha256);
  assert.equal(sha(file), validator.sha256);
  assert.equal(motion, gate.motion_sha256);
  assert.equal(master, gate.master_sha256);
  assert.deepEqual(new Set(Object.keys(gate.clips)), new Set(clips));
  assert.equal(gate.interval_frames, .5);
  assert.equal(gate.fps, 30);
  const rows = clips.map(clip => gate.clips[clip]);
  const failure = rows.some(row => row.max_vertices_inside || row.max_triangle_pairs || (garment && row.min_signed_m < .0005));
  const { numErrors, numWarnings } = validator.issues;
  const maxTexture = Math.max(0, ...validator.info.resources.flatMap(row => row.image ? [row.image.width, row.image.height] : []));
  const bytes = fs.statSync(path.join(root, file)).size;
  const triangleCount = validator.info.totalTriangleCount;
  const minimumClip = clips.reduce((best, clip) => gate.clips[best].min_signed_m <= gate.clips[clip].min_signed_m ? best : clip);
  const pass = !failure && !numErrors && !numWarnings && maxTexture <= 1024 && bytes <= 1.5 * 2 ** 20;
  for (const clip of clips) {
    const row = gate.clips[clip];
    if (row.max_vertices_inside || row.max_triangle_pairs || (garment && row.min_signed_m < .0005)) {
      exceptions.push(`| ${name} | ${clip} | ${row.max_vertices_inside} | ${row.max_triangle_pairs} | ${mm(row.min_signed_m)} |`);
    }
  }
  if (garment) {
    assert.equal(assets[name].sha256, gate.module_sha256);
    assert.equal(offset[name].output_sha256, gate.module_sha256);
    assert.equal(layers.asset_sha256[name], gate.module_sha256);
  }
  byModule[name] = { file, pass, min_mm: mm(gate.clips[minimumClip].min_signed_m), minimumClip,
    inside: Math.max(...rows.map(row => row.max_vertices_inside)), pairs: Math.max(...rows.map(row => row.max_triangle_pairs)),
    bytes, triangleCount, maxTexture, numErrors, numWarnings };
}

assert.equal(layers.motion_sha256, motion);
assert.equal(layers.asset_sha256.sneakers, report.sneakers.module_sha256);
const expectedViews = ["front", "front-left", "left", "back", "right", "front-right"];
const outfitViews = ["front", "front-left", "back", "right"];
const setups = {
  tshirt: ["tshirt"], dress: ["dress"], jeans: ["jeans"],
  "bob-casual": ["hair-bob", "tshirt", "jeans", "sneakers"],
  "bob-dress": ["hair-bob", "dress", "sneakers"],
  "spiky-casual": ["hair-spiky", "tshirt", "jeans", "sneakers"],
};
for (const [folder, modules] of Object.entries(setups)) {
  const view = read(`renders/${folder}/views.json`);
  const outfit = modules.length > 1;
  assert.equal(view.renderer, "Cycles CPU");
  assert.equal(view.body_sha256, sha("../body_female.glb"));
  assert.deepEqual(Object.keys(view.images), outfit ? outfitViews : expectedViews);
  assert.deepEqual(Object.keys(view.module_sha256), modules);
  assert.equal(view.pose, outfit ? "idle" : "rest");
  if (outfit) assert.equal(view.motion_sha256, motion);
  for (const name of modules) assert.equal(view.module_sha256[name], report[name].module_sha256);
  for (const image of Object.values(view.images)) assert.equal(sha(image.file), image.sha256);
}
const sheet = fs.readFileSync(path.join(root, "renders/full-outfits.png"));
assert.equal(sheet.readUInt32BE(16), 1660);
assert.equal(sheet.readUInt32BE(20), 1248);
const pairNames = ["tshirt/jeans", "jeans/sneakers", "dress/sneakers"];
const layerPeaks = Object.fromEntries(pairNames.map(pair => [pair, Math.max(...clips.map(clip => layers.clips[clip].pairings[pair].peak_pairs))]));
const gap = Math.min(...clips.flatMap(clip => Object.values(layers.clips[clip].cuff_opening).map(row => row.min_axis_gap_mm)));
const layered = Object.values(layerPeaks).every(count => count === 0);
let layoutNotes = "";
const visualPath = fs.existsSync(path.join(root, "visual_review.md")) ? "visual_review.md" : ".runtime/visual-notes.md";
try { layoutNotes = fs.readFileSync(path.join(root, visualPath), "utf8").trim(); }
catch (error) { if (error.code !== "ENOENT") throw error; }

const inputRecord = fs.existsSync(path.join(root, "checks", "round1-inputs.json")) ? "checks/round1-inputs.json" : ".runtime/round1-inputs.json";
const previous = read(inputRecord);
for (const [relative, entry] of Object.entries(previous)) {
  assert.equal(sha(path.join("..", relative)), entry.sha256, `Round-one input changed: ${relative}`);
}

const bodyTable = names.map(name => {
  const m = byModule[name];
  return `| [${path.basename(m.file)}](${m.file}) · [checks](checks/${name}/gate.json) | ${m.triangleCount.toLocaleString("en-US")} | ${(m.bytes / 2 ** 20).toFixed(3)} | ${m.maxTexture || "—"} | ${m.inside} | ${m.pairs} | ${m.min_mm} (${m.minimumClip}) | ${m.numErrors} / ${m.numWarnings} | ${m.pass ? "PASS" : "OPEN"} |`;
}).join("\n");
const labels = ["T-shirt", "Dress", "Jeans", "Bob", "Spiky", "Sidepart", "Sneakers"];
const minHead = "| Clip | Samples | " + labels.join(" | ") + " |";
const minDivider = "| --- | ---: | " + labels.map(() => "---:").join(" | ") + " |";
const minima = clips.map(clip => `| ${clip} | ${layers.clips[clip].samples} | ${names.map(name => mm(report[name].clips[clip].min_signed_m)).join(" | ")} |`).join("\n");
const layerRows = clips.map(clip => {
  const row = layers.clips[clip];
  return `| ${clip} | ${pairNames.map(pair => row.pairings[pair].peak_pairs).join(" | ")} | ${row.cuff_opening.Left.min_axis_gap_mm.toFixed(3)} | ${row.cuff_opening.Right.min_axis_gap_mm.toFixed(3)} |`;
}).join("\n");
const fitRows = changed.map(name => {
  const row = offset[name];
  return `| ${name} | ${row.split_edges} | ${row.turned_hem_boundary_edges ?? row.turned_cuff_boundary_edges ?? 0} | ${row.hem_cut_height_m ? mm(row.hem_cut_height_m) : "—"} | ${mm(row.max_baked_clearance_offset_m)} | ${mm(row.max_reimport_adjustment_m ?? 0)} | [trace](female-${name}-v2.fit.json) |`;
}).join("\n");
const cuffDescription = offset.jeans.opposite_sneaker_taper ?
  "The jeans retain the lower cut. A localized taper gives the opposite female sneaker room when the feet cross in the running clip." :
  "The jeans use a cropped cuff to give the opposite female sneaker room when the feet cross in the running clip.";

const notes = `# Female modular garments · round 2

This round uses the first-round [female body](../body_female.glb), [female motion bank](../motion_female.glb), [female master](../master_female.blend) and the round-one local checkers. The motion bank SHA-256 is \`${motion}\`. All ${Object.keys(previous).length} first-round files matched their [pre-fit hashes](${inputRecord}).

## Body and asset checks

The vertex and triangle tests ran on each imported GLB at 30 fps, at integer and half frames and the authored endpoints. The checkers' combined output includes rest and the fourteen named clips. The 0.500 mm minimum applies to the three v2 garments.

| Module and proof | Triangles | MiB | Max texture px | Peak inside vertices | Peak overlap pairs | Min signed mm | Khronos errors / warnings | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
${bodyTable}

[GLB format, texture and bind evidence](assets.json). The garment texture payloads are byte-identical to round one.

### Signed distance by clip, mm

${minHead}
${minDivider}
${minima}

${exceptions.length ? `### Open readings

| Module | Clip | Peak inside vertices | Peak overlap pairs | Min signed mm |
| --- | --- | ---: | ---: | ---: |
${exceptions.join("\n")}
` : "Both collision counts are zero for every listed module and clip. All three v2 garments meet the signed-distance requirement.\n"}
## Finish and layering

The offset bake used nearest-body directions from signed vertex distances and triangle witnesses across the full pose bank. It projected the penetration plus 1.5 mm target into bind space, clamped the offset to 30 mm and restored constrained components after smoothing. After a crossed edge was subdivided, its material coordinates, tangents and joint influences were interpolated. Weight and fit trials were evaluated against the motion bank. The hem edges were cut in the already-rigged panels and folded inward. The T-shirt cut leaves the waistband in its original position. ${cuffDescription}

| Garment | Crossed edges split | Turned hem segments | Bind hem height mm | Peak bake offset mm | Peak reimport adjustment mm | Evidence |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
${fitRows}

[Full layering measurements](layering.json). ${layered ? "Every sampled pair count is zero." : "Some outfit pairs still intersect."} The smallest cuff-to-collar gap along the posed shin axis was ${gap.toFixed(3)} mm. Positive values put the cuff above the collar in that projection.

| Clip | T-shirt / jeans pairs | Jeans / sneakers pairs | Dress / sneakers pairs | Left cuff gap mm | Right cuff gap mm |
| --- | ---: | ---: | ---: | ---: | ---: |
${layerRows}

## Renders

- Six reimported Cycles CPU views per garment. [T-shirt](renders/tshirt/views.json) · [Dress](renders/dress/views.json) · [Jeans](renders/jeans/views.json)
- [Full outfits sheet](renders/full-outfits.png). Rows show bob with T-shirt and jeans, bob with dress, and spiky with T-shirt and jeans. All wear the female sneakers. The outfit captures use idle frame 18.

${layoutNotes ? layoutNotes + "\n" : ""}
## Recheck

Run from this directory. The Blender wrapper sets two threads and uses the provided local Blender executable.

\`\`\`sh
./run_blender.sh verify.py
./run_blender.sh verify.py -- --layers
node validate_assets.cjs
./run_blender.sh render_final.py -- tshirt dress jeans outfits
\`\`\`
`;

fs.writeFileSync(path.join(root, "NOTES.md"), notes);
fs.writeFileSync(path.join(root, "summary.json"), JSON.stringify({motion, master, byModule, layerPeaks, cuffMinGapMm: gap}, null, 2) + "\n");
console.log(JSON.stringify({byModule, layerPeaks, cuffMinGapMm: gap}, null, 2));
