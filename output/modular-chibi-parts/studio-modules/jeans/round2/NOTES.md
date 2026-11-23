# Studio jeans fitting, round 2

**Motion status: REWORK.** The half-frame gate passed in rest, dance. Remaining clips are walk, run, wave, jump, idle, nod.

## Artifacts

- [Editable Blender file](jeans_v2.blend), 4,228,760 bytes.
- [Skinned GLB](jeans_v2.glb), 3,339,564 bytes, 4,564 triangles, 4,079 exported vertices, one garment mesh, one skin, 65 master joints, at most 4 normalized influences per vertex, and zero animations.
- Khronos glTF Validator 2.0.0-dev.3.10 reported 0 errors and 0 warnings. [Validation report](gltf_validator.json)
- GLB SHA-256 `fc5140275ff60d7d237afb418182542d0901550cf9fd24d1bbf6cb2226b9a913`.
- Blender SHA-256 `396b2e3103095285a0c7cb4ba4c08f0a6a1cecf7e92d9e6a9212366ee657bea9`.
- [Six-view rest sheet](six_view.png) · [Walk](walk.png) · [Run](run.png) · [Wave](wave.png) · [Jump](jump.png). [Render frames and hashes](render_manifest.json)

The Tripo material and inherited UV layout are retained. The embedded base color, roughness/metallic and normal maps are each 1024 × 1024. All three embedded image byte hashes match round 1.

The editable file was reopened and its parent, skin modifier, packed images and normalized weights were verified. The editable positions and skin were reconstructed on the source mesh after Blender protected the appended source path. A re-export matched every triangle corner's positions, UVs and joint indices and the weights matched within 0.000001. The original UV corner coordinates are identical. The largest source-to-output vertex movement was 18.031 mm.

## Supplied checker RESULT tables

The vertex checker samples 12 integer times per clip. The triangle checker samples every third integer frame. Both supplied checkers round clip distances to 0.1 mm. The numeric paths ran on the exported GLB.

### Vertex checker

[RESULT text](motion_check.txt) · [JSON](motion_check.json)

| Clip | Max vertices inside | Min signed vertex distance (mm) |
| --- | ---: | ---: |
| rest | 0 | +1.585 |
| walk | 50 | -6.500 |
| run | 66 | -8.000 |
| wave | 3 | -3.000 |
| jump | 22 | -3.900 |
| idle | 8 | -6.300 |
| nod | 7 | -3.200 |
| dance | 0 | +1.200 |

### Triangle checker

[RESULT text](motion_check_tri.txt) · [JSON](motion_check_tri.json)

| Clip | Max triangle pairs | Min signed vertex distance (mm) |
| --- | ---: | ---: |
| rest | 0 | +1.585 |
| walk | 268 | -6.500 |
| run | 371 | -8.000 |
| wave | 56 | -3.300 |
| jump | 119 | -5.500 |
| idle | 51 | -6.300 |
| nod | 51 | -3.200 |
| dance | 0 | +1.200 |

## Half-frame RESULT

Blender reimported the final GLB, bound it to the master and evaluated 824 poses spanning rest, all half frames and integer frames, both endpoints and each supplied checker sample. Each count is the peak in one pose. Vertex and triangle extrema can occur in different poses.

| Clip | Poses | Max vertices inside | Min vertex (mm) | Frame | Max triangle pairs | Frame | Round 1 peak pairs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | +1.585 | 1 | 0 | 1 | 0 |
| walk | 113 | 55 | -6.557 | 9.5 | 306 | 29 | 298 |
| run | 61 | 107 | -8.005 | 27 | 404 | 29 | 454 |
| wave | 129 | 3 | -3.433 | 50 | 56 | 19 | 60 |
| jump | 101 | 34 | -6.252 | 44.5 | 119 | 9 | 119 |
| idle | 177 | 8 | -6.407 | 55 | 51 | 16.5 | 55 |
| nod | 113 | 8 | -3.210 | 17 | 51 | 15 | 53 |
| dance | 129 | 0 | +1.223 | 48 | 0 | 0 | 0 |

The sum of triangle pair counts across the sweep was 56,635, compared with 62,431 in round 1. These totals count recurring contacts at each sampled pose.

## Residual contacts

The deepest triangle value is an estimate from an eight-division barycentric grid on intersecting triangles. Full per-frame records, garment regions and body-joint categories are in [dense_check.json](dense_check.json).

| Clip | Deepest vertex (mm), frame | Garment / body zone | Deepest triangle sample (mm), frame | Garment / body zone | Overlapping poses |
| --- | ---: | --- | ---: | --- | ---: |
| walk | -6.557 at 9.5 | waistband / Hips | -8.006 at 40 | upper thigh / LeftHandIndex2 | 113 |
| run | -8.005 at 27 | knee / RightUpLeg | -12.584 at 9 | upper thigh / RightLeg | 61 |
| wave | -3.433 at 50 | waistband / LeftForeArm | -5.844 at 50 | waistband / LeftForeArm | 129 |
| jump | -6.252 at 44.5 | waistband / LeftForeArm | -6.252 at 44.5 | waistband / LeftForeArm | 50 |
| idle | -6.407 at 55 | waistband / LeftForeArm | -6.407 at 55 | waistband / LeftForeArm | 177 |
| nod | -3.210 at 17 | waistband / LeftForeArm | -5.408 at 17 | waistband / LeftForeArm | 113 |

The unchanged master also has upper-body versus hip triangle contacts at walk at 9.5 (103 pairs), wave at 50 (34 pairs), jump at 44.5 (32 pairs), idle at 55 (32 pairs), nod at 17 (34 pairs).

## Rest clearance

| Region | Vertices | Min (mm) | P10 | Median | P90 | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 4,079 | 1.585 | 2.998 | 9.283 | 14.575 | 17.093 | 27.030 |
| crotch | 850 | 3.735 | 8.403 | 11.753 | 19.934 | 22.459 | 27.030 |
| cuff | 492 | 5.356 | 7.572 | 10.285 | 12.141 | 12.553 | 14.758 |
| front hips | 444 | 1.585 | 1.600 | 2.423 | 9.269 | 10.758 | 15.397 |
| knee | 428 | 3.761 | 8.792 | 11.934 | 14.260 | 17.281 | 20.624 |
| lower leg | 455 | 4.433 | 5.703 | 8.483 | 10.210 | 10.623 | 11.327 |
| seat | 63 | 1.685 | 2.303 | 4.223 | 13.279 | 13.664 | 15.066 |
| upper thigh | 415 | 1.600 | 3.770 | 8.887 | 14.108 | 17.770 | 25.083 |
| waistband | 932 | 1.600 | 2.843 | 7.256 | 12.823 | 14.700 | 17.628 |

0 exported vertices exceed the 30 mm rest clearance limit.

- Waist opening spans Z 406.4–430.3 mm.
- Right cuff opening spans Z 70.5–79.4 mm.
- Left cuff opening spans Z 70.5–79.9 mm.

The six-view sheet shows shallow folds along the upper thighs and crotch. The cuffs sit near the ankles and the waist follows the hips.


## Method and reproduction

The fitter starts from the editable round 1 mesh and original Tripo material. It contracts the side hips and adds smooth initial allowance around the saddle and knees. The half-frame bake uses the nearest posed body surface directions and triangle intersection witnesses, back-projected through the blended skin matrices with a 2 mm target margin. Laplacian passes retain the projected displacement component before the 30 mm cap and mesh validity constraints. Long contact edges are bisected and recurrent inner-thigh faces receive extra local edges during the search. Hip and knee weight changes are smoothed, limited to four influences and normalized.

The export retained bake iteration 1 and local search iteration 1. The local dance recovery affected 123 editable vertices. The selected export retains the round 1 triangle layout. The subdivided candidates increased the overall collision score or missed the rest clearance floor. The fit history records all candidates and their measured results. [Fit history](fit_history.json)

Run Blender 5.1.2 in background mode with the binary and guard supplied in the assignment. The original rotation modes are preserved and every motion selects its action slot. The wrapper runs the supplied numeric checkers with their original sampling, and renders with Cycles CPU.

```sh
export TMPDIR="$PWD/"
export DYLD_INSERT_LIBRARIES="$GUARD"
"$BLENDER" -b -t 6 -noaudio --python-exit-code 1 --python fit_jeans_r2.py
"$BLENDER" -b -t 6 -noaudio --python-exit-code 1 --python fit_jeans_r2.py -- --polish
"$BLENDER" -b -t 6 -noaudio --python-exit-code 1 --python fit_jeans_r2.py -- --checkers
"$BLENDER" -b -t 6 -noaudio --python-exit-code 1 --python fit_jeans_r2.py -- --verify
"$BLENDER" -b -t 6 -noaudio --python-exit-code 1 --python fit_jeans_r2.py -- --renders
```

Geometry, skinning, collision measurements, and PNGs were produced locally in Blender. The Khronos validator used the repository's installed offline package. No external service or Git operation was used.
