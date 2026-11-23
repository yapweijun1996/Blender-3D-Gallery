# Blue Studio slip-ons v2

[Web-demo GLB](shoes_slipons_v2.glb) · [Editable Blender scene](shoes_slipons_v2.blend) · [Fitter](fit_shoes.py) · [Six-view render](fit_views_v2.png) · [Deepest run comparison](run_deepest_frame_v2.png)

## Motion gate

The candidate was reimported against the rigged master and the three corrected clip banks. All six supplied checker runs passed, including their repeated rest and shared-clip measurements. The independent sweep covered 1,683 poses including rest, sampled every half frame and every quarter frame for run. The signed distances in the table are garment-vertex distances to the body in millimetres. Triangle pairs are measured separately with BVH overlap.

| Clip | Supplied vertices inside | Supplied triangle pairs | Supplied vertex min (mm) | Supplied triangle min (mm) | Dense min (mm) | Dense samples |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `rest` | 0 | 0 | 2.374 | 2.374 | 2.341 | 1 |
| `walk` | 0 | 0 | 2.300 | 2.300 | 2.283 | 113 |
| `run` | 0 | 0 | 1.000 | 1.000 | 0.961 | 121 |
| `wave` | 0 | 0 | 2.300 | 2.300 | 2.335 | 129 |
| `jump` | 0 | 0 | 2.300 | 2.300 | 2.305 | 101 |
| `idle` | 0 | 0 | 2.300 | 2.300 | 2.335 | 177 |
| `nod` | 0 | 0 | 2.300 | 2.300 | 2.341 | 113 |
| `dance` | 0 | 0 | 2.300 | 2.300 | 2.334 | 129 |
| `sit_down` | 0 | 0 | 2.337 | 2.337 | 2.337 | 73 |
| `sit_idle` | 0 | 0 | 2.337 | 2.337 | 2.337 | 181 |
| `stand_up` | 0 | 0 | 2.337 | 2.337 | 2.337 | 61 |
| `hold_item` | 0 | 0 | 2.335 | 2.335 | 2.335 | 121 |
| `hold_box` | 0 | 0 | 2.335 | 2.335 | 2.335 | 121 |
| `hold_bag` | 0 | 0 | 2.335 | 2.335 | 2.335 | 121 |
| `take_item` | 0 | 0 | 2.335 | 2.335 | 2.335 | 121 |

| Run comparison | Frame | Vertices inside | Triangle pairs | Min signed clearance (mm) |
| --- | ---: | ---: | ---: | ---: |
| v1 deepest contact | 0 | 6 | 37 | -0.325 |
| v2 at the same pose | 0 | 0 | 0 | 1.124 |
| v2 minimum through run | 3 | 0 | 0 | 0.961 |

[Combined results](qa/motion_summary.json) · [Dense results by frame](qa/motion_gate.json) · [Shared vertex](qa/checkers/shared/vertex/RESULT.txt) · [Shared triangle](qa/checkers/shared/triangle/RESULT.txt) · [Sit/hold vertex](qa/checkers/sit-hold/vertex/RESULT.txt) · [Sit/hold triangle](qa/checkers/sit-hold/triangle/RESULT.txt) · [Carry vertex](qa/checkers/carry/vertex/RESULT.txt) · [Carry triangle](qa/checkers/carry/triangle/RESULT.txt)

The checkers retain their original measurement code, sampling, and output formats. Their preview blocks use Cycles CPU because Workbench crashes in the supplied Blender environment. The shared vertex, shared triangle, and sit/hold vertex passes produced identical pixel data for each of the four legacy preview poses. The sit/hold triangle and carry folders reuse those renders for the matching frames and camera on the same GLB. Each check directory contains its own result log and original measurement JSON, plus per-frame JSON where the checker supplies it.

## Fit

The fitter starts from the v1 GLB. It evaluates the corrected run at all 61 integer and half-frame poses. For collisions it uses the nearest body-surface direction and witnesses along intersecting triangle segments. The required displacement is the measured depth plus a 1.5 mm margin, clamped to 0–20 mm. It projects corrections into bind space using the posed skin matrices and reapplies the contact constraints after each of three Laplacian passes. The final maximum projection residual is 0.19 µm. Blender 5 action slots are assigned directly and pose-bone rotation modes are preserved.

The correction moves 23 welded positions around the right collar and upper, corresponding to 42 exported vertices at UV and material seams. Largest displacement is 2.426 mm and the mean over moved positions is 1.035 mm. The same patch receives two local weight-smoothing passes across the ankle and nearest Foot/ToeBase blend. The original topology, UVs, material factors, joint order, and inverse binds are preserved. [Fit statistics and run samples](fit_report.json)

## Asset contract

| Property | v2 | Limit |
| --- | ---: | ---: |
| Triangles | 3,474 | 3,500 |
| GLB bytes | 1,227,248 (1.170 MiB) | 1,258,291 (1.2 MiB) |
| Blender bytes | 1,195,502 | — |
| Meshes / skins / animation clips | 1 / 1 / 0 | 1 / 1 / 0 |
| Joints | 65 | 65 |
| Active influences per vertex | 3 | 4 |
| Embedded texture dimensions | 3 × 1024 × 1024 | 1024 px per axis |
| Khronos errors / warnings | 0 / 0 | 0 / 0 |

The GLB is 67.4% smaller than v1's 3,765,036 bytes. The three textures use embedded JPEG at 1024 × 1024. Quality values are 96 for base color and 95 for both the normal and packed roughness/metallic maps. The editable scene was reopened and verified to contain all three packed images, the 65-joint rig, and 3,474 triangles. [GLB contract](qa/asset_contract.json) · [Khronos validator](qa/validator.json)

## Appearance

The six-view sheet shows front, left and back on the first row, then right, top and bottom. The run sheet compares v1 on the left against v2 on the right at matched poses. Its upper row shows the deepest v1 contact at frame 0, and its lower row shows the lowest v2 clearance at frame 3. Both sheets use Blender Cycles CPU and matched orthographic cameras. [v1 six-view reference](qa/fit_views_v1.png) · [Matched three-quarter views](qa/angled_comparison.png) · [Render manifest](qa/render_manifest.json)

Independent visual review passed for the rounded toe and heel silhouette, open ankle and padded collar, blue gradients and cream bands, stitching, and continuous welt and outsole. The close-ups at frames 0 and 3 showed the same toe bend and sole tilt as v1, with no visible new openings, spikes or skin breakthrough in those cameras. In the matched rest images, the overlap of the v1/v2 silhouette masks is at least 99.81%, and the largest mean absolute colour difference across the views is 1.03 out of 255 per RGB channel. The review applies to the recorded renders of the exact candidate hash below.

## Rebuild and verification

Run from this directory with the supplied Blender 5.1.2 installation and the repository's existing Node validator. The launcher accepts `SLIPONS_BLENDER_ROOT` to locate the guarded installation and the two shared checker scripts.

```sh
./blender --python fit_shoes.py
node validate_glb.cjs
./blender --python run_checkers.py -- shared sit-hold:vertex
./blender --python run_checkers.py -- --reuse-shared-previews sit-hold:triangle carry
./blender --python qa_motion.py
./blender --python render_fit.py
node summarize_motion.cjs
```

| Asset | SHA-256 |
| --- | --- |
| v2 GLB | `dddfd60bc6d95bea1887ffeccd1503782a31836eb678f17a8ca35dd9c3b166c2` |
| v2 Blender scene | `6ea85418158ef438933e2fd31b7cc0476c339f3ccef5e0ea3abddb4bd164ec01` |
| v1 GLB | `b9e96178dcf918e6dd89bfce3f933a6b8605773d9bab3e257599b8319f35bd6d` |

**Remaining.** All requested motion and asset gates pass. Verification is local to Blender and Node. Browser playback of the web demo remains unverified under the offline scope.
