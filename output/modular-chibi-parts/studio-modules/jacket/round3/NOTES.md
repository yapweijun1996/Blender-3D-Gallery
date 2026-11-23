# Studio bomber round 3

The best round-3 export still misses the motion gate in walk and run.
The two Blender checkers independently reimported the delivered GLB on the supplied master and sampled rest plus 415 integer and 408 half frames of the corrected clips. Garment-to-body triangle-pair occurrences fell from 44,823 in round 2 on the corrected clips to 178.

## Deliverables

- [Editable Blender file](jacket_v3.blend), [skinned GLB](jacket_v3.glb) and [fit script](fit_jacket_r3.py).
- [Vertex RESULT](motion_check.txt), [per-pose vertex data](motion_check.json), [triangle RESULT](motion_check_tri.txt) and [per-pose triangle data](motion_check_tri.json).
- [Six-view render](six_view.png), [walk](walk.png), [run](run.png), [wave](wave.png), [jump](jump.png).

## Vertex RESULT

Counts are maxima within one sample. Distance is the minimum signed nearest-surface distance across the clip in millimetres. The gate is at least +0.500 mm.

| Clip | Poses | Max inside vertices | Min signed mm | Frame |
| --- | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | +1.414 | 1 |
| walk | 113 | 7 | -12.710 | 9 |
| run | 61 | 2 | -4.005 | 3.5 |
| wave | 129 | 0 | +1.349 | 19 |
| jump | 101 | 0 | +1.131 | 9 |
| idle | 177 | 0 | +1.362 | 66 |
| nod | 113 | 0 | +1.392 | 34.5 |
| dance | 129 | 0 | +0.672 | 49 |

## Triangle RESULT

Counts are epsilon-zero BVH intersections between one posed master-body triangle and one posed jacket triangle. The minimum column measures vertex clearance during the same independent sweep.

| Clip | Poses | Max pairs | Peak frame | Pair occurrences | Min signed mm |
| --- | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | — | 0 | +1.414 |
| walk | 113 | 7 | 16 | 66 | -12.710 |
| run | 61 | 17 | 12.5 | 112 | -4.005 |
| wave | 129 | 0 | — | 0 | +1.349 |
| jump | 101 | 0 | — | 0 | +1.131 |
| idle | 177 | 0 | — | 0 | +1.362 |
| nod | 113 | 0 | — | 0 | +1.392 |
| dance | 129 | 0 | — | 0 | +0.672 |

The hash-matched [body-only baseline](../../../body-fix/NOTES.md) reports 318 neutral self-pairs (163 eye insert/head, 60 shorts/legs and 95 foot/toe). Its corrected-clip total is 148,758 body-only occurrences at integer frames. The garment check compares two distinct meshes. The two sets of counts are recorded in the triangle JSON.

## Remaining motion findings

Negative grid depth is the smallest signed distance over a ten-division barycentric grid on intersecting jacket faces. Face and vertex minima may occur at different frames.

| Clip | Rest zone | Max inside vertices | Min vertex mm (frame) | Max pairs | Min intersecting-face sample mm (frame) |
| --- | --- | ---: | --- | ---: | --- |
| walk | center torso panels | 5 | -12.710 (9) | 0 | — |
| walk | left shoulder/armpit | 2 | -0.829 (16) | 7 | -0.829 (16) |
| run | center torso panels | 1 | -4.005 (3.5) | 0 | — |
| run | left shoulder/armpit | 2 | -0.470 (13) | 17 | -0.968 (9) |
| run | left torso panels | 0 | +0.181 (13.5) | 4 | -0.160 (14) |

21 distinct garment faces intersected. 13 have a rest edge longer than 12 mm.

## Rest clearance

The 341,682-point rest surface grid measured a minimum signed clearance of +0.753 mm and a maximum Euclidean clearance of 29.969 mm. 0 samples fell below 0.500 mm. 0 exceeded 30 mm.

| Region | GLB vertices | Min signed | P10 | Median | P90 | P95 | Max Euclidean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 5,432 | 1.414 | 6.313 | 11.342 | 20.582 | 24.996 | 29.840 |
| ribbed cuffs | 577 | 1.414 | 3.762 | 9.468 | 12.537 | 13.949 | 23.734 |
| ribbed hem | 590 | 2.015 | 4.198 | 9.596 | 12.080 | 12.909 | 20.474 |
| shoulder/armpit | 499 | 4.242 | 8.398 | 12.280 | 21.354 | 25.490 | 29.769 |
| sleeves | 655 | 2.671 | 4.127 | 9.955 | 16.095 | 17.475 | 23.755 |
| stand collar | 612 | 8.492 | 9.401 | 11.117 | 15.690 | 16.370 | 18.246 |
| torso panels | 2,499 | 3.342 | 9.400 | 13.460 | 24.776 | 27.903 | 29.840 |

## Fit and export

The run started with the round-2 Blender garment and reused its fitting and GLB export code. The round-2 GLB was independently reimported for the motion baseline. The fitting path used worst-pose nearest-surface directions transformed into rest space, a 2 mm working target, Laplacian smoothing with an offset floor, and contact-driven bmesh subdivision and local four-influence skinning.
The selected candidate came from the six-pass initial correction and the final coupled contact solve at iteration 16. A separate rest-face pass projected over-cap samples toward the body and the two deliverable checkers re-ran on the exported bytes.
Two contact-driven subdivision passes added 295 triangles. An additional local split trial increased the swept collision score. The final candidate retained the earlier subdivisions.

- 5,177 triangles, 5,432 GLB vertices, 3,766,120 GLB bytes and 4,621,767 Blender bytes.
- 1 mesh, 65 joints, 0 embedded animations, maximum 4 skin influences.
- 3 embedded 1024 × 1024 textures. Round-2 embedded image byte equality verified. Round-2 GLB material-definition equality verified.
- The editable UV layer retained all 5,200 distinct round-2 coordinates out of 5,200. Subdivision added UV loops from 14,646 to 15,531.
- Khronos glTF Validator 2.0.0-dev.3.10 reported 0 errors and 0 warnings.

An independent visual reviewer compared the final images to the round-2 six-view sheet. The loose silhouette, stand collar, wrist cuffs, ribbed hip hem, olive finish and zipper read consistently. The reviewer observed uneven pocket edges, small pointed folds below the sleeves and along the hem, and dark folds around the armpit or cuff in some action frames. The renders show single views at selected poses.

The six-view sheet shows front, back and left profile on the first row, then right profile, three-quarter and jacket-only. The detail images use Cycles CPU and follow the frame with the highest overlap count where available or the minimum vertex clearance frame.

| Render | Frame | SHA-256 |
| --- | ---: | --- |
| [six_view.png](six_view.png) | 1 | `92644cef2b3ed24fa70a6a4cd19d156c6be9815b1c8700ae08d06be2d36cfb59` |
| [walk.png](walk.png) | 16 | `7a271135666ca9b6adb6b557a26ca9af953b72d95c776e303ffe26ffb75dde14` |
| [run.png](run.png) | 12.5 | `965ae6a32f7f0ffdc3aea8f4f95851fb95ab9b4033f952daadaa2709ba6ee7b4` |
| [wave.png](wave.png) | 19 | `00458b89c8da7f69ab76b11b74a81952c0b22d37cb1fc7051bccb4810e6c747e` |
| [jump.png](jump.png) | 9 | `88449146bcf3973285f1d3c2180a8f7579dfc03117800a350f96cec671cd3636` |

## Reproduce locally

Set `BLENDER` and `DYLD_INSERT_LIBRARIES` to the supplied executable and guard. Run from this folder.

```sh
parts=$(cd ../../.. && pwd)
mkdir -p .runtime
export TMPDIR="$PWD/.runtime/"
export PYTHONDONTWRITEBYTECODE=1
master=$parts/master/GJH_Chibi_Master_rigged.blend
motion=$parts/body-fix/motion_fixed.glb
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_jacket_r3.py
"$BLENDER" -b -noaudio --python-exit-code 1 --python motion_check.py -- "$master" "$motion" "$PWD/jacket_v3.glb" "$PWD"
"$BLENDER" -b -noaudio --python-exit-code 1 --python motion_check_tri.py -- "$master" "$motion" "$PWD/jacket_v3.glb" "$PWD"
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_jacket_r3.py -- --inspect
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_jacket_r3.py -- --renders
```

| Input or output | SHA-256 |
| --- | --- |
| Round-2 GLB | `5b47594d616e9b8558b0c0772c0c04717fc3fedc8871527d63dd8daab5e77dca` |
| Round-2 Blender source | `a702b42813ae87ca0b80c2a44eb9fe0420c2261fa3bd6084a97cc683ba0dca70` |
| Master | `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f` |
| Corrected motion | `3484f5978e94f3e714b320357397d107dd490d56f2eeb64770be292322f9aa2c` |
| Round-3 GLB | `e8cc6c6a5fe6639400cbc2a239f6668bcd9f858220636446252dc9da24b0a2b0` |
| Round-3 Blender source | `45d14d6242f2571b8ef07d3f94d0ac1fb124f105cc4799d26c032621247791e8` |
