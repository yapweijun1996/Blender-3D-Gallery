# Studio T-shirt, Round 3

**REWORK.** The delivered GLB has 3,491 garment/body triangle-pair occurrences across the 824 sampled poses. Its minimum signed vertex clearance is -0.798 mm. The gate requires zero inside vertices and zero triangle pairs in every sample, with a signed minimum of +0.500 mm.

[GLB](tshirt_v3.glb) · [Editable BLEND](tshirt_v3.blend) · [Blender fitter](fit_tshirt_r3.py)

The GLB contains **4,699 triangles**, **3,230,440 bytes**, one T-shirt mesh and skin, 65 original joints, at most four normalized influences, and zero animations. The editable BLEND is 4,067,238 bytes and includes the master body as a reference. The Tripo material, three embedded 1024 × 1024 maps, and inverse bind matrices match Round 2 byte-for-byte where stored as binary, and the material definitions match structurally. UV coordinates were carried through as corner attributes. Added edge midpoints interpolate both sides of each UV seam.

The left and right cuffs end at 41.3% and 44.5% of the respective upper arms. The hem spans 393.8–402.4 mm in rest Z. The welded garment has one opening each at the neck, hem and cuffs, and 0 edges incident on more than two faces. Khronos glTF Validator 2.0.0-dev.3.10 reported **0 errors and 0 warnings**. Blender's exporter emitted its inherited shared-texture-sampler notice. The fitter repairs any zero-length tangent it finds in the export using a neighboring tangent projected onto the vertex tangent plane. This leaves the UVs and image bytes intact. [Export checks](export_check.json) · [Khronos report](gltf_validation.json)

## RESULT tables

Both measurements come from a fresh import of this exact GLB. They bind the seven quaternion actions from [motion_fixed.glb](../../../body-fix/motion_fixed.glb) to the master armature at 24 fps, with Blender 5 action slots and the original bone rotation modes. Peak counts are per pose. The columns separate integer and intervening half frames, include endpoints, and use the +0.500 mm floor. The rest row measures one neutral pose.

### Inside garment vertices

| Clip | Samples | Integer peak | Half-frame peak | Min signed vertex (mm) | Min frame |
| --- | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | — | +0.999 | 1 |
| walk | 113 | 13 | 11 | -0.734 | 16 |
| run | 61 | 18 | 13 | -0.798 | 10 |
| wave | 129 | 0 | 0 | +0.742 | 0 |
| jump | 101 | 0 | 0 | +0.319 | 8 |
| idle | 177 | 0 | 0 | +0.650 | 80 |
| nod | 113 | 0 | 0 | +0.742 | 0 |
| dance | 129 | 7 | 7 | -0.260 | 49 |

[RESULT text](motion_check.txt) · [Per-frame JSON](motion_check.json)

### Garment/body triangle-overlap pairs

| Clip | Samples | Integer peak | Half-frame peak | Min signed vertex (mm) | Min frame |
| --- | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | — | +0.999 | 1 |
| walk | 113 | 68 | 68 | -0.734 | 16 |
| run | 61 | 51 | 39 | -0.798 | 10 |
| wave | 129 | 0 | 0 | +0.742 | 0 |
| jump | 101 | 0 | 0 | +0.319 | 8 |
| idle | 177 | 0 | 0 | +0.650 | 80 |
| nod | 113 | 0 | 0 | +0.742 | 0 |
| dance | 129 | 39 | 39 | -0.260 | 49 |

[RESULT text](motion_check_tri.txt) · [Per-frame JSON](motion_check_tri.json)

## Remaining garment contacts

Nearest-body zones use the highest total skin weight of the nearest triangle. Triangle depth is the signed distance of an intersection witness on the garment surface. The per-frame integer and half-frame results remain available in the checker JSON.

| Clip | Sample | Garment / body zone | Frame | Signed witness (mm) |
| --- | --- | --- | ---: | ---: |
| walk | vertex | shoulder / armpit / LeftArm | 16 | -0.734 |
| walk | vertex | front panel / LeftArm | 14 | -0.670 |
| walk | vertex | shoulder / armpit / RightArm | 22 | -0.500 |
| walk | vertex | back panel / LeftArm | 21 | -0.262 |
| walk | vertex | shoulder / armpit / Spine1 | 22 | -0.207 |
| walk | vertex | sleeve / cuff / LeftArm | 34 | -0.022 |
| walk | vertex | back panel / Spine1 | 34 | -0.019 |
| walk | vertex | sleeve / cuff / Spine1 | 22 | +0.022 |
| walk | vertex | front panel / Spine1 | 34 | +0.030 |
| walk | triangle witness | front panel / LeftArm | 16 | -1.013 |
| walk | triangle witness | shoulder / armpit / LeftArm | 16 | -0.734 |
| walk | triangle witness | back panel / LeftArm | 48 | -0.596 |
| walk | triangle witness | shoulder / armpit / Spine1 | 35 | -0.573 |
| walk | triangle witness | front panel / Spine1 | 35 | -0.573 |
| walk | triangle witness | shoulder / armpit / RightArm | 22 | -0.500 |
| walk | triangle witness | back panel / Spine1 | 35 | -0.387 |
| walk | triangle witness | sleeve / cuff / LeftArm | 34 | -0.064 |
| walk | triangle witness | sleeve / cuff / Spine1 | 22 | -0.058 |
| run | vertex | shoulder / armpit / LeftArm | 10 | -0.798 |
| run | vertex | sleeve / cuff / LeftArm | 24 | +0.019 |
| run | vertex | shoulder / armpit / Spine1 | 24 | +0.032 |
| run | vertex | sleeve / cuff / Spine1 | 24.5 | +0.192 |
| run | vertex | hem / RightUpLeg | 15.5 | +0.491 |
| run | triangle witness | shoulder / armpit / LeftArm | 10 | -0.929 |
| run | triangle witness | sleeve / cuff / LeftArm | 9 | -0.139 |
| jump | vertex | shoulder / armpit / RightArm | 8 | +0.319 |
| dance | vertex | shoulder / armpit / LeftArm | 49 | -0.260 |
| dance | vertex | back panel / LeftArm | 49 | +0.071 |
| dance | vertex | shoulder / armpit / RightArm | 8 | +0.410 |
| dance | triangle witness | shoulder / armpit / LeftArm | 49 | -0.511 |
| dance | triangle witness | back panel / LeftArm | 49 | -0.367 |
| dance | triangle witness | front panel / LeftArm | 49 | -0.147 |

[Dense measurements and witness zones](dense_check.json)

## Rest signed clearance

| Region | Min (mm) | P10 | Median | P90 | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| overall | 0.999 | 3.392 | 5.861 | 11.024 | 13.793 | 19.302 |
| back panel | 2.523 | 3.654 | 7.467 | 12.341 | 12.854 | 15.150 |
| collar | 4.466 | 5.255 | 6.323 | 13.392 | 15.740 | 19.302 |
| front panel | 2.174 | 3.290 | 3.793 | 11.798 | 15.784 | 18.163 |
| hem | 2.468 | 4.292 | 6.645 | 11.735 | 13.807 | 18.316 |
| shoulder / armpit | 0.999 | 5.155 | 6.170 | 9.162 | 10.235 | 16.428 |
| sleeve / cuff | 1.985 | 3.073 | 5.972 | 7.265 | 8.810 | 14.608 |

## Master-only baseline

The garment results above use cross-mesh pairs. The neutral master separately contains 318 body-only pairs, consisting of 163 eye/head insert pairs, 60 shorts/leg pairs and 95 foot/toe pairs. The triangle checker reproduced the master-only counts for every integer sample in the corrected-motion baseline. Its half-frame counts use the same adjacency exclusion for exact-position seam copies.

| Clip | Body-only integer occurrences | Body-only half-frame occurrences |
| --- | ---: | ---: |
| rest | 318 | 0 |
| walk | 28,651 | 28,151 |
| run | 17,166 | 16,613 |
| wave | 20,540 | 20,222 |
| jump | 16,201 | 15,889 |
| idle | 28,131 | 27,815 |
| nod | 17,994 | 17,681 |
| dance | 20,075 | 19,771 |

[Master clearance notes and pair categories](../../../body-fix/NOTES.md)

## Fit and reproduction

The fitter imports [Round 2](../round2/tshirt_v2.glb) and reuses its fit helpers. It welds duplicate seam positions for the solve, keeps per-corner UVs, and splits crossed edges over 12 mm and repeatedly crossed armpit spans to support local shaping. Each sweep tests every requested half frame. The largest signed deficit plus up to 2 mm margin is pulled back through the blended skin transform to rest space, clamped to 30 mm, and used as the floor for Laplacian smoothing. Candidate updates use triangle-interior contact witnesses and localized, smoothed skin-weight changes. The candidate selection favors fewer and shallower contacts within the rest clearance cap.

Round 2 had 133,633 cumulative garment triangle-pair occurrences with the corrected clips and a minimum signed vertex distance of −6.110 mm. The selected Round 3 candidate is pass 16. [Fit history](fit_history.json)

Run these commands from the Round 3 folder with the provided Blender 5.1.2 bundle and guard library. The run directory keeps Blender temporary data in this folder.

```sh
bundle=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
mkdir -p .runtime
export TMPDIR="$PWD/.runtime/" BLENDER_USER_RESOURCES="$PWD/.runtime/blender"
export XDG_CACHE_HOME="$PWD/.runtime/cache" PYTHONDONTWRITEBYTECODE=1
export DYLD_INSERT_LIBRARIES="$bundle/guard.dylib"
blender() {
  "$bundle/B/Blender.app/Contents/MacOS/Blender" -b -t 4 -noaudio --factory-startup --disable-autoexec --python-exit-code 1 "$@"
}
master=../../../master/GJH_Chibi_Master_rigged.blend
motion=../../../body-fix/motion_fixed.glb
blender --python fit_tshirt_r3.py
blender --python fit_tshirt_r3.py -- --verify
blender --python motion_check.py -- "$master" "$motion" tshirt_v3.glb "$PWD"
blender --python motion_check_tri.py -- "$master" "$motion" tshirt_v3.glb "$PWD"
blender --python fit_tshirt_r3.py -- --renders
```

GLB SHA-256 `6d21284ee87de7cd95c6ce498ff8a7a1e27e5cb8e609f819764e91e12095e4ee`  
BLEND SHA-256 `29249f09ecdd44fbfcf1b7b4a66cbcda68ca2938a6f0ec6de650b03958f2b846`  
Corrected motion SHA-256 `3484f5978e94f3e714b320357397d107dd490d56f2eeb64770be292322f9aa2c`  
Master SHA-256 `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f`

## Render evidence

Cycles CPU captures from the reimported GLB and corrected clips. The six-view plate shows the collar, short sleeve cuffs and hip-length hem from the front, back and both sides. Render frames and image hashes are in the manifest.

[Six views](six_views.png) · [Walk 13.5](walk.png) · [Run 9](run.png) · [Wave 25](wave.png) · [Jump 20](jump.png) · [Render manifest](render_info.json)

Independent visual inspection verified the GLB and all five PNG hashes against the manifest. The collar, short cuffs, hip-length hem, lilac trim and controller relief remain identifiable in the final renders. Small hem ripples and a localized crease below an armhole remain. The arms obscure part of the sleeve/body boundary in walk and run. The numerical collision gate remains open.
