# Chestnut twin tails v1

The detachable hair module contains one mesh, one material and the master skeleton. The exported GLB has **2,918 triangles** and occupies **1,805,916 bytes**. Khronos glTF Validator 2.0.0-dev.3.10 reported **0 errors and 0 warnings**. The editable Blender scene includes the original rigged base body as a fitting reference.

## Extraction and fitting

Blender 5.1.2 imported the Studio model upright along +Z, facing −Y. The face opening and fringe are visible from −Y and the central nape part is visible from +Y. The original mesh is 0.978 source units wide and 0.787 high. Welding coincident UV seams produced one connected 9,746-triangle mesh. The skin-colored face, ears and neck were fused into the hair and shared its material.

The build traces the connected mannequin skin in the original base-color atlas, cuts the buried nape return and clears the ear rims. The outer hair, purple ties and long curled tails come from the Studio mesh. Each short cheek lock keeps its own root. Its lower section follows the original sliced centerline and cross-section dimensions, replacing a fold where the Studio face and strand met. Chestnut values for these repaired ends are sampled from the outward-facing original strands. The cap turns inward at the cut edge and joins a newly fitted, concave hair lining. The separate hair-only image shows the empty opening from the front and underneath.

The head-fit deformation pulls the loose tails toward the ears and lifts the lateral fringe clear of the eye rims. Surface-aware collapse is applied in the fitted coordinates. A new UV atlas samples the Studio color, roughness/metallic and tangent-normal maps from the detailed fitted mesh. This preserves strand shading across the source's 767 UV islands. All three maps are embedded at 1024 × 1024 px. The base-color factor is tinted chestnut. The GLB has **1 connected shell, 0 open edges and 0 nonmanifold edges** after welding glTF attribute splits at 0.0000001 m.

The GLB uses the same 65 joint names, order, parent–child hierarchy and inverse bind matrices as `master/base_body.glb` within 0.000001 absolute matrix tolerance. Weights are normalized, with a maximum of 2 nonzero influences per vertex. Head carries the wig. Neck weight rises smoothly to 10.50% on the low rear strands. Animation comes from the shared master rig.

## Rest fit and visual inspection

| Checked surface | Samples | Gap in mm |
| --- | ---: | ---: |
| Vertical outer crown at the skull center | 1 | 10.662 |
| First hair surface above the upper scalp | 5,941 | 4.820–9.705 |
| Skull-facing lining, including its lower course | 79,560 | 4.258–9.747 |

The upper scalp test casts one ray every two degrees in azimuth and elevation from 25° through the pole. All rays hit. The lining test samples 153 barycentric positions per triangle, including vertices and edges. The minimum Euclidean clearance over the same sampling of the **whole hair mesh** was 4.258 mm. The minimum signed normal projection over those static triangle samples was 2.810 mm. The supplied motion checkers report signed distances at vertices. The raised ridges and free ponytail ends extend beyond the fitted lining.

The six orthographic panels, each 570 × 570 px, show the front, +X and −X three-quarter, left profile, back and right profile in reading order. Blender reimported the exact GLB onto the unchanged master for these Cycles CPU captures. Front/three-quarter eye rays identified the visible eye triangles of the bare master and then tested the hair on those sight lines.

| View | Visible bare-master eye pixels | Hidden by hair |
| --- | ---: | ---: |
| Front | 5,958 | 0 |
| Three-quarter +X | 4,817 | 0 |
| Three-quarter −X | 4,798 | 0 |

The author and an independent reviewer inspected the final six views and the isolated hair. The scalp and nape stay covered behind the ear roots. The short temple locks have smooth lower surfaces and clear both outer eye corners. The lower curls turn inward, leaving intentional openings between their free ends and the cheeks. The exposed inside is chestnut, with no visible source face, ears or neck. Walk, run, wave and jump retain both tails and the eye openings.

**Remaining differences.** The low-poly tips have flatter facets than the reference. The middle three-quarter view shows a few short dark marks on a bang and a tail. A small angular tab remains at one rear cap-to-tail junction. The purple ties look narrower and shinier than in the front reference. The Studio mesh supplied the side and rear shapes because the reference shows only the front.

## Supplied checker results

The two unchanged checkers were run against the shipped GLB, the rigged master and `models/tripo-chibi-motion/motion.glb`. Both original action-slot selections and frame schedules were retained. Pose-bone quaternion rotation modes were preserved. The previously established headless Workbench crash on this machine was handled with the bob's Cycles CPU frame handler. Each invocation had its own output directory because both scripts write a file named `motion_check.json`. The four action PNGs show the vertex checker’s 40% clip frames. Its static camera clipped the top of the jumping hair. The delivered jump PNG uses the same evaluated frame, view direction, orthographic scale and lighting, with the camera centered vertically on the posed figure. The raw checker image is retained in `work/jump_checker.png`.

### Vertex RESULT

| Pose or clip | Maximum vertices inside | Minimum signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.006161289 |
| walk | 0 | 0.006100000 |
| run | 0 | 0.005400000 |
| wave | 0 | 0.006200000 |
| jump | 0 | 0.006200000 |
| idle | 0 | 0.006200000 |
| nod | 0 | 0.006200000 |
| dance | 0 | 0.006200000 |

### Triangle RESULT

| Pose or clip | Maximum overlapping triangle pairs | Minimum signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.006161289 |
| walk | 0 | 0.006100000 |
| run | 0 | 0.005400000 |
| wave | 0 | 0.006200000 |
| jump | 0 | 0.006200000 |
| idle | 0 | 0.006200000 |
| nod | 0 | 0.006200000 |
| dance | 0 | 0.006100000 |

### Supplemental integer-frame sweep

The vertex checker samples 12 frames per clip. The triangle checker samples every third integer frame. The supplemental sweep evaluates every integer frame including both endpoints. Measurements between integer frames are outside this test.

| Pose or clip | Frames | Maximum vertices inside | Maximum triangle pairs | Minimum signed distance (m) |
| --- | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | 0 | 0.006161289 |
| walk | 57 | 0 | 0 | 0.006138390 |
| run | 31 | 0 | 0 | 0.005382352 |
| wave | 65 | 0 | 0 | 0.006161289 |
| jump | 51 | 0 | 0 | 0.006153341 |
| idle | 89 | 0 | 0 | 0.006155959 |
| nod | 57 | 0 | 0 | 0.006148612 |
| dance | 65 | 0 | 0 | 0.006137088 |

## Rebuild and inspect

From this directory, use the guarded local Blender executable given in the task, with `-b -noaudio --python-exit-code 1 --python fit_hair.py`. The optional stage arguments after `--` are `build`, `sheet`, `underside`, `vertex`, `tri` and `audit`. A default invocation runs all six. The pipeline uses the bob's local Blender helpers, the supplied checker scripts in `work/` and the repository's installed Khronos validator. For a workspace-local Blender temporary directory, create `work/tmp` and set `TMPDIR` to its absolute path before launching Blender. Source and motion files are read-only. The validation data and image hashes below identify this particular export.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| hair_twintails_v1.glb | 1,805,916 | `d8a2ea69efc3d309f30a9dac7511fccea23964d801defdd12b3cf18a65777688` |
| hair_twintails_v1.blend | 2,630,637 | `db9fff9041eb20ca53ed5ba018eda3114044e1fd53fdaa59dad839f68740bccb` |
| fit_hair.py | 43,618 | `307c5bbb76a7a26fbe34ac47d9b6f27b3a13856bbe4eb7f9ce6d3d916fdb8950` |
| fit_views.png | 2,436,621 | `f8da24adbe35d88037cc0cecaec802d810bf80078aa17df2851d2d6603a1c420` |
| walk.png | 293,403 | `1f01c5e5675b5674ec36d0e5698100a15c9d78980cf5a3b95ea2dbbd47d12f6f` |
| run.png | 292,552 | `886b99b25d530c2a148a62250bc624376e69e25851f90a7e1d47d26860ee5913` |
| wave.png | 291,587 | `dc3187cbc203236fbac223ee3849d369b46b82059880653a4d6931fbebc75a43` |
| jump.png | 292,719 | `754a44c19104c2ef37d4223a414049fdbc5864cc62da52f4ab7c3c323386277d` |
| motion_check.json | 181 | `6d5bb529dee33c17ac7de00ab8ef45c48344a04f3080925782358636471d3a05` |
| motion_check_tri.json | 181 | `7dfb002ae69a9221487fcf5a5fca7442ddfe7f508dacab377e5c5445603b5fba` |
| work/hair_underside.png | 776,877 | `977e34562a56694777164563d13a2f8ccc24357e07a614a20402e3aa90dad76c` |
| work/jump_checker.png | 292,256 | `c47bdbe23fd9bce0e6b2c0da62e274291a9d153025aef33e5af9fa1950dfa55a` |
| work/asset_audit.json | 1,601 | `2639c62304de83ab446844a77d36cc34689161091faf21f9b6cd068604edae1e` |

| Input | SHA-256 |
| --- | --- |
| source_studio_retopo.glb | `63e41238ef1bfb684f582c22ce928cf9ac3e17d175377ba5ca32f6ece5b470ff` |
| GJH_Chibi_Master_rigged.blend | `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f` |
| base_body.glb | `404d83fa84630baf77a2d7fb443c80955ab5270e3dc09b652c7167547b8ae853` |
| hair-03-twin-tails.png | `b1dfac70cb3f808f8e17d1de04aba9ceb570fd12b864297adc3dc49053b57e33` |
| motion.glb | `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410` |
| fit_hair.py | `26e739e2c5da70894cda2072113c49f2b96e0b097607494db9a3e24ed10dd1b7` |
| motion_check.py | `5e5b269858431688f2f853a38230227362cb88faf9aa2f588e514840486e96d8` |
| motion_check_tri.py | `c1b94e4b5b8c6fa20f93675ebc504652ca6f978d39768ceee644a4f8ab7828d3` |
