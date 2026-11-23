# Studio cargo pants, round 3

**Run fails the clearance gate.** All other clips and rest pass both overlap checks and the 0.5 mm clearance threshold.

The fit starts with the Round 2 Studio cargo pants. It uses the master armature and corrected [motion_fixed.glb](../../../body-fix/motion_fixed.glb) at all 415 integer frames and 408 half frames, plus one neutral pose.

## Artifacts

- [pants_v3.glb](pants_v3.glb) · 4,334,364 bytes, 7,999 triangles, 7,268 exported vertices, one mesh, 65 joints, no embedded animation.
- [pants_v3.blend](pants_v3.blend) · 4,352,894 bytes, with the editable garment mesh and compatible armature.
- Maximum 4 normalized influences per vertex and 0 unweighted vertices.
- The Tripo material retains the original normal, base color and metallic-roughness textures, all byte-identical to Round 2 at 1024 × 1024. The fit retains the original UV charts. Blender interpolates corner UVs at the locally edited edges.
- [Fitting script](fit_pants_r3.py) and both checker entry points, [vertex](motion_check.py) and [triangle](motion_check_tri.py).
- Khronos glTF Validator 2.0.0-dev.3.10 reports **0 errors and 0 warnings**. [Validator report](gltf_validator.json)
- GLB SHA-256 `c7688fac3e84f4cd29b8d6c423695a4bacaf509c6a0d7299cf84831328431cbf`.
- BLEND SHA-256 `9cbeb5d54bf04fa4cc05206a8915c091fdb71034d70235dd949cc141b6234cbd`.
- Corrected motion SHA-256 `3484f5978e94f3e714b320357397d107dd490d56f2eeb64770be292322f9aa2c`.
- Master SHA-256 `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f`.
- Round 2 source SHA-256 `e62868f63c4a093ee49a5c8244bf24bba6ca0493b8316a87cbd0bac712af4e00`.

## RESULT — Garment vertices inside the master

| Clip | Poses | Integer peak | Half-frame peak | Minimum signed distance (mm) | Minimum frame |
| --- | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | — | 2.069 | 1 |
| walk | 113 | 0 | 0 | 0.618 | 28 |
| run | 61 | 2 | 2 | -1.296 | 9 |
| wave | 129 | 0 | 0 | 2.069 | 0 |
| jump | 101 | 0 | 0 | 1.627 | 9 |
| idle | 177 | 0 | 0 | 2.069 | 0 |
| nod | 113 | 0 | 0 | 2.069 | 0 |
| dance | 129 | 0 | 0 | 1.922 | 14 |

[RESULT output](motion_check.txt) · [Per-frame data](motion_check.json)

## RESULT — Garment–body triangle pairs

| Clip | Poses | Integer peak | Half-frame peak | Minimum signed distance (mm) | Minimum frame |
| --- | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | — | 2.069 | 1 |
| walk | 113 | 0 | 0 | 0.618 | 28 |
| run | 61 | 38 | 36 | -1.296 | 9 |
| wave | 129 | 0 | 0 | 2.069 | 0 |
| jump | 101 | 0 | 0 | 1.627 | 9 |
| idle | 177 | 0 | 0 | 2.069 | 0 |
| nod | 113 | 0 | 0 | 2.069 | 0 |
| dance | 129 | 0 | 0 | 1.922 | 14 |

[RESULT output](motion_check_tri.txt) · [Per-frame data](motion_check_tri.json)

The vertex sign is the dot product of the closest body triangle's outward normal and the displacement from the surface to the pants vertex. The triangle checker measures entire triangles with an epsilon-zero Blender BVH. The signed distance in both tables is the same vertex metric. Counts are per-pose peaks.

## Comparison with Round 2

These are the exact exported cargo pants, including UV-split vertices. Both rounds were checked with the corrected clips. The manager's jeans measurement concerns a separate garment.

| Clip | Round 2 vertices inside | Round 2 garment–body pairs | Round 2 min (mm) | Round 3 vertices inside | Round 3 garment–body pairs |
| --- | ---: | ---: | ---: | ---: | ---: |
| rest | 0 | 0 | 1.450 | 0 | 0 |
| walk | 49 | 210 | -15.061 | 0 | 0 |
| run | 234 | 785 | -22.848 | 2 | 38 |
| wave | 0 | 0 | 0.888 | 0 | 0 |
| jump | 11 | 50 | -8.642 | 0 | 0 |
| idle | 0 | 0 | 1.358 | 0 | 0 |
| nod | 0 | 0 | 1.422 | 0 | 0 |
| dance | 1 | 8 | -1.089 | 0 | 0 |

## Master body-only pairs

| Clip | Integer baseline peak | Measured integer peak | Measured half-frame peak | Added or missing baseline pairs |
| --- | ---: | ---: | ---: | ---: |
| rest | 318 | 318 | — | 0 |
| walk | 521 | 521 | 521 | 0 |
| run | 573 | 573 | 577 | 0 |
| wave | 317 | 317 | 316 | 0 |
| jump | 322 | 322 | 322 | 0 |
| idle | 317 | 317 | 317 | 0 |
| nod | 317 | 317 | 317 | 0 |
| dance | 313 | 313 | 312 | 0 |

Neutral master pairs include 163 at the eye inserts, 60 between the modeled shorts and the legs, and 95 in the foot and toe surfaces. The body-only comparison applies the same exact-position adjacency rule as the source audit. Triangle IDs agree at rest and on every audited integer frame. Half frames were measured independently. Garment–body pairs use the full master surface and a separate BVH query. [Body baseline notes](../../../body-fix/NOTES.md)

## Rest clearance

Cuff-to-waist Z range 72.952–415.892 mm. The clearance window is 0.5–30 mm.

| Region | Min (mm) | P10 | Median | P90 | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 2.069 | 3.568 | 6.219 | 20.637 | 26.451 | 29.704 |
| crotch / inner thigh | 2.879 | 6.096 | 10.334 | 14.961 | 16.136 | 18.150 |
| hips | 2.393 | 3.337 | 4.199 | 6.789 | 8.707 | 18.155 |
| left cuff | 5.495 | 5.500 | 5.727 | 7.775 | 9.144 | 12.504 |
| left knee | 4.441 | 7.299 | 15.225 | 27.985 | 29.449 | 29.700 |
| left lower leg | 5.500 | 5.711 | 11.812 | 17.069 | 18.321 | 20.109 |
| left thigh | 2.802 | 5.928 | 14.824 | 27.780 | 28.878 | 29.700 |
| right cuff | 4.488 | 5.497 | 5.737 | 8.373 | 9.703 | 12.683 |
| right knee | 4.774 | 7.412 | 15.263 | 29.249 | 29.543 | 29.698 |
| right lower leg | 2.987 | 5.674 | 11.340 | 16.659 | 18.148 | 20.198 |
| right thigh | 2.069 | 5.660 | 16.031 | 28.944 | 29.456 | 29.704 |
| waistband | 2.288 | 3.361 | 4.171 | 7.404 | 8.808 | 15.339 |

## Residuals

Triangle depth is the deepest sampled signed distance on intersecting garment faces. A value near zero can occur at a tangency. The pair tally uses the entire triangle surface.

| Clip | Garment zone | Deepest vertex (mm) | Vertex frame | Nearest joint at vertex | Peak pairs | Deepest face witness (mm) | Witness frame |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |
| run | left thigh | — | — | — | 34 | -4.963 | 8 |
| run | right knee | -1.296 | 9 | RightLeg | 34 | -1.836 | 9 |
| run | right lower leg | — | — | — | 4 | -0.267 | 9 |

Run has garment–body triangle pairs at frames 8, 8.5, 9, 9.5, 10, 23, 23.5, 24, 24.5, 25 and 25.5. The two inside vertices are present at frames 9, 9.5, 10, 24, 24.5 and 25. The per-frame checker reports include the counts and triangle IDs.

## Fitting and reproduction

Blender evaluates the master with the corrected action slots and preserves the master pose-bone rotation modes. The fit pulls the nearest-surface gradients at the worst samples back through the garment skinning transforms and targets a 2 mm margin. Laplacian offset passes restore the strongest local requirement after averaging. The fitter clamps rest clearance and tests local position and joint-blend hypotheses. A fresh export check evaluates the Blender armature modifier on the reimported GLB.

Selected update 16 of a maximum of 16. The selected path split 23 local support edges and consolidated 23 short, flat edges to stay within the triangle budget. It retained two Laplacian binding passes with a 0.10 gain in areas with clearance. An outlier pass reduced isolated binding changes at 40 vertices. One exported rest vertex was moved inward to enforce the 30 mm ceiling, then the mesh was re-exported and checked again. [Fit history](fit_history.json) · [Dense check and rest statistics](dense_check.json)

Set `BLENDER` and `DYLD_INSERT_LIBRARIES` to the guarded paths supplied with the task. Use the Round 3 directory. The verification and render scripts read the master and shared motion assets without changing them.

```sh
export PYTHONDONTWRITEBYTECODE=1
mkdir -p .runtime
export TMPDIR="$PWD/.runtime/"
PANTS_ROUND3_OUTPUT="$PWD/.runtime/local" "$BLENDER" -b -t 5 -noaudio --python-exit-code 1 --python fit_pants_r3.py -- build-checkpoint
"$BLENDER" -b -t 5 -noaudio --python-exit-code 1 --python fit_pants_r3.py -- polish
"$BLENDER" -b -t 5 -noaudio --python-exit-code 1 --python fit_pants_r3.py -- smooth smooth-outliers cap-rest verify renders
master=../../../master/GJH_Chibi_Master_rigged.blend
motion=../../../body-fix/motion_fixed.glb
"$BLENDER" -b -t 5 -noaudio --python-exit-code 1 --python motion_check.py -- "$master" "$motion" pants_v3.glb .
"$BLENDER" -b -t 5 -noaudio --python-exit-code 1 --python motion_check_tri.py -- "$master" "$motion" pants_v3.glb .
```

## Captures

Cycles CPU, 16 samples, AgX, orthographic camera, reimported final export. Motion captures show the peak garment-pair pose or the minimum vertex clearance pose for a clean clip. The independent visual review confirms the hip-height waist, ankle cuffs, cargo pockets, purple strips and tapered cut. The long run spike found during review is gone. Short thigh creases, a crumpled cargo pocket flap and a localized rear-thigh bulge remain. The reviewer spot-checked the final run and six-view renders after the clearance adjustment.

| Capture | Pose | SHA-256 |
| --- | --- | --- |
| [walk.png](walk.png) | walk frame 28 | `96655749ccc75e23862b16761974c687ac7c0dad9adc58bd92f207237b62c38a` |
| [run.png](run.png) | run frame 8 | `4ebfe900ad3531860f9ccfcd58d98b0efcae56b48f345589287f35dcd9866efc` |
| [wave.png](wave.png) | wave frame 0 | `3bd4b0c3ab9ffec7651275f72a1d506c421793c6103a1cc6a0a999aac834adfb` |
| [jump.png](jump.png) | jump frame 9 | `e3538b6a2a061e937e11e1480714c8935a84398b4492205ce2f264cb78c3af6b` |
| [six_view.png](six_view.png) | Rest, six views | `66f362dc6d5c0b39f5d1322917e497bd64cd4c6d161efd0dedaafe67d7dadafa` |
