# Studio female body v1

The body is the supplied Tripo Studio female character. The source and reference were read locally. Model construction, skinning, pose fitting, image processing and rendering used the supplied Blender 5.1.2 installation. Khronos validation used the repository's installed offline validator.

## Files and playback

| File | Use |
| --- | --- |
| [body_female_v1.glb](body_female_v1.glb) | Neutral skinned body with embedded PBR textures |
| [hand_gestures_female.glb](hand_gestures_female.glb) | Rotation clips on a skeleton-only node hierarchy. Match targets to the body by exact bone name |
| [body_female_v1.blend](body_female_v1.blend) | Packed, editable body and rig, in the neutral pose. The Action Editor contains 18 pose assets |
| [hand_gestures_female.json](hand_gestures_female.json) | One XYZ Euler delta in degrees for each of the 20 bones on the active hand. Also contains rest axes and both grip fixtures |
| [contact_sheet.png](contact_sheet.png) · [gesture_closeups.png](gesture_closeups.png) | Palmar, dorsal and radial views of both hands and enlarged contact views |
| [check.log](check.log) · [audit.json](audit.json) | Reimported geometry, influence, collision, closest-surface witnesses, clip and validator results |
| [motion_review.json](motion_review.json) · [appearance_check.json](appearance_check.json) | Per-clip deformation measurements, capture hashes, texture and mirror comparisons |

In Blender 5, assign both the action and its matching action slot. Reset unkeyed finger rotations to neutral when switching from a previous isolated pose. The JSON is in native bind-local space. For bone rotation, convert its XYZ Euler delta to a quaternion. The GLB stores quaternion samples. An armature-only glTF hierarchy can appear as empties in an importer that uses a skin to recognize bones. Map the library channels to the body's named joints, or use the actions in the supplied blend. The seven whole-body motions are test inputs and remain in their original library.

## Construction and contact testing

The repair retains the Studio surface through the symmetric wrist cut at absolute Blender X of 0.2862 m, plus dorsal forearm-weighted anchors distal to that plane. It interpolates source UVs, normals and influences at the cut. Source bones and vertices are first brought into a shared metre-scaled world frame. The original index-to-pinky knuckle line supplies the wrist roll. The distal palm and five digits use new connected surface loops. The thenar side opens into the thumb shaft, with a proximal and a distal phalanx, a metacarpal and a terminal rig helper. Each free shaft has one finger-chain owner. Skin blends longitudinally around each hinge. The old body's wrist fade, digit ownership, bind-frame alignment and evaluated-surface checks informed this repair.

One material covers both body and hands. The hand surface has continuous UVs in a 24 × 24 skin swatch shared in the existing atlas. Base colour, tangent-space normal and channel-packed roughness/metallic remain distinct PBR inputs. Outside this swatch, all three exported maps match the corresponding Blender-downsampled source exactly across 1,048,000 pixels per map. The actual source dimensions are 4096² colour and 2048² normal and roughness/metallic. All outputs are 1024².

Contact patches are defined once in bind space on the distal, forward-facing volar pad, then carried through skinning. The surface routine tests vertex/triangle and interior edge/edge cases. The fist also checks the four long-finger caps against palmar skin and the thumb pad against folded digits. A positive submillimetre clearance models a pressed contact on a rigidly skinned surface. The collision check separately tests every nonadjacent triangle pair in the whole body for each clip, excluding pairs sharing a geometrically welded bind vertex. The cylinder test uses the minimum axis-to-triangle distance over the hand, including triangle interiors, for a 20 mm radius.



## Body and rest frame

| Measurement | Final value |
| --- | --- |
| Static body | 1 mesh, 1 skin, 65 joints, 0 clips, 1 material, 67 nodes, 4,183,108 bytes |
| Pose library | 0 meshes, 65 joints, 66 nodes, 18 clips, 94,528 bytes. One quaternion key at 0 s on each of 20 digit bones per clip, 360 rotation channels total |
| Editable source | 4,996 mesh vertices, 2 scene objects, 3 packed images, 18 one-frame action assets, neutral active pose |
| Triangles | Source 8,901 → 9,987 total. Conservative hand count including all triangles touching the wrist-distal half-space is 1,361 L / 1,396 R. Centroid count is 1,315 L / 1,381 R |
| Exported vertex count | 8,639 after the Blender default glTF import, including seam splits |
| Dimensions | Height 0.977000713 m, sole Z -0.0000000663 m. Bounds [-0.416392, -0.186414, -0.0] to [0.416392, 0.186414, 0.977001] m. T-pose faces −Y, anatomical left is +X |
| Skinning | Maximum 4 influences, 0 unweighted, 0 above four. Weight sum 0.9999998882–1.0000001192. Max sum error 1.19e-07 |
| Finger bleed | Source 926 multi-chain vertices, including 211 with second digit above 0.2. Final 0 multi-chain vertices at any positive weight, 0 above 0.2, max second-digit weight 0. Independent geometric shaft samples with foreign weights 0 of 453 per side |
| Source-position preservation | 14,817 source vertices before the symmetric cut, 14,752 at or before the anatomical wrist and 14,732 dominated by a non-hand joint. Each test had max displacement 0.000239 mm, 0 over 0.5 mm |
| Wrist cut interpolants | Maximum distance to original surface 0.000201 mm |
| Unchanged body triangles | 7,262 of 7,262 correspond, UV component error 0.0, corner normal error p99 0.02798°, maximum 0.50590° |
| Rig compatibility | 65 matching joint names, 0 parent differences, max exported local/world rest matrix component difference 0. Inverse-bind identity max error 5.53e-07 |
| Playback accuracy | JSON vs clip GLB max skin-point difference 0.000568 mm across 18 clips. Rest matching max 0.000423 mm |
| Khronos validation | Body 0 errors / 0 warnings / 0 infos / 0 hints. Library 0 errors / 0 warnings, 1 informational UNUSED_OBJECT on the standalone skin, 0 hints. Both validator JSON reports are included |

| Rest measurement | Left | Right |
| --- | --- | --- |
| Wrist roll applied about Blender X (degrees) | -54.8458 | -54.8880 |
| Palmar normal off −Z (degrees) | 0.67086 | 0.31153 |
| Thumb off −Y (degrees) | 25.08106 | 25.08106 |
| Wrist to mean knuckle (mm) | 63.20486 | 70.59095 |
| Thumb CMC to skin tip (mm) | 53.96473 | 53.96486 |
| Palmar unit normal | (0.0117, 0.0000, -0.9999) | (0.0054, 0.0000, -1.0000) |
| Thumb direction | (0.4199, -0.9057, -0.0583) | (-0.4199, -0.9057, -0.0584) |
| CMC / proximal / distal pivot intervals (mm) | 16.000 / 18.000 / 18.000 | 16.000 / 18.000 / 18.000 |

| Thumb width × depth, mm | Left | Right |
| --- | --- | --- |
| 30% from CMC | 16.701 × 20.234 | 16.741 × 20.234 |
| 50% from CMC | 17.895 × 17.213 | 17.895 × 17.213 |
| 70% from CMC | 15.443 × 14.721 | 15.443 × 14.721 |
| 85% from CMC | 14.238 × 13.328 | 14.238 × 13.328 |
| 95% from CMC | 11.943 × 11.080 | 11.943 × 11.080 |


## Finger axes

Each local +Y axis follows its repaired shaft. Projecting world −Z perpendicular to that shaft gives the positive local Z direction. The right-hand cross product of the shaft and projected down direction gives positive local X. Positive local X curl moves a shaft toward the palm on both hands. Positive local Z spread moves local +Y toward local −X. Mirror lateral spread and axial twist at the opposite hand. The thumb also uses Y-axis twist to oppose its pad. The table gives Blender world-space unit rotation axes, rounded across joints 1–4. The JSON records all 40 bones individually.

| Chain | Left curl +X | Right curl +X | Left spread +Z | Right spread +Z |
| --- | --- | --- | --- | --- |
| Index | (0.1564, 0.9877, 0.0000) | (0.1564, -0.9877, 0.0000) | (-0.0247, 0.0039, -0.9997) | (0.0247, 0.0039, -0.9997) |
| Middle | (0.0523, 0.9986, 0.0000) | (0.0523, -0.9986, 0.0000) | (-0.0250, 0.0013, -0.9997) | (0.0250, 0.0013, -0.9997) |
| Ring | (-0.0523, 0.9986, 0.0000) | (-0.0523, -0.9986, 0.0000) | (-0.0250, -0.0013, -0.9997) | (0.0250, -0.0013, -0.9997) |
| Pinky | (-0.1736, 0.9848, 0.0000) | (-0.1736, -0.9848, 0.0000) | (-0.0246, -0.0043, -0.9997) | (0.0246, -0.0043, -0.9997) |
| Thumb | (0.9073, 0.4206, 0.0000) | (0.9073, -0.4206, 0.0000) | (-0.0252, 0.0544, -0.9982) | (0.0252, 0.0544, -0.9982) |


## Contact and grip measurements

| Surface measurement, mm | Left | Right |
| --- | --- | --- |
| pinch thumb pulp to index pulp | 0.37650 | 0.36872 |
| ok thumb pulp to index pulp | 0.37027 | 0.36968 |
| Fist index pulp to palm | 0.22026 | 0.21999 |
| Fist middle pulp to palm | 0.22042 | 0.22019 |
| Fist ring pulp to palm | 0.22019 | 0.22011 |
| Fist pinky pulp to palm | 0.22094 | 0.22076 |
| Fist thumb pulp to palm | 4.27465 | 4.28013 |
| Fist thumb pulp to folded index | 6.42355 | 6.05060 |
| Fist thumb pulp to folded middle | 0.29890 | 0.29841 |
| Fist thumb pulp to folded ring | 12.01669 | 13.88402 |
| Fist thumb pulp to folded pinky | 29.16477 | 29.52268 |
| Thumbs-up center above highest other tip center | 56.40811 | 56.39875 |
| Thumbs-up tip surface above other tip surfaces | 55.49765 | 55.50051 |

| Clip | Side | Pad normal dot product | Thumb area within 1 mm (mm²) | Index area within 1 mm (mm²) |
| --- | --- | --- | --- | --- |
| pinch | L | -0.88593 | 5.5326 | 3.9039 |
| pinch | R | -0.89142 | 10.1916 | 9.2478 |
| ok | L | -0.95322 | 5.5326 | 3.9039 |
| ok | R | -0.95246 | 5.8738 | 6.5757 |

The 15–30 mm grip gap follows the worked library’s fingertip-to-palmar-skin definition. Both pad-surface gaps and tip-center gaps are inside the specified interval. The independent cylinder-fit measurement covers each triangle. The wider thumb/index opening is also reported.

| Grip-small measurement, mm | Left | Right |
| --- | --- | --- |
| Index pulp to palm | 22.63094 | 22.63048 |
| Middle pulp to palm | 23.12119 | 23.11937 |
| Ring pulp to palm | 22.48465 | 22.48451 |
| Pinky pulp to palm | 21.29716 | 21.29684 |
| Thumb pulp to palm | 20.78349 | 20.75707 |
| Index terminal center to palm | 28.78982 | 28.77842 |
| Middle terminal center to palm | 28.72581 | 28.72400 |
| Ring terminal center to palm | 28.55289 | 28.55550 |
| Pinky terminal center to palm | 27.60895 | 27.60860 |
| Thumb terminal center to palm | 28.45506 | 27.67528 |
| Thumb/index pulp opening | 48.62318 | 54.84169 |
| Palm nearest skin to cylinder axis | 22.73246 | 22.73233 |
| Index nearest skin to cylinder axis | 21.11200 | 21.14434 |
| Middle nearest skin to cylinder axis | 21.27777 | 21.27750 |
| Ring nearest skin to cylinder axis | 20.96011 | 20.95986 |
| Pinky nearest skin to cylinder axis | 21.31514 | 21.31501 |
| Thumb nearest skin to cylinder axis | 20.75293 | 21.81820 |
| 40 mm gauge radial clearance | 0.75293 | 0.95986 |
| Penetrating triangles | 0 | 0 |
| Gauge center, world mm | [331, -20, 506] | [-331, -20, 506] |
| Gauge axis unit vector | [-0.029963, 0.998752, -0.03995] | [0.029963, 0.998752, -0.03995] |


## All 18 library poses

The four long fingertips touch the palm on fist and thumbs-up. Point releases the index, and peace releases index and middle. The open gestures use separate spread and curl amounts. The pinch brings three free digits toward the palm. OK leaves those digits extended. The full log includes the actual world-space coordinates, witness triangles and per-digit measurements.

| Gesture | Whole-body intersections L / R | Max skin movement L / R, mm | Non-hand drift L / R, mm | Euler JSON replay max L / R, mm |
| --- | --- | --- | --- | --- |
| fist | 0 / 0 | 88.020721 / 88.02179 | 0.000189 / 0.000189 | 0.000534 / 0.000503 |
| open_relaxed | 0 / 0 | 28.32296 / 28.323328 | 0.000189 / 0.000189 | 0.000534 / 0.000551 |
| point | 0 / 0 | 88.020721 / 88.02179 | 0.000189 / 0.000189 | 0.000534 / 0.000486 |
| thumbs_up | 0 / 0 | 88.020721 / 88.02179 | 0.000189 / 0.000189 | 0.000534 / 0.000486 |
| peace | 0 / 0 | 86.212967 / 83.075653 | 0.000189 / 0.000189 | 0.000534 / 0.000486 |
| ok | 0 / 0 | 78.045212 / 76.979195 | 0.000189 / 0.000189 | 0.000534 / 0.000486 |
| grip_small | 0 / 0 | 73.724464 / 73.724724 | 0.000189 / 0.000189 | 0.000534 / 0.000568 |
| pinch | 0 / 0 | 78.127228 / 75.891113 | 0.000189 / 0.000189 | 0.000534 / 0.000515 |
| open_wide | 0 / 0 | 9.842602 / 9.842614 | 0.000189 / 0.000189 | 0.000534 / 0.000497 |


## Motion and joint deformation

Seven original quaternion clips, 415 integer frames per binding mode, 830 evaluations total. The direct test binds matching bone names. The second conjugates the source pose delta through source and target world-rest bases. Both use Blender 5 action slots. Pose-bone rotation modes are preserved. All 4,650 coincident seam pairs stayed at 0 mm separation in both passes and in the stress pose.

| Clip | Frames | Direct max edge stretch × | Rest-adjusted max edge stretch × | Rest-adjusted floor Z min / max, mm |
| --- | --- | --- | --- | --- |
| walk | 57 | 2.4016 | 2.4180 | -17.580 / -0.022 |
| run | 31 | 5.2963 | 5.3493 | -2.228 / 16.445 |
| wave | 65 | 2.0315 | 2.0300 | -0.000 / -0.000 |
| jump | 51 | 2.6462 | 2.6557 | -18.526 / 217.405 |
| idle | 89 | 2.1007 | 2.0964 | -0.000 / -0.000 |
| nod | 57 | 2.0315 | 2.0300 | -0.000 / -0.000 |
| dance | 65 | 1.7341 | 1.7392 | -1.289 / 1.374 |

Four rest-adjusted frames were rendered and inspected. [Walk 15](motion_walk_015.png) · [Run 8](motion_run_008.png) · [Wave 19](motion_wave_019.png) · [Jump 9](motion_jump_009.png).

| Joint | Test bend | Max local edge stretch × |
| --- | --- | --- |
| shoulder | 75° | 1.6835 |
| elbow | 95° | 2.0701 |
| hip | 65° | 2.2745 |
| knee | 100° | 2.0331 |

The simultaneous bend is visible in the [stress frame](motion_joint_stress.png). Per-frame render metrics, local edge ratios, worst edges, capture settings and file digests are in [motion_review.json](motion_review.json).


## Visual assessment and limits

Matched frontal images preserve the Studio face, outfit and legs. On 41,118 mutually opaque non-hand pixels, the mean absolute difference is 0.388 / 255, P95 1.667 and P99 4.333. The left panel shows the Studio input and the right shows the repaired body. [Body comparison](body_comparison.png)

The projected thumb-cap traversal from the index center toward the middle center measures 88.33% L and 87.49% R. The final fist crosses the index and reaches the lower edge of the folded middle finger. The palmar and oblique views show a small recess beneath the bent proximal fingers. Finger pads remain adjacent to the palm. The thumb tapers and has two visible articulated segments, with mild faceting at macro scale. The palm heel retains a shallow angular transition at the preserved wrist, most visible in wave. The thumb remains diagonally forward and the palm is nearly horizontal.

The 100° knee bend shows local faceting. The source torso has a short edge that stretches about 5.35× in run, also present in the untouched Studio character. The original walk and jump motions can lower the sole approximately 17.58 and 18.53 mm below rest ground. Contact and whole-body intersection results cover the 18 single-frame finger clips. The seven motion tests cover integer frames and four rendered motion samples plus the stress pose.

The welded hand regions have 0 nonmanifold edges. Elsewhere the source and export both have 8 boundary edges and 9 edges incident to three faces. This module retains those body features. The editable mesh uses reconstructed hand loops and triangles in the preserved Studio body. High-magnification shots show the triangle budget.

| Mirror-to-surface statistic, mm | Source mean / P95 / max | Final mean / P95 / max |
| --- | --- | --- |
| whole | 0.074542 / 0.457723 / 3.122054 | 0.068546 / 0.381906 / 3.122054 |
| hands | 0.003256 / 0.000219 / 1.686753 | 0.007157 / 0.000423 / 1.468496 |

Mirror statistics use world X=0 and the closest opposite surface for each unique rest point. The exact method is recorded in [appearance_check.json](appearance_check.json). The [independent visual review](visual_review.json) identifies the evidence images and their hashes.


## Offline reproduction

Run from this directory with the supplied guarded Blender executable. The wrapper sets its temporary directory inside the workspace. build_body.py reads the Studio input. apply_library.py reads the delivered hand_gestures_female.json, adds the action assets to the blend and exports the separate library. A clean body rebuild from the read-only Studio GLB reproduced the delivered GLB SHA-256 exactly.

```sh
./run_blender.sh build_body.py
./run_blender.sh apply_library.py
./run_blender.sh audit_female.py
./run_blender.sh check_appearance.py
./run_blender.sh motion_review.py
./run_blender.sh gesture_views.py
```

The numerical audit reuses the local round-two surface-distance implementation and the repository’s installed Khronos validator. The previous hand repair and the gesture library remain read-only. The original assets, generated reference, motion input and outputs are identified below.

| File | SHA-256 |
| --- | --- |
| studio_rigged.glb | `a4e3df41cb970ec52fdc5b21c4ba3093171af1caa5161b817d2eb4c00b9ac916` |
| female-body-tpose.png | `a733a2722f75b7eeb7524b2ce4f322d7b8e03a5c38fda6072a9b1c6cda8d46cc` |
| motion.glb | `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410` |
| body_female_v1.glb | `31e16b400988b18c18ee30e988ee28a42b0b968073b0f12c5afda2dc678143f6` |
| body_female_v1.blend | `4ba9dc515a16496312db06bd089467aee6334452a60ee5cf67edec2bea0b870f` |
| hand_gestures_female.glb | `c692ca7398bea37a9890016be1c361100b06a9d70fe968060a5fa2e6028d1965` |
| hand_gestures_female.json | `1f96de044c802a0ca5698441655e47f64761f36d401ef6f62243ae5f24e760bc` |
| contact_sheet.png | `21de35b640b6254d9b3b14f015bd94112c95d20040c947d87c46e2f87e1d6f7b` |
| gesture_closeups.png | `ae982ca2da01a39832cb8390e6645260880d37870e24a0a9575c6954601bea2a` |
| body_comparison.png | `56817e1393a3a3fd59b010f3caa8e6109096d1ffb0d45596fda2284f650987c8` |

