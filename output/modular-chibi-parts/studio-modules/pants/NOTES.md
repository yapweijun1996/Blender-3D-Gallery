# Cargo pants fitting report

Rest and dance pass both collision checkers and the 0.5 mm minimum clearance gate. Walk, run, wave, jump, idle, and nod still fail. The GLB format gate passes.

## Source and coordinates

The Tripo Studio best-quality quad-retopology export arrived as one 5,472-triangle mesh. After import into Blender, the buckle faces −Y and the cuffs point toward −Z. The model uses the same forward and up axes as the master. The original reference shows the purple-grey belt and buckle, hip and cargo pockets, purple side stripes, and ribbed ankle cuffs.

The fit welds coincident seam positions while preserving corner UVs. It removes the occluded waistband deck and both closed ankle ends. The cross sections are aligned to the ankles, knee, crotch and pelvis, with independent clearance at the legs and waist. Only long edges incident on body-cutting triangles are split. The original Tripo base color, roughness/metallic channels and normal map are packed at 1,024 × 1,024 pixels with the original UV layout and interpolated UVs on any splits.

The weights come from barycentric interpolation on the nearest master body triangle. The inside-leg check keeps a vertex attached to its own leg when the opposite thigh is closer, and three adjacency passes smooth the hip and knee blends. The build retains a maximum of four normalized influences. The editable blend contains the master armature and a hidden Base_Body fit reference. The GLB contains the cargo pants mesh and its 65-joint skin.

## Bake and measurement

Blender 5.1.2 evaluates the master body and quaternion actions with their assigned action slots. The fit scans rest and every half-frame in the seven clips, including clip endpoints and the supplied checker sample times. Each adjustment projects the worst signed distance deficits into rest space with a 2.15 mm target margin, smooths with a required-offset floor, and caps the rest clearance to 30 mm. The local fitting pass uses triangle intersection witnesses and bounded position and weight candidates, with a rest triangle test and a full vertex trajectory check before accepting changes. The build retains the best measured candidate and can stop after three non-improving sweeps, up to 12 iterations. A final UV-correspondence pass restores the thickness and smooth profile of the rim and buckle area from the untightened fit. The finish preserves the rest collision and 30 mm clearance limit, then the exported module is rechecked in all clips.

Both supplied checker measurements run on a fresh GLB import. The original Workbench render attempt exited 134 in the background process. The runner executes the original sampling and collision code without the rendering tail and writes the reports under separate names. The ten textured PNGs are separately rendered from the exact GLB using Cycles CPU at 20 samples. The four motion images use the supplied checker’s 40%-through-clip sampling rule with close views of the pants.

The dense report independently evaluates the imported GLB on the master using Blender's armature modifier. It reports unrounded signed distances, the max triangle pair count, frame and body region, and the deepest sampled witness within overlapping faces. The supplied scripts print clip distances rounded to 0.1 mm. The rest rows retain the raw reported distances.

## Rebuild

From this directory, set `BLENDER` and `DYLD_INSERT_LIBRARIES` to the guarded Blender binary and library provided in the request. The following stages read the original sources in their gallery locations.

```sh
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_pants.py -- build
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_pants.py -- checkers verify renders
```

The geometry build uses ordered inputs, fixed sample times and stable candidate sorting. A second byte-for-byte build comparison was not performed.

## Export

The GLB contains 5,774 triangles and 5,960 exported vertices with 65 matching joints, 4 maximum influences and 0 unweighted vertices. The bounds in Z are 0.07295 to 0.41600 m, from the cuff edges to the belt rim. The GLB is 4,232,060 bytes and the BLEND is 5,071,954 bytes. Khronos Validator 2.0.0-dev.3.10 reports 0 errors and 0 warnings. The recorded fit chose iteration 1 after 4 numbered sweeps beyond the initial evaluation.

[Editable BLEND](pants_v1.blend) · [Skinned GLB](pants_v1.glb) · [Validator report](gltf_validator.json) · [Fit history](fit_history.json)

## RESULT — Supplied vertex checker

| Clip | Max vertices inside | Min signed distance (mm) |
| --- | ---: | ---: |
| rest | 0 | 4.302 |
| walk | 150 | -17.500 |
| run | 163 | -16.700 |
| wave | 89 | -9.000 |
| jump | 140 | -9.600 |
| idle | 85 | -8.900 |
| nod | 90 | -8.800 |
| dance | 0 | 1.500 |

[Vertex stdout](motion_check.txt) · [Vertex data](motion_check.json)

## RESULT — Supplied triangle checker

| Clip | Max triangle overlap pairs | Min signed distance (mm) |
| --- | ---: | ---: |
| rest | 0 | 4.302 |
| walk | 387 | -18.400 |
| run | 493 | -16.700 |
| wave | 89 | -9.100 |
| jump | 412 | -10.700 |
| idle | 86 | -9.000 |
| nod | 79 | -8.700 |
| dance | 0 | 1.500 |

[Triangle stdout](motion_check_tri.txt) · [Triangle data](motion_check_tri.json)

## Half-frame check of the exported GLB

| Clip | Poses | Max inside vertices | Max triangle pairs | Min vertex distance (mm) | Minimum frame | Pants zone | Nearby body joint |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| rest | 1 | 0 | 0 | 4.302 | 1 | right cuff | — |
| walk | 113 | 207 | 401 | -20.065 | 3.5 | waistband | LeftForeArm |
| run | 61 | 292 | 611 | -19.937 | 23 | waistband | LeftForeArm |
| wave | 129 | 89 | 90 | -9.182 | 15.5 | waistband | LeftForeArm |
| jump | 101 | 141 | 415 | -10.718 | 9 | hips | LeftHand |
| idle | 177 | 87 | 86 | -8.986 | 59.5 | waistband | LeftForeArm |
| nod | 113 | 90 | 79 | -8.820 | 40.5 | waistband | LeftForeArm |
| dance | 129 | 0 | 0 | 1.436 | 41.5 | waistband | — |

[Full dense export report](dense_check.json)

## Rest clearance in millimeters

| Pants zone | Min | P10 | Median | P90 | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 4.302 | 5.500 | 7.850 | 20.463 | 28.005 | 29.703 |
| crotch / inner thigh | 5.500 | 5.500 | 10.004 | 16.275 | 18.258 | 19.913 |
| hips | 5.324 | 5.500 | 6.005 | 9.857 | 12.542 | 19.439 |
| left cuff | 5.025 | 5.500 | 5.534 | 6.541 | 8.321 | 12.504 |
| left knee | 5.500 | 5.812 | 15.167 | 29.440 | 29.700 | 29.700 |
| left lower leg | 5.500 | 5.689 | 11.949 | 17.232 | 18.368 | 20.097 |
| left thigh | 5.496 | 5.500 | 16.823 | 29.681 | 29.700 | 29.700 |
| right cuff | 4.302 | 5.500 | 5.527 | 6.607 | 8.317 | 12.491 |
| right knee | 5.500 | 5.968 | 14.882 | 29.515 | 29.700 | 29.703 |
| right lower leg | 5.500 | 5.672 | 11.591 | 17.383 | 18.356 | 20.095 |
| right thigh | 5.500 | 5.500 | 18.125 | 29.646 | 29.700 | 29.700 |
| waistband | 5.500 | 6.814 | 8.227 | 12.312 | 14.761 | 21.021 |

## Remaining contacts by clip and pants zone

Distances are signed. A negative value shows penetration. The triangle depth comes from sampling an intersecting triangle and may be near zero at a surface contact.

| Clip | Pants zone | Min vertex distance (mm) | Frame | Body joint near that vertex | Max triangle overlaps | Deepest triangle sample (mm) | Frame |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |
| walk | crotch / inner thigh | — | — | — | 2 | -1.852 | 34 |
| walk | hips | -11.219 | 14 | LeftHandRing1 | 181 | -10.112 | 13 |
| walk | left knee | 0.059 | 41 | LeftLeg | 28 | -7.491 | 15 |
| walk | left lower leg | — | — | — | 3 | -0.113 | 41 |
| walk | left thigh | -10.117 | 15 | LeftHandRing1 | 219 | -9.733 | 14.5 |
| walk | right knee | -0.769 | 28 | RightLeg | 23 | -0.900 | 28 |
| walk | right thigh | -8.371 | 35 | RightHand | 133 | -10.094 | 34.5 |
| walk | waistband | -20.065 | 3.5 | LeftForeArm | 123 | -17.349 | 3 |
| run | crotch / inner thigh | -8.094 | 12 | Hips | 47 | -8.537 | 12 |
| run | hips | -18.653 | 8 | RightHand | 218 | -15.060 | 8 |
| run | left cuff | -0.038 | 9 | LeftFoot | 5 | -1.090 | 9 |
| run | left knee | -7.750 | 17 | LeftUpLeg | 63 | -9.559 | 16 |
| run | left lower leg | -5.755 | 17 | LeftUpLeg | 33 | -6.720 | 17 |
| run | left thigh | -13.163 | 7.5 | LeftHand | 152 | -10.707 | 16.5 |
| run | right cuff | -3.034 | 9 | RightUpLeg | 39 | -8.115 | 25 |
| run | right knee | -10.097 | 25.5 | RightUpLeg | 68 | -13.252 | 9 |
| run | right lower leg | -13.778 | 24.5 | RightUpLeg | 63 | -12.530 | 8.5 |
| run | right thigh | -17.876 | 8 | RightHand | 282 | -19.305 | 8 |
| run | waistband | -19.937 | 23 | LeftForeArm | 142 | -18.589 | 23 |
| wave | hips | -6.695 | 43 | LeftForeArm | 30 | -5.316 | 13 |
| wave | waistband | -9.182 | 15.5 | LeftForeArm | 65 | -7.780 | 12 |
| jump | hips | -10.718 | 9 | LeftHand | 163 | -9.344 | 9 |
| jump | left thigh | -9.429 | 9 | LeftHandIndex1 | 208 | -10.288 | 8 |
| jump | waistband | -9.180 | 43 | LeftForeArm | 69 | -9.852 | 7.5 |
| idle | hips | -4.693 | 39 | LeftForeArm | 19 | -4.233 | 22.5 |
| idle | waistband | -8.986 | 59.5 | LeftForeArm | 68 | -7.264 | 70 |
| nod | hips | -3.684 | 33 | LeftForeArm | 14 | -3.964 | 44 |
| nod | waistband | -8.820 | 40.5 | LeftForeArm | 65 | -7.883 | 21 |

Independent body geometry tests detect arm-to-pelvis self-intersection with the pants absent. walk frame 3.5 has 110 pairs, run frame 23 has 82 pairs, wave frame 15.5 has 52 pairs, jump frame 9 has 69 pairs, idle frame 59.5 has 42 pairs, nod frame 40.5 has 42 pairs. The signed clearance and overlap limits were applied to the whole supplied body during pants verification. The author’s image review and the remaining motion gate results are recorded below.

## Visual review

The author inspected all six static views and all four motion captures from the final GLB. The four body-on static views show separate legs, a fitted waistband, and cuffs ending near the ankles. The two garment-only angles show the open waist and cuff rims. The purple-grey material, buckle, patch pockets, snaps, side stripes, and ribbed cuffs remain readable. The final rim pass removes the visible folds around the belt loops that appeared in the previous candidate. A narrow light band is still visible immediately above the waist in the body-on views.

Restoring the rim increased the deepest half-frame walk penetration from 11.971 mm to 20.065 mm. The earlier candidate already failed the same six clips and showed folds around the belt loops in the static front view. The delivered files retain the repaired rim.

The chosen walk and wave images retain the recognizable garment and closed fabric panels. The run image shows exposed body on the raised thigh and a small inner-thigh cut. The chosen jump view shows a small irregularity at the side of the waistband. These observations and the collision reports leave the motion visual gate unresolved.

[rest_front](renders/rest_front.png) · [rest_back](renders/rest_back.png) · [rest_left](renders/rest_left.png) · [rest_right](renders/rest_right.png) · [rest_waist](renders/rest_waist.png) · [rest_cuffs](renders/rest_cuffs.png) · [walk](renders/walk.png) · [run](renders/run.png) · [wave](renders/wave.png) · [jump](renders/jump.png)

## Artifact identity

| Artifact | SHA-256 |
| --- | --- |
| [source_studio_retopo.glb](source_studio_retopo.glb) | `06edfca277a5ae4f1f64499b8adea79395d5f3dbec6af606de90232c342e17a8` |
| [tpose-bottom-01-cargo-pants.png](../../generated/tpose-bottom-01-cargo-pants.png) | `329d547b65f86bcb8e98bb828da50aadf9be690b3d634ff67a0d4c731a245f82` |
| [GJH_Chibi_Master_rigged.blend](../../master/GJH_Chibi_Master_rigged.blend) | `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f` |
| [motion.glb](../../../../models/tripo-chibi-motion/motion.glb) | `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410` |
| [pants_v1.blend](pants_v1.blend) | `23aec2dd2ad38c3087affae3d2a63b2dfdeabd5fe9709bd40058738b99df379d` |
| [pants_v1.glb](pants_v1.glb) | `31649fcca978beb05a49330b5a26e5a37a0f6dea6c1608aef601a52949784f01` |
| [fit_pants.py](fit_pants.py) | `32e46483f408fc699692c32b0e49c8c69902932f090320cb1e0ae448e08346a8` |
| [fit_history.json](fit_history.json) | `7e348e52fa4ca7530652ac57b3adc79f5790d362205821888737d7909be0b549` |
| [motion_check.txt](motion_check.txt) | `db21f6e2cd8370692ad1baac330418613c56d54cebcaf66abf3be0d5ea706e2f` |
| [motion_check_tri.txt](motion_check_tri.txt) | `01028a9147978d40acdd17d103af55ae28c1a1b0b9af84eb683de5e70086668e` |
| [dense_check.json](dense_check.json) | `bf1f80f94a79a2b761c76d260104954e903dfb39d5d88e5c103ddda1860cb95a` |
| [gltf_validator.json](gltf_validator.json) | `619e8764324a598538f71381c9e3151c91f2800c678ffcc78ec928ebba76cf21` |
| [rest_front.png](renders/rest_front.png) | `623d4ba29174e1c0056161658b697d79ab33cab741798318c46cb373c609e19d` |
| [rest_back.png](renders/rest_back.png) | `a3930d18b336b3fcf680f00243375ac310241ed8db1ef8e32fd74cfc79de53bd` |
| [rest_left.png](renders/rest_left.png) | `5e0b5133340760fc1c7e1c657e051c526d379033db3074afff40521392b2dd62` |
| [rest_right.png](renders/rest_right.png) | `5738104900387778326c1094d2f5039b277b04d6eb800a07f5d49884fbbc3ea6` |
| [rest_waist.png](renders/rest_waist.png) | `dd9aca49f766db8c024b4ca80a055e88567668509b8c42a4bb19430504496920` |
| [rest_cuffs.png](renders/rest_cuffs.png) | `37e5449cf4b0fa6507b996a397eef886abebe8bea550ee5fa2ee51a07e3c066c` |
| [walk.png](renders/walk.png) | `e69dee2c12062b65fcb2a6d6078a0c9ba6cfb9bddfe0e1f9c8bf658ba6eb022a` |
| [run.png](renders/run.png) | `1f3b897c9d90259e677fe7c92970be76b2111162c26fb98bec75095240785b5e` |
| [wave.png](renders/wave.png) | `7d4b8b46772132394a15b69ef0e7fc3246872e77444e5d4414c6ce4a0028c611` |
| [jump.png](renders/jump.png) | `274dafad703c99d8f91a70e2f3a6747f0cfc7ec4e1dad36f0b52b820e72bfeb6` |
