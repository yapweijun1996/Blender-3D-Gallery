# Boy’s side-part hair · Round 3

The final hair-only GLB contains **2,982 triangles** and occupies **124,428 bytes**. The two motion checkers each tested **824 poses** on the corrected clips. The worst result was **0 inside vertices**, **0 overlapping triangle pairs**, and **0.976922 mm** minimum signed vertex clearance. Six-view near-black pixels fell from **4,668 to 34** (99.27%).

[GLB](hair_sidepart_v3.glb) · [Editable fitting scene](hair_sidepart_v3.blend) · [Fit script](fit_hair_r3.py) · [Six views](fit_views_v3.png) · [Front hairline](closeup_front_hairline.png) · [Side](closeup_side.png) · [Nape](closeup_nape.png)

## Independent visual review

A separate reviewer who did not author the model reopened the final six-view sheet, the front/side/nape close-ups, the round-two fit sheet and the original hairstyle reference. The verdict for GLB SHA-256 `05b448a6db5a85f465426ba939d1907a34d5a98a50a5979ed512fdd3cd0d7a43` was **PASS** on all five requested appearance criteria. The reviewer also passed a formerly visible diagonal scratch and isolated chip on the upper sweep.

| Criterion | Decision | Observation |
| --- | --- | --- |
| Sweep-to-cap junction | PASS | The lock flows continuously into the cap in the front and both three-quarter views. The dark shelf has cleared. |
| Forehead and temples | PASS | The central arch and both ear-front tips meet the skin cleanly in the frontal close-up. The earlier slit has cleared in both three-quarter views. |
| Strand tips and overlaps | PASS | Both profiles show broad curved locks with smooth ends. The former deep black notches have cleared. |
| Rolled nape | PASS | The rear edge describes a shallow continuous U and rises smoothly toward each ear in profile. |
| Side-part identity | PASS | The long wave sweeps toward the viewer’s left from the high part on the right. The shorter return and rounded back retain the round-two silhouette. |

The broader locks have shallower layering than the original concept. Some ridge highlights are slightly angular near the part and along the long sweep. A faint brown crease remains beside the part. All required appearance and technical gates passed.

## Construction and glTF checks

The rebuild starts from the editable round-two hair. Blender samples its outer volume and forehead contour. Three large swept banks and the shorter banks on the opposite side share a single surface. The spline-guided relief tapers into the cap. The sideburns turn forward onto the temples and the back rim follows a smooth height curve. Four circumferential courses roll underneath into a fitted lining. Surface probes support the interiors of long triangles over the head and near the ears.

The chestnut material uses a gentle vertex-colour gradient and smooth normals derived from the sculpt. It has one material, one primitive, and no texture images or UV islands. Blender exported one hair mesh and its 65-joint skin. Head and Neck supply at most two nonzero weights per vertex. Joint order, joint hierarchy and inverse bind matrices agree with the round-two skeleton. The fitting body is included in the editable scene. The GLB carries only the skinned hair.

Reloading the GLB and welding coincident positions at 0.0000001 m yielded one connected component, zero non-manifold edges, zero inconsistent windings and zero nonadjacent self-intersections. The editable scene was reopened and its smooth mesh, armature modifier and triangle count verified. Khronos glTF Validator 2.0.0-dev.3.10 returned **0 errors and 0 warnings**. [Geometry audit](geometry_check.json) · [Khronos report](khronos_validation.json)

## Corrected motion gate

Both checks use the requested master and `body-fix/motion_fixed.glb`. The fit script executes each supplied checker's scene setup and original `measure()` function. It binds the imported action's first slot and advances the master scene at 0.5-frame intervals, including both endpoints. The supplied standalone drivers use coarser sampling and round animated clearance. The round-three driver preserves unrounded measurements. Both distances reported here are signed distances from hair **vertices** to the nearest body surface. The triangle checker independently counts intersecting hair/body face pairs. Acceptance requires zero in both count columns and at least 0.0005 m minimum signed vertex clearance.

| Pose | Frame range | Samples per checker | Max inside | Max triangle pairs | Min signed distance (m) | Frame of minimum |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| rest | 1–1 | 1 | 0 | 0 | 0.000994025 | 1 |
| walk | 1–57 | 113 | 0 | 0 | 0.000990970 | 47 |
| run | 0–30 | 61 | 0 | 0 | 0.000976922 | 28.5 |
| wave | 0–64 | 129 | 0 | 0 | 0.000994038 | 0 |
| jump | 0–50 | 101 | 0 | 0 | 0.000992088 | 9 |
| idle | 0–88 | 177 | 0 | 0 | 0.000993778 | 60.5 |
| nod | 0–56 | 113 | 0 | 0 | 0.000991431 | 8 |
| dance | 0–64 | 129 | 0 | 0 | 0.000993695 | 24.5 |

[Vertex checker output](check_vertex/motion_check.json) · [Triangle-overlap checker output](check_tri/motion_check.json)

## Near-black pixels

Both sheets use the master body, the same six orthographic views, a camera target of (0, 0, 0.807 m), 0.55 m orthographic scale, 520 × 520 px tiles, AgX and the round-two studio setup with 12-sample denoised CPU Cycles. Both masks cast one ray through each pixel centre and exclude hair occluded by the body. The pixel test is the round-two display-encoded threshold (0.2126R + 0.7152G + 0.0722B < 0.12) on normalized PNG samples. Values read back from the completed six-view PNGs reproduced the JSON counts.

| View | R2 visible hair px | R3 visible hair px | R2 near-black | R3 near-black |
| --- | ---: | ---: | ---: | ---: |
| front | 69,874 | 72,947 | 678 | 0 |
| three quarter left | 81,786 | 82,328 | 494 | 8 |
| three quarter right | 83,328 | 84,708 | 1,429 | 21 |
| left | 99,039 | 100,365 | 120 | 5 |
| back | 107,908 | 107,285 | 1 | 0 |
| right | 102,031 | 102,775 | 1,946 | 0 |
| **Total** | **543,966** | **550,408** | **4,668** | **34** |

[Round-two counts](../round2/pixels_v2.json) · [Round-three counts](pixels_v3.json)

## Reproduction

Run the commands below from this round-three directory. They use the supplied local Blender 5.1.2, the existing repository validator and the two supplied checker scripts. `HAIR_CHECKER_DIR` can point to another local copy of those scripts. The fit script also accepts individual stages after `--`, named `build`, `audit`, `vertex`, `tri`, `views` and `closeups`.

```sh
runtime=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
mkdir -p "$PWD/.runtime"
export TMPDIR="$PWD/.runtime/" XDG_CACHE_HOME="$PWD/.runtime" BLENDER_USER_RESOURCES="$PWD/.runtime/blender"
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export DYLD_INSERT_LIBRARIES="$runtime/guard.dylib"
"$runtime/B/Blender.app/Contents/MacOS/Blender" -b -noaudio -t 4 --python-exit-code 1 --python fit_hair_r3.py
```

## Artifact identity

The render and checker records above apply to this export. The rig master SHA-256 is `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f` and the corrected motion GLB SHA-256 is `3484f5978e94f3e714b320357397d107dd490d56f2eeb64770be292322f9aa2c`. The round-two reference GLB SHA-256 is `b012f66308ce26fa052c7ec217eed43391092e0c40f7b7fd5ea96ff9c1365db5`. The six-view baseline PNG SHA-256 is `5da2c685e5f523d0089dcb6ffbfb3acfc6572ac6034ecfb4e7803dac3ab11f94`.

| File | SHA-256 |
| --- | --- |
| `hair_sidepart_v3.glb` | `05b448a6db5a85f465426ba939d1907a34d5a98a50a5979ed512fdd3cd0d7a43` |
| `hair_sidepart_v3.blend` | `b556918aebe6e16af585ddb59968d41e55a85155c4da3c5e69e8aefc2f22cbc5` |
| `fit_hair_r3.py` | `d2a5213bb10cacb5844def2687444bb47ca992bb98dfce0327d3a3e791b0fbd9` |
| `fit_views_v3.png` | `540de1944fd2c3cd885882529329498c79d6a206c8b22033c0fda7eb84b22de4` |
| `closeup_front_hairline.png` | `1cfbb1eee5c675090dd291451681233b8ce506382cc032aa6b3da3012247bf08` |
| `closeup_side.png` | `7867ee3f13d60e21e37d3e0a2e929c84d94be0731cf995f66deec8fbd643b602` |
| `closeup_nape.png` | `a43662b4655c1fecf74e97e8470d10339d3209a616bd8b41fc6f1da4d2bc532a` |
| `geometry_check.json` | `2bdc5c67adc243beadeac1d547559452b0e78bc56fc4dfbd40d742e3866a031e` |
| `khronos_validation.json` | `99bc17f66ade69757882e76f176004f4697ccfe9396027de584034574cf6662e` |
| `pixels_v3.json` | `812e1158dc2b1c12cf567172d1cd0cb2598ca4136be569e748c3f8971e9f237a` |
| `check_vertex/motion_check.json` | `cd1c2235831309a661b348bba3ac7d67abc61a02a02309d57cc0d8c5cde94f7f` |
| `check_tri/motion_check.json` | `fa4a8df86f25054471db41954bbf2eab1cfa34af1c83cc7a27b85c8d82291172` |
