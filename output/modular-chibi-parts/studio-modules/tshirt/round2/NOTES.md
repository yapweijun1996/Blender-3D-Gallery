# Studio T-shirt, round 2

**REWORK.** The final GLB passes both rest collision gates and retains motion contacts in all seven requested clips. Over 824 poses, the deepest vertex is 9.569 mm inside at jump frame 6.5. The deepest intersecting-triangle witness is 9.769 mm inside at jump frame 7.5. Both are on the front panel beside the left forearm.

The final GLB contains **3,903 triangles** and **3,193,296 bytes**. The editable BLEND is **4,035,037 bytes**. The GLB contains one garment mesh, 65 original joints, up to four normalized skin influences and zero animations. Three Tripo maps remain 1024 × 1024. The embedded image bytes, material definition, and joint inverse bind matrices exactly match round 1. The source UV chart is retained. Khronos glTF Validator 2.0.0-dev.3.10 reported **0 errors and 0 warnings**. Blender reported its shared-sampler export notice for the inherited material.

The left cuff center is 41.3% along the rest upper arm and the right is 44.5%. The hem spans z = 392.3–400.0 mm. The welded model has one opening each at the collar, left cuff, right cuff and hem, with zero edges shared by more than two faces.

- [GLB](tshirt_v2.glb), [editable BLEND](tshirt_v2.blend), [Blender fitter](fit_tshirt_r2.py)
- [Export structure](export_check.json), [Khronos validation](gltf_validation.json), [fit history](fit_history.json)
- GLB SHA-256 `f6430450b6934cef4f4125531289435308cc4a3ae467d867df710ede9576182c`
- BLEND SHA-256 `3f0c090c67141e543b70462f8f2f40128a6935e55e6472ca190fc4155dca70ff`

## Supplied checker RESULT tables

The vertex checker measures twelve samples per clip. The triangle checker measures every third integer frame. The motion minimum distances use each checker's original rounding.

### Inside vertices

| Clip | Peak count | Minimum signed vertex distance (mm) |
| --- | ---: | ---: |
| rest | 0 | +1.084 |
| walk | 182 | -7.200 |
| run | 86 | -7.300 |
| wave | 56 | -8.700 |
| jump | 86 | -8.100 |
| idle | 73 | -8.100 |
| nod | 57 | -8.500 |
| dance | 43 | -4.500 |

### Triangle-overlap pairs

| Clip | Peak count | Minimum signed vertex distance (mm) |
| --- | ---: | ---: |
| rest | 0 | +1.084 |
| walk | 869 | -6.900 |
| run | 708 | -7.300 |
| wave | 460 | -8.700 |
| jump | 535 | -8.900 |
| idle | 492 | -8.100 |
| nod | 465 | -8.500 |
| dance | 191 | -4.500 |

Raw results [vertex TXT](motion_check.txt), [vertex JSON](motion_check.json), [triangle TXT](motion_check_tri.txt), [triangle JSON](motion_check_tri.json).

## Half-frame RESULT and remaining contacts

All values come from the reimported GLB on the supplied master and clips. Each count is the maximum for a single sample. The body zone identifies the dominant skin joint of the nearest body triangle. The deepest triangle-interior distances are estimates from samples on intersected faces, including intersection-line witnesses. The [dense report](dense_check.json) lists the deepest observation for every affected zone.

| Clip | Samples | Max inside vertices | Max crossing pairs | Deepest vertex (zone, frame, mm) | Deepest triangle witness (zone, frame, mm) |
| --- | ---: | ---: | ---: | --- | --- |
| rest | 1 | 0 | 0 | — | — |
| walk | 113 | 189 | 873 | front panel / LeftForeArm, 16.5, -7.504 | hem / LeftForeArm, 40.5, -9.057 |
| run | 61 | 156 | 708 | hem / RightForeArm, 28.5, -9.567 | back panel / LeftForeArm, 23, -8.797 |
| wave | 129 | 56 | 460 | back panel / LeftForeArm, 48, -8.683 | hem / LeftForeArm, 19, -9.414 |
| jump | 101 | 91 | 535 | front panel / LeftForeArm, 6.5, -9.569 | front panel / LeftForeArm, 7.5, -9.769 |
| idle | 177 | 73 | 492 | back panel / LeftForeArm, 22, -8.065 | hem / LeftForeArm, 43, -8.583 |
| nod | 113 | 57 | 465 | back panel / LeftForeArm, 17, -8.505 | hem / LeftForeArm, 17, -9.230 |
| dance | 129 | 43 | 191 | front panel / LeftForeArm, 48, -4.475 | back panel / LeftArm, 44.5, -4.839 |

The master also shows forearm/hand-to-trunk self-intersections at several failure poses. The stand-alone body has 162 such triangle pairs on the left at walk 16.5, and 41 left plus 112 right at run 28.5. Dance still has garment contacts at checked poses with zero distal arm-to-trunk pairs. The source-body intersections explain some tight clearances. Additional cloth contacts remain.

## Rest signed clearance in mm

The supplied checkers measured a rest minimum of +1.084 mm. The dense check measured the distribution below with its own triangle BVH traversal. Both meet the 0.500 mm floor and all measured rest vertices meet the 30 mm cap.

| Region | Min | P10 | Median | P90 | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| overall | 1.335 | 2.937 | 5.199 | 9.420 | 12.568 | 19.204 |
| back panel | 2.370 | 3.229 | 5.774 | 10.614 | 11.187 | 13.114 |
| collar | 4.466 | 5.351 | 6.286 | 13.131 | 15.230 | 19.204 |
| front panel | 1.800 | 3.150 | 3.655 | 11.960 | 15.785 | 18.140 |
| hem | 1.797 | 2.170 | 4.427 | 8.199 | 9.837 | 16.191 |
| shoulder / armpit | 1.800 | 3.434 | 5.813 | 7.812 | 8.674 | 13.945 |
| sleeve / cuff | 1.335 | 2.422 | 5.966 | 6.792 | 7.449 | 13.853 |

## Fit selection and visual evidence

The final build evaluated the close-cut seed and 16 successive passes. Three trial subdivision stages inserted 445, 446 and 441 local edge midpoints in total across their respective stages. Pass 2 had the lowest combined score, with shallower penetrations and fewer inside-vertex observations than the round 1 baseline. It precedes the subdivision stages. The delivered topology therefore has the original triangle count and long crossing edges remain possible. The final export reduced peak vertex depth from 14.424 mm to 9.569 mm, while the aggregate crossing-pair count rose from 235,947 to 338,588 across the same poses.

An independent visual review matched the five PNG hashes to the final GLB. The T-pose retains a close collar, short cuffs, and a hip-length tapered silhouette. Light creases remain around the sides and hem, and the gamepad relief is more angular around the buttons than in round 1. Walk frame 22.5 exposes a clear skin wedge from the near armpit toward the hem and a smaller sliver beneath the opposite cuff. Run frame 9 shows bunching at the sleeve and waist. The camera occludes part of the shirt in run, wave and jump. The numerical checks cover those occluded contacts.

[Six rest views](six_views.png) · [Walk](walk.png) · [Run](run.png) · [Wave](wave.png) · [Jump](jump.png) · [Render frames and hashes](render_info.json)

## Fit and reproduction

The build starts from the round 1 T-shirt GLB. It welds geometric UV splits in Blender and retains per-corner UVs and the Tripo material. The editable scene carries the unchanged master reference body. The GLB exports the garment and its skin.

The fitter evaluates the original quaternion actions with their Blender 5 action slots. Its measurements cover T-pose and 823 half-frame samples, including both endpoints of all seven clips. It pulls the largest measured vertex and intersecting-triangle witness deficits into rest space with a 2 mm target margin. Three Laplacian passes preserve the required directional component before the solver reconciles competing motion constraints, rest bounds, cuff placement, and face orientation. The resulting compromises can leave a deficit. Candidate moves are checked against the actual nearest surface, and the fitter splits long crossing edges and adds local armpit loops where useful. Skin weights are smoothed at the sleeve, shoulder, and hem and normalized to at most four influences per vertex.

Use the guarded Blender 5.1.2 command supplied with the task, with the same DYLD setting. Run from this directory. The build and evidence stages use local inputs and tools.

```sh
OPENBLAS_NUM_THREADS=2 "$BLENDER" -b -noaudio -t 2 --python-exit-code 1 --python fit_tshirt_r2.py
"$BLENDER" -b -noaudio -t 2 --python-exit-code 1 --python fit_tshirt_r2.py -- --checkers
"$BLENDER" -b -noaudio -t 2 --python-exit-code 1 --python fit_tshirt_r2.py -- --verify
"$BLENDER" -b -noaudio -t 4 --python-exit-code 1 --python fit_tshirt_r2.py -- --renders
```

The checker runner preserves both supplied measurement paths and frame selections. It skips their Workbench render calls and gives their JSON files distinct names. The PNGs use Cycles CPU on the reimported GLB. The motion images show each clip's peak measured triangle-overlap sample when contacts remain. The six-view sheet orders the front, front three-quarter, right, back, back three-quarter and left views.

## Read-only input SHA-256

| Input | SHA-256 |
| --- | --- |
| `tshirt_v1.glb` | `b3720ea4780f0cc98e28185749cb6f0284a7132481cf0a7e8eb419183e8b5034` |
| `source_studio_retopo.glb` | `04c8eda2b71811e6abdd02066df8103dde88b2accfb7fd656cfc4744aa90d933` |
| `GJH_Chibi_Master_rigged.blend` | `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f` |
| `motion.glb` | `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410` |
