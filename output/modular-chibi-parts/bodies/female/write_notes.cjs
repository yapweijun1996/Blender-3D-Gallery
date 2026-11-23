const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const root = __dirname;
const modules = ["hair-bob", "hair-spiky", "hair-sidepart", "tshirt", "dress", "jeans", "sneakers"];

const read = name => {
  const file = path.join(root, name);
  return fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, "utf8")) : null;
};
const hash = name => crypto.createHash("sha256").update(fs.readFileSync(path.join(root, name))).digest("hex");
const mib = bytes => (bytes / 2 ** 20).toFixed(3);
const mm = distance => (distance * 1000).toFixed(3);
const bodily = read("body_assets.json");
const bodyAudit = read("body_selfcheck.json");
const auditCurrent = bodyAudit && bodyAudit.motion_sha256 === hash("motion_female.glb");
const bodyValidator = read("body_female.validator.json");
const lib = read("hand_gestures_female.validator.json");
const motionValidator = read("motion_female.validator.json");
let notes = `# Studio female modular fit

## Stage 1 · Body readiness

| File or gate | Observed result |
| --- | --- |
| [body_female.glb](body_female.glb) | ${bodily.triangles.toLocaleString()} triangles, ${mib(bodily.body_bytes)} MiB, one skinned mesh named \`Base_Body\`, one material, three 1024 px embedded JPEG PBR maps. |
| Rest fit | Studio height ${bodily.female_height_m.toFixed(6)} m versus neutral ${bodily.neutral_height_m.toFixed(6)} m. Retained scale ${bodily.height_scale.toFixed(1)}× because the difference is 2.25%. In glTF, the body faces +Z and minimum Y is ${bodily.floor_y_m.toExponential(3)} m. |
| [Body validator](body_female.validator.json) | ${bodyValidator.issues.numErrors} errors and ${bodyValidator.issues.numWarnings} warnings. |
| [master_female.blend](master_female.blend) | Packed Studio geometry, 65 animated joints with names and parent relationships matching the neutral master, and two objects named \`Armature\` and \`Base_Body\`. Scene FPS 30. |
| [hand_gestures_female.glb](hand_gestures_female.glb) | Byte-identical to the supplied library. All 18 gesture names match. Khronos ${lib.issues.numErrors} errors and ${lib.issues.numWarnings} warnings. |
| Motion library | ${fs.existsSync(path.join(root, "motion_female.glb")) ? `[motion_female.glb](motion_female.glb), 14 animations on the female skeleton. Khronos ${motionValidator.issues.numErrors} errors and ${motionValidator.issues.numWarnings} warnings.` : "Retarget passes in progress."} |

Retargeting transfers the neutral master’s evaluated quaternion deltas through each joint’s two rest bases. The library carries the source hips translation relative to the female bind, including the forward travel in the raw walk source. Pose-local finger relaxation, arm and knee clearance, ankle alignment and sole-height correction are baked where needed. The sole target is zero whenever the neutral reference is at or below 1 mm. At other samples it is the neutral airborne height. Clip timing is preserved in Float32 seconds. The stage uses 30 fps and checks each integer and half frame plus the authored endpoints.

The current dress-up loader discards per-joint translation and scale from its seven shared motions. Integrate this already-retargeted bank as authored playback so the leg and arm clearance tracks survive. For an in-place preview, hold the horizontal hips position at rest and keep the baked vertical bob and other per-joint tracks.
`;
if (auditCurrent) {
  notes += `
The supplied body checker ran on the reimported, combined motion GLB. [Body self-overlap and foot witnesses](body_selfcheck.json) · [Bake diagnostics](motion_fit.json).

| Clip | Samples | End time (s) | Peak self-pairs | Maximum depth (mm) | Worst planted sole error (mm) |
| --- | ---: | ---: | ---: | ---: | ---: |
`;
  for (const [clip, item] of Object.entries(bodyAudit.clips)) {
    const sync = bodyAudit.sync[clip];
    notes += `| ${clip} | ${item.samples} | ${sync.output_duration_s.toFixed(4)}${sync.same_end_time ? "" : " (duration mismatch)"} | ${item.peak_pairs} | ${item.max_depth_mm.toFixed(3)} | ${item.grounded_max_error_mm.toFixed(4)} |\n`;
  }
  const failures = Object.entries(bodyAudit.clips).filter(([, item]) => item.peak_pairs || item.grounded_max_error_mm > 1);
  if (failures.length) {
    notes += `\n### Body gates still open\n\n`;
    for (const [clip, item] of failures) {
      const zones = Object.entries(item.zone_counts).sort((a, b) => b[1].depth_mm - a[1].depth_mm);
      notes += `- **${clip}**. ${zones.map(([k, v]) => `${k} ${v.depth_mm.toFixed(3)} mm at frame ${v.worst_frame}`).join(", ")}${item.grounded_max_error_mm > 1 ? `. Planted sole error ${item.grounded_max_error_mm.toFixed(3)} mm` : ""}.\n`;
    }
  }
}
notes += `
## Stage 2 · Auto-fit tool

| Component | Implementation |
| --- | --- |
| [fit_module.py](fit_module.py) | Head, torso, arms, legs and feet use region-constrained neutral-to-female surface correspondences with skeletal registration, barycentric interpolation and Laplacian smoothing. Welded coincident vertices share a displacement across UV and material seams. |
| Skin and finish | Keeps topology, UVs, material definitions and rigid weights. Blends transferred body weights at blended cloth vertices that move, then limits to four influences. Winding is preserved and normals and tangents follow the displacement. Image recompression fits the file and resolution caps. |
| Motion bake | Uses the deepest signed point and triangle-witness constraints across the 14 clips. Transforms the 1.5 mm margin into bind space, preserves the constrained component during Laplacian smoothing, and caps extra offset at 30 mm. Checks the blended skin at integer and half frames. |
| Static trial | All seven registered inputs produced a geometry seed within their triangle, texture-resolution and file-size budgets. |
| Usage | \`./run.sh fit_module.py -- path/to/source.glb female-example.glb\` or \`./run.sh fit_module.py -- all\`. |

## Stage 3 · Fitted modules

| Module | Triangles | MiB | Max texture (px) | Peak inside vertices | Peak overlap pairs | Min signed (mm) | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
`;
const failures = [];
for (const name of modules) {
  const glb = `female-${name}.glb`;
  const fit = read(`female-${name}.fit.json`);
  if (!fit) {
    notes += `| ${name} | — | — | — | — | — | — | Pending |\n`;
    continue;
  }
  const gate = read(`checks/${name}/gate.json`);
  const checked = gate && gate.module_sha256 === fit.output_sha256 && gate.motion_sha256 === fit.motion_sha256;
  const rows = Object.entries(checked ? gate.clips : fit.results);
  const vertices = Math.max(...rows.map(([, v]) => v.max_vertices_inside ?? v.vertices_inside));
  const triangles = Math.max(...rows.map(([, v]) => v.max_triangle_pairs ?? v.triangle_pairs));
  const min = Math.min(...rows.map(([, v]) => v.min_signed_m ?? v.minimum_signed_m));
  const status = (vertices || triangles || min < .0005) ? "Open" : checked ? "Pass" : "Fit scan only";
  const imageSide = Math.max(0, ...(fit.texture_images ?? []).flatMap(x => x.size));
  notes += `| [${name}](${glb}) | ${fit.triangles.toLocaleString()} | ${mib(fit.bytes)} | ${imageSide || "—"} | ${vertices} | ${triangles} | ${mm(min)} | ${status} |\n`;
  for (const [clip, row] of rows) {
    const inside = row.max_vertices_inside ?? row.vertices_inside;
    const pairs = row.max_triangle_pairs ?? row.triangle_pairs;
    const signed = row.min_signed_m ?? row.minimum_signed_m;
    if (!inside && !pairs && signed >= .0005) continue;
    const source = fit.results[clip];
    const official = read(`checks/${name}/witnesses.json`);
    const witness = official?.module_sha256 === fit.output_sha256 ? official.clips[clip] : null;
    const zones = Object.entries(source.peak_triangle_zones ?? {}).map(([zone, v]) =>
        `${zone} ${v.sat_depth_mm.toFixed(3)} mm`).join(", ");
    failures.push(`| ${name} | ${clip} | ${witness?.frame ?? source.minimum_frame} | ${inside} / ${pairs} | ${witness?.zone ?? source.body_zone} | ${mm(signed)} | ${zones || "—"} |`);
  }
}
if (failures.length) {
  notes += `
### Module gates still open

Signed values below zero are vertex penetration. Signed minima and witness frames come from reimported geometry. Triangle depths use the fitted triangulation and may reflect a different peak frame. A positive signed distance below 0.500 mm is a clearance failure even when both counts are zero. The \`checks\` folders include the supplied checker reports and the exact reimport witnesses.

| Module | Clip | Min frame | Peak inside / pairs | Min signed zone | Min signed (mm) | Triangle zones and depths |
| --- | --- | ---: | ---: | --- | ---: | --- |
${failures.join("\n")}
`;
}
notes += `
**Geometry and format.** [Asset contracts](assets_check.json) records the exact bind matches, UVs, triangle indices, materials and embedded texture sizes.

**Recheck.** \`./run.sh audit_body.py\` applies the supplied body checker. \`./run.sh audit_modules.py\` runs the local copies of the supplied dense and triangle checks. The copies preserve the numerical tests, sample at half frames, and leave preview rendering to Cycles CPU.

**Renders.** \`./run.sh render.py\` writes six views per module and a [full outfit contact sheet](renders/full-outfits.png). Each view directory includes a manifest with hashes, camera settings and pose. [Independent visual findings](visual_review.md).
`;
fs.writeFileSync(path.join(root, "NOTES.md"), notes);
