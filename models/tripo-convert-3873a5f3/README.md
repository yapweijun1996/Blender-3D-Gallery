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
- `character-motion.glb`: skinned glTF export, 3,045,236 bytes, 10,458 triangles, one 4096×4096 JPEG texture and 65 joints.
- `create_motion.py`: reproducible import, actions, floor adjustment and export procedure.
- `review/`: representative renders from the final GLB.

| Clip | Duration | Behavior |
| --- | ---: | --- |
| `Idle` | 2.00 s | Gentle head and torso sway. |
| `Walk_InPlace` | 1.21 s | In-place walk sampled from frames 11–40 of the supplied walk. |
| `Run_InPlace` | 0.83 s | Stylized jog based on the walk with increased leg movement and suspension. |
| `Jump` | 1.50 s | Crouch, jump, and return to standing. |
| `Sit` | 3.00 s | Lower into a seated pose, hold, and return to standing; not aligned to a specific chair. |
| `Wave` | 3.00 s | Wave and return to standing. |

The walk and run are in-place clips with level, IK-baked feet during stance; the application must move the character forward at **0.12414 m/s for walk** or **0.28 m/s for run** at the original scale and 1× playback speed. Scale both speeds with playback rate and model scale. These speeds cancel the feet's backward stance motion on a level floor. At zero movement speed, in-place playback necessarily shows backward foot travel during contact. Head and neck rotations retain the neutral rest orientation. Clip samples start at time zero, avoiding an extra held frame at the loop boundary; all six clips have matching sampled endpoints. Blend between different clips.

This remains a draft: run is a stylized jog, chair contact is not solved, and transitions, uneven terrain, arbitrary speeds, mobile playback, and all camera angles have not been verified. The face has no expression morph targets. The final whole-frame Blender samples showed no measurable ground penetration for the six clips; this does not establish contact for every subframe or other scene.

To reproduce, extract the animated ZIP preserving its `.fbm` folder and run from this directory:

```sh
blender -b -t 4 --python create_motion.py -- /path/to/tripo_convert_69ed1771-0c9f-43d9-9f4f-f2101d92cb75.fbx
node validate-motion.mjs
blender -b -t 4 --python-exit-code 1 --python audit_gait.py
blender -b -t 4 --python-exit-code 1 --python audit_chair.py
```

The Khronos glTF Validator reports zero errors and warnings. Desktop Chromium/Three.js loaded the actual GLB, played all six clips, and confirmed endpoint equality and zero horizontal hip motion in the in-place gaits. The gait audit measures weighted sole vertices at half-frame intervals for two loops, applying the stated forward controller speeds. Maximum stance drift is 2.35 mm for walk and 2.80 mm for run; sampled stance soles remain between -0.16 mm and +0.49 mm of ground. The same audit rejects the previous GLB, whose maximum drift under the same test was 128 mm for walk and 125 mm for run. This is sampled evidence, not a guarantee for arbitrary playback or surfaces.

### Chair fit check

The selected comparator is the repository's `plastic-dining-chair/exports/optimized.glb` (SHA-256 `645efe38638896bf2fbcd3dce6342dbc8287cdf30a788e9ae198d0db82a2999e`). Its unscaled seat is approximately 0.4675 m above the ground, too high for this approximately 1 m stylized character's current sit. For the documented test it is uniformly scaled to 0.35 and placed at Blender `(0.01, 0.08, 0)` m; its seat top is 0.163625 m. At the seated hold, the nearest sampled hip/thigh-weighted vertex above the seat is about 7.2 mm away. Triangle intersection checks find no seat intersections but 73 overlap pairs against the two back posts. Therefore the current sit does **not** pass a chair-fit check; the pose, chair and/or backpack needs further adjustment. This is one pose and one test placement, not a full collision or ergonomic assessment. See `review/chair-side.png` and `review/chair-quarter.png`; `audit_chair.py` reproduces the geometric check without modifying the chair asset.

GLB SHA-256: `74ba5bb62a5c275fd390871f6294594d5dd26ea7e5ac0a808235eeb936ef7f6d`; Blender SHA-256: `f1946c6088c47faf2289b72216e4fb33ae574fa3f9c26bdb0f02dd54d31a164c`.
