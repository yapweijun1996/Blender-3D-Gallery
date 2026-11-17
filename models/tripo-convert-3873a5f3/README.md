# Tripo FBX character: 3873a5f3

Status: source archive, not a published gallery entry. This is a distinct pink-haired character; it is not the `stylized-chibi-boy` asset.

The original user-provided archive is preserved unchanged:

- `tripo_convert_3873a5f3-8032-4944-a156-a6793f98e1fb.zip`
- SHA-256: `599983a23f8e9d145d7aed4de9e1ae4023aaffb982befa6dd80a0bfdd41569bc`
- Contents: an FBX and its adjacent `.fbm/` folder containing one 4096×4096 JPEG texture.

Extract the archive with its directory structure intact, then import the FBX into Blender. `preview.png` is a front-view render from the imported model; it is not a substitute for the source.

## Inspection

The archive passed a ZIP integrity check. Blender 5.1.2 imported the FBX and loaded the texture. The imported scene has one 5,479-vertex mesh, 10,458 triangles, and an armature with 65 bones. All mesh vertices have weights and the mesh has an Armature modifier. No animation Actions were found. These checks do not establish deformation quality, animation compatibility, or browser playback. At that initial source inspection, no GLB conversion or gallery admission had been performed.

The source's creator, generation inputs, and redistribution license were not provided; no license is inferred here.

## Animated derivative (draft)

The user supplied `tripo_convert_69ed1771-0c9f-43d9-9f4f-f2101d92cb75.zip` (SHA-256 `6ece61b93f2fd8d947beaaf37c23b15398aeb778f478b103ac7e50b893eee962`). Its texture matches the first archive byte-for-byte; its FBX contains the same character and a 120-frame forward-walking action. Both source ZIP archives are retained unchanged. Tripo CLI could not locate the original task in the active account, so the existing skin was retained and the additional actions were authored locally in Blender.

- `character-motion.blend`: editable Blender 5.1.2 scene with packed texture and six Actions.
- `character-motion.glb`: skinned glTF export, 3,046,524 bytes, 10,458 triangles, one 4096×4096 JPEG texture and 65 joints.
- `create_motion.py`: reproducible import, actions, floor adjustment and export procedure.
- `fitted-chair.glb` and `fitted-chair.blend`: character-scale chair variant in the same coordinate space as the character.
- `create_fitted_chair.py`: builds the chair variant from the original chair GLB and the current character GLB.
- `review/`: representative renders from the final GLB.

| Clip | Duration | Behavior |
| --- | ---: | --- |
| `Idle` | 2.00 s | Gentle head and torso sway. |
| `Walk_InPlace` | 1.21 s | In-place walk sampled from frames 11–40 of the supplied walk. |
| `Run_InPlace` | 0.83 s | Stylized jog based on the walk with increased leg movement and suspension. |
| `Jump` | 1.50 s | Crouch, jump, and return to standing. |
| `Sit` | 3.00 s | Sit on the fitted chair, hold, and return to standing. |
| `Wave` | 3.00 s | Wave and return to standing. |

The walk and run are in-place clips with level, IK-baked feet during stance; the application must move the character forward at **0.12414 m/s for walk** or **0.28 m/s for run** at the original scale and 1× playback speed. Scale both speeds with playback rate and model scale. These speeds cancel the feet's backward stance motion on a level floor. At zero movement speed, in-place playback necessarily shows backward foot travel during contact. Head and neck rotations retain the neutral rest orientation. Clip samples start at time zero, avoiding an extra held frame at the loop boundary; all six clips have matching sampled endpoints. Blend between different clips.

This remains a draft: run is a stylized jog, and transitions, uneven terrain, arbitrary speeds, mobile playback, and all camera angles have not been verified. The face has no expression morph targets. The final whole-frame Blender samples showed no measurable ground penetration for the six clips; this does not establish contact for every subframe or other scene.

To reproduce, extract the animated ZIP preserving its `.fbm` folder and run from this directory:

```sh
blender -b -t 4 --python create_motion.py -- /path/to/tripo_convert_69ed1771-0c9f-43d9-9f4f-f2101d92cb75.fbx
blender -b -t 4 --python create_fitted_chair.py
node validate-motion.mjs
blender -b -t 4 --python-exit-code 1 --python audit_gait.py
blender -b -t 4 --python-exit-code 1 --python audit_chair.py
```

The Khronos glTF Validator reports zero errors and warnings. Desktop Chromium/Three.js loaded the actual GLB, played all six clips, and confirmed endpoint equality and zero horizontal hip motion in the in-place gaits. The gait audit measures weighted sole vertices at half-frame intervals for two loops, applying the stated forward controller speeds. Maximum stance drift is 2.35 mm for walk and 2.80 mm for run; sampled stance soles remain between -0.16 mm and +0.49 mm of ground. The same audit rejects the previous GLB, whose maximum drift under the same test was 128 mm for walk and 125 mm for run. This is sampled evidence, not a guarantee for arbitrary playback or surfaces.

### Fitted chair and sit check

The variant derives from `plastic-dining-chair/exports/optimized.glb` (SHA-256 `645efe38638896bf2fbcd3dce6342dbc8287cdf30a788e9ae198d0db82a2999e`); the original remains unchanged. The variant widens and extends the seat, moves the back and rear supports clear of the character, and adds a contoured cushion sampled from the seated mesh. The Sit clip moves the hips slightly back and leans the torso forward. Both GLBs are authored to share their default origin and scale; load them together without applying the old 0.35 test scale or position. Changing the pose, scale, or placement requires a new fit check. This fitted variant is for this character and pose, not an ergonomic or structural furniture specification.

`audit_chair.py` checks both final GLBs at 145 half-frame samples over the whole 3-second sit-and-rise clip. It finds no character/chair triangle intersections, and the minimum sampled ground height is -0.067 mm. At the seated hold, downward-facing hip and left/right thigh vertex samples have nearest vertical gaps of 0.37, 0.08 and 0.09 mm respectively; 2, 17 and 14 samples are within 2 mm. This is finite surface sampling, not proof that every point touches or that unsampled times and poses cannot intersect. The same audit fails against the previous Sit clip: 77 sampled frames intersect the fitted chair and the selected hip samples lack near support.

Both GLBs passed the Khronos validator with zero errors and warnings. Desktop Chromium/Three.js loaded both assets at their shared origin and played Sit; the console had no errors or warnings. `audit_gait.py` still passes after the sit change. `review/chair-side.png` and `review/chair-quarter.png` show the actual final exports.

SHA-256: character GLB `0c2c62c0e2d08c74eafdd90dc115030d2ce4de12cd543657942cb8af5ddb7c5c`, character Blender source `76bd7a20f07fcdec2363b48922d0c4ebceba5c08c56f0aa4232571a21bb2d938`, fitted chair GLB `d4f924faa80b00989c6c6a15c12a7409ac49b6a5e505c5c1f45c3ad2d0b9e299`, fitted chair Blender source `115279b8fa7f33410bec8b4769ae44ecfd3b206fd91c761dc5bc000425f59e79`.
