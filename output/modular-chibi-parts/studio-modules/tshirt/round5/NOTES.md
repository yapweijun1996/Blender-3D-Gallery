# Studio T-shirt, Round 5

**REWORK.** The named checkers measured 33,725 garment/body triangle-pair occurrences over 1,260 samples. The signed vertex minimum is -1.371 mm. Round 3 measured 84,928 occurrences and -4.021 mm with the same inputs and cadence. Poses meeting both collision checks and the +0.500 mm floor are rest, wave, jump, idle, nod.

[GLB](tshirt_v5.glb) · [Editable BLEND](tshirt_v5.blend) · [Fitter](fit_tshirt_r5.py) · [Six views](six_views.png) · [Sit idle](sit_idle.png) · [Hold item](hold_item.png)

The GLB contains **4,699 triangles** and **3,230,440 bytes**. The BLEND is **4,071,663 bytes**. The GLB contains one skinned mesh, 65 joints, a maximum of 4 normalized influences, and 0 animations. The three embedded Tripo textures each measure 1024 × 1024. Rest signed clearance spans 0.804–26.041 mm. Khronos glTF Validator 2.0.0-dev.3.10 reports 0 errors and 0 warnings. [Structure and material](export_check.json) · [Khronos report](gltf_validation.json)

The Tripo material, embedded image payloads, and inverse bind matrices match Round 3. The UV triangle chart matches Round 3 at 0.000001 precision.

## Garment / body motion checks

Counts are per-pose peaks. Signed distances are minima across all garment vertices and poses in the clip. The wrappers retain the supplied measurement functions and sample every integer and half frame. The legacy bank was imported at 24 fps and the corrected action bank at 30 fps.

### Inside vertices

[Per-frame JSON](motion_check.json) · [Text output](motion_check.txt)

| Pose | Samples | Integer peak | Half-frame peak | Min signed vertex (mm) | Frame | Round 3 peak |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | — | +0.804 | 1 | 0 |
| walk | 113 | 21 | 21 | -1.100 | 35 | 13 |
| run | 61 | 4 | 2 | -0.256 | 12.5 | 18 |
| wave | 129 | 0 | 0 | +0.745 | 0 | 0 |
| jump | 101 | 0 | 0 | +0.544 | 20.5 | 0 |
| idle | 177 | 0 | 0 | +0.716 | 66 | 0 |
| nod | 113 | 0 | 0 | +0.745 | 0 | 0 |
| dance | 129 | 1 | 1 | -0.394 | 49 | 7 |
| sit_down | 73 | 10 | 9 | -1.135 | 26 | 87 |
| sit_idle | 181 | 14 | 14 | -1.201 | 21.5 | 98 |
| stand_up | 61 | 10 | 9 | -1.371 | 11 | 87 |
| hold_item | 121 | 7 | 7 | -0.614 | 14 | 34 |

### Overlapping triangle pairs

[Per-frame JSON](motion_check_tri.json) · [Text output](motion_check_tri.txt)

| Pose | Samples | Integer peak | Half-frame peak | Min signed vertex (mm) | Frame | Round 3 peak |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | — | +0.804 | 1 | 0 |
| walk | 113 | 75 | 74 | -1.100 | 35 | 68 |
| run | 61 | 64 | 48 | -0.256 | 12.5 | 51 |
| wave | 129 | 0 | 0 | +0.745 | 0 | 0 |
| jump | 101 | 0 | 0 | +0.544 | 20.5 | 0 |
| idle | 177 | 0 | 0 | +0.716 | 66 | 0 |
| nod | 113 | 0 | 0 | +0.745 | 0 | 0 |
| dance | 129 | 28 | 26 | -0.394 | 49 | 39 |
| sit_down | 73 | 83 | 83 | -1.135 | 26 | 243 |
| sit_idle | 181 | 88 | 88 | -1.201 | 21.5 | 247 |
| stand_up | 61 | 90 | 88 | -1.371 | 11 | 240 |
| hold_item | 121 | 76 | 76 | -0.614 | 14 | 154 |

## Residual garment zones

Each row gives the worst measured witness for a garment/body zone. The body label is the dominant joint of the closest body triangle. A triangle witness is sampled on the garment surface. Positive signed values below +0.500 mm are clearance shortfalls. [Unrounded zone and pose measurements](dense_check.json)

| Clip | Witness | Garment / body zone | Frame | Signed distance (mm) |
| --- | --- | --- | ---: | ---: |
| walk | vertex | shoulder / armpit / LeftArm | 35 | -1.100 |
| walk | vertex | shoulder / armpit / Spine1 | 35 | -0.922 |
| walk | vertex | front panel / LeftArm | 16 | -0.783 |
| walk | vertex | sleeve / cuff / Spine1 | 30 | -0.632 |
| walk | vertex | front panel / Spine1 | 35 | -0.411 |
| walk | vertex | sleeve / cuff / LeftArm | 34 | -0.272 |
| walk | vertex | back panel / LeftArm | 21 | +0.056 |
| walk | vertex | back panel / Spine1 | 22 | +0.389 |
| walk | triangle witness | back panel / LeftArm | 35 | -1.631 |
| walk | triangle witness | back panel / Spine1 | 34 | -1.539 |
| walk | triangle witness | front panel / LeftArm | 14 | -1.494 |
| walk | triangle witness | shoulder / armpit / LeftArm | 35 | -1.471 |
| walk | triangle witness | shoulder / armpit / Spine1 | 34.5 | -1.383 |
| walk | triangle witness | front panel / Spine1 | 34 | -1.119 |
| walk | triangle witness | sleeve / cuff / Spine1 | 30 | -0.632 |
| walk | triangle witness | sleeve / cuff / LeftArm | 34 | -0.490 |
| run | vertex | hem / RightUpLeg | 12.5 | -0.256 |
| run | vertex | shoulder / armpit / LeftArm | 10 | -0.139 |
| run | vertex | shoulder / armpit / Spine1 | 24 | +0.166 |
| run | vertex | sleeve / cuff / LeftArm | 18 | +0.340 |
| run | vertex | back panel / Spine1 | 12 | +0.355 |
| run | vertex | hem / Spine1 | 12.5 | +0.428 |
| run | triangle witness | shoulder / armpit / LeftArm | 10 | -0.533 |
| run | triangle witness | hem / RightUpLeg | 12.5 | -0.279 |
| run | triangle witness | back panel / LeftArm | 24 | -0.147 |
| run | triangle witness | back panel / Spine1 | 13 | -0.081 |
| run | triangle witness | sleeve / cuff / LeftArm | 10 | -0.056 |
| run | triangle witness | shoulder / armpit / Spine1 | 5 | -0.000 |
| dance | vertex | shoulder / armpit / LeftArm | 49 | -0.394 |
| dance | triangle witness | shoulder / armpit / LeftArm | 49 | -0.401 |
| dance | triangle witness | sleeve / cuff / LeftArm | 49.5 | -0.000 |
| sit_down | vertex | shoulder / armpit / LeftArm | 26 | -1.135 |
| sit_down | vertex | sleeve / cuff / LeftArm | 16 | -0.150 |
| sit_down | vertex | sleeve / cuff / Spine1 | 35 | -0.060 |
| sit_down | vertex | shoulder / armpit / Spine1 | 12 | +0.007 |
| sit_down | vertex | sleeve / cuff / RightArm | 16 | +0.033 |
| sit_down | vertex | shoulder / armpit / RightArm | 15.5 | +0.155 |
| sit_down | triangle witness | shoulder / armpit / LeftArm | 33.5 | -1.855 |
| sit_down | triangle witness | back panel / LeftArm | 32.5 | -1.058 |
| sit_down | triangle witness | back panel / RightArm | 2 | -0.837 |
| sit_down | triangle witness | front panel / LeftArm | 24.5 | -0.339 |
| sit_down | triangle witness | sleeve / cuff / LeftArm | 16 | -0.301 |
| sit_down | triangle witness | sleeve / cuff / Spine1 | 18 | -0.279 |
| sit_down | triangle witness | shoulder / armpit / Spine1 | 17.5 | -0.062 |
| sit_down | triangle witness | shoulder / armpit / RightArm | 30.5 | -0.008 |
| sit_idle | vertex | shoulder / armpit / LeftArm | 21.5 | -1.201 |
| sit_idle | vertex | sleeve / cuff / Spine1 | 64.5 | -0.265 |
| sit_idle | vertex | sleeve / cuff / LeftArm | 62 | -0.027 |
| sit_idle | vertex | sleeve / cuff / RightArm | 69 | +0.332 |
| sit_idle | triangle witness | shoulder / armpit / LeftArm | 6 | -1.866 |
| sit_idle | triangle witness | back panel / LeftArm | 11.5 | -1.125 |
| sit_idle | triangle witness | back panel / RightArm | 78 | -0.813 |
| sit_idle | triangle witness | sleeve / cuff / LeftArm | 69 | -0.284 |
| sit_idle | triangle witness | sleeve / cuff / Spine1 | 64.5 | -0.265 |
| sit_idle | triangle witness | shoulder / armpit / RightArm | 22 | -0.000 |
| stand_up | vertex | shoulder / armpit / LeftArm | 11 | -1.371 |
| stand_up | vertex | sleeve / cuff / LeftArm | 17 | -0.221 |
| stand_up | vertex | sleeve / cuff / Spine1 | 20.5 | -0.149 |
| stand_up | vertex | shoulder / armpit / Spine1 | 15 | -0.074 |
| stand_up | vertex | sleeve / cuff / RightArm | 18 | +0.069 |
| stand_up | vertex | shoulder / armpit / RightArm | 18.5 | +0.157 |
| stand_up | triangle witness | shoulder / armpit / LeftArm | 2 | -1.864 |
| stand_up | triangle witness | back panel / LeftArm | 2.5 | -1.086 |
| stand_up | triangle witness | back panel / RightArm | 0 | -0.717 |
| stand_up | triangle witness | front panel / LeftArm | 7 | -0.625 |
| stand_up | triangle witness | sleeve / cuff / Spine1 | 16 | -0.397 |
| stand_up | triangle witness | sleeve / cuff / LeftArm | 15.5 | -0.395 |
| stand_up | triangle witness | shoulder / armpit / Spine1 | 16 | -0.163 |
| stand_up | triangle witness | sleeve / cuff / RightArm | 14 | -0.000 |
| hold_item | vertex | shoulder / armpit / LeftArm | 14 | -0.614 |
| hold_item | vertex | sleeve / cuff / Spine1 | 14 | -0.009 |
| hold_item | vertex | sleeve / cuff / LeftArm | 11 | +0.038 |
| hold_item | triangle witness | shoulder / armpit / LeftArm | 14 | -0.898 |
| hold_item | triangle witness | sleeve / cuff / LeftArm | 13 | -0.135 |
| hold_item | triangle witness | sleeve / cuff / Spine1 | 10 | -0.079 |
| hold_item | triangle witness | back panel / LeftArm | 15 | -0.045 |

## Body-only knee contacts

The existing body audit used the same master and corrected action hashes. It reports unordered non-adjacent body triangle pairs. The deepest knee value is a triangle separating translation. [Body-only summary](body_only_pairs.json)

| Clip | Peak same-side thigh/shin pairs | Pair occurrences | Deepest knee (mm) | Frame |
| --- | ---: | ---: | ---: | ---: |
| sit_down | 15 | 220 | 4.141 | 35.5 |
| sit_idle | 15 | 2715 | 4.100 | 0 |
| stand_up | 15 | 181 | 4.134 | 0.5 |
| hold_item | 0 | 0 | 0.000 | — |

## Visual review

The independent reviewer compared the exact-export renders against the Round 3 six-view sheet. The controller relief, purple collar and cuff piping, and folded hem retain their appearance. The neutral cut stays close to the reference, with more puckering under one cuff visible from the side and rear three-quarter views. In sit_idle, the front hem arches over the raised thighs and the side hem forms a small fold. In hold_item, the sleeve follows the raised upper arm and the hand and cup cover part of the graphic. The two camera angles cover the visible front and side surfaces. [Six views](six_views.png) · [Sit idle](sit_idle.png) · [Hold item](hold_item.png)

## Fit and reproduction

The fitter imports the shipped Round 3 mesh and welds positional UV splits for continuous deformation. It keeps UVs as corner data and tests shape and weight edits using half-frame scans, worst-frame offsets, Laplacian smoothing and local triangle tests. Round 3 had shallow legacy contacts in walk, run and dance. Its jump clearance also fell below the requested margin. Local subdivision increased garment contacts in the tested branch, so the delivered mesh retains the Round 3 triangle topology. The cuff adjustment cleared jump and increased the hold_item pair peak from 58 to 76 relative to the preceding candidate. All four corrected actions still improved relative to the shipped Round 3 GLB. The walk and run pair peaks increased relative to Round 3.

The selected candidate uses the sixth local fitting pass, restores the regions needed by the three previously passing clips, and adds a 0.15 mm cuff adjustment for jump. Maximum rest-space displacement **22.886 mm**. Vertices with a weight edit above 0.001 L1 **530**. [Fit history](fit_history.json)

The action images show the lowest signed-clearance vertex or triangle witness frame on the exact reimported GLB. Sit idle uses frame 6 and hold item uses frame 14. [Render manifest](render_info.json)

```sh
sh run.sh fit_tshirt_r5.py
sh run.sh check_motion_r5.py
sh run.sh check_motion_r5.py -- --triangles
sh run.sh review_tshirt_r5.py
sh run.sh review_tshirt_r5.py -- --validator
sh run.sh review_tshirt_r5.py -- --renders
```

```text
GLB SHA-256 0601a38193299f543fd25f95b491da05d8b653cfd4c18155308527f15cdfc689
Master SHA-256 0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f
Motion SHA-256 3484f5978e94f3e714b320357397d107dd490d56f2eeb64770be292322f9aa2c
Actions SHA-256 0d3a57ae8906edeebee590b67d0e84333640389340bfbfbe0af041ccf8f871c9
```
