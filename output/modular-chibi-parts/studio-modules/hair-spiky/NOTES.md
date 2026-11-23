# Spiky hair module v1

The runtime GLB contains one skinned hair mesh with **2,972 triangles** and occupies **1,957,368 bytes**. The editable Blender scene includes the master body as a fitting reference. Its hair material packs the original Studio base color, roughness/metallic and tangent-space normal maps, each transferred to a 1024 × 1024 atlas for the reduced mesh. The rolled underside uses a chestnut material.

## Source and fit

The Studio export has 9,935 triangles and one connected hair, cheek, ear and neck surface after welding UV seams. Orthographic views from four cardinal directions, above and below show the blank face and swept fringe facing Blender −Y. Its Blender bounds span 0.978 × 0.904 × 0.916 before fitting. The master also faces −Y. The fitting script preserves handedness, scales the source to the master, raises the fringe clear of the eye corners, and brings the side curtain down around the ear.

The extraction follows the skin–hair color boundary in the source UV atlas. It removes the face/ear/neck surface, deep nape returns and a stray one-sided triangle. The original asymmetric crest and both sets of side locks supply the exterior. The fitted inner surface joins the outer hair around a continuous rolled hem. A small fitted section closes the deep groove beneath the swept part. An exact geometric split and a solid-angle winding test discard buried folds before the final silhouette-preserving collapse. The exported mesh reimports as one connected component with **zero boundary edges, zero nonmanifold edges and 0 intersecting non-adjacent triangle pairs** after welding glTF UV and material seams.

The source paint was resampled against the original fitted strands after reducing the mesh. The transfer interpolates the source UVs, rejects nearby back-facing layers, transforms detailed normals to the new tangent frame and pads the new islands. The material multiplier warms the chestnut under the same studio lights used for the bob.

## Clearance and appearance

| First fitted hair surface on the resting head | Rays | Clearance (mm) |
| --- | ---: | ---: |
| Upper scalp | 5,941 | 5.669–9.015 |
| Sides and nape | 2,148 | 6.466–9.424 |
| Vertical crown | 1 | 8.252 |

Every sampled direction hit hair. Upper sampling uses two-degree azimuth/elevation steps from 25° elevation through the pole. The second grid covers both sides and the rear from ±75° azimuth, beginning above the ear openings and extending down to −26° at the nape. Values measure from the first hair surface to the master skull. The swept tips and overlapping outer locks have additional sculpted thickness.

Pixel-center ray tests compare both visible bare-master eyes against the exported hair in each frontal camera. Front, camera +X three-quarter and camera −X three-quarter hid **0 of 7,350**, **0 of 5,938** and **0 of 5,917** visible eye pixels respectively.

The author and an independent image reviewer inspected the final six views and four action PNGs. Both profiles show a continuous curtain above and behind the ear into the nape, with no visible join or daylight behind either ear. The asymmetric sweep, narrow upright crest and central fringe remain legible at action-render scale. Both outer eye corners are clear. The jump framing includes the complete crown.

Close-up differences remain. A small twig-like projection is visible on the viewer-right outline in the front view. Several short lock ends near the ears look squarer than the pointed tips in the reference. Under the QA lights the color reads a little lighter and more rose-brown than the reference. The reference shows only the front. The rear shape follows the supplied Studio geometry.

## Skeleton and motion

The GLB uses the master origin, one skin, 65 joint names in master order, identical child hierarchies, and inverse bind matrices matching the base GLB at absolute tolerance 0.000001. Every vertex has normalized weights with at most 2 active influences. Head carries the hairstyle. Neck weight rises smoothly to 9.79% on the lowest rear strands. The GLB contains the hair and rig. The report and renders use Blender 5.1.2. Khronos glTF Validator 2.0.0-dev.3.10 reported 0 errors and 0 warnings.

Both supplied checker files ran unchanged on the delivered GLB with the specified master and motion files. Their Blender 5 action slots were assigned and quaternion rotations retained. The known headless Workbench issue on this runtime was handled with the bob's Cycles CPU render-only hook. The vertex checker samples 12 frames per clip, the triangle checker every third integer frame. Both print animated minimum distances rounded to four decimal places in metres.

### Vertex checker RESULT

| Pose | Max vertices inside | Minimum signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.005635495 |
| walk | 0 | 0.005200000 |
| run | 0 | 0.005200000 |
| wave | 0 | 0.005200000 |
| jump | 0 | 0.005200000 |
| idle | 0 | 0.005200000 |
| nod | 0 | 0.005200000 |
| dance | 0 | 0.005200000 |

### Triangle checker RESULT

| Pose | Max triangle-overlap pairs | Minimum signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.005635495 |
| walk | 0 | 0.005200000 |
| run | 0 | 0.005200000 |
| wave | 0 | 0.005200000 |
| jump | 0 | 0.005200000 |
| idle | 0 | 0.005200000 |
| nod | 0 | 0.005200000 |
| dance | 0 | 0.005200000 |

### Supplemental all-integer-frame audit

| Pose | Frames | Max vertices inside | Max overlap pairs | Minimum signed distance (mm) |
| --- | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | 0 | 5.635495 |
| walk | 57 | 0 | 0 | 5.201365 |
| run | 31 | 0 | 0 | 5.086180 |
| wave | 65 | 0 | 0 | 5.211382 |
| jump | 51 | 0 | 0 | 5.208461 |
| idle | 89 | 0 | 0 | 5.209086 |
| nod | 57 | 0 | 0 | 5.206719 |
| dance | 65 | 0 | 0 | 5.200650 |

The supplemental audit includes all 416 integer frames counting rest, including clip endpoints. Fractional animation times were outside this measurement.

## Files and reproduction

From this module directory, use the supplied guarded Blender executable and its supplied `DYLD_INSERT_LIBRARIES`, followed by `-b -noaudio --python-exit-code 1 --python fit_hair.py`. The default stages are `build`, `sheet`, `vertex`, `tri` and `audit`. To run one stage, append for example `-- tri`. The original round-1 bob script supplies shared BVH, clearance and lighting helpers. The validator uses the existing repository Node package. Its two informational messages describe unused UVs and tangents on the constant-color underside. Inputs remain in their original repository locations.

The 1560 × 1040 six-view sheet shows the reimported GLB. Its top row is front and both three-quarters. Its bottom row is left profile, back and right profile. Each 520 px orthographic tile spans 0.60 m to keep the outward-swept spikes inside all six frames. Walk, run, wave and jump use the supplied action poses at the checker's 40% frame. The original jump camera crops the crest. The delivered jump image centers the character vertically at the same pose and scale. The unadjusted checker frame is preserved in `work/checker_jump.png`. Both original RESULT JSONs are at the module root. The complete checker logs are in `work/motion_check.log` and `work/motion_check_tri.log`.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| hair_spiky_v1.glb | 1,957,368 | `f5927f87adf8250513d30a29f39f2f0d7689062ddd8d456478b28f79296ea5be` |
| hair_spiky_v1.blend | 2,792,955 | `411c857d92882954bc1a7e9f88cd24319307ceaa0af3b087ab2eb6882c011511` |
| fit_hair.py | 40,659 | `c1ba244f6c293322e81ebe49a524be5117dd162b1ee6460cfd4695a768efc4d5` |
| fit_views.png | 2,114,875 | `e921d9343ea058a5656b1bfe3079e9ad8f14d38e175a58da3606bb968b619f76` |
| walk.png | 286,410 | `2059b2f4d14ac102cff929219c65440db57f3ed7e57ac8aa2374711c0ffafef2` |
| run.png | 284,795 | `9a334bd9b8a2ebd58c5952259378544d78aedb4f1394c8a74bdbfe948ce929ca` |
| wave.png | 284,647 | `55bd85ff2d721607c81e7e0a62bde95d47585e645cc78589ee290f4fd9a54b19` |
| jump.png | 285,709 | `8d4e286862af68004e65a89be19e3e8b80c39f62d3ca633dc1c2c5309cb0c11a` |
| motion_check.json | 181 | `7f2c7c8ab759b772a113980a769f372621d3773a30b04e63b8a539851f7d3107` |
| motion_check_tri.json | 181 | `7f2c7c8ab759b772a113980a769f372621d3773a30b04e63b8a539851f7d3107` |
| work/fit_audit.json | 1,514 | `ce6bd4abe34276f5c09edfb06ce51b172df91f911c62bf7d36b27066bfb1e2cf` |
| work/gltf_validator.json | 2,206 | `71518a5e6aef0d859a1b0ced7b00a510b647dd18800f1b333738d1423d267557` |
| work/checker_jump.png | 283,613 | `7ce67dde87e5f384372781bab1cdcfba58d3a89222e6ac81598c97aed5cc8a8a` |

| Read-only input | SHA-256 |
| --- | --- |
| source_studio_retopo.glb | `40aedef505ffc62b1b3bb60292931c9472b8a4dbcd6e02a5d5474cb22a48f19d` |
| hair-02-spiky.png | `635e30231cd811d580b93f7668beb982e6fc50fe1b96d18ed0f7008eef7addc2` |
| GJH_Chibi_Master_rigged.blend | `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f` |
| motion.glb | `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410` |
| fit_hair.py | `26e739e2c5da70894cda2072113c49f2b96e0b097607494db9a3e24ed10dd1b7` |
| motion_check.py | `5e5b269858431688f2f853a38230227362cb88faf9aa2f588e514840486e96d8` |
| motion_check_tri.py | `c1b94e4b5b8c6fa20f93675ebc504652ca6f978d39768ceee644a4f8ab7828d3` |
