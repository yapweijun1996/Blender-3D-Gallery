# Export measurements

Blender 5.1.2. All pose measurements use both delivered GLBs reimported into an empty scene. Distances below are in millimetres unless indicated.

Detailed world-space witnesses, rest-defined patch sizes, individual triangle IDs and per-clip normalization evidence are in [export_checks.json](export_checks.json). Khronos messages and versions are in [khronos.json](khronos.json).

| File | SHA-256 | Khronos errors / warnings / infos |
| --- | --- | --- |
| body_male_v1.glb | 09d5e03d5da489e350432bb521e59255393a167a2847ae602b7d92a6a102e387 | 0 / 0 / 0 |
| hand_gestures_male.glb | 140e8d616494344c13f23f895e690588a05b671fb6ce72441e152741ff1ad310 | 0 / 0 / 1 |

## Bind mesh

| Measurement | Value |
| --- | --- |
| Meshes / skins / joints / animations | 1 / 1 / 65 / 0 |
| Triangles, whole / left wrist-distal / right wrist-distal | 9974 / 1044 / 1047 |
| Editable source vertices / reimported vertex copies | 4989 / 8171 |
| Height / lowest z, metres | 0.97785366 / -1e-07 |
| Packed textures | Body_Male_BaseColor 1024 × 1024, Body_Male_MetallicRoughness 1024 × 1024, Body_Male_Normal 1024 × 1024 |
| Materials | 1 |
| Skin vertices / unweighted / over four | 8171 / 0 / 0 |
| Max influences / maximum weight-sum error | 4 / 1.1920929e-07 |
| Multi-digit vertices, any / two above 0.2 | 0 / 0 |
| Original non-hand vertex copies / maximum displacement | 15870 / 0.014976 |
| Bind non-adjacent triangle pairs, source / repaired | 31 / 0 |
| Retessellated toe faces / frontal crease offset | 28 toe triangles / 0.015 mm at one source coordinate |
| Repaired hand open edges beyond wrist, left / right | 0 / 0 |
| Repaired hand edges incident to >2 triangles, left / right | 0 / 0 |
| Reimport nearest reflected vertex mean / RMS / maximum | 0.10858 / 0.43433 / 6.6292 |
| Reflected vertex-to-skin mean / RMS / 95th / maximum, source | 0.01396 / 0.12138 / 0.00048 / 2.3426 |
| Reflected vertex-to-skin mean / RMS / 95th / maximum, export | 0.03537 / 0.14586 / 0.22256 / 2.34256 |
| Clip count / rotation channels / scale channels | 18 / 360 / 0 |
| Armature common joint names / largest world bind-matrix component difference | 65 / 0 |

The wrist boundary is |X| = 0.28245 m. Hand triangle counts include every triangle with a vertex beyond the wrist. The non-hand comparison looks up every original vertex copy against the reimported bind surface vertices.

## Re-derived local axes

Curl turns the distal axis toward the palmar pad. Spread turns index/middle toward the thumb and ring/pinky toward the little-finger side. The thumb spread column measures movement toward palmar abduction. Signs are the dominant actual bone-local axes. The JSON retains full unit vectors at all four joints.

| Digit | Curl L | Curl R | Spread L | Spread R | Left / right distal shaft vertices checked |
| --- | --- | --- | --- | --- | --- |
| Index | +X | +X | +Z | -Z | 55 / 55 |
| Middle | +X | +X | +Z | -Z | 55 / 55 |
| Ring | +X | +X | -Z | +Z | 44 / 44 |
| Pinky | +X | +X | -Z | +Z | 46 / 46 |
| Thumb | +X | +X | +Z | -Z | 73 / 73 |

## Rest hands

| Measure | Left | Right |
| --- | --- | --- |
| Palmar normal | [0.282293, -0.103856, -0.95369] | [-0.282294, -0.103856, -0.95369] |
| Degrees from world down | 17.5051 | 17.5052 |
| Thumb root-to-skin-tip direction | [0.52031, -0.8455, -0.12007] | [-0.52031, -0.8455, -0.12007] |
| Thumb head spacings, metacarpal / two visible segments | [17.8425, 20.475, 18.7199] | [17.8425, 20.475, 18.72] |
| Thumb width × thickness at 0.36 shaft fraction | 19.387 × 19.783 | 19.387 × 19.783 |
| Thumb width × thickness at 0.62 shaft fraction | 17.499 × 17.856 | 17.499 × 17.856 |
| Thumb width × thickness at 0.84 shaft fraction | 14.336 × 14.628 | 14.336 × 14.628 |
| Index_Middle free-shaft gap | 7.37946 | 7.37946 |
| Middle_Ring free-shaft gap | 7.06697 | 7.06697 |
| Ring_Pinky free-shaft gap | 8.10093 | 8.10093 |

## Posed surface and collision measurements

Each clip uses one quaternion sample at 0 seconds on the 20 bones of its authored hand. All 18 clips are named below.

Fingertip centroids use the distal 1.8 mm support band. The palmar surface is the underside of the hand between wrist and MCPs. The pulp patch faces forward and volar on the fingertip, lies within 16 mm of its end and within 2.65 mm of the distal support plane. Witness distance considers vertex-to-face and interior edge-to-edge minima in both directions. A face crossing counts as zero separation and is flagged independently.

| Clip | Rotation / scale channels | Non-adjacent pairs, full / L / R | Tip-to-palm, I / M / R / P / T | Thumb above other tips | Pulp gap, OK/pinch | Replay max |
| --- | --- | --- | --- | --- | --- | --- |
| hand_fist_L | 20 / 0 | 0 / 0 / 0 | 4.80256 / 1.53823 / 1.68117 / 3.44553 / 25.42539 | -20.44043 | — | 0.00032 |
| hand_open_relaxed_L | 20 / 0 | 0 / 0 / 0 | 61.22598 / 67.25822 / 63.41854 / 50.83345 / 47.85116 | -5.13732 | — | 0.00026 |
| hand_point_L | 20 / 0 | 0 / 0 / 0 | 61.00643 / 1.53823 / 1.68117 / 3.44553 / 12.13 | -3.44211 | — | 0.00027 |
| hand_thumbs_up_L | 20 / 0 | 0 / 0 / 0 | 4.80256 / 1.53823 / 1.68117 / 3.44553 / 52.72356 | 76.3877 | — | 0.00034 |
| hand_peace_L | 20 / 0 | 0 / 0 / 0 | 60.83745 / 67.47986 / 1.68117 / 3.44553 / 13.06401 | -3.94225 | — | 0.00027 |
| hand_ok_L | 20 / 0 | 0 / 0 / 0 | 26.64953 / 67.55444 / 63.84028 / 50.94144 / 23.27655 | -19.5685 | 0.24799 | 0.00034 |
| hand_grip_small_L | 20 / 0 | 0 / 0 / 0 | 27.01661 / 26.25248 / 26.20601 / 27.82083 / 25.57487 | -9.77153 | — | 0.00056 |
| hand_pinch_L | 20 / 0 | 0 / 0 / 0 | 29.26932 / 62.22981 / 58.3079 / 47.40427 / 26.23002 | 2.99335 | 0.24941 | 0.00035 |
| hand_open_wide_L | 20 / 0 | 0 / 0 / 0 | 60.328 / 67.18436 / 63.15729 / 50.19324 / 50.83339 | -5.31948 | — | 0.00024 |
| hand_fist_R | 20 / 0 | 0 / 0 / 0 | 4.8573 / 1.5383 / 1.68092 / 3.44552 / 25.42568 | -20.44067 | — | 0.00038 |
| hand_open_relaxed_R | 20 / 0 | 0 / 0 / 0 | 61.22595 / 67.25849 / 63.41859 / 50.83336 / 47.85119 | -5.13744 | — | 0.00023 |
| hand_point_R | 20 / 0 | 0 / 0 / 0 | 61.00646 / 1.5383 / 1.68092 / 3.44552 / 12.13 | -3.44199 | — | 0.00038 |
| hand_thumbs_up_R | 20 / 0 | 0 / 0 / 0 | 4.8573 / 1.5383 / 1.68092 / 3.44552 / 52.72371 | 76.38776 | — | 0.00038 |
| hand_peace_R | 20 / 0 | 0 / 0 / 0 | 60.83736 / 67.48008 / 1.68092 / 3.44552 / 13.06402 | -3.94231 | — | 0.00038 |
| hand_ok_R | 20 / 0 | 0 / 0 / 0 | 26.64959 / 67.55465 / 63.84037 / 50.94124 / 23.27675 | -19.5685 | 0.24784 | 0.0003 |
| hand_grip_small_R | 20 / 0 | 0 / 0 / 0 | 27.01674 / 26.2528 / 26.2062 / 27.82121 / 25.57495 | -9.77147 | — | 0.00036 |
| hand_pinch_R | 20 / 0 | 0 / 0 / 0 | 29.26949 / 62.23024 / 58.30797 / 47.40427 / 26.23033 | 2.99329 | 0.24924 | 0.0003 |
| hand_open_wide_R | 20 / 0 | 0 / 0 / 0 | 60.32795 / 67.18456 / 63.15733 / 50.19305 / 50.83337 | -5.31954 | — | 0.0003 |

| Fist metric | Left | Right |
| --- | --- | --- |
| Index pulp to palmar skin | 0.37909 | 0.37949 |
| Middle pulp to palmar skin | 0.40409 | 0.40422 |
| Ring pulp to palmar skin | 0.39776 | 0.39755 |
| Pinky pulp to palmar skin | 0.36943 | 0.36931 |
| Thumb terminal skin to folded digits | 0.47676 | 0.47651 |

| Exterior contact or internal opening | Left | Right |
| --- | --- | --- |
| Thumb terminal to exposed palmar-side folded surface | 0.47676 | 0.47651 |
| Thumb pulp to exposed palmar-side folded surface | 0.47676 | 0.47651 |
| fist side silhouette enclosed holes, mm² | [] | [] |
| thumbs_up side silhouette enclosed holes, mm² | [] | [] |
| ok opposing pulp area within 0.5 mm, thumb / index, mm² | 8.2531 / 6.8648 | 8.2531 / 6.8647 |
| pinch opposing pulp area within 0.5 mm, thumb / index, mm² | 7.9455 / 6.89 | 7.9454 / 6.8901 |
| ok opposing pulp area within 1 mm, thumb / index, mm² | 14.1046 / 11.6762 | 14.1047 / 11.676 |
| pinch opposing pulp area within 1 mm, thumb / index, mm² | 14.7171 / 11.4509 | 14.7171 / 11.451 |

Exterior tests retain folded triangles whose outward normals point toward the underside and whose centres are visible from below on the folded stack with the thumb removed. Opening areas use a direct skin silhouette at 0.25 mm per pixel in the oblique thumb-side view, with 8-connected background and at least four pixels per component. Pulp contact area is estimated by 144 equal-area triangle samples per face and requires opposing normals.

| 40 mm grip cylinder | Left | Right |
| --- | --- | --- |
| World point, mm | [331.0, -23.2212, 505.0] | [-331.0, -23.1913, 504.7537] |
| World axis | [-0.099504, 0.995037, 0.0] | [0.099504, 0.995037, 0.0] |
| Axis-to-skin minimum | 20.19989 | 20.19978 |
| Penetrating triangles | 0 | 0 |
| Largest angle between the nearest per-part support directions, degrees | 193.148 | 193.149 |
| Largest angular gap over all skin projections, degrees | 153.685 | 153.684 |

Full-body crossings use a BVH on the deformed triangles, retaining a pair if the two triangles share no welded rest-position vertex. The additional coplanar test requires positive overlapping interior area. The mandrel also lies inside the convex hull of the complete projected hand when its largest angular gap is below 180°. Coordinate weld precision is 1 micrometre. The cylinder check projects every hand triangle onto the plane perpendicular to the declared axis, including triangle interiors.

The two toe patches retain all original corner coordinates. Diagonal changes alter toe triangle interiors by up to 2.954 mm left and 2.192 mm right in bidirectional 24-subdivision sampling. Measurements and sample counts are in [source_patch_distances.json](source_patch_distances.json).

## Check results

- PASS · static_structure
- PASS · one_material_max1024
- PASS · names_and_parents
- PASS · triangles
- PASS · weights
- PASS · nonhand_rest_position
- PASS · clip_structure
- PASS · all_whole_body_intersections_zero
- PASS · gesture_rest_matches_body
- PASS · ok_L
- PASS · pinch_L
- PASS · fist_contact_L
- PASS · thumbs_up_L
- PASS · grip_gaps_L
- PASS · cylinder_L
- PASS · ok_R
- PASS · pinch_R
- PASS · fist_contact_R
- PASS · thumbs_up_R
- PASS · grip_gaps_R
- PASS · cylinder_R
- PASS · editable_json_and_reimport_consistency
