# Studio female modular fit

## Stage 1 · Body readiness

| File or gate | Observed result |
| --- | --- |
| [body_female.glb](body_female.glb) | 9,987 triangles, 1.105 MiB, one skinned mesh named `Base_Body`, one material, three 1024 px embedded JPEG PBR maps. |
| Rest fit | Studio height 0.977001 m versus neutral 0.999512 m. Retained scale 1.0× because the difference is 2.25%. In glTF, the body faces +Z and minimum Y is -6.050e-8 m. |
| [Body validator](body_female.validator.json) | 0 errors and 0 warnings. |
| [master_female.blend](master_female.blend) | Packed Studio geometry, 65 animated joints with names and parent relationships matching the neutral master, and two objects named `Armature` and `Base_Body`. Scene FPS 30. |
| [hand_gestures_female.glb](hand_gestures_female.glb) | Byte-identical to the supplied library. All 18 gesture names match. Khronos 0 errors and 0 warnings. |
| Motion library | [motion_female.glb](motion_female.glb), 14 animations on the female skeleton. Khronos 0 errors and 0 warnings. |

Retargeting transfers the neutral master’s evaluated quaternion deltas through each joint’s two rest bases. The library carries the source hips translation relative to the female bind, including the forward travel in the raw walk source. Pose-local finger relaxation, arm and knee clearance, ankle alignment and sole-height correction are baked where needed. The sole target is zero whenever the neutral reference is at or below 1 mm. At other samples it is the neutral airborne height. Clip timing is preserved in Float32 seconds. The stage uses 30 fps and checks each integer and half frame plus the authored endpoints.

The current dress-up loader discards per-joint translation and scale from its seven shared motions. Integrate this already-retargeted bank as authored playback so the leg and arm clearance tracks survive. For an in-place preview, hold the horizontal hips position at rest and keep the baked vertical bob and other per-joint tracks.

The supplied body checker ran on the reimported, combined motion GLB. [Body self-overlap and foot witnesses](body_selfcheck.json) · [Bake diagnostics](motion_fit.json).

| Clip | Samples | End time (s) | Peak self-pairs | Maximum depth (mm) | Worst planted sole error (mm) |
| --- | ---: | ---: | ---: | ---: | ---: |
| walk | 142 | 2.3750 | 0 | 0.000 | 0.0002 |
| run | 76 | 1.2500 | 0 | 0.000 | 0.0001 |
| wave | 161 | 2.6667 | 0 | 0.000 | 0.0000 |
| jump | 126 | 2.0833 | 0 | 0.000 | 0.0001 |
| idle | 221 | 3.6667 | 0 | 0.000 | 0.0000 |
| nod | 141 | 2.3333 | 0 | 0.000 | 0.0000 |
| dance | 161 | 2.6667 | 0 | 0.000 | 0.0001 |
| sit_down | 73 | 1.2000 | 0 | 0.000 | 0.0002 |
| sit_idle | 181 | 3.0000 | 0 | 0.000 | 0.0001 |
| stand_up | 61 | 1.0000 | 0 | 0.000 | 0.0002 |
| hold_item | 121 | 2.0000 | 0 | 0.000 | 0.0000 |
| hold_box | 121 | 2.0000 | 0 | 0.000 | 0.0001 |
| hold_bag | 121 | 2.0000 | 0 | 0.000 | 0.0001 |
| take_item | 121 | 2.0000 | 0 | 0.000 | 0.0001 |

## Stage 2 · Auto-fit tool

| Component | Implementation |
| --- | --- |
| [fit_module.py](fit_module.py) | Head, torso, arms, legs and feet use region-constrained neutral-to-female surface correspondences with skeletal registration, barycentric interpolation and Laplacian smoothing. Welded coincident vertices share a displacement across UV and material seams. |
| Skin and finish | Keeps topology, UVs, material definitions and rigid weights. Blends transferred body weights at blended cloth vertices that move, then limits to four influences. Winding is preserved and normals and tangents follow the displacement. Image recompression fits the file and resolution caps. |
| Motion bake | Uses the deepest signed point and triangle-witness constraints across the 14 clips. Transforms the 1.5 mm margin into bind space, preserves the constrained component during Laplacian smoothing, and caps extra offset at 30 mm. Checks the blended skin at integer and half frames. |
| Static trial | All seven registered inputs produced a geometry seed within their triangle, texture-resolution and file-size budgets. |
| Usage | `./run.sh fit_module.py -- path/to/source.glb female-example.glb` or `./run.sh fit_module.py -- all`. |

## Stage 3 · Fitted modules

| Module | Triangles | MiB | Max texture (px) | Peak inside vertices | Peak overlap pairs | Min signed (mm) | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| [hair-bob](female-hair-bob.glb) | 2,994 | 0.176 | 1024 | 0 | 0 | 1.210 | Pass |
| [hair-spiky](female-hair-spiky.glb) | 2,972 | 0.750 | 1024 | 0 | 0 | 1.960 | Pass |
| [hair-sidepart](female-hair-sidepart.glb) | 2,982 | 0.118 | — | 0 | 0 | 0.713 | Pass |
| [tshirt](female-tshirt.glb) | 4,699 | 0.799 | 1024 | 21 | 119 | -4.755 | Open |
| [dress](female-dress.glb) | 4,042 | 0.556 | 1024 | 1 | 0 | -0.213 | Open |
| [jeans](female-jeans.glb) | 4,704 | 0.717 | 1024 | 4 | 0 | -0.523 | Open |
| [sneakers](female-sneakers.glb) | 3,492 | 0.174 | — | 0 | 0 | 0.994 | Pass |

### Module gates still open

Signed values below zero are vertex penetration. Signed minima and witness frames come from reimported geometry. Triangle depths use the fitted triangulation and may reflect a different peak frame. A positive signed distance below 0.500 mm is a clearance failure even when both counts are zero. The `checks` folders include the supplied checker reports and the exact reimport witnesses.

| Module | Clip | Min frame | Peak inside / pairs | Min signed zone | Min signed (mm) | Triangle zones and depths |
| --- | --- | ---: | ---: | --- | ---: | --- |
| tshirt | walk | 15 | 21 / 119 | torso | -2.511 | torso 1.514 mm, Left arm 1.132 mm |
| tshirt | run | 1.5 | 10 / 103 | Left leg | -4.755 | torso 0.429 mm, Left arm 1.857 mm |
| tshirt | jump | 9.5 | 1 / 8 | Left leg | -0.653 | Right arm 0.188 mm, Left arm 0.081 mm |
| tshirt | idle | 100 | 0 / 4 | Left arm | 0.675 | Left arm 0.003 mm |
| tshirt | dance | 60 | 4 / 34 | Left leg | -0.674 | Left arm 1.728 mm |
| tshirt | sit_down | 33 | 9 / 67 | Right leg | -2.846 | torso 0.125 mm, Left arm 1.875 mm |
| tshirt | sit_idle | 21 | 4 / 70 | Right leg | -3.082 | torso 0.343 mm, Left arm 1.693 mm |
| tshirt | stand_up | 1.5 | 7 / 71 | Right leg | -1.552 | torso 0.343 mm, Left arm 1.984 mm |
| tshirt | hold_item | 9 | 3 / 36 | Left arm | -1.279 | Left arm 1.834 mm |
| tshirt | hold_box | 45 | 2 / 31 | torso | -0.453 | torso 0.388 mm, Left arm 0.533 mm |
| dress | run | 15.5 | 1 / 0 | Right leg | -0.213 | — |
| dress | sit_down | 30.5 | 0 / 0 | Left leg | 0.319 | — |
| jeans | run | 27.5 | 4 / 0 | Left leg | -0.377 | — |
| jeans | sit_down | 24.5 | 2 / 0 | torso | -0.523 | — |

**Geometry and format.** [Asset contracts](assets_check.json) records the exact bind matches, UVs, triangle indices, materials and embedded texture sizes.

**Recheck.** `./run.sh audit_body.py` applies the supplied body checker. `./run.sh audit_modules.py` runs the local copies of the supplied dense and triangle checks. The copies preserve the numerical tests, sample at half frames, and leave preview rendering to Cycles CPU.

**Renders.** `./run.sh render.py` writes six views per module and a [full outfit contact sheet](renders/full-outfits.png). Each view directory includes a manifest with hashes, camera settings and pose. [Independent visual findings](visual_review.md).
