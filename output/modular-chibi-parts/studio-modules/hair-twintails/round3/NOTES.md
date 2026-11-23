# Chestnut twin tails · round 3

**Independent visual review PASS. Motion, pixel and export gates PASS.** The final skin has 2,984 triangles. Across 824 poses the largest inside-vertex count and triangle-overlap count were both zero. The minimum signed vertex distance was 4.0807 mm.

## Model and fit

The editable scene starts from the round-two fit. The scalp, bangs and overlapping ponytail lobes were welded into one closed volume. New swept sections form two tapered fringe tips and a broad inner hook with a slimmer outer curl on each side. The ends lift and shift outward through a smooth falloff. The inward-facing cap received extra room so its longer triangle edges clear the convex skull. The fitted master body is present in the Blender scene.

The rear hem rolls up towards the ears. A fresh chestnut gradient and shallow directional normal map follow the main locks and sweep continuously across the back. Each violet band follows the plane fitted to the original attachment. UV charts have eight texels of dilation and a chestnut fill beyond the padding.

## Independent visual review

The independent reviewer inspected the six views and the three close-ups against the original frontal illustration and the round-two fit. The reviewed GLB is identified by SHA-256 `0260c3834267246f6daa1817b36d0814e50cca211203e0ca2f5fa850884089c3`.

- Fringe and hairline PASS. Two tapered central locks overlap. The temples frame the cheeks, and the former forehead slash and scattered dark flecks are absent.
- Ponytails PASS. Both high violet ties, S-shaped silhouettes, outer prongs and inward hooks are legible. The exposed broad tail surfaces are free of long black slits.
- Rear cap and nape PASS. The swept bands cross the center continuously. The reviewer saw no vertical center seam or obvious flat shading on the lower cap.

[Six views](fit_views_v3.png) · [Front hairline](closeups/front_hairline.png) · [Side](closeups/side.png) · [Nape](closeups/nape.png) · [Review record](checks/independent_visual_review.json)

## Motion against the corrected clips

The supplied vertex and triangle scripts ran unchanged against the rigged master and `body-fix/motion_fixed.glb`. The vertex script samples integer frames and the triangle script strides by three. An additional sweep uses their BVH tests, posed master and action-slot binding at every integer and intervening half frame, including the endpoints. Rest is sampled once. Signed distance is the nearest-body-face normal projection at a hair vertex. Triangle counts measure intersecting body–hair pairs.

| Pose | Frame range | Samples | Max vertices inside | Max overlapping pairs | Min signed distance, mm | Frame of minimum |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 1 | 0 | 0 | 4.1473 | 1 |
| walk | 1–57 | 113 | 0 | 0 | 4.1327 | 46.5 |
| run | 0–30 | 61 | 0 | 0 | 4.0807 | 29 |
| wave | 0–64 | 129 | 0 | 0 | 4.1473 | 0 |
| jump | 0–50 | 101 | 0 | 0 | 4.1393 | 9 |
| idle | 0–88 | 177 | 0 | 0 | 4.1420 | 66 |
| nod | 0–56 | 113 | 0 | 0 | 4.1366 | 8 |
| dance | 0–64 | 129 | 0 | 0 | 4.1295 | 8 |

[Supplied vertex results](checks/vertex/motion_check.json) · [Supplied triangle results](checks/triangle/motion_check.json) · [Full integer and half-frame results](checks/motion_integer_half.json)

## Six-view pixel measurements

Both rounds use the same neutral master, orthographic 0.73 m framing, 570 × 570 panels, AgX and three-light Cycles CPU studio at 12 samples. Each pixel-center ray must hit hair before body. Face, eyes, background and the gaps between curls are excluded. The primary count uses encoded sRGB with Rec. 709 weights and a strict luminance threshold of 0.12. The second count first decodes sRGB to linear light. The round-two counts were remeasured from its actual sheet, reproducing every per-view count in its visual_check.json.

| View | Mask R2 | Mask R3 | Near-black R2 | Near-black R3 | Linear < 12% R2 | Linear < 12% R3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| front | 84,258 | 80,015 | 5,860 | 158 | 49,028 | 22,845 |
| three quarter left | 80,566 | 77,797 | 2,990 | 238 | 38,303 | 14,646 |
| three quarter right | 81,417 | 79,255 | 3,305 | 294 | 46,258 | 26,630 |
| left | 75,849 | 73,085 | 1,735 | 13 | 34,354 | 16,452 |
| back | 117,101 | 112,197 | 2,720 | 0 | 59,114 | 34,705 |
| right | 75,735 | 72,477 | 2,982 | 161 | 44,855 | 29,028 |
| total | 514,926 | 494,826 | 19,592 | 864 | 271,912 | 144,306 |

Display near-black pixels fell by 18,728 (95.59%). Their share of the visible hair fell from 3.805% to 0.175%. All six views improved. [Measurements and render hashes](checks/pixels_v3.json)

## Export checks

- One skinned mesh, one primitive, one material and 65 master joints. Bone names, ordered hierarchy and inverse bind matrices match the master. Each vertex has at most 2 normalized positive weights. The module contains no animation, body mesh, camera or lights.
- 2,984 triangles, one connected closed shell, zero open edges, nonmanifold edges, inconsistent windings and nonadjacent self-intersection pairs. Every face in the editable hair mesh uses smooth shading.
- Two embedded 1024 × 1024 PNG maps. Both maps are packed in the editable scene. A UV scan found zero texel centers shared by triangle interiors. The editable and exported meshes have identical sets of model-space positions.
- Khronos glTF Validator 2.0.0-dev.3.10 returned 0 errors and 0 warnings.

[Geometry](checks/geometry.json) · [Editable source](checks/source.json) · [Khronos report](checks/gltf_validator.json)

## Remaining observations

At close-up scale there is a shallow triangular pinch where the side lock meets the temple, and a small angular notch above the right ear along the nape. Some tips remain mildly angular. The curls have fewer overlapping locks and the tie edges are softer than in the illustration. The reviewer accepted the whole-head appearance. All requested gates passed.

## Rebuild

Run these commands from this round3 directory. Blender 5.1.2 supplies bpy, NumPy and OpenVDB. Node loads the locally installed Khronos validator for the format check. The default stages build the files, validate the export, render and measure both rounds, and run both supplied checkers plus the half-frame sweep.

```sh
mkdir -p "$PWD/.work"
export MODULAR_CHECKER_DIR=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
export TMPDIR="$PWD/.work/" TEMP="$PWD/.work" TMP="$PWD/.work"
export XDG_CACHE_HOME="$PWD/.work/cache" BLENDER_USER_RESOURCES="$PWD/.work/blender"
export PYTHONDONTWRITEBYTECODE=1 DYLD_INSERT_LIBRARIES="$MODULAR_CHECKER_DIR/guard.dylib"
"$MODULAR_CHECKER_DIR/B/Blender.app/Contents/MacOS/Blender" -b -noaudio -t 5 --python-exit-code 1 --python "$PWD/fit_hair_r3.py"
```

The source script reads the adjacent round-two blend and original fit helpers. The render stills from the supplied checkers use Cycles CPU through a render-only frame handler. Hashes for the corrected clips, master, checker scripts and raw results are stored with their reports.
