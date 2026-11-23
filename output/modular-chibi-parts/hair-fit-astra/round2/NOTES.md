# Chestnut bob v2

**Final visual and technical verdict: PASS.** The exported module has **2,994 triangles** and occupies **227,404 bytes**. It contains one skinned hair mesh, one material and one embedded 1024 × 1024 JPEG. The Blender file includes the master body as an editable fitting reference. The GLB contains only the hair and its skeleton.

## What changed

The ear opening, the temple point and the outer side curtain now follow one continuous modeled surface. The fuller curtain behind the ear turns under and meets a scalp-fitted lining. This closes the opening that showed the background between the v1 side locks. The swept fringe was rebuilt as six tapered sections around the original part position. Their tips follow the exposed forehead. The side and back share a continuous strip in the chestnut texture atlas, with the longitudinal UV wrap at the nape. A small allowance in the low occipital lining maintains clearance as the neck bends in the run cycle.

The hair uses the 65 joint names, order, hierarchy and inverse bind matrices of the supplied base. It uses at most two nonzero, normalized influences per vertex. Head carries the hair and Neck contributes a smooth falloff reaching 10.50% at the lower rear. The armature modifier supplies the master rig for the root-level glTF mesh. The saved Blender mesh is parented to the armature. The round-trip audit verified the exported binding against `base_body.glb`.

## Appearance and fit

The author and a separate image-only reviewer inspected the final six views and four action PNGs. Both profiles show the lower hair turning in behind the ear, with no strip of grey background between locks. The chestnut surface above each ear is continuous. The naturally darker hair along the rim follows the shape of the ear opening. All three frontal views show skin between the upper eye rims and fringe tips, including the outer corners. The rounded silhouette, crown part and pointed central fringe remain recognizable in the front reference.

**Remaining differences.** The lower nape edge is slightly faceted and blunter than the pointed ends in the reference. The side panels are shorter and have fewer separately visible tips. The supplied style reference shows a blank face from the front. The fitted master and the fixed three-quarter cameras establish eye clearance, and the side and rear shapes are modeled interpretations.

| Rest-pose measurement | Samples | Clearance |
| --- | ---: | ---: |
| First layer over the upper scalp | 5,941 | 4.330–9.947 mm |
| First layer on the side and rear, down toward the nape | 3,602 | 4.185–11.047 mm |
| Vertical clearance over the crown | 1 | 5.129 mm |

The upper-cap probe covers all azimuths at two-degree intervals from 25° elevation to the pole. The side and rear probe covers the surface inside the designed hem at absolute azimuths of at least 75° and at elevations through 25°. Every sampled ray hit hair. Clearance is the distance from the first hair surface to the nearest head surface. The outside of the rolled hem includes the modeled thickness of the hair.

Eye occlusion was also tested at the pixel centers of the three 520 px views. Rays first identified bare-master eye triangles visible to each camera, then tested the exported hair along the same lines of sight.

| Camera | Visible bare-master eye pixels | Pixels hidden by hair |
| --- | ---: | ---: |
| Front | 8,760 | 0 |
| Three-quarter, camera +X | 7,064 | 0 |
| Three-quarter, camera −X | 7,039 | 0 |

## Supplied checker RESULT tables

Khronos glTF Validator 2.0.0-dev.3.10 reported **0 errors and 0 warnings**. Both supplied checker scripts ran unchanged on the reimported GLB, against the specified master and motion file. The wrapper uses Cycles CPU for rendering because headless Workbench had crashed in round 1. The pose data, quaternion rotation modes, action slots, cameras, frame selection and measurement code come directly from the original scripts. A separate temporary output directory for each invocation preserves both JSON reports, since both scripts write `motion_check.json`. The four published action PNGs come from the vertex checker.

### Vertex checker

| Clip | Max vertices inside | Minimum signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.005818413 |
| walk | 0 | 0.004900000 |
| run | 0 | 0.004800000 |
| wave | 0 | 0.004900000 |
| jump | 0 | 0.004900000 |
| idle | 0 | 0.004900000 |
| nod | 0 | 0.004900000 |
| dance | 0 | 0.004900000 |

### Triangle checker

| Clip | Max triangle overlap pairs | Minimum signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.005818413 |
| walk | 0 | 0.004900000 |
| run | 0 | 0.004800000 |
| wave | 0 | 0.004900000 |
| jump | 0 | 0.004900000 |
| idle | 0 | 0.004900000 |
| nod | 0 | 0.004900000 |
| dance | 0 | 0.004900000 |

The vertex checker uses 12 sampled frames per clip. The triangle checker tests every third integer frame. Both round animated minimum distances to four decimal places in metres.

### Supplemental full-frame audit

| Clip | Integer frames | Max vertices inside | Max triangle overlap pairs | Min signed distance (mm) |
| --- | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | 0 | 5.818413 |
| walk | 57 | 0 | 0 | 4.880096 |
| run | 31 | 0 | 0 | 4.761484 |
| wave | 65 | 0 | 0 | 4.884686 |
| jump | 51 | 0 | 0 | 4.890975 |
| idle | 89 | 0 | 0 | 4.888486 |
| nod | 57 | 0 | 0 | 4.888949 |
| dance | 65 | 0 | 0 | 4.864722 |

The full audit includes both endpoints and covers all 416 integer frames, including rest. Its lowest signed distance was **4.761484 mm**, during run. Fractional frames were outside the audit.

## Capture and reproduction

`fit_views_v2.png` was rendered from the reimported GLB on the original master, using the round-1 camera function unchanged. The sheet is 1560 × 1040. Each orthographic tile is 520 × 520, spans 0.55 m and targets (0, 0, 0.807). The first row is front and the two opposing three-quarter views. The second row is left profile, back and right profile. The camera vectors, lighting, AgX view transform and Cycles CPU settings match round 1.

From this directory run the supplied guarded Blender 5.1.2 executable with `-b -noaudio --python-exit-code 1 --python fit_hair_v2.py`. The default entry point builds the blend and GLB, runs both checkers, renders the sheet and runs the fit, skin, validation and full-frame audits. Optional stages following `--` are `build`, `vertex`, `tri`, `sheet` and `audit`. The local Khronos validator requires Node.js and the repository's installed `gltf-validator` package. The build reads the adjacent round-1 Blender file and camera/fitting helpers. A separate build using the delivered script reproduced the GLB byte for byte.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| hair_bob_v2.glb | 227,404 | `32cadfa94be111706295032933e823529364047484f2cd78b71c7919abfd811d` |
| hair_bob_v2.blend | 1,132,456 | `9dc521e0908a481383ecc73e9e2a9a5e6d24f6bb322e81a7cd4d83a45713d9b7` |
| fit_hair_v2.py | 22,329 | `9310ae38380b01bb92fb7f630c40f54e068eeccfd8c8819e2e24c8280863b545` |
| fit_views_v2.png | 1,864,360 | `798c15e08d0e48dff69bd719457f9e9ab3ceec5ef0c03003f62f411aa2de98e1` |
| walk.png | 278,679 | `69c37954a4e24912c27b5ebeee4796f7ab554ffeb4cf33259338a413a454cca6` |
| run.png | 276,909 | `7fc54afbd4a488d083b20687f46489dac6e40aca8cbfb4ffea210c718fb3643e` |
| wave.png | 276,757 | `939f115b0b5209a55059eafa354b8d25d256548e1c1901b5fdc213ac621fbccb` |
| jump.png | 277,143 | `1fb09a172557490c9483f84af9894e3c31f28d5703faa5281b464dc4b65818eb` |
| motion_check.json | 181 | `5c7d324cbc24e45443b1e0d0392aac77ba98e33f2d8de0fe2e5f4c32d55172d0` |
| motion_check_tri.json | 181 | `5c7d324cbc24e45443b1e0d0392aac77ba98e33f2d8de0fe2e5f4c32d55172d0` |

| Read-only input | SHA-256 |
| --- | --- |
| Round-1 blend | `77ba009b2a0f0180a0790daa5bd0d0ff64a6bdc042db4659e449b7f654c9e9fb` |
| Round-1 build and camera helpers | `26e739e2c5da70894cda2072113c49f2b96e0b097607494db9a3e24ed10dd1b7` |
| Style reference | `b46ed818f83ebebc61ad95ad8bf784f65ee5246cebc1f87434d9bf5e35537939` |
| Rigged master | `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f` |
| Motion GLB | `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410` |
| Vertex checker | `5e5b269858431688f2f853a38230227362cb88faf9aa2f588e514840486e96d8` |
| Triangle checker | `c1b94e4b5b8c6fa20f93675ebc504652ca6f978d39768ceee644a4f8ab7828d3` |
