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
- `character-motion.glb`: skinned glTF export, 3,050,456 bytes, 10,458 triangles, one 4096×4096 JPEG texture and 65 joints.
- `create_motion.py`: reproducible import, actions, floor adjustment and export procedure.
- `review/`: representative renders from the final GLB.

| Clip | Duration | Behavior |
| --- | ---: | --- |
| `Idle` | 2.04 s | Gentle head and torso sway. |
| `Walk_InPlace` | 1.25 s | In-place walk sampled from frames 11–40 of the supplied walk. |
| `Run_InPlace` | 0.88 s | Stylized jog based on the walk with increased leg movement and suspension. |
| `Jump` | 1.54 s | Crouch, jump, and return to standing. |
| `Sit` | 3.04 s | Lower into a seated pose, hold, and return to standing; not aligned to a specific chair. |
| `Wave` | 3.04 s | Wave and return to standing. |

The walk and run remove horizontal root displacement; the application must provide locomotion. Head and neck rotations in those two clips use neutral rest orientation to correct the source walk's pronounced upward tilt. A short blend closes the gait loop, and the character's vertical position is adjusted using sampled mesh bounds. All six clips have matching first and last sampled poses, but transitions between different clips should be blended.

This remains a draft: gait contact and sliding are not physically solved, the jog is stylized, and sitting requires a suitable seat. On exported whole-frame samples, maximum ground penetration was about 6.1 mm for Jump and 4.7 mm for Sit; other clips had no measurable penetration at that sampling precision. Subframes, arbitrary scenes, mobile playback, and all possible camera angles have not been verified. There are no facial expression morph targets.

To reproduce, extract the animated ZIP preserving its `.fbm` folder and run from this directory:

```sh
blender -b -t 4 --python create_motion.py -- /path/to/tripo_convert_69ed1771-0c9f-43d9-9f4f-f2101d92cb75.fbx
node validate-motion.mjs
```

The Khronos glTF Validator reported zero errors and zero warnings for the exported GLB. Desktop Chromium with Three.js loaded the actual export; every clip changed sampled skinned vertex positions, the first and last sampled poses matched, and Walk_InPlace and Run_InPlace had no horizontal hip displacement. Blender renders were inspected at representative poses, and deformed mesh minimum heights were measured at whole frames. These checks do not prove smooth transitions, complete foot contact, or production-quality deformation. GLB SHA-256: `6ad6f239a0f79a4be486d58febf278868e82399dc3144151b4b4f6b6a39862ed`; Blender SHA-256: `6b7073523af5d37df4aa73a3eb1e216696ab598537153c3f91859024b8b5bbf3`.
