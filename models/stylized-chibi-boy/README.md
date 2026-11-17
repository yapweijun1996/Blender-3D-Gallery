# Stylized chibi boy — rig and motion draft

**Status: draft.** This is a Tripo-rigged derivative of the user-provided `stylized chibi boy 3d model.glb`. It is not registered in the gallery catalog. The source GLB identifies Tripo as its generator; its original author, generation prompt, and redistribution license were not supplied. Do not infer a license from this repository.

## Deliverables

- `chibi-boy-rig.blend`: editable Blender 5.1.2 source with packed textures, a 41-joint rig, and the seven imported Actions.
- `chibi-boy-animated.glb`: the exported skinned mesh and seven clips, with in-place motion requested from Tripo. The application is responsible for locomotion.
- `review/`: rendered midpoint examples showing the known sit and wave limitations below.

| Clip | Approximate duration (seconds) | Description |
| --- | ---: | --- |
| `idle` | 15.33 | Idle |
| `walk` | 2.33 | Walk |
| `run` | 1.25 | Run |
| `jump` | 2.21 | Jump |
| `sit` | 7.17 | Sit preset |
| `greet_01` | 3.50 | Greeting gesture; not speech animation |
| `wave_goodbye_01` | 6.58 | Wave gesture |

The original smiling expression is baked into the model. There are no facial morph targets, animated smiles, lip sync, or speech-driven hand animation. Midpoint inspection found clothing intersection in the sit pose and sleeve stretching in the wave pose. The weight adjustment improves the torso, but this is not a production-quality deformation pass; other frames, transitions, and foot contacts need manual review. The motion presets are not guaranteed to loop seamlessly. Do not assume the sit preset aligns with a chair.

The GLB is 68,401,108 bytes, with 1,311,174 triangles and three 4096×4096 textures. This exceeds the project's proposed interactive asset budgets, and mobile playback has not been tested. Runtime transforms on ancestors of the skinned mesh require particular care: the glTF validator reports `NODE_SKINNED_MESH_NON_ROOT`.

## Provenance and reproduction

The original downloaded GLB SHA-256 was `a84c4b8a0ceef084ae014dd8bedd98ee3a59b8f936516e9a30fa995430129857`. Tripo CLI 0.11.2 imported it (task `bcf32bbd-13bf-4868-8e77-c016a105236e`, normalization scale 0.99993896484375), checked it as biped, and rigged it with `rig-v1.0` (task `77c7f606-b136-42a4-9e65-f281d262930f`). Retarget task `dc2294fd-cf38-4daf-94dc-583492c8d1a0` produced idle, walk, run, jump and sit; task `81780aa7-a80f-48c4-a3c1-6783fc3b062f` produced greet and wave. Access to those task artifacts depends on the originating Tripo account. A separate v3 rig task `11799bd4-6ee9-48e2-9cb0-2ec3a5c8196c` was created during investigation but is not used in this deliverable.

Given the two original v1 retarget GLBs, combine their animation data and apply the model-specific weight repair in Blender:

```sh
python3 merge_clips.py BASIC.glb GESTURES.glb combined.glb
blender -b -t 4 --python repair_and_export.py -- combined.glb
```

The repair is an approximate spatial adjustment to torso and sleeve weights. The export keeps the four strongest joint influences where more are present, so Blender and GLB may differ slightly. Preserve the source GLB and check representative poses after any edit or re-export.

## Verification

- Khronos glTF Validator: zero errors, one `NODE_SKINNED_MESH_NON_ROOT` warning; seven animations, one skin, and maximum four influences.
- Chromium, Three.js `GLTFLoader` and `AnimationMixer`: the actual exported GLB loaded; each of the seven clips changed bone transforms between sampled times. No console errors or warnings in the test harness.
- Blender: rendered a midpoint of each exported clip and identified the limitations above. This is not an exhaustive motion, mobile, gallery, or accessibility test.
- Export SHA-256: `14bd82351b9ddd4fff04317f1bc70a681385076b889176a0705d05a74f0e4e84`; Blender source SHA-256: `42e061d981852b96139a725800902ad70388f13fe8a235f4f61a5bc3f622cfd6`.
