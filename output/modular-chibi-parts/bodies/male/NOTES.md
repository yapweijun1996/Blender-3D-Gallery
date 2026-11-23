# Studio male modular dress-up

## 1. Body readiness

| Deliverable | Verification |
| --- | --- |
| [body_male.glb](body_male.glb) | 1.141 MiB, 9,974 triangles, one skinned `Base_Body` mesh, 65 joints and the neutral parent hierarchy, textures 320×320, 1024×1024, 320×320. Khronos errors/warnings 0/0. |
| [master_male.blend](master_male.blend) | `Armature` and `Base_Body` with identity world transforms, quaternion pose bones and packed PBR maps. Bind-pose self-overlap 0. |
| [motion_male.glb](motion_male.glb) | 14 quaternion clips, matching bind hierarchy and source durations, skeleton-only GLB. Khronos errors/warnings 0/0. |
| [hand_gestures_male.glb](hand_gestures_male.glb) | Byte-for-byte Studio bank. Eighteen `hand_<name>_L` / `hand_<name>_R` clips on the exact male bind. Khronos errors/warnings 0/0. |

The Studio GLB contains 9,974 triangles. The male is 0.97785 m tall against the Blender master at 0.99951 m, a 2.17% difference. The chosen scale is **1.000000**. It faces glTF +Z and the lowest rest vertex is at y = −0.000000029 m. The base color was JPEG-encoded and the normal and metallic–roughness maps were resampled to fit the byte budget. The original geometry, UV and skin payloads are intact.

The retarget uses joint rotation deltas expressed in the two bind bases. The source Hips displacement in world metres, root axes and clip times are preserved. Pose clearance adds lateral shoulder and elbow adjustments, distributed leg glide, and limited toe or digit relaxation. A floor compensation is distributed through the upper leg, shin and foot. Locomotion contact is inferred from each original male-retargeted sole trajectory. The lower stance foot is planted when near the floor, and an airborne interval is preserved. Stationary actions keep both feet planted. The maximum planted error in the bake was **0.0901 mm**. Floor error is vertical, and no horizontal foot-lock threshold was requested.

**Body self-overlap** · 3 of 14 audited clips reached zero. The body animation clearance gate remains open.
The Blender reimport measured **0.0902 mm** maximum planted error on the integer and half-frame grids. A supplementary offset grid in walk measured **1.9203 mm** during a support transition. [Floor evidence](qa/floor_validation.json)

The table uses the original body checker’s overlap and adjacency rules against the reimported master and motion. It evaluates endpoints and integer and half frames for both the shared 24 fps and extra 30 fps conventions. The after count sums occurrences across these samples. A triangle-pair depth of zero can be a tangency.

| Clip | Before pairs | After pairs | Peak at one sample | Deepest pair in mm · zone · frame | Lowest sole (mm) |
| --- | ---: | ---: | ---: | --- | ---: |
| idle | 4841 | 0 | 0 | — | 0.0899 |
| walk | 16393 | 1366 | 15 | 0.9447 · Hips / Hips · f9.4 | -0.2199 |
| run | 3931 | 2480 | 59 | 1.8425 · LeftFoot / LeftLeg · f3.2 | 0.0898 |
| wave | 506 | 0 | 0 | — | 0.0899 |
| jump | 2541 | 156 | 5 | 0.0037 · Head / Head · f9 | 0.0899 |
| nod | 3411 | 36 | 1 | 0.0073 · Head / Head · f8 | 0.0899 |
| dance | 2870 | 523 | 5 | 0.0132 · Head / Head · f40 | 0.0899 |
| sit_down | 8139 | 3957 | 141 | 3.5501 · Hips / LeftUpLeg · f26.4 | 0.0898 |
| sit_idle | 67524 | 39386 | 140 | 2.4588 · Hips / LeftUpLeg · f56.8 | 0.0900 |
| stand_up | 6689 | 3171 | 142 | 3.6039 · Hips / LeftUpLeg · f2 | 0.0897 |
| hold_item | 13546 | 5597 | 29 | 4.0646 · RightArm / RightForeArm · f10 | 0.0900 |
| hold_box | 11009 | 2903 | 34 | 1.2542 · RightForeArm / RightHand · f12 | 0.0899 |
| hold_bag | 386 | 0 | 0 | — | 0.0899 |
| take_item | 5667 | 4023 | 36 | 6.6943 · RightArm / RightForeArm · f4.8 | 0.0899 |

[Baseline](qa/body_baseline.json) · [Baked floor](qa/body_bake_batch.json) · [Body self-check](qa/body_selfcheck.json) · [Khronos reports and hashes](qa/khronos.json) · [Every outstanding zone](qa/clearance_failures.md)

## 2. Auto-fit tool

[fit_module.py](fit_module.py) projects the neutral body to the male by region using a joint-pivot seed, same-facing surface correspondence and smooth distance weighting. It interpolates the resulting field with Laplacian smoothing across welded UV seams while retaining the triangle topology, UVs and material slots. It retains authored skinning where possible and blends in nearby male surface weights on mapped tops and bottoms. The fitter expands the displacement envelope using signed penetration plus 1.5 mm, including triangle-only hits, with a 30 mm clearance correction cap. Smoothing retains the highest sampled local requirement up to the cap. It exports and reimports the exact GLB and compares the numerical skin evaluation against Blender.

Use `./run.sh fit_module.py -- /absolute/neutral.glb male-custom.glb --slot top` from this folder. Slots are `hair`, `top`, `dress`, `bottom` and `shoes`. [Source and final measurement code](fit_module.py) · [Supplied checker adaptations](qa/checkers) · [Stage 2 smoke log](qa/fit-smoke.log)

## 3. Seven fitted modules

The cutoff is zero inside vertices, zero triangle pairs and ≥0.5000 mm signed clearance in the bind pose and all 14 clips. Peaks are the worst individual sample. Counts cover body-to-module intersections.

| Module | Triangles | MiB | Texture dimensions | Clearance gate | Peak verts / pairs | Minimum (mm) | On-body renders |
| --- | ---: | ---: | --- | --- | --- | ---: | --- |
| [male-hair-bob.glb](male-hair-bob.glb) | 2994 | 0.217 | 1024×1024 | PASS · Blender | 0 / 0 | 0.5837 | [Six views](renders/hair-bob/six-views.png) |
| [male-hair-spiky.glb](male-hair-spiky.glb) | 2972 | 1.011 | 512×512, 1024×1024, 512×512 | PASS · Blender | 0 / 0 | 2.6096 | [Six views](renders/hair-spiky/six-views.png) |
| [male-hair-sidepart.glb](male-hair-sidepart.glb) | 2982 | 0.118 | — | PASS · Blender | 0 / 0 | 0.8129 | [Six views](renders/hair-sidepart/six-views.png) |
| [male-tshirt.glb](male-tshirt.glb) | 4699 | 1.188 | 512×512, 1024×1024, 512×512 | FAIL · Blender | 22 / 71 | -4.6015 | [Six views](renders/tshirt/six-views.png) |
| [male-dress.glb](male-dress.glb) | 4042 | 0.921 | 512×512, 1024×1024, 512×512 | FAIL · Blender | 45 / 262 | -6.9323 | [Six views](renders/dress/six-views.png) |
| [male-jeans.glb](male-jeans.glb) | 4704 | 1.142 | 512×512, 1024×1024, 512×512 | FAIL · Blender | 66 / 193 | -7.8794 | [Six views](renders/jeans/six-views.png) |
| [male-sneakers.glb](male-sneakers.glb) | 3492 | 0.188 | — | PASS · Blender | 0 / 0 | 0.5173 | [Six views](renders/sneakers/six-views.png) |

[Full-outfit contact sheet](renders/outfits.png) · [Render settings and export hashes](renders/manifest.json)
[Clearance failures with clips, zones, frames and depths](qa/clearance_failures.md) · [Machine-readable stage summary](qa/summary.json) · [Independent visual review](qa/visual_review.md)

The reimported T-shirt and jeans have **0** layer overlaps at the rendered idle frame and **6** at bind. The hem was reshaped with extra motion probes after a taller trial caused larger intersections in walk. The sneaker fit links the liner, midsole and tread to keep its white toe cap intact. The dress retains small hem creases and the jeans retain heavier rear knee folds than the neutral reference. [Layer bake](qa/outfit_layer.json) · [Reimport](qa/outfit_layer_reimport.json)

All GLBs validate with zero Khronos errors. Remaining warnings occur on male-hair-bob.glb (1), male-hair-sidepart.glb (1), male-hair-spiky.glb (2). The warnings flag the nested skinned mesh nodes and, on Spiky, shader-generated tangents. [Validator details](qa/khronos.json)

## Runtime handoff

The headless [Three.js smoke check](qa/demo_runtime_smoke.json) exercises the existing demo’s rig and skeleton remapper. It uses offline texture placeholders. The Blender renders exercise the embedded materials. Consumers of the male motion bank need to play the non-Hips translations and animated scales to retain the baked clearances. The demo’s current shared-clip branch filters those channels when stripping horizontal Hips motion. Also wire the fitted modules and the male gestures against the male skeleton. The existing expression atlas expects face morphs on the neutral body and is outside this asset build.

## Rebuild and check

From this directory, rebuild the static assets with `./run.sh build_body.py`, retarget with `./run.sh build_motion.py`, and bake male motion with `./run.sh batch_clear.py`. Run `./run.sh body_audit.py` and `node verify_floor.mjs` for the body. The current fitter runs all slots with `node batch_fit.mjs 5`. The delivered clothing and shoes were chosen from multiple fit and render rounds. The shipped hashes are in the [delivery manifest](qa/delivery.json). Audit finished GLBs with `./run.sh gate_suite.py` and generate all views with `./run.sh render_modules.py`. The supplied checker copies can also run via `./run.sh gate_module.py -- male-hair-bob.glb`. Refresh the report with `node report.mjs`.
