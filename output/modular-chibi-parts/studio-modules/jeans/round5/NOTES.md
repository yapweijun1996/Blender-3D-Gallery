# Studio jeans round 5

**Pass.** The delivered GLB has zero inside vertices and zero jeans–body triangle pairs at all **1,260** samples. This covers rest and all integer frames, half frames, and endpoints of the eleven clips. The smallest signed clearance is **1.034275 mm** at `sit_idle` frame 22. Rest clearance spans **1.591405–29.879944 mm**.

## Deliverables

- [jeans_v5.glb](jeans_v5.glb) is **3,346,588 bytes** with **4,704 triangles**, 4,170 exported vertices, one skinned jeans mesh, 65 joints, up to four normalized influences, and zero animations.
- [jeans_v5.blend](jeans_v5.blend) is **4,284,384 bytes**. It reopens with the packed Tripo textures, master armature binding, and hidden body reference.
- The round-3 Tripo material, samplers, and three 1024 × 1024 texture payloads match the source. All 4,131 distinct round-3 UVs were retained at 0.000001 UV precision. [Export verification](export_check.json)
- Khronos glTF Validator 2.0.0-dev.3.10 reports **0 errors, 0 warnings**. [Validator report](gltf_validator.json)
- The Cycles CPU captures show the exact GLB on the master. [Six views](six_view.png) · [Sit idle frame 22](sit_idle.png) · [Hold item frame 15](hold_item.png) · [Render manifest](render_manifest.json)
- [Half-frame fitter](fit_jeans_r5.py) · [Waistband restoration](waist_jeans_r5.py) · [Exported-seam refinement](refine_jeans_r5.py) · [Fit history](fit_history.json)

GLB SHA-256 `ed1095fba852e25cc785ce51999f1a866810e27d3101f65d7a20886c9cbb1f61`.

## Vertex checker

| Clip | Samples | Peak inside vertices | Minimum signed distance (mm) | Minimum frame |
| --- | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | 1.591405 | 1 |
| walk | 113 | 0 | 1.142193 | 12 |
| run | 61 | 0 | 1.044837 | 3 |
| wave | 129 | 0 | 1.307878 | 34 |
| jump | 101 | 0 | 1.100305 | 8.5 |
| idle | 177 | 0 | 1.311868 | 23 |
| nod | 113 | 0 | 1.326967 | 0 |
| dance | 129 | 0 | 1.177616 | 35 |
| sit_down | 73 | 0 | 1.048852 | 36 |
| sit_idle | 181 | 0 | 1.034275 | 22 |
| stand_up | 61 | 0 | 1.034501 | 5.5 |
| hold_item | 121 | 0 | 1.323878 | 15 |

[Result text](motion_check.txt) · [Detailed sweep and rest measurements](motion_check.json) · [Supplied shared clip checker](motion_check_legacy_supplied.json) · [Supplied corrected action checker](motion_check_added_supplied.json)

## Triangle-overlap checker

The pair count covers all overlaps between a denim triangle and a master-body triangle. The distance column records the same signed vertex metric as the vertex checker.

| Clip | Samples | Peak jeans–body pairs | Minimum signed distance (mm) | Minimum frame |
| --- | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | 1.591405 | 1 |
| walk | 113 | 0 | 1.142193 | 12 |
| run | 61 | 0 | 1.044837 | 3 |
| wave | 129 | 0 | 1.307878 | 34 |
| jump | 101 | 0 | 1.100305 | 8.5 |
| idle | 177 | 0 | 1.311868 | 23 |
| nod | 113 | 0 | 1.326967 | 0 |
| dance | 129 | 0 | 1.177616 | 35 |
| sit_down | 73 | 0 | 1.048852 | 36 |
| sit_idle | 181 | 0 | 1.034275 | 22 |
| stand_up | 61 | 0 | 1.034501 | 5.5 |
| hold_item | 121 | 0 | 1.323878 | 15 |

[Result text](motion_check_tri.txt) · [Detailed sweep](motion_check_tri.json) · [Supplied shared clip checker](motion_check_tri_legacy_supplied.json) · [Supplied corrected action checker](motion_check_tri_added_supplied.json)

## Body-only residuals

The published body-only checks match the master and corrected clip-bank hashes used here. The seated knee contacts are same-side thigh–shin overlaps. Peak counts include both knees, and the deepest pair in each seated clip lies at the left rear knee. The whole-body column also includes pre-existing contacts in other regions.

| Clip | Peak whole-body pairs | Peak knee pairs | Deepest knee pair (mm) | Frame |
| --- | ---: | ---: | ---: | ---: |
| sit_down | 396 | 15 | 4.141088 | 35.5 |
| sit_idle | 401 | 15 | 4.100275 | 0 |
| stand_up | 396 | 15 | 4.133855 | 0.5 |
| hold_item | 460 | 0 | 0 | — |

Garment residuals are zero in every clip. [Body-only baseline with input hashes and all clip totals](body_only_baseline.json)

## Fit and visual review

The fitter starts from `../round3/jeans_v3.glb`. It maps the worst half-frame vertex and intersection-witness deficits back through the blended skin, targets 2 mm of clearance, and smooths the local corrections with a Laplacian pass. Rest-space guards limit the displacement, signed clearance, and triangle deformation. A trial subdivision of eight edges scored worse, so the selected geometry uses the original triangle count.

The initial bake cleared the new action bank. The rear waistband then recovered a local blend of the shipped round-3 skin weights with a 1 mm inward rest-space offset at the center of the patch. The last refinement changed two small waistband seam groups and one right-knee vertex group. Every accepted residual adjustment was measured against all sampled poses. The final checkers reimported the resulting GLB. The adapter extends the supplied checkers to half frames, retains distance precision, and skips Workbench previews. The separate detailed sweep corroborated the supplied counts and clearance gate on the same final bytes. [Checker adapter](check_jeans_r5.py)

Independent visual review passed. The six views preserve the straight loose legs, waistband height, stitched ankle cuffs, blue denim, front pockets, belt loops, button and zipper. The original light waviness at the back waist and knee folds remain. At `sit_idle` frame 22, the near seat has a small angular fold and the inner crotch has a pointed cloth fold. The jeans follow the bent knees and stay legible. In `hold_item` frame 15, the waist and cuffs retain the standing silhouette. Both views were clear of visible body poke-through. [Six views](six_view.png) · [Sit idle](sit_idle.png) · [Hold item](hold_item.png)

## Reproduction

Run from the round-5 directory. The supplied Blender 5.1.2 bundle and guard paths are in `run_blender.sh`. The geometry, poses, checks, and renders run in Blender Python. The offline Khronos check uses the repository's installed validator.

```sh
sh run_blender.sh fit_jeans_r5.py
sh run_blender.sh waist_jeans_r5.py --
sh run_blender.sh refine_jeans_r5.py
sh run_blender.sh fit_jeans_r5.py -- --verify-export
sh run_blender.sh report_body_baseline.py
for bank in legacy added detail; do
  sh run_blender.sh check_jeans_r5.py -- "$bank"
  sh run_blender.sh check_jeans_r5.py -- "$bank" --triangles
done
sh run_blender.sh render_jeans_r5.py
node - <<'JS'
const fs = require('node:fs');
const crypto = require('node:crypto');
const validator = require('../../../../../node_modules/gltf-validator');
const bytes = fs.readFileSync('jeans_v5.glb');
validator.validateBytes(new Uint8Array(bytes), {
  uri: 'jeans_v5.glb', maxIssues: 0, writeTimestamp: false,
}).then(report => {
  report.glb_sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
  fs.writeFileSync('gltf_validator.json', JSON.stringify(report, null, 2) + '\n');
  if (report.issues.numErrors || report.issues.numWarnings) process.exitCode = 1;
}).catch(error => { console.error(error); process.exitCode = 1; });
JS
```
