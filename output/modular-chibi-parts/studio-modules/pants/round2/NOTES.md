# Studio cargo pants, round 2

The collision gate remains open for walk, run, wave, jump, idle, nod, dance.
Rest passes both collision checks and the 0.5 to 30 mm clearance window. The dense sweep evaluates the exported GLB with the supplied master body and clips.

## Artifacts

- [pants_v2.glb](pants_v2.glb) — 4,334,092 bytes, 7,999 triangles, 7,264 exported vertices, one garment mesh and one 65-joint skin.
- [pants_v2.blend](pants_v2.blend) — 4,328,350 bytes, pants mesh and master armature.
- At most 4 skin influences per vertex and 0 unweighted vertices.
- Local Khronos Validator 2.0.0-dev.3.10 reports 0 errors and 0 warnings. [GLB validation](gltf_validator.json)
- All three embedded 1024 × 1024 textures are byte-identical to Round 1.
- Blender removed one invalid face during the initial export. The saved mesh reopened with 7,999 triangles and passed Blender mesh validation. The final re-export and Khronos validation cover that topology.
- GLB SHA-256 `e62868f63c4a093ee49a5c8244bf24bba6ca0493b8316a87cbd0bac712af4e00`.
- BLEND SHA-256 `4c2e4290c01d71f5a1eb88f17b1abd8ab61d58ce639bc709cc18de4a90418d5a`.

## RESULT — Supplied vertex checker

| Clip | Max vertices inside | Min signed distance (mm) |
| --- | ---: | ---: |
| rest | 0 | +1.450 |
| walk | 146 | -16.200 |
| run | 282 | -23.300 |
| wave | 64 | -6.100 |
| jump | 95 | -8.300 |
| idle | 62 | -5.600 |
| nod | 63 | -5.400 |
| dance | 1 | -1.100 |

The checker samples 12 times per clip. [RESULT output](motion_check.txt) · [Data](motion_check.json)

## RESULT — Supplied triangle checker

| Clip | Max overlapping triangle pairs | Min signed distance (mm) |
| --- | ---: | ---: |
| rest | 0 | +1.450 |
| walk | 504 | -17.700 |
| run | 1111 | -23.300 |
| wave | 99 | -6.100 |
| jump | 474 | -8.900 |
| idle | 88 | -5.600 |
| nod | 85 | -5.400 |
| dance | 8 | -1.100 |

The checker samples every third integer frame. [RESULT output](motion_check_tri.txt) · [Data](motion_check_tri.json)

## RESULT — Dense export check

Both metrics were measured at 824 poses, including rest, every integer frame, every half frame and the clip endpoints. Each count is a peak at a single pose. The minimum distance may occur at a different frame. The fit and dense checks include the full body surface. [Dense checker data](dense_check.json)

| Clip | Poses | Max inside | Max triangle pairs | Min vertex distance (mm) | Frame | Pants zone | Nearest body joint |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| rest | 1 | 0 | 0 | +1.450 | 1 | waistband | — |
| walk | 113 | 172 | 649 | -17.937 | 27 | right thigh | mixamorig:RightUpLeg |
| run | 61 | 298 | 1158 | -25.171 | 26.5 | right thigh | mixamorig:RightUpLeg |
| wave | 129 | 70 | 99 | -6.109 | 43.5 | hips | mixamorig:LeftForeArm |
| jump | 101 | 127 | 474 | -8.938 | 9 | right thigh | mixamorig:RightUpLeg |
| idle | 177 | 62 | 89 | -5.601 | 22 | waistband | mixamorig:LeftForeArm |
| nod | 113 | 63 | 86 | -5.431 | 17 | waistband | mixamorig:LeftForeArm |
| dance | 129 | 1 | 8 | -1.089 | 0 | left thigh | mixamorig:LeftUpLeg |

## Rest clearance

The cuff-to-waist Z bounds are 72.952 to 415.937 mm. The rest allowance is 30 mm.

| Region | Min (mm) | P10 (mm) | Median (mm) | P90 (mm) | P95 (mm) | Max (mm) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 1.450 | 3.321 | 5.924 | 19.963 | 26.204 | 29.800 |
| crotch / inner thigh | 2.109 | 5.498 | 9.317 | 14.764 | 16.260 | 18.135 |
| hips | 2.000 | 3.235 | 3.709 | 6.203 | 7.903 | 18.146 |
| left cuff | 3.960 | 5.500 | 5.601 | 6.883 | 8.750 | 12.504 |
| left knee | 3.611 | 6.588 | 15.159 | 27.901 | 29.415 | 29.700 |
| left lower leg | 5.425 | 5.712 | 11.734 | 17.069 | 18.322 | 20.097 |
| left thigh | 1.851 | 5.458 | 14.037 | 27.750 | 28.738 | 29.800 |
| right cuff | 3.905 | 5.497 | 5.526 | 7.230 | 8.906 | 12.491 |
| right knee | 4.712 | 6.829 | 14.484 | 28.545 | 29.527 | 29.697 |
| right lower leg | 2.191 | 5.594 | 10.972 | 16.661 | 18.145 | 20.095 |
| right thigh | 2.000 | 5.618 | 14.152 | 28.925 | 29.419 | 29.800 |
| waistband | 1.450 | 3.152 | 3.676 | 7.286 | 8.732 | 15.336 |

## Remaining zones

The depth column for triangles comes from sampled intersection witnesses and face interiors. The BVH overlap count is computed over entire triangles.

| Clip | Pants zone | Min vertex distance (mm) | Vertex frame | Nearby body joint | Peak triangle pairs | Deepest triangle sample (mm) | Triangle depth frame |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |
| walk | crotch / inner thigh | -0.280 | 34 | mixamorig:LeftUpLeg | 6 | -0.764 | 35 |
| walk | hips | -8.107 | 12.5 | mixamorig:LeftHand | 207 | -8.665 | 39.5 |
| walk | left knee | -4.831 | 15.5 | mixamorig:LeftHandMiddle3 | 31 | -5.730 | 27 |
| walk | left thigh | -10.509 | 15 | mixamorig:LeftHandRing1 | 414 | -10.043 | 2 |
| walk | right knee | -12.854 | 22 | mixamorig:RightLeg | 68 | -11.410 | 22 |
| walk | right thigh | -17.937 | 27 | mixamorig:RightUpLeg | 149 | -12.627 | 27 |
| walk | waistband | -7.865 | 12 | mixamorig:LeftForeArm | 185 | -6.864 | 29.5 |
| run | crotch / inner thigh | -5.623 | 27 | mixamorig:Hips | 88 | -5.357 | 27 |
| run | hips | -7.786 | 18 | mixamorig:LeftUpLeg | 323 | -10.526 | 29 |
| run | left cuff | -2.166 | 9 | mixamorig:LeftFoot | 32 | -2.457 | 25 |
| run | left knee | -13.855 | 12 | mixamorig:LeftUpLeg | 232 | -9.369 | 14 |
| run | left lower leg | -5.080 | 2 | mixamorig:LeftUpLeg | 56 | -5.562 | 1 |
| run | left thigh | -7.233 | 20 | mixamorig:LeftUpLeg | 279 | -7.837 | 22.5 |
| run | right cuff | -2.916 | 9 | mixamorig:RightUpLeg | 40 | -5.051 | 9.5 |
| run | right knee | -13.844 | 25 | mixamorig:RightLeg | 232 | -16.563 | 25 |
| run | right lower leg | -8.046 | 8.5 | mixamorig:RightUpLeg | 158 | -7.188 | 8.5 |
| run | right thigh | -25.171 | 26.5 | mixamorig:RightUpLeg | 412 | -18.919 | 26.5 |
| run | waistband | -6.577 | 23 | mixamorig:LeftForeArm | 158 | -6.679 | 23 |
| wave | hips | -6.109 | 43.5 | mixamorig:LeftForeArm | 27 | -5.334 | 10.5 |
| wave | waistband | -6.068 | 48 | mixamorig:LeftForeArm | 76 | -5.969 | 8 |
| jump | hips | -5.697 | 2.5 | mixamorig:LeftForeArm | 117 | -4.631 | 43.5 |
| jump | left cuff | — | — | — | 2 | +0.000 | 9 |
| jump | left thigh | -4.678 | 9 | mixamorig:LeftHandMiddle1 | 274 | -5.468 | 9 |
| jump | right knee | +0.126 | 9 | mixamorig:RightLeg | 4 | -0.008 | 9 |
| jump | right thigh | -8.938 | 9 | mixamorig:RightUpLeg | 18 | -5.182 | 9 |
| jump | waistband | -6.029 | 43 | mixamorig:LeftForeArm | 75 | -6.206 | 4 |
| idle | hips | -4.051 | 39 | mixamorig:LeftForeArm | 17 | -3.705 | 36 |
| idle | waistband | -5.601 | 22 | mixamorig:LeftForeArm | 79 | -5.402 | 22 |
| nod | hips | -3.381 | 33 | mixamorig:LeftForeArm | 11 | -3.466 | 43.5 |
| nod | waistband | -5.431 | 17 | mixamorig:LeftForeArm | 76 | -5.205 | 17 |
| dance | hips | — | — | — | 2 | -0.471 | 0 |
| dance | left thigh | -1.089 | 0 | mixamorig:LeftUpLeg | 6 | -0.387 | 0 |

The supplied base body has arm–pelvis self-intersections at several measured worst frames. walk 27 has 181, wave 43.5 has 51, jump 9 has 69, idle 22 has 43, nod 17 has 42 triangle pairs in the body alone.

## Fit and reproduction

The fitter uses Blender 5.1.2 and starts from Round 1's skinned GLB with coincident seam positions merged. It keeps the Tripo material and corner UVs, interpolating UVs where Blender inserts support loops.

The first pass compares waistband heights, waist take-in, and local weight transfer. The solver transforms worst-frame nearest-surface directions back through the skinning Jacobian and targets the measured deficit plus 2 mm. Laplacian smoothing preserves the directional floor before trial gain, displacement caps and rest-shape guards. Intersecting triangles contribute interior witnesses. Long contact edges at or above 12 mm are subdivided within the 8,000-triangle budget. The local searches and smoothed, normalized four-joint weights concentrate changes around the hips, inner thigh and knees.

The fitter used 16 update slots and selected iteration 16 by the dense score among fits that met the rest limits. The score combines sampled vertex deficits and triangle contacts, with a triangle-count normalization across mesh densities. Round 1 passed dance, which regressed in the selected fit. The dense run pair peak increased from 611 in Round 1 to the value recorded above. The supplied checker measurement code runs unchanged in the wrapper. A separate Cycles CPU stage renders the captures. [Fit history](fit_history.json)

The first export measured 30.074 mm at one source vertex represented by three GLB vertices. The ceiling pass moved that vertex inward and re-exported. All reports and PNGs above use the re-exported GLB.

Run with the supplied guarded Blender binary and DYLD setting from this directory.

```sh
"$BLENDER" -b -t 5 -noaudio --python-exit-code 1 --python fit_pants_r2.py -- build
"$BLENDER" -b -t 5 -noaudio --python-exit-code 1 --python fit_pants_r2.py -- verify checkers renders
```

## Captures

The six-view sheet shows the belt at the hips and the ribbed cuffs near the ankles. The cargo pockets and purple side stripes remain readable. Small folds remain on the waistband and rear thighs. The run capture shows skin on the raised right thigh and creasing at the opposite pocket. The walk and jump captures show hand or forearm contact near the pockets. The wave capture shows the left forearm touching the side of the waist.

The captures use Cycles CPU, 16 samples, AgX and an orthographic camera. The six-view sheet shows the front, front three-quarter, side, back, waist and cuff angles. Each motion image uses the peak-pair frame, or the minimum-clearance frame for a clean clip.

| Capture | Frame | SHA-256 |
| --- | ---: | --- |
| [walk.png](walk.png) | 38.5 | `db226b1f5c3ee209904b56b4e3be720b3ac159c8a8678e57d9c6f35b927ec54f` |
| [run.png](run.png) | 11 | `d89bcfe9aa25cf4d9a6906dbe25cd5c52e57c5b29c7842c35c5152a77030b41e` |
| [wave.png](wave.png) | 15.5 | `9b7330cc3310f778c5c3fdb6b9f31220303707ece84c5613f3dabccab6534358` |
| [jump.png](jump.png) | 9 | `b471f0afcf369cdb731385a140b97c61357e639f92e2edb38ee31290350d8f81` |
| [six_view.png](six_view.png) | 1 | `3e8dd8d1db7bc59d04a1fe6a5be40f7cfa63cd40220b1e1072493d2362b86fd9` |
