# Chibi hand gestures · round 2

Both pinches and both OK signs close within 0.037 mm on the exported fingertip pulp. All 18 poses have zero non-adjacent triangle crossings involving either hand. The full-body mesh retains 318 crossings outside the hands. Their triangle identities match the first-pass GLB in bind and in every clip.

Open [hands_gestures.blend](hands_gestures.blend) for the editable body, armature and 18 pose assets with refreshed 256 × 224 previews. For playback, pair [base_body.glb](base_body.glb) and [hand_gestures.glb](hand_gestures.glb) from this directory. The static body has one mesh, one skin, 65 joints and zero animations. The motion file has one skeleton, 66 nodes, zero meshes and 18 one-sample clips starting at 0 seconds.

## Surface distances

These figures come from the reimported GLBs. World-space witness coordinates and triangle-patch sizes for every reported contact are under roundtrip.exported_surface in [hand_check.json](hand_check.json). Coordinates and distances use millimetres.

| Feature | Left (mm) | Right (mm) |
| --- | --- | --- |
| pinch · thumb pulp to index pulp | 0.01671 | 0.03651 |
| ok · thumb pulp to index pulp | 0.01901 | 0.03549 |
| Fist · index fingertip to palm | 0.10025 | 0.13630 |
| Fist · middle fingertip to palm | 0.14359 | 0.18775 |
| Fist · ring fingertip to palm | 0.18296 | 0.18670 |
| Fist · pinky fingertip to palm | 0.19730 | 0.16449 |
| Fist · thumb fingertip to palm | 2.44712 | 3.14202 |
| Fist · thumb cap to folded fingers, editable mesh | 0.0083 | 0.0077 |
| point · thumb tip to proximal index | 0.54395 | 1.10549 |
| peace · thumb tip to proximal index | 0.06707 | 0.25829 |

Within the displayed precision, the four folded digits of each fist attain the same clearance on the smaller, forward-facing pulp patches. The fist thumb wraps across the folded digits. Its distance to the palm is greater.

| Gesture | Folded fingertip pulp to palm | Left (mm) | Right (mm) |
| --- | --- | --- | --- |
| point | Middle | 0.12056 | 0.18775 |
| point | Ring | 0.18296 | 0.18670 |
| point | Pinky | 0.19699 | 0.16449 |
| thumbs_up | Index | 0.38021 | 0.93948 |
| thumbs_up | Middle | 0.06320 | 0.18775 |
| thumbs_up | Ring | 0.18296 | 0.18670 |
| thumbs_up | Pinky | 0.19600 | 0.16449 |
| peace | Ring | 0.56839 | 0.23179 |
| peace | Pinky | 0.19633 | 0.16845 |

The checker identifies the pulp on the bind mesh within 16 mm of the tip. It retains triangles within 2.65 mm of a forward-and-volar support plane, filtered by outward face orientation. The separate terminal cap for fingertip-to-palm measurements uses the final 8 mm along the shaft. Both patches follow skinning. The minimum tests vertices against opposing triangles in both directions and checks edge interiors against edge interiors. Each witness lies on the deformed skin.

## Geometry, skin and playback

| Measurement | Result |
| --- | --- |
| Vertices / triangles | 6,010 / 9,512 · whole-body budget 10,000 |
| Hand triangle counts | 2,628 left / 2,626 right · budget 3,000 per hand |
| Rig | 65 bones, 65 vertex groups, 0 changed parents, 0 non-finger bind-matrix component change |
| Skin influences | Maximum 4, above four 0, unweighted 0, maximum normalization error 1.00582838e-07 |
| Weight bleed | 0 vertices mixing finger chains at any positive weight, 0 above the 0.2 threshold |
| Free finger shafts | 856 left / 845 right sampled, 0 with foreign influences |
| Central palm | 19 left / 17 right sampled, minimum hand weight 1.0 on both |
| Thenar pads | 31 left / 30 right sampled. Thumb weight ranges 0.159993–0.575041 left and 0.159973–0.539406 right |
| Topology | 0 welded nonmanifold edges in either hand. Native hand quads 972 left / 975 right |
| Outside the hands | 2,790 original vertices, 0 m bind displacement, 0 weight changes, 4,210 unchanged faces, 0 UV component difference and 0 changed encoded corner normals |
| Wrist motion | Maximum 3e-05 mm and 0.0° over 18 poses |
| Export errors | Weights 1.1920929e-07, inverse bind identity 4.17232513e-07, rest transforms 0, quaternion components 1.78813934e-07, scale components 2.58171315e-07 |
| Reimport | 18 actions assigned with slots. Maximum rest vertex error 0.000359 mm, maximum posed error 0.000626 mm |

Triangle budgets use the original wrist threshold at absolute X above 0.270 m. Collision testing includes the wrist from absolute X above 0.255 m and every other triangle in the body. Triangles sharing a welded rest-space vertex are adjacent. The whole-body comparison matches each intersecting pair by the rest-space geometry of its triangles.

| Clip | Native hand pairs | Export hand pairs | Whole-body pairs | New pairs | Scale tracks | Max replay error (mm) |
| --- | --- | --- | --- | --- | --- | --- |
| hand_fist_L | 0 | 0 | 318 | 0 | 4 | 0.000481 |
| hand_open_relaxed_L | 0 | 0 | 318 | 0 | 0 | 0.000481 |
| hand_point_L | 0 | 0 | 318 | 0 | 3 | 0.000481 |
| hand_thumbs_up_L | 0 | 0 | 318 | 0 | 4 | 0.000481 |
| hand_peace_L | 0 | 0 | 318 | 0 | 2 | 0.000481 |
| hand_ok_L | 0 | 0 | 318 | 0 | 0 | 0.000481 |
| hand_grip_small_L | 0 | 0 | 318 | 0 | 0 | 0.000481 |
| hand_pinch_L | 0 | 0 | 318 | 0 | 0 | 0.000481 |
| hand_open_wide_L | 0 | 0 | 318 | 0 | 0 | 0.000481 |
| hand_fist_R | 0 | 0 | 318 | 0 | 4 | 0.00055 |
| hand_open_relaxed_R | 0 | 0 | 318 | 0 | 0 | 0.000537 |
| hand_point_R | 0 | 0 | 318 | 0 | 3 | 0.000485 |
| hand_thumbs_up_R | 0 | 0 | 318 | 0 | 4 | 0.00055 |
| hand_peace_R | 0 | 0 | 318 | 0 | 2 | 0.000364 |
| hand_ok_R | 0 | 0 | 318 | 0 | 0 | 0.00062 |
| hand_grip_small_R | 0 | 0 | 318 | 0 | 0 | 0.000609 |
| hand_pinch_R | 0 | 0 | 318 | 0 | 0 | 0.000626 |
| hand_open_wide_R | 0 | 0 | 318 | 0 | 0 | 0.00043 |

## Pose data and compatibility

On each long finger, joint 2 now lies partway along the proximal phalanx, joint 3 at the proximal interphalangeal joint and joint 4 at the distal interphalangeal joint. The bone names, parent links and 65-joint count carry over. The two proximal joints share the same skin transform when the auxiliary bend is neutral. The thumb retains its first-pass joint layout. Local dorsal smoothing rounds the knuckle transitions. Gently flattened index and thumb pads give the tips a broader visible meeting surface.

The [pose JSON](hand_gestures.json) uses schema version 2. Each gestures[clip][bone] entry gives a local XYZ Euler rotation in degrees. Apply scales[clip][bone] where present. These local XYZ scale factors are dimensionless. Reset the pose to bind when switching clips and use unit scale for omitted bones. Fist and thumbs-up each key four proximal scale tracks per side, point three, and peace two. The other ten clips use rotations alone. The library contains 360 rotation channels and 26 scale channels. Custom rotation-only JSON readers need the scale map to reproduce the eight compact poses. In Blender 5, set both the animation data action and its action_slot when applying an imported clip.

Grip-small and open-wide retain the original joint articulation after mapping the PIP and DIP rotations to the revised finger chain. Local dorsal and fingertip sculpting affects both surfaces. The 40 mm grip test found zero penetrating triangles on each side. The smallest axis-to-skin clearance is 20.1792 mm left and 20.1814 mm right.

| Protected pose versus round 1 | Hand RMS change (mm) | Maximum change (mm) |
| --- | --- | --- |
| hand_grip_small_L | 0.50347 | 2.25241 |
| hand_open_wide_L | 0.53982 | 2.37272 |
| hand_grip_small_R | 0.51729 | 2.2189 |
| hand_open_wide_R | 0.55573 | 2.40246 |

## Visual review

Both the author and an independent reviewer inspected the final [54-view sheet](contact_sheet.png) and [eight close-ups](pinch_ok_closeups.png). Both were rendered directly from the two delivered GLBs in Blender 5.1.2 using Cycles CPU. Standard tiles are 384 × 336 at 14 samples, with the same orthographic directions as in round 1. Macro tiles are 576 × 448 at 24 samples, with a 62 mm palmar field of view and a 38 mm oblique field of view. The grip-small side views include the 40 mm gauge.

| Feature | Final independent visual findings |
| --- | --- |
| Pinch | Both pads visibly meet from both angles. The other fingers sweep forward. The right resting fingers curl somewhat more than the left. |
| OK | Both rings enclose clear space and close at the finger pads. The other three fingers extend. |
| Fist | Both side profiles are compact, the thumb wraps across the folded fingers and the dorsal knuckle contour is low. |
| Point / peace | The index and V silhouettes read clearly. The thumb lies alongside the index. The former peace openings appear as shallow shaded creases. |
| Thumbs up | The index folds into the stack on both sides. Narrow background slits remain between the lowest fingers. |
| Open relaxed / open wide | The relaxed thumbs stand clear of the palms. Open-wide retains greater spread. |
| Grip small | Both hands surround the circular guide. |

Some fingertip pads and knuckles show polygon facets in the close-ups. The surface and collision results cover the 18 authored single-frame poses. Blends between different clips were outside the static pose check.

## Rebuild and audit

Run from this directory. The wrapper uses the supplied guarded Blender binary and keeps its temporary files here. The original hand library, its studio script and the original character master are read-only inputs. Temporary render materials affect the review scene only.

~~~sh
./run_blender.sh build_hands.py
./run_blender.sh render_hands.py
./run_blender.sh build_hands.py --embed-previews
./run_blender.sh hand_check.py > hand_check.log 2>&1
~~~

Rendering stages tiles in .work/views/ for sheet assembly and asset previews. [The log](hand_check.log) includes the Blender process output. [The machine-readable check](hand_check.json) contains the per-pose measurements, witnesses, all 18 replay errors, asset hashes and individual gates.

| Artifact | SHA-256 |
| --- | --- |
| hands_gestures.blend | 7fa90638f0349998f7a757b58e5bfe1966498e696a3b39adc7eb6b331d2b7b4c |
| base_body.glb | cc06cbac9befd86a0cf0455f76d76c68dfe215d6db7711c32d7d1c5fac613b96 |
| hand_gestures.glb | a59c02e6a5347885c95d6ee6f777b2c07cde8633df35216fd512214fb14cc7db |
| hand_gestures.json | 8c48f6cedb1048585f46fccee47c0cf8848f80d81f26c4557a2eba0110e169da |
| contact_sheet.png | 7f2b9e49c455d1e67263b40019fa28d3a4f82c5ef5d343e22bc6075c216eaff1 |
| pinch_ok_closeups.png | a840bdab90caaa8d95c3cf5a22f99a0b8aa9ad263d9fcff15ee6c60585cdfb6b |
| ../contact_sheet.png | 7487b59da47570e71c2f9b9f5add6e38ee6646c54fb55710ba0767d0e07cc6bc |
| ../hands_gestures.blend | e2bb8187d2f4148dccde9503d71ceae39710a3ea4533674e7a1259d5c172a57c |
| ../../master/GJH_Chibi_Master_rigged.blend | 0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f |

