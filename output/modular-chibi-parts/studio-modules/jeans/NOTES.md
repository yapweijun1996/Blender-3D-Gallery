# Studio jeans fit

**Motion status: REWORK.** The fitted module passes both collision checkers in rest and dance. Walk, run, wave, jump, idle and nod still have contacts. The original rig, body and motion files have matching pre/post SHA-256 hashes.

## Artifacts

- [jeans_v1.blend](jeans_v1.blend) is the editable skinned module with three packed textures and the hidden master body for inspection.
- [jeans_v1.glb](jeans_v1.glb) contains one garment mesh with one skin, 65 named master joints, at most four normalized influences per vertex and no animations.
- The GLB has 4,564 triangles and 4,079 glTF vertices. The editable garment has 2,315 vertices. The GLB is 3,339,556 bytes and the BLEND is 4,230,555 bytes.
- The original Tripo material and UV layout are retained. The base color, normal and packed roughness/metallic maps are each 1024 × 1024. The exporter normalizes tangents for the retained UVs and fills one zero-length tangent.
- The local Khronos glTF Validator reports 0 errors and 0 warnings. [Validator report](gltf_validator.json)
- The Blender asset was opened and verified with the garment parented to the armature, a single armature modifier, normalized weights and packed maps.
- GLB SHA-256 `b2f6c75bbfa79d75a08cb77d3686b7392deaf0218df75f12a9d027d6fcf702b2`. An independent rebuild using the default fitter produced identical GLB bytes.
- BLEND SHA-256 `ef5cfb0e7950e3a76838781b728f0aad47bebfb0087b6c98beab92aa23e746bc`.

## Fitting

The imported Tripo mesh in Blender was upright along +Z with its button, fly and front pockets toward −Y. The jeans reference was [bottom-04-jeans-tpose.png](../../generated2/bottom-04-jeans-tpose.png). The matching jeans image is in `generated2/` alongside the legacy `generated/` images.

The build removes 495 hidden cap or interior faces before fitting. It aligns the waistband, saddle, knees and cuffs on the master. A smooth contour adjustment takes in the side hips and knee creases, then adjusts the rear waistband to cover the base shorts in rest. Weights come from barycentric interpolation on the nearest body triangle with mesh-neighborhood smoothing around the hips and knees. The garment retains its material seams, cuffs, front fly and belt-loop details. A small right-thigh offset and localized weight blend toward the right knee close the skin wedge seen at run frame 12. The rest side profile is smoother than the large-offset trial. Compared with the smooth fit before this repair, the walk checker peak rose from 272 to 274 pairs and the run triangle-checker minimum changed from −9.5 to −9.9 mm. The deepest sampled triangle interior changed from −11.351 mm to −13.528 mm.

The selected cutoff of the waistband opening runs from Z 0.411 to 0.431 m, with a mean of 0.419 m. The rear rim reaches 0.431 m to cover the master shorts. Both cuff openings run from Z 0.070 to 0.080 m. The rest clearance cap is 30 mm.

The half-frame bakes tested outward offsets, direction and weight adjustments, and subdivision of long triangles involved in contact. Uniform outward pushes reduced some of the thigh contacts and deepened other contacts with the moving extremities. Subdividing the contact triangles also exposed additional intersections. The bake trials reached 6,000 triangles and delivered poorer combined results. The selected smooth fit retains 4,564 triangles. The script retains the experimental bake entry point with a ceiling of 12 passes.

## Supplied checker RESULT tables

The garment was exported, reimported, and bound to the original master armature for numeric QA. The vertex checker samples 12 frames per clip. The triangle checker samples every third integer frame. The following minima are nearest oriented body-triangle distances. The requirement is at least +0.500 mm and zero counts.

### Vertex checker

[stdout](motion_check.txt) · [JSON](motion_check.json)

| Clip | Max inside vertices | Min signed distance (mm) |
| --- | ---: | ---: |
| rest | 0 | +2.587 |
| walk | 112 | -8.000 |
| run | 114 | -9.900 |
| wave | 9 | -7.400 |
| jump | 45 | -8.100 |
| idle | 12 | -8.100 |
| nod | 9 | -7.700 |
| dance | 0 | +1.600 |

### Triangle checker

[stdout](motion_check_tri.txt) · [JSON](motion_check_tri.json)

| Clip | Max overlap pairs | Min signed distance (mm) |
| --- | ---: | ---: |
| rest | 0 | +2.587 |
| walk | 274 | -9.700 |
| run | 385 | -9.900 |
| wave | 60 | -7.800 |
| jump | 119 | -8.300 |
| idle | 55 | -8.300 |
| nod | 53 | -7.800 |
| dance | 0 | +1.600 |

## Half-frame results

The reimported GLB was measured on 824 poses, including both clip endpoints and both supplied checker schedules. The deepest vertex and the largest triangle-pair count may occur on different frames. Body zone names identify the dominant joint of the contacted body triangle. [Detailed poses and triangle residuals](dense_check.json)

| Clip | Poses | Inside vertices | Min vertex (mm) | Frame | Garment / body zone at min | Triangle pairs | Frame |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| rest | 1 | 0 | +2.587 | 1 | waistband / LeftUpLeg | 0 | 1 |
| walk | 113 | 139 | -10.235 | 39 | waistband / RightForeArm | 298 | 29 |
| run | 61 | 153 | -9.865 | 12 | crotch / RightUpLeg | 454 | 29 |
| wave | 129 | 9 | -7.795 | 54 | waistband / LeftForeArm | 60 | 11.5 |
| jump | 101 | 47 | -8.943 | 9.5 | front hips / LeftForeArm | 119 | 9 |
| idle | 177 | 12 | -8.345 | 45 | waistband / LeftForeArm | 55 | 16.5 |
| nod | 113 | 10 | -8.022 | 17.5 | waistband / LeftForeArm | 53 | 33 |
| dance | 129 | 0 | +1.622 | 0 | crotch / RightUpLeg | 0 | 0 |

The overlap-triangle depths below come from a barycentric grid. Grid coverage limits their precision.

| Clip | Frame | Garment / body zone at deepest sampled triangle | Signed depth (mm) |
| --- | ---: | --- | ---: |
| walk | 36.5 | waistband / RightForeArm | -10.190 |
| run | 12 | crotch / RightUpLeg | -13.528 |
| wave | 8.5 | waistband / LeftForeArm | -8.334 |
| jump | 0.5 | waistband / LeftForeArm | -8.334 |
| idle | 45 | waistband / LeftForeArm | -8.345 |
| nod | 25.5 | waistband / LeftForeArm | -8.286 |

Upper-body versus hip triangle pairs on the master alone were measured at the deepest vertex frames. The frame and count were walk frame 39 (121 pairs), run frame 12 (0 pairs), wave frame 54 (32 pairs), jump frame 9.5 (51 pairs), idle frame 45 (32 pairs), nod frame 17.5 (34 pairs). These checks distinguish the extremity contacts at the waistband and front hips from the calf-versus-upper-thigh contact in run. The zero-contact acceptance target remains open.

## Rest clearance

Distances are signed and shown in mm. All exported vertices are within the 30 mm rest cap.

| Region | Vertices | Min | P10 | Median | P90 | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 4,079 | 2.587 | 4.789 | 8.573 | 12.223 | 14.366 | 21.977 |
| crotch | 856 | 3.664 | 5.185 | 9.005 | 15.557 | 19.132 | 21.977 |
| cuff | 489 | 5.356 | 7.628 | 10.384 | 12.162 | 12.658 | 13.474 |
| front hips | 443 | 4.024 | 4.419 | 7.486 | 10.964 | 12.141 | 12.947 |
| knee | 422 | 3.967 | 5.096 | 6.464 | 9.746 | 9.915 | 10.329 |
| lower leg | 452 | 3.973 | 5.396 | 8.141 | 9.758 | 10.194 | 11.335 |
| seat | 67 | 4.580 | 4.678 | 6.408 | 12.627 | 13.320 | 14.339 |
| upper thigh | 430 | 3.998 | 4.623 | 6.428 | 10.019 | 11.106 | 20.595 |
| waistband | 920 | 2.587 | 4.375 | 8.300 | 13.561 | 14.941 | 17.629 |

## Visual review

The fitter and an independent reviewer both visually inspected all ten reimported GLB PNGs. The rest views show a close chibi silhouette with a continuous ankle hem, a hollow waist opening and intact denim texture. Gold stitching, the fly, two front belt loops and pocket rivets are apparent in the front close-ups. The four motion previews retain the cloth silhouette and seam details. The previous run frame 12 skin wedge is gone. The same frame still shows an angular waistband fold and a pointed cuff. Walk frame 23 has a compressed but continuous inner-thigh fold. The wave wrist partly occludes the left waistband. The contact metrics cover additional frames and keep the motion gate open.

| Capture | Frame |
| --- | ---: |
| [rest_front](renders/rest_front.png) | 1 |
| [rest_back](renders/rest_back.png) | 1 |
| [rest_left](renders/rest_left.png) | 1 |
| [rest_right](renders/rest_right.png) | 1 |
| [rest_front_three_quarter](renders/rest_front_three_quarter.png) | 1 |
| [rest_rear_three_quarter](renders/rest_rear_three_quarter.png) | 1 |
| [walk](renders/walk.png) | 23 |
| [run](renders/run.png) | 12 |
| [wave](renders/wave.png) | 25 |
| [jump](renders/jump.png) | 20 |

The ten Cycles CPU renders use 12 samples with denoising. The manifest binds each capture to the GLB SHA-256 and records camera and frame settings. [Render manifest](render_manifest.json)

## Reproduction

From this module directory, use Blender 5.1.2 in background mode. `BLENDER` and `GUARD` are the local paths specified with the assignment. The two supplied checker scripts are run verbatim for geometry and frame sampling. The wrapper suppresses their Workbench renders and gives each JSON its own filename. The textured visual review is generated with the separate Cycles command.

```sh
export TMPDIR="$PWD/work/"
export DYLD_INSERT_LIBRARIES="$GUARD"
"$BLENDER" -b -t 6 -noaudio --python-exit-code 1 --python fit_jeans.py
"$BLENDER" -b -t 6 -noaudio --python-exit-code 1 --python fit_jeans.py -- --checkers
"$BLENDER" -b -t 6 -noaudio --python-exit-code 1 --python fit_jeans.py -- --verify
"$BLENDER" -b -t 6 -noaudio --python-exit-code 1 --python fit_jeans.py -- --renders
```

Quaternion rotation modes are preserved. Blender 5.1 actions are selected with their action slots. All fitting and image rendering ran in Blender. The installed Khronos validator ran locally.

The first unguarded Blender diagnostic launch crashed at startup and wrote its automatic crash log to macOS temporary storage. The guarded build, exported models and QA reports used this module directory.
