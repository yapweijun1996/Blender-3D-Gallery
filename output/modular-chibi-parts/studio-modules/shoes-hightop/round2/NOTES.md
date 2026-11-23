# Purple star high-top shoes v2

[Web GLB](shoes_hightop_v2.glb) · [Editable Blender fitting scene](shoes_hightop_v2.blend) · [Fit script](fit_shoes.py) · [Six-view sheet](fit_views_v2.png) · [Deepest run frame](run_deepest_frame_v2.png)

## Fit

The supplied v1 checker reports recorded a peak of 54 penetrated render vertices and 96 overlapping triangle pairs on the corrected `run` clip. A half-frame reconstruction grouped UV and split-normal copies by position and weight. On that physical-vertex mesh, the same run reached 16 penetrated vertices, 96 triangle pairs, and −1.350 mm signed distance at frame 0.

The fit measures posed nearest-surface directions on the corrected body at integer and half frames. It maps contact depths and the 1.5 mm run margin back through the skin transforms. Barycentric witnesses cover intersecting triangles between vertices. The two Laplacian passes per early iteration are projected back onto the measured clearance constraints, with rest displacement clamped to 20 mm. Local ankle and forefoot weights were relaxed inside the original same-side bone palette. Across 1,669 physical vertices, 96 moved, the maximum rest displacement was 5.895 mm, and 208 formed the weight-smoothing region. A rear-view ray comparison found that the first fit pulled some purple lining in front of the ivory trim. The layer-order pass adjusted nine exterior vertices by up to 2.223 mm. A separate pass used the original base-color UVs to identify the ivory trim. It moved three trim vertices outward by up to 0.783 mm, restoring the ivory band over the purple without changing the material.

The exported triangle indices, UVs, split normals, tangents, material parameters, joint order, and inverse-bind bytes match v1. The GLB embeds the three source maps as quality-93 JPEGs at 1024 × 1024. The edit scene contains the master body, fitted pair, packed shoe textures, and all 14 selectable actions.

## Motion gate

All six supplied checker runs passed. The Blender reimport sweep added 1,829 rest, integer-frame, half-frame, and exact endpoint samples across all 14 clips. The distance column takes the minimum of the full-precision supplied results and the reimport sweep. The reopened Blender scene agreed with the GLB at all 15 closest poses.

| Case | Reimport samples | Max inside vertices | Max overlapping triangle pairs | Min signed distance (mm) |
| --- | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | 0 | 2.415 |
| walk | 142 | 0 | 0 | 1.880 |
| run | 76 | 0 | 0 | 0.608 |
| wave | 161 | 0 | 0 | 2.415 |
| jump | 127 | 0 | 0 | 2.394 |
| idle | 221 | 0 | 0 | 2.415 |
| nod | 141 | 0 | 0 | 2.415 |
| dance | 161 | 0 | 0 | 2.426 |
| sit_down | 73 | 0 | 0 | 2.425 |
| sit_idle | 181 | 0 | 0 | 2.425 |
| stand_up | 61 | 0 | 0 | 2.425 |
| hold_item | 121 | 0 | 0 | 2.415 |
| hold_box | 121 | 0 | 0 | 2.415 |
| hold_bag | 121 | 0 | 0 | 2.415 |
| take_item | 121 | 0 | 0 | 2.415 |

## Export contract

| Property | v1 | v2 |
| --- | ---: | ---: |
| Triangles | 3,383 | 3,383 |
| GLB bytes | 4,602,568 | 1,239,272 |
| Blend bytes | 5,843,781 | 6,688,417 |
| Embedded maps | 3 × 1,024 × 1,024 PNG | 3 × 1,024 × 1,024 JPEG |
| Skinned meshes / joints | 1 / 65 | 1 / 65 |
| Max influences per vertex | 3 | 3 |
| Embedded animations | 0 | 0 |
| Khronos errors / warnings | 0 / 0 | 0 / 0 |

Final GLB SHA-256 is `ba35dcf9fcd12312f140ab12884020a6a71772605274fd7560b5decd00e24437`. The requested offline deliverables and acceptance checks are complete.

## Evidence

- [Fit iterations, source hashes and deepest v1 contact](fit_history.json)
- [Half-frame mesh reimport sweep and per-frame results](motion_half_frames.json)
- [Closest-frame checks on the reopened Blender scene](editable_check.json)
- Shared bank [vertex output](checkers/shared/motion_check_dense.txt) and [triangle output](checkers/shared/motion_check_tri.txt)
- Sit and hold bank [vertex output](checkers/sit_hold/motion_check_dense.txt) and [triangle output](checkers/sit_hold/motion_check_tri.txt)
- Carry bank [vertex output](checkers/carry/motion_check_dense.txt) and [triangle output](checkers/carry/motion_check_tri.txt)
- [Checker source and export hashes](checker_manifest.json) · [Asset contract](asset_contract.json) · [Khronos report](validator.json)
- [Matched v1 views](fit_views_v1_reference.png) · [Matched v2 views](fit_views_v2.png) · [Render manifest](render_manifest.json)

The six views are front, left, back, right, top and bottom, in row order. The deepest-run sheet shows the fitted v2 pair from the front and rear oblique angles at frame 0, the deepest v1 contact. The images render freshly imported GLBs in Cycles CPU. The reference sheets use the same cameras and lighting, with 16 samples per pixel for v1 and 8 for v2.

Independent visual review passed the six matched views and both frame-0 oblique views for the final export. Both ivory rear bands are continuous. The reviewer confirmed the palette, straps, stars, toe and collar silhouette, and tread. The run stills show no visible skin breaking through the collar, upper, or visible sole. The numeric checks cover the obscured geometry.

## Reproduce offline

Run from this directory with Blender 5.1.2 and Node. The bundled launcher points to the Blender binary and guard supplied with the task. Set `HIGHTOP_CHECKER_DIR` if the shared checker scripts move.

```sh
sh run_blender.sh --python fit_shoes.py -- --fit --editable
node validate.cjs
sh run_blender.sh --python fit_shoes.py -- --verify
sh run_blender.sh --python run_checkers.py
sh run_blender.sh --python render_fit.py
```

The vertex and triangle code is taken from the six supplied checker entry points. The runner suppresses the legacy Workbench render calls for headless compatibility, preserving frame selection, pose binding, and collision calculations. The separate Cycles script supplies the visual evidence.
