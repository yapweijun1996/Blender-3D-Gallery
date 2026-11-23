# Chestnut side-part quiff

**The detachable hair module has 3,000 triangles and occupies 1,681,712 bytes.** The exported GLB contains one mesh, one material, three embedded 1024 × 1024 maps, and the master’s 65-joint skeleton. The compressed Blender file includes the rigged master body as a fitting reference. The GLB can be mounted at the master origin. It contains no body geometry or clips.

## Source, extraction and fitting

Four orthographic source renders established that the Studio mesh already faces Blender −Y, with Z up. The tall forelock turns toward the viewer’s left and the shorter fan starts at the part on the viewer’s right. Imported dimensions were approximately 0.978 × 0.906 × 0.837 in Blender units. Blender imported 9,398 triangles. The base-color image was 4096². The tangent normal and packed roughness/metallic images were 2048².

Welding coincident UV-seam vertices revealed one connected mesh. The unwanted central concave scalp/face underside shares the chestnut material with the strands. A continuous cut isolates it by its position and connected surface. The build removes the central shell and two internal retopology fins. It keeps the exterior quiff, the rolled strand ends and their surface detail. The rounded rear contour comes from the Studio geometry.

The build collapses the exterior in source space, makes a padded UV atlas, and resamples the original color, tangent normal and roughness/metallic maps. The normal transfer accounts for the UV tangent frames. The fitted material attenuates tangent relief on the smooth occiput. This removes stair-stepped highlights after GLB reimport. The lip turns under along the brow and joins a single skull-fitted lining. Both sides use continuous geometry from the source. Local support edges stabilize the fit behind the ear. Welding GLB attribute duplicates on reimport yields one connected surface with **zero non-manifold edges**.

## Rig and rest fit

The joint names, order and parent-child relationships match the master’s reference GLB. The inverse bind matrices match within 0.000001 absolute tolerance. The exported weights sum to one at every vertex. Head carries the hair. A smooth lower-rear Neck falloff reaches **2.961%**. The maximum number of active influences is two. A stronger trial falloff pulled the central nape inward during the run cycle.

The rest-pose audit samples every 0.5° of azimuth and elevation from −60° to the pole about (0.001, 0, 0.807). Each ray starts just outside the master skin, hits the first hair surface, and measures its nearest distance to the head. This measures the surface seated on the skull. The tips and raised outer quiff have additional thickness.

| Measurement | Ray hits | Clearance |
| --- | ---: | ---: |
| First hair surface across all covered directions | 147,408 | 4.324–11.768 mm |
| Upper cap, elevation ≥ 25° | 94,320 | 4.576–9.534 mm |

Every upper-cap ray hit hair. On each sampled meridian, coverage continued from the first hit through the crown. At 520 px per view, ray comparisons against the bare master found **0 of 8,760** visible eye pixels obscured from the front, **0 of 7,064** from the +X three-quarter view and **0 of 7,039** from the −X three-quarter view.

## Supplied checker results

Both original checker scripts ran unchanged on the exported GLB, the requested rigged master and the supplied motion GLB. Separate output directories prevent one checker from replacing the other’s JSON. The vertex checker samples 12 frames per clip. The triangle checker samples every third integer frame. Both report animated distances rounded to 0.0001 m. The scripts bind Blender 5 action slots and use the existing quaternion rotation modes.

### Vertex checker

| Clip | Max vertices inside | Minimum signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.006010915 |
| walk | 0 | 0.006000000 |
| run | 0 | 0.006000000 |
| wave | 0 | 0.006000000 |
| jump | 0 | 0.006000000 |
| idle | 0 | 0.006000000 |
| nod | 0 | 0.006000000 |
| dance | 0 | 0.006000000 |

### Triangle checker

| Clip | Max triangle-overlap pairs | Minimum signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.006010915 |
| walk | 0 | 0.006000000 |
| run | 0 | 0.006000000 |
| wave | 0 | 0.006000000 |
| jump | 0 | 0.006000000 |
| idle | 0 | 0.006000000 |
| nod | 0 | 0.006000000 |
| dance | 0 | 0.006000000 |

### Supplemental integer-frame check

| Clip | Frames | Max vertices inside | Max overlap pairs | Minimum signed distance (mm) |
| --- | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | 0 | 6.010915 |
| walk | 57 | 0 | 0 | 5.997951 |
| run | 31 | 0 | 0 | 5.979486 |
| wave | 65 | 0 | 0 | 6.006600 |
| jump | 51 | 0 | 0 | 6.006515 |
| idle | 89 | 0 | 0 | 6.010174 |
| nod | 57 | 0 | 0 | 6.005023 |
| dance | 65 | 0 | 0 | 6.003711 |

The full pass includes 416 rest/animated frame evaluations and both clip endpoints. Its lowest signed vertex distance was **5.979486 mm** during run. Fractional times between frames were outside this check.

## Visual review

The author and a separate image reviewer inspected the six views of the final reimported module. The first row shows front and the +X and −X three-quarter views. The second row shows the character’s left side (+X), rear and right side (−X). Both ear rims have continuous hair-to-skin contours with no visible background slit or jagged join. The fringe clears the eye corners. The rear cap has a smooth chestnut gradient.

The upturned tips are thicker and blunter than in the reference. Small dark facets remain on two side-facing lock ends. Angular overlaps remain in the lower locks above the opposite temple, clear of the ear rim. The supplied reference shows only the front, so it cannot establish side or rear likeness.

The six-view sheet uses the bob’s fixed 0.55 m orthographic camera and Cycles CPU lighting at 520 × 520 per tile. The four motion stills use each supplied clip at its 40% sample. The native headless Workbench failure recorded on this same Blender runtime in the bob work prompted the Cycles CPU fallback. The published jump image shifts the checker camera vertically to retain the entire airborne crown with 0.10 m above it. The pose, projection scale and collision measurements are unchanged by that capture adjustment.

## Reproduce locally

Use Blender 5.1.2, the supplied local guard, the project layout and the repository’s installed Khronos validator. From this module directory, run the following commands.

```sh
sh work/blender.sh --python fit_hair.py
sh work/blender.sh --python fit_hair.py -- dense
```

The default stages are `build`, `sheet`, `vertex`, `tri` and `audit`. The optional `dense` stage repeats the collision checks at every integer clip frame. The build imports shared mesh and camera utilities from `../../hair-fit-astra/fit_hair.py`. The launcher keeps Blender’s temporary working files in this module. Geometry, material transfer, skinning and rendering run in Blender. Offline validation uses the installed `gltf-validator` Node package. Khronos Validator 2.0.0-dev.3.10 reported **zero errors and zero warnings**.

## Verified artifact set

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `hair_sidepart_v1.glb` | 1,681,712 | `b7a692b7cc2d726dbe469fa70770944649a8511d67a6b37b76b81e6e7903fff1` |
| `hair_sidepart_v1.blend` | 2,527,769 | `258da0f5154f899e4f170fb633d78fc3ea24de071f9a6cf4b3db0aade53386a7` |
| `fit_hair.py` | 35,678 | `4dc69864f82eaca50c3fef50b2e7c99270566079eef2977cc6948885b9f040e5` |
| `fit_views.png` | 2,113,585 | `9df387997dab73ddcac930ec127b842cc42ccc27f36cad08bf1491ae2cab6746` |
| `walk.png` | 284,436 | `d9b41c1863906bef38927fa0c965555faf21778465f1ccacabbd122581be43cc` |
| `run.png` | 283,574 | `3595619489aa233bbc434c6dac6f4f3d6ef09ae86beeb11b9dfe07e4905e45d6` |
| `wave.png` | 283,122 | `89438f10ca1f63dd2e2512f63d32fb5cabd150ab209859693366918677b4d476` |
| `jump.png` | 283,621 | `09697d35ef6180c8c77ffd351287455a5a0f3e11a25b1e893e9acd23899ccec2` |
| `motion_check.json` | 175 | `8ce3e722a09ac508b160b71489623704ad1581aa283bbbc12f3fb5b9581d6fd2` |
| `motion_check_tri.json` | 175 | `8ce3e722a09ac508b160b71489623704ad1581aa283bbbc12f3fb5b9581d6fd2` |
| `khronos_validation.json` | 1,787 | `b2a84c83ed98a9202a3049d479768180b03d236ed503e97f35eaa31506c813ee` |

## Read-only inputs

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `source_studio_retopo.glb` | 4,942,592 | `e339824e4fa613dcb8cc263616cc24555b886d92e2ddc6a17eb3425cee135619` |
| `hair-04-male-sidepart.png` | 355,371 | `40249b24cb40b4aab165960d4a8167b92a5f49903a2b823da304d732ea0bd80f` |
| `GJH_Chibi_Master_rigged.blend` | 978,143 | `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f` |
| `base_body.glb` | 776,124 | `404d83fa84630baf77a2d7fb443c80955ab5270e3dc09b652c7167547b8ae853` |
| `motion.glb` | 5,388,704 | `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410` |
| `fit_hair.py` | 33,745 | `26e739e2c5da70894cda2072113c49f2b96e0b097607494db9a3e24ed10dd1b7` |
| `motion_check.py` | 3,117 | `5e5b269858431688f2f853a38230227362cb88faf9aa2f588e514840486e96d8` |
| `motion_check_tri.py` | 3,253 | `c1b94e4b5b8c6fa20f93675ebc504652ca6f978d39768ceee644a4f8ab7828d3` |
