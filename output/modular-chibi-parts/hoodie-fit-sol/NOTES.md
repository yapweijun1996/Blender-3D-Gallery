# Tripo hoodie fitting and motion QA

The module passes the T-pose check and the hood clears the head during nod. The seven motion clips still fall short of the full-garment clearance target.

## Deliverables

| File | Contents |
| --- | --- |
| `fit_hoodie.py` | Blender 5.1 build and checker runner |
| `top_hoodie_v1.blend` | Editable skinned hoodie with the master body hidden as a fitting reference |
| `top_hoodie_v1.glb` | One mesh, one skin, 65 matching `mixamorig:*` joints, zero animations |
| `motion_check.json` | Measurements from the supplied checker |
| `walk.png`, `run.png`, `wave.png`, `jump.png` | The checker’s four posed frames |

The GLB contains 5,022 triangles and 3,279 exported vertices, including UV and normal splits. Its size is 1,236,560 bytes. The editable Blender file is 2,193,685 bytes. A clean repeat build produced a byte-identical GLB. All exported vertices carry at most four positive weights, with maximum normalization error below 0.000001. The Tripo material and UVs carry one embedded 1024 × 1024 PNG downsampled from 2048 × 2048. The module is in the master's bind coordinates with +Y up and +Z forward in glTF. The Khronos validator 2.0.0-dev.3.10 reported **0 errors and 0 warnings**.

## RESULT

The checker measures a signed nearest-body distance. It evaluates 12 sampled frames per clip. The target is zero inside vertices and at least +0.0005 m for every row.

| Clip | Initial max inside | Final max inside | Final minimum signed distance (m) |
| --- | ---: | ---: | ---: |
| rest | 0 | 0 | +0.004396 |
| walk | 200 | 100 | −0.0124 |
| run | 281 | 54 | −0.0088 |
| wave | 101 | 18 | −0.0043 |
| jump | 112 | 35 | −0.0091 |
| idle | 107 | 3 | −0.0049 |
| nod | 96 | 3 | −0.0045 |
| dance | 54 | 21 | −0.0027 |

The initial result is from the first fitted and skinned export, before the motion corrections. A supplemental BVH test on the final reimport found **zero garment/body triangle intersections at rest**. T-pose clearance medians were 0.0083 m at the torso, 0.0124 m at the sleeves, and 0.0105 m at the cuffs. The sleeve 90th percentile was 0.0249 m and the maximum was 0.0341 m at the puff. The fitted sleeves span x = −0.2630 to +0.2652 m, and the hem reaches z = 0.3818 m in Blender.

The supplemental test evaluated every integer frame through the clip endpoints, plus half frames for nod. Its worst run frame had 141 inside vertices, and its smallest run distance was −0.0171 m at frame 23. The 113 nod evaluations found zero triangle intersections against the head surface. The rear hood vertices in that check stayed at least 0.0094 m from the full body.

## Fit changes and remaining contacts

- **Rest.** Rotated the original mesh, shaped the torso in horizontal sections, and fitted the sleeves around the master arm axes. Removed the recessed plugs from both cuffs and kept the turned lips. Lifted the shoulder and cuff patches using both point clearance and intersecting faces.
- **Walk and run.** Reduced the bulk on the inner sleeves, adjusted hem and elbow room, and baked bounded motion offsets. There is still contact near the forearms, trunk and hips during close arm swings.
- **Wave and jump.** Smoothed the transferred shoulder and elbow weights and adjusted contact patches on the sleeves and torso. Lowered or inward-moving arms still intersect the garment in some poses.
- **Idle and nod.** Refined sleeve and side contacts in the arm-down posture. Rolled the hood behind the neck and added a Neck/Head falloff so it follows the head in nod. Residual nod contacts are below the head.
- **Dance.** Reduced contacts at the upper-arm and torso transition with the same bounded offsets. The armpit and side still show residual contact.

In a body-only test, forearm or distal upper-arm triangles crossed the trunk in walk, run, wave, jump, idle and nod. That source geometry limits the clearance available to a fitted garment in those poses. An unconstrained per-vertex search nearly cleared the checker but produced folded and crossed garment triangles. A later hem smoothing trial reduced the visible fold and increased motion penetration, particularly in idle and nod. The delivered version keeps the lower measured motion penetration.

Independent visual review confirmed the rear hood, wrist cuffs, two sleeve stripes, both drawstrings, pocket trims and purple hem. The sleeves are flatter and more faceted than the reference, the pocket trims are angular, and the hem flares with a small dark fold on the wearer's left. The selected run frame shows the most shoulder and hem compression. The four front PNGs cover one frame each.

## Rebuild

Run from this directory with the guarded Blender executable supplied with the inputs and its `DYLD_INSERT_LIBRARIES` setting.

```sh
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_hoodie.py
```

Add `-- --build-only` to rebuild just the two model files. The default run executes the supplied `motion_check.py` with a render-only substitution for Cycles CPU because Workbench aborted in the headless macOS environment. The checker file, pose sampling, distance calculation, framing and output names are preserved.

Validated GLB SHA-256 `f82e5ce96c6e23743aad79a10b1673b3cf9dc8a745b60d98864b059e501931a4`
