# Studio T-shirt, Round 4

**REWORK.** The action refit is available as a candidate. Acceptance requires zero inside vertices, zero triangle-overlap pairs and a minimum signed vertex clearance of +0.500 mm in every sampled pose.

[GLB](tshirt_v4.glb) · [Editable BLEND](tshirt_v4.blend) · [Blender fitter](fit_tshirt_r4.py) · [Six views](six_views.png) · [Sit idle](sit_idle.png) · [Hold item](hold_item.png)

## Export

The skinned garment GLB has **4,699 triangles**, **3,230,440 bytes**, 1 garment mesh, 65 joints, up to 4 normalized weights per vertex and 0 animations. The editable BLEND is 4,070,645 bytes and includes the master for fitting reference. Rest vertex clearance is +0.999 to +19.302 mm. The geometric mesh has one opening at the collar, hem and each cuff, with 0 edges incident on more than two faces.

The compressed Tripo images match Round 3 byte for byte. All three images measure 1024 × 1024 px. The material definition and inverse bind matrices match Round 3. The per-triangle UV charts match at 0.000001 UV precision. Khronos glTF Validator 2.0.0-dev.3.10 reported **0 errors and 0 warnings**. [Export inspection](export_check.json) · [Khronos report](gltf_validation.json)

## Inside garment vertices

The checkers reimported the exact GLB on the specified master. The corrected legacy bank was sampled at 24 fps and the new bank at 30 fps, through both endpoints at half-frame steps. The neutral rest pose was sampled once. Peak counts apply to a single sampled pose.

| Pose | Samples | Integer peak | Half-frame peak | Minimum signed vertex (mm) | Frame |
| --- | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | — | +0.999 | 1 |
| walk | 113 | 13 | 11 | -0.734 | 16 |
| run | 61 | 17 | 13 | -0.741 | 10 |
| wave | 129 | 0 | 0 | +0.742 | 0 |
| jump | 101 | 0 | 0 | +0.346 | 8 |
| idle | 177 | 0 | 0 | +0.650 | 80 |
| nod | 113 | 0 | 0 | +0.742 | 0 |
| dance | 129 | 7 | 7 | -0.260 | 49 |
| sit_down | 73 | 233 | 236 | -10.539 | 0 |
| sit_idle | 181 | 121 | 121 | -6.749 | 47 |
| stand_up | 61 | 217 | 226 | -10.539 | 30 |
| hold_item | 121 | 119 | 119 | -11.942 | 44 |

[Per-frame vertex results](motion_check.json) · [Vertex result text](motion_check.txt)

## Garment/body triangle overlap pairs

| Pose | Samples | Integer peak | Half-frame peak | Minimum signed vertex (mm) | Frame |
| --- | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | — | +0.999 | 1 |
| walk | 113 | 68 | 68 | -0.734 | 16 |
| run | 61 | 51 | 39 | -0.741 | 10 |
| wave | 129 | 0 | 0 | +0.742 | 0 |
| jump | 101 | 0 | 0 | +0.346 | 8 |
| idle | 177 | 0 | 0 | +0.650 | 80 |
| nod | 113 | 0 | 0 | +0.742 | 0 |
| dance | 129 | 39 | 39 | -0.260 | 49 |
| sit_down | 73 | 529 | 530 | -10.539 | 0 |
| sit_idle | 181 | 495 | 495 | -6.749 | 47 |
| stand_up | 61 | 528 | 533 | -10.539 | 30 |
| hold_item | 121 | 410 | 409 | -11.942 | 44 |

[Per-frame triangle results](motion_check_tri.json) · [Triangle result text](motion_check_tri.txt)

## Remaining contacts

The shipped Round 3 file already had legacy overlaps in walk, run and dance and sub-floor clearance in jump when measured at this cadence. Legacy clips still outside the Round 4 gate are walk, run, jump, dance.

The signed witness below is measured at a garment vertex or on an intersected garment triangle. The zone uses the rest garment region and the dominant bone of the nearest master triangle. A positive witness below +0.500 mm identifies a clearance shortfall. Counts and every affected frame are in the two checker JSON files.

| Clip | Witness | Garment / nearest master bone | Frame | Signed clearance (mm) |
| --- | --- | --- | ---: | ---: |
| walk | vertex | shoulder / armpit / LeftArm | 16 | -0.734 |
| walk | vertex | front panel / LeftArm | 14 | -0.670 |
| walk | vertex | shoulder / armpit / RightArm | 22 | -0.500 |
| walk | vertex | back panel / LeftArm | 21 | -0.262 |
| walk | vertex | shoulder / armpit / Spine1 | 22 | -0.207 |
| walk | vertex | back panel / Spine1 | 34 | -0.019 |
| walk | vertex | sleeve / cuff / Spine1 | 22 | +0.022 |
| walk | vertex | front panel / Spine1 | 34 | +0.030 |
| walk | vertex | sleeve / cuff / LeftArm | 22 | +0.083 |
| walk | triangle witness | front panel / LeftArm | 16 | -1.013 |
| walk | triangle witness | shoulder / armpit / LeftArm | 16 | -0.734 |
| walk | triangle witness | back panel / LeftArm | 48 | -0.596 |
| walk | triangle witness | shoulder / armpit / Spine1 | 35 | -0.573 |
| walk | triangle witness | front panel / Spine1 | 35 | -0.573 |
| walk | triangle witness | shoulder / armpit / RightArm | 22 | -0.500 |
| walk | triangle witness | back panel / Spine1 | 35 | -0.387 |
| walk | triangle witness | sleeve / cuff / Spine1 | 22 | -0.058 |
| walk | triangle witness | sleeve / cuff / LeftArm | 22 | -0.037 |
| run | vertex | shoulder / armpit / LeftArm | 10 | -0.741 |
| run | vertex | sleeve / cuff / LeftArm | 24 | +0.019 |
| run | vertex | shoulder / armpit / Spine1 | 24 | +0.032 |
| run | vertex | sleeve / cuff / Spine1 | 24.5 | +0.192 |
| run | vertex | hem / RightUpLeg | 15.5 | +0.491 |
| run | triangle witness | shoulder / armpit / LeftArm | 10 | -0.929 |
| run | triangle witness | sleeve / cuff / LeftArm | 9 | -0.139 |
| jump | vertex | shoulder / armpit / RightArm | 8 | +0.346 |
| dance | vertex | shoulder / armpit / LeftArm | 49 | -0.260 |
| dance | vertex | back panel / LeftArm | 49 | +0.071 |
| dance | vertex | shoulder / armpit / RightArm | 8 | +0.410 |
| dance | triangle witness | shoulder / armpit / LeftArm | 49 | -0.511 |
| dance | triangle witness | back panel / LeftArm | 49 | -0.367 |
| dance | triangle witness | front panel / LeftArm | 49 | -0.147 |
| sit_down | vertex | back panel / LeftForeArm | 0 | -10.539 |
| sit_down | vertex | back panel / RightForeArm | 5 | -10.066 |
| sit_down | vertex | front panel / LeftForeArm | 6.5 | -8.842 |
| sit_down | vertex | hem / LeftForeArm | 3 | -8.419 |
| sit_down | vertex | hem / RightForeArm | 2 | -7.701 |
| sit_down | vertex | back panel / RightArm | 0.5 | -7.634 |
| sit_down | vertex | front panel / LeftArm | 9.5 | -7.476 |
| sit_down | vertex | front panel / RightForeArm | 9 | -6.975 |
| sit_down | vertex | front panel / RightArm | 36 | -6.621 |
| sit_down | vertex | back panel / LeftArm | 6 | -5.819 |
| sit_down | vertex | sleeve / cuff / RightArm | 33 | -5.253 |
| sit_down | vertex | sleeve / cuff / LeftArm | 33.5 | -4.750 |
| sit_down | vertex | sleeve / cuff / Spine1 | 3.5 | -4.684 |
| sit_down | vertex | shoulder / armpit / RightArm | 36 | -3.736 |
| sit_down | vertex | shoulder / armpit / LeftArm | 36 | -3.598 |
| sit_down | vertex | shoulder / armpit / Spine1 | 27.5 | -3.542 |
| sit_down | vertex | hem / Hips | 33.5 | -2.032 |
| sit_down | vertex | hem / LeftUpLeg | 36 | -0.264 |
| sit_down | vertex | hem / RightUpLeg | 31.5 | +0.303 |
| sit_down | triangle witness | back panel / LeftForeArm | 0 | -10.539 |
| sit_down | triangle witness | hem / LeftForeArm | 0 | -10.539 |
| sit_down | triangle witness | back panel / RightForeArm | 4 | -9.897 |
| sit_down | triangle witness | front panel / LeftForeArm | 0.5 | -7.981 |
| sit_down | triangle witness | hem / RightForeArm | 5.5 | -7.907 |
| sit_down | triangle witness | front panel / RightArm | 9 | -7.814 |
| sit_down | triangle witness | front panel / RightForeArm | 9 | -7.185 |
| sit_down | triangle witness | back panel / RightArm | 9.5 | -7.177 |
| sit_down | triangle witness | back panel / LeftArm | 1 | -7.171 |
| sit_down | triangle witness | front panel / LeftArm | 3 | -5.400 |
| sit_down | triangle witness | sleeve / cuff / RightArm | 33 | -5.253 |
| sit_down | triangle witness | shoulder / armpit / RightArm | 33.5 | -4.785 |
| sit_down | triangle witness | sleeve / cuff / LeftArm | 33.5 | -4.750 |
| sit_down | triangle witness | sleeve / cuff / Spine1 | 3.5 | -4.684 |
| sit_down | triangle witness | shoulder / armpit / LeftArm | 27 | -3.910 |
| sit_down | triangle witness | shoulder / armpit / Spine1 | 27.5 | -3.542 |
| sit_down | triangle witness | hem / LeftUpLeg | 33.5 | -1.113 |
| sit_down | triangle witness | hem / RightUpLeg | 35 | -0.845 |
| sit_idle | vertex | front panel / RightArm | 47 | -6.749 |
| sit_idle | vertex | front panel / LeftArm | 67 | -6.446 |
| sit_idle | vertex | sleeve / cuff / RightArm | 29 | -5.047 |
| sit_idle | vertex | back panel / LeftArm | 67 | -4.879 |
| sit_idle | vertex | sleeve / cuff / LeftArm | 25.5 | -4.667 |
| sit_idle | vertex | sleeve / cuff / Spine1 | 71.5 | -4.608 |
| sit_idle | vertex | shoulder / armpit / RightArm | 52.5 | -3.942 |
| sit_idle | vertex | shoulder / armpit / LeftArm | 22.5 | -3.747 |
| sit_idle | vertex | shoulder / armpit / Spine1 | 21 | -2.686 |
| sit_idle | vertex | front panel / RightForeArm | 69 | -2.343 |
| sit_idle | vertex | hem / Hips | 23.5 | -1.706 |
| sit_idle | vertex | front panel / LeftForeArm | 65 | -1.684 |
| sit_idle | vertex | back panel / RightArm | 67 | -1.570 |
| sit_idle | vertex | hem / LeftUpLeg | 12.5 | -0.284 |
| sit_idle | vertex | hem / RightUpLeg | 20 | +0.305 |
| sit_idle | triangle witness | front panel / LeftArm | 56 | -6.130 |
| sit_idle | triangle witness | back panel / LeftArm | 84.5 | -5.757 |
| sit_idle | triangle witness | back panel / RightArm | 61.5 | -5.294 |
| sit_idle | triangle witness | sleeve / cuff / RightArm | 29 | -5.047 |
| sit_idle | triangle witness | front panel / RightArm | 26 | -4.931 |
| sit_idle | triangle witness | shoulder / armpit / RightArm | 1.5 | -4.852 |
| sit_idle | triangle witness | sleeve / cuff / LeftArm | 25.5 | -4.667 |
| sit_idle | triangle witness | sleeve / cuff / Spine1 | 71.5 | -4.608 |
| sit_idle | triangle witness | shoulder / armpit / LeftArm | 17 | -3.805 |
| sit_idle | triangle witness | front panel / LeftForeArm | 66 | -3.508 |
| sit_idle | triangle witness | front panel / RightForeArm | 69 | -2.853 |
| sit_idle | triangle witness | shoulder / armpit / Spine1 | 22 | -2.775 |
| sit_idle | triangle witness | hem / LeftUpLeg | 62 | -1.091 |
| sit_idle | triangle witness | hem / RightUpLeg | 70.5 | -0.905 |
| stand_up | vertex | back panel / LeftForeArm | 30 | -10.539 |
| stand_up | vertex | back panel / RightForeArm | 30 | -9.999 |
| stand_up | vertex | front panel / LeftForeArm | 25 | -8.520 |
| stand_up | vertex | hem / LeftForeArm | 27.5 | -8.501 |
| stand_up | vertex | hem / RightForeArm | 28.5 | -7.611 |
| stand_up | vertex | back panel / RightArm | 29.5 | -7.598 |
| stand_up | vertex | front panel / RightForeArm | 24 | -6.708 |
| stand_up | vertex | front panel / RightArm | 0 | -6.621 |
| stand_up | vertex | front panel / LeftArm | 22 | -6.552 |
| stand_up | vertex | back panel / LeftArm | 26.5 | -6.050 |
| stand_up | vertex | sleeve / cuff / RightArm | 2 | -5.188 |
| stand_up | vertex | sleeve / cuff / LeftArm | 2 | -4.748 |
| stand_up | vertex | sleeve / cuff / Spine1 | 27.5 | -4.639 |
| stand_up | vertex | shoulder / armpit / LeftArm | 13 | -3.984 |
| stand_up | vertex | shoulder / armpit / RightArm | 18.5 | -3.763 |
| stand_up | vertex | shoulder / armpit / Spine1 | 6 | -3.433 |
| stand_up | vertex | hem / Hips | 6 | -1.686 |
| stand_up | vertex | hem / LeftUpLeg | 0 | -0.264 |
| stand_up | vertex | hem / RightUpLeg | 3.5 | +0.294 |
| stand_up | triangle witness | back panel / LeftForeArm | 30 | -10.539 |
| stand_up | triangle witness | hem / LeftForeArm | 30 | -10.539 |
| stand_up | triangle witness | back panel / RightForeArm | 27 | -10.022 |
| stand_up | triangle witness | front panel / LeftForeArm | 30 | -7.941 |
| stand_up | triangle witness | hem / RightForeArm | 28.5 | -7.611 |
| stand_up | triangle witness | front panel / RightArm | 23.5 | -7.603 |
| stand_up | triangle witness | back panel / RightArm | 25 | -7.523 |
| stand_up | triangle witness | back panel / LeftArm | 29 | -7.082 |
| stand_up | triangle witness | front panel / RightForeArm | 23.5 | -6.967 |
| stand_up | triangle witness | front panel / LeftArm | 27.5 | -5.685 |
| stand_up | triangle witness | sleeve / cuff / RightArm | 2 | -5.188 |
| stand_up | triangle witness | sleeve / cuff / Spine1 | 10.5 | -4.870 |
| stand_up | triangle witness | shoulder / armpit / RightArm | 1.5 | -4.796 |
| stand_up | triangle witness | sleeve / cuff / LeftArm | 2 | -4.748 |
| stand_up | triangle witness | shoulder / armpit / LeftArm | 9 | -4.035 |
| stand_up | triangle witness | shoulder / armpit / Spine1 | 12 | -3.510 |
| stand_up | triangle witness | hem / LeftUpLeg | 2.5 | -1.094 |
| stand_up | triangle witness | hem / RightUpLeg | 1 | -0.855 |
| hold_item | vertex | back panel / LeftForeArm | 44 | -11.942 |
| hold_item | vertex | hem / LeftForeArm | 13 | -7.868 |
| hold_item | vertex | front panel / LeftForeArm | 15 | -5.680 |
| hold_item | vertex | front panel / LeftArm | 15 | -4.915 |
| hold_item | vertex | back panel / LeftArm | 44 | -4.585 |
| hold_item | vertex | front panel / RightArm | 55.5 | -4.441 |
| hold_item | vertex | sleeve / cuff / Spine1 | 16 | -4.377 |
| hold_item | vertex | shoulder / armpit / RightArm | 46 | -2.790 |
| hold_item | vertex | shoulder / armpit / Spine1 | 16 | -1.999 |
| hold_item | vertex | shoulder / armpit / LeftArm | 13 | -0.910 |
| hold_item | vertex | sleeve / cuff / LeftArm | 51 | -0.290 |
| hold_item | triangle witness | back panel / LeftForeArm | 44 | -11.942 |
| hold_item | triangle witness | hem / LeftForeArm | 44 | -11.942 |
| hold_item | triangle witness | front panel / LeftForeArm | 38 | -8.085 |
| hold_item | triangle witness | back panel / LeftArm | 28.5 | -7.174 |
| hold_item | triangle witness | front panel / RightArm | 13.5 | -5.135 |
| hold_item | triangle witness | back panel / RightArm | 13.5 | -5.135 |
| hold_item | triangle witness | front panel / LeftArm | 14 | -4.992 |
| hold_item | triangle witness | sleeve / cuff / Spine1 | 16 | -4.377 |
| hold_item | triangle witness | shoulder / armpit / LeftArm | 33.5 | -3.643 |
| hold_item | triangle witness | shoulder / armpit / RightArm | 43.5 | -3.519 |
| hold_item | triangle witness | sleeve / cuff / LeftArm | 21 | -2.360 |
| hold_item | triangle witness | shoulder / armpit / Spine1 | 16 | -2.308 |
| hold_item | triangle witness | sleeve / cuff / RightArm | 54.5 | -0.077 |

[Detailed measurements](dense_check.json)

## New-clip depth comparison

| Clip | Shipped Round 3 minimum signed vertex (mm) | Round 4 minimum signed vertex (mm) |
| --- | ---: | ---: |
| sit_down | -11.634 | -10.539 |
| sit_idle | -7.089 | -6.749 |
| stand_up | -11.634 | -10.539 |
| hold_item | -12.819 | -11.942 |

The fixed action poses also have body-only contact between distal arm and trunk triangles. The rows below exclude triangles sharing a welded rest vertex and include the Round 4 lowest-clearance frames. These pairs quantify the body geometry around the garment contacts.

| Clip | Frame | Left distal arm / trunk pairs | Right distal arm / trunk pairs |
| --- | ---: | ---: | ---: |
| sit_down | 0 | 40 | 54 |
| sit_idle | 47 | 0 | 9 |
| sit_idle | 59 | 0 | 9 |
| stand_up | 30 | 40 | 54 |
| hold_item | 39 | 46 | 0 |
| hold_item | 44 | 46 | 0 |

## Fit and local reproduction

Fitting started from the shipped Round 3 GLB. The initial ±30 mm capped offset bake scanned all 1,260 poses and used a 2 mm margin with Laplacian smoothing. The large contact zones admitted competing nearest-surface directions. A subsequent local search tested alternate offsets and four-influence weight blends, then compared each legacy half frame to the shipped Round 3 contact envelope and attenuated edits where they introduced new contacts. An edge-split trial added 619 triangles and increased overlap counts. The selected candidate retains the original topology. The last all-frame search targeted 160 of the deepest action vertices. Its best hold_item depth improved by another 0.846 mm, while the sit_down overlap peak rose from 530 to 540 and run and jump clearance decreased. The delivered candidate retains the stronger legacy clearance. The selected rest displacement is at most 13.368 mm. The six-view visual review confirmed the short cuffs, gamepad relief, collar and hip-length hem. The action frames show the shirt with the chair or cup. [Fit history](fit_history.json)

Run from the Round 4 directory with the supplied local Blender binary and guard library. The two checker wrappers keep the original measurement functions and extend sampling to every half frame. Cycles CPU produced the review images. The new action renders use their minimum signed vertex frames of **47** for sit_idle and **44** for hold_item. [Render manifest](render_info.json)

```sh
bundle=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
mkdir -p .runtime
export TMPDIR="$PWD/.runtime/" BLENDER_USER_RESOURCES="$PWD/.runtime/blender"
export XDG_CACHE_HOME="$PWD/.runtime/cache" PYTHONDONTWRITEBYTECODE=1
export DYLD_INSERT_LIBRARIES="$bundle/guard.dylib"
export VECLIB_MAXIMUM_THREADS=2 OPENBLAS_NUM_THREADS=2
blender() {
  "$bundle/B/Blender.app/Contents/MacOS/Blender" -b -t 5 -noaudio --factory-startup --disable-autoexec --python-exit-code 1 "$@"
}
blender --python fit_tshirt_r4.py
blender --python check_motion_r4.py
blender --python check_motion_r4.py -- --triangles
blender --python review_tshirt_r4.py
blender --python review_tshirt_r4.py -- --renders
```

GLB SHA-256 `51c03dabd6845642f4b29a809484a95635617bc172a77680eeb2a53b596343e8`  
BLEND SHA-256 `038588e91de05d15ebdddb65597b4a4148b3f4896e0838acd9eab50dfea94cb3`  
Master SHA-256 `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f`  
Corrected motion SHA-256 `3484f5978e94f3e714b320357397d107dd490d56f2eeb64770be292322f9aa2c`  
Actions SHA-256 `e0b71ba549ed60f15a23b925be39cdf0eeef1ba9185fef35572cef8117b984d9`
