# Studio male chibi body v1

The Blender body faces −Y and stands 0.977854 m high. Both repaired palms face down. The thumbs project forward and have independently articulating proximal and distal segments. The static body and single-frame gesture library share 65 Mixamo joint names, parent relationships and joint rest transforms.

## Files

| Artifact | Use |
| --- | --- |
| [Static body](body_male_v1.glb) | One mesh, one material, one skin, 65 joints, no animation |
| [Gesture library](hand_gestures_male.glb) | Armature only, 18 one-frame clips, 20 finger/thumb rotation channels per clip |
| [Editable Blender source](body_male_v1.blend) | Packed material maps, skinned surface, armature and 18 pose Actions, opens at rest |
| [Pose data](hand_gestures_male.json) | Each value is a Blender bone-local XYZ Euler rest delta in degrees |
| [Gesture contact sheet](contact_sheet.png) · [hand closeups](views/hand_closeups.png) | All nine shapes on both hands from palm, dorsal and thumb side, plus detailed contact views |
| [Run](motion/run_frame_008.png) · [wave](motion/wave_frame_019.png) · [jump](motion/jump_frame_009.png) · [joint bends](motion/joint_bends_frame_000.png) | Textured Cycles CPU renders of the reimported body |
| [Check log](audit/check.log) · [full numerical audit](audit/export_checks.json) · [Khronos results](audit/khronos.json) | Skin, geometry, poses, exact triangle witnesses, playback and binary validation |
| [Independent visual review](views/VISUAL_REVIEW.md) · [motion audit](motion/motion_check.json) · [raw animation compatibility](motion/runtime_binding.json) | Capture settings, inspected views, movement measurements and limitations |

## Modeling and pose authoring

The read-only input was the Studio Best Quality, quad-retopologized male body with the Mixamo preset. The input GLB contained 9,374 triangles. Its decoded base color was 4096 × 4096. Its metallic–roughness and normal images were 2048 × 2048. The reference was the supplied front-view bald male in white shorts.

The repair retains the Studio surface through a cut at |X| = 0.28245 m. It reuses the original wrist contour, rolls its distal section into the anatomical hand frame, builds a tapered wrist-to-palm transition and retopologizes the distal palm, webs and five digit shafts. The two hands retain independent skinning. Each thumb has a basal metacarpal, two visible phalanges and the original named terminal joint. A 35 mm wrist weight transition carries the source forearm weights into the heel. All finger-shaft weights are confined to the owning chain and its palmar attachment.

The existing Astra hand repair, gesture authoring and round-two surface checks supplied the method for orienting the palm, assigning separate digit ownership, aligning the curl plane and measuring fixed bind-space pulp patches. The male gestures were fitted against this male surface. The fist fit used the palmar-visible exterior of the folded fingers, with a separate check for a hollow side silhouette. Pinch and OK were fitted over finite opposing pulp triangles. Grip-small was fitted against an actual 40 mm transverse cylinder. The right rotations were derived by reflecting through the measured left and right joint rest frames, then tested separately. The library contains rotations only. The three maps share one packed PBR material. A sampled wrist color transition runs into a shared distal skin swatch to keep deformed knuckle normals continuous.

The imported bind mesh contained 31 non-adjacent triangle crossings outside the hands. Repairing the toe diagonals and a near-coplanar facial crease was necessary for the requested full-body collision test. Both the resulting vertex displacement and toe triangle interior changes are recorded in the measurements below.

## Playback

Use the names `hand_{gesture}_L` and `hand_{gesture}_R`. In Blender 5 assign the imported Action **and its slot** to the target armature. The matched armature has quaternion pose bones. To consume the JSON, convert its degree triples to XYZ Euler rotations and then to unit quaternions. Blender frame 1 corresponds to the exported single sample at 0 s. When layering over locomotion, apply the chosen hand channels to the matching bones; restore the previous hand state when leaving the gesture.

The 25 body and wrist rest bases were aligned with the existing motion skeleton while retaining the male joint pivots and all 40 authored digit frames. The original motion GLB keys translation, rotation and scale on every joint, 195 channels per clip. Direct assignment of its imported Blender Actions was tested. A game engine consuming raw glTF tracks should transfer **bind-relative** joint transforms to preserve male proportions. Replacing the male joint translations with the source's absolute tracks shifts the neutral skin by **48.733 mm RMS and 137.658 mm maximum**. The raw replay and bind-relative comparison are reproduced in [check_runtime_binding.py](motion/check_runtime_binding.py).

## Joint deformation

All seven original Actions were evaluated at every integer frame using their action slots. The direct pass sampled 415 frames and the bind-relative pass sampled another 415. The separate stress pose bends the left shoulder 58°, elbow 82°, hip 62° and knee 88°. The right side was simultaneously posed at 34°, 32°, 12° and 20°, respectively; signed axes are in the motion log. The four rendered frames use direct Action playback for run, wave and jump, and the explicit stress pose for the fourth image.

The reimported mesh has **4198 rest-coincident seam pairs**. Maximum separation was **0 mm** across the tested clips and the stress pose. The edge-strain pass measured 17,705 edges at least 0.5 mm long. Stretch ratio is posed length divided by bind length.

| Original clip | Frames | Maximum seam separation (mm) | Lowest skin Z (mm) | Peak whole-body edge stretch | Peak wrist-strip stretch |
| --- | ---: | ---: | ---: | ---: | ---: |
| walk | 57 | 0.000000 | -36.257 | 2.362199× | 2.362199× |
| run | 31 | 0.000000 | -21.118 | 5.075255× | 2.282394× |
| wave | 65 | 0.000000 | -0.000 | 1.799191× | 1.189246× |
| jump | 51 | 0.000000 | -21.097 | 2.888512× | 1.000072× |
| idle | 89 | 0.000000 | -0.000 | 1.800703× | 1.000124× |
| nod | 57 | 0.000000 | -0.000 | 1.792674× | 1.000060× |
| dance | 65 | 0.000000 | -0.712 | 1.871089× | 1.000074× |

The four images show continuous shoulders, elbows, hips and knees. Run retains the source's spread leading fingers, and the knee and lower abdomen show small creases at high flexion. The 5.075255× run peak is on a lower-back edge at frame 3. The corresponding Studio edge reaches 5.075265×. Walk, run, jump and dance can cross the nominal ground plane at the minima above. The still-pose collision checks cover the 18 authored poses. Interpolated transitions between arbitrary gestures have not been collision-tested.

## Appearance and remaining limits

The design image is a single front view. The comparison below checks retention of the supplied Studio body's look with matching textured renders. RGB differences are mean absolute channel errors on an 8-bit scale. The final export retains a low-poly silhouette, most visible at the fingertips and folded knuckles. A small shading transition at the extreme wrist and a mild knee indentation remain visible in close views. The grip cylinder has a measured clearance of about 0.20 mm at its closest surface. The contact poses retain a small positive separation so the pads appear to meet without meshing through each other.

- head — pixels 39206, mean absolute 8bit channel error 0.47083779693584316, p95 absolute 8bit channel error 2.0, max absolute 8bit channel error 153.0.
- eyes — pixels 12987, mean absolute 8bit channel error 0.8297784964451631, p95 absolute 8bit channel error 4.0, max absolute 8bit channel error 47.0.
- torso shorts legs feet — pixels 44214, mean absolute 8bit channel error 0.2318496403853983, p95 absolute 8bit channel error 1.0, max absolute 8bit channel error 50.0.

## Rebuild

Run from this directory using the provided guarded Blender executable. The JSON is the authoritative pose source for the rebuild. The scripts preserve the original Studio GLB and rebuild the mesh from it. Blender stores its working data in this directory.

```sh
./run_blender.sh scripts/build_body.py
./run_blender.sh scripts/export_module.py
./run_blender.sh audit/verify_exports.py
node audit/validate.cjs
```

The official locally installed Khronos validator is used solely for binary validation. A separate clean rebuild produced a byte-identical static GLB. The regenerated animation GLB contained the same 65 joint transforms and all 360 identical quaternion samples and timestamps. Blender can serialize the channel order differently. [Rebuild comparison](audit/rebuild.json)

## Detailed hand and export measurements

Blender 5.1.2. All pose measurements use both delivered GLBs reimported into an empty scene. Distances below are in millimetres unless indicated.

Detailed world-space witnesses, rest-defined patch sizes, individual triangle IDs and per-clip normalization evidence are in [export_checks.json](audit/export_checks.json). Khronos messages and versions are in [khronos.json](audit/khronos.json).

| File | SHA-256 | Khronos errors / warnings / infos |
| --- | --- | --- |
| body_male_v1.glb | 09d5e03d5da489e350432bb521e59255393a167a2847ae602b7d92a6a102e387 | 0 / 0 / 0 |
| hand_gestures_male.glb | 140e8d616494344c13f23f895e690588a05b671fb6ce72441e152741ff1ad310 | 0 / 0 / 1 |

### Bind mesh

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

### Re-derived local axes

Curl turns the distal axis toward the palmar pad. Spread turns index/middle toward the thumb and ring/pinky toward the little-finger side. The thumb spread column measures movement toward palmar abduction. Signs are the dominant actual bone-local axes. The JSON retains full unit vectors at all four joints.

| Digit | Curl L | Curl R | Spread L | Spread R | Left / right distal shaft vertices checked |
| --- | --- | --- | --- | --- | --- |
| Index | +X | +X | +Z | -Z | 55 / 55 |
| Middle | +X | +X | +Z | -Z | 55 / 55 |
| Ring | +X | +X | -Z | +Z | 44 / 44 |
| Pinky | +X | +X | -Z | +Z | 46 / 46 |
| Thumb | +X | +X | +Z | -Z | 73 / 73 |

### Rest hands

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

### Posed surface and collision measurements

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

The two toe patches retain all original corner coordinates. Diagonal changes alter toe triangle interiors by up to 2.954 mm left and 2.192 mm right in bidirectional 24-subdivision sampling. Measurements and sample counts are in [source_patch_distances.json](audit/source_patch_distances.json).

### Check results

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

## File identities

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| body_male_v1.glb | 3,909,624 | `09d5e03d5da489e350432bb521e59255393a167a2847ae602b7d92a6a102e387` |
| hand_gestures_male.glb | 95,796 | `140e8d616494344c13f23f895e690588a05b671fb6ce72441e152741ff1ad310` |
| body_male_v1.blend | 3,898,378 | `63bd8eea3f6647b8d2095b76b7c9a19e70d46d8112600e761fd5696ce7799e61` |
| hand_gestures_male.json | 33,417 | `797b46e570bc151c13ecd9e92306972b543051fe6b52d2c4e03ddaff890ab5bf` |
| contact_sheet.png | 6,039,532 | `2c0b80cb30ea8f3e7616398714002dae518e5ab4644c192245b9807128753d39` |
| views/hand_closeups.png | 3,067,587 | `ab3679669c3b29c88c4bf159b2a7fa1171c3e061eef849dcedbc76332586d4f5` |
| motion/run_frame_008.png | 509,903 | `644d0968c6b157a84828a66cc520ee9bd59a85b7b93b58829862ce7fa535a8ef` |
| motion/wave_frame_019.png | 511,550 | `32c17439363ba8fdbc23a9f22a895f877a02f8990eca07923560fd9e69f576ca` |
| motion/jump_frame_009.png | 517,103 | `0767d92349ab462693bcf9a77286b024949ea66a09455d7b657070c0051dc63a` |
| motion/joint_bends_frame_000.png | 510,835 | `9c902da59793d48027f817333af55f3e03d5bde1e9972d7d0a69ad2847ffe1ce` |
