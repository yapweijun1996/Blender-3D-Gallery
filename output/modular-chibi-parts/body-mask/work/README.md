# Body-region masking for modular chibi outfits

The region GLB contains 16 named skinned meshes and one skin with the original 65 Mixamo joints. Each original triangle goes to the region with the largest sum of its three corners' skin weights. Where bone weights alone cannot express the cut, the Neck contribution above rest-space glTF Y = 0.621 belongs to the head, and the Hips contribution at or above Y = 0.373 belongs to the torso. Names ending in `_L` and `_R` use the character's left and right.

The splitter copies the positions, normals, UVs, joint indices and weights for each referenced vertex byte for byte. A vertex referenced by more than one region is copied at the same position with the same influences. Texture data and inverse bind matrices are preserved. Khronos validation of the final export reported zero errors and zero warnings. The Node test compares all oriented triangle corners and skin attributes to those of the original body.

## Manifest convention

`hides` is an optional array of distinct region names on a module. An omitted or empty array hides no regions. The runtime counts references across the currently worn modules and hides each named body mesh while its count is positive. Removing the final reference restores the mesh. Stored outfit choices do not carry their own hide lists.

| Existing garment or module | Proposed `hides` |
| --- | --- |
| Tripo Hoodie v1–v3 and Studio Jacket v1 | `["torso","upper_arm_L","upper_arm_R","forearm_L","forearm_R"]` |
| Sol T-shirt v1–v3, Astra T-shirt v1 and Studio T-shirt v1 | `["torso","upper_arm_L","upper_arm_R"]` |
| Studio Pants and Jeans | `["pelvis","thigh_L","thigh_R","shin_L","shin_R"]` |
| Studio sleeveless Dress v1 | `["torso","pelvis"]` as an initial candidate. Check the neckline, armholes and hem before adding thigh regions. |
| Sol Sneakers and Studio Boots, High-tops, Sandals and Slip-ons | `["foot_L","foot_R"]` as the footwear default. Check exposed skin on open shoes before use. |
| Bob, Studio Side Part, Spiky and Twin Tails | `[]` |

The table describes starting masks. Garment-level QA determines whether enough fabric covers the complete region. The integration manifest retains the existing wardrobe binaries, including Hoodie v2, and its existing review statuses. The hoodie measurements below are for v3.

## Reproduce the checks

Run from this directory. The generator uses the repository's installed Khronos validator. `BLENDER` is the supplied Blender executable and `DYLD_INSERT_LIBRARIES` points to the supplied guard dylib.

```sh
node split_body_regions.mjs ../../hand-gestures-astra/round2/base_body.glb .
motion=../../../../models/tripo-chibi-motion/motion.glb
hoodie=../../hoodie-fit-sol/round3/top_hoodie_v3.glb
tshirt=../../sol-tshirt/v3/top_tshirt_v3.glb

for checker in motion_check_masked.py motion_check_tri_masked.py; do
  PYTHONDONTWRITEBYTECODE=1 "$BLENDER" -b -noaudio --python-exit-code 2 --python "$checker" -- \
    base_body_regions.glb "$motion" "$hoodie" hoodie-v3 \
    --hide torso,upper_arm_L,upper_arm_R,forearm_L,forearm_R
  PYTHONDONTWRITEBYTECODE=1 "$BLENDER" -b -noaudio --python-exit-code 2 --python "$checker" -- \
    base_body_regions.glb "$motion" "$tshirt" tshirt-v3 --hide torso,upper_arm_L,upper_arm_R
done
```

The first positional argument accepts the segmented GLB. Legacy invocations which pass a `.blend` resolve to the segmented GLB beside the checkers. When `--hide` is omitted, `garment.json` beside `garment.glb` supplies `{"hides":["torso"]}`. The flag takes precedence. Exit code 1 indicates a failed gate after the report has been written. With `--python-exit-code 2`, unexpected execution errors are distinguished from failed measurements.

Garments are bound to the body armature. Quaternion samples transfer through the two rigs' rest bases, preserving Blender's rotation modes and keeping vertical root travel. Blender 5 uses the imported action and its action slot. Vertex checks sample 12 frames per clip using the legacy spacing. The triangle checker samples every third frame using the legacy spacing. Both require zero collisions. The visible triangle check uses a BVH containing only visible body triangles. The vertex check uses the original surface's nearest triangle to assign each vertex to a body region, then counts negative signed distances only for visible owners. This avoids treating the open edge of a mask as the boundary of an enclosed volume. Signed distances are in Blender units.

The opening check rasterizes flat region IDs by tracing one ray per pixel centre. It uses 256 × 256 orthographic views at eight azimuths and elevations −12°, 4° and 28°. Surfaces are opaque and two-sided for this geometric test. The first hit is a garment, visible body, or hidden body pixel. The latter counts as exposed. The denominator includes all first-hit pixels in the combined silhouette. The gate requires the worst single view to be below 0.2% on rest and on 12 samples each of walk, run and wave. Counts include all exposed hidden skin, including necklines, cuffs and hems. The JSON includes a breakdown by hidden region for each view. Browser shading and poses between the sampled frames are outside these measurements.

## Export and runtime files

- [base_body_regions.glb](base_body_regions.glb), [regions.json](regions.json) and [validator.json](validator.json) hold the export, per-region triangle counts and validation report.
- [split_body_regions.mjs](split_body_regions.mjs) builds the export. [motion_check_masked.py](motion_check_masked.py), [motion_check_tri_masked.py](motion_check_tri_masked.py) and [masked_check_common.py](masked_check_common.py) implement the validators.
- [dressup-integration.patch](dressup-integration.patch) applies the seven text updates. The matching file tree and the model copy are under [integration](integration/). The source repository paths are outside the writable workspace. Apply the patch from the gallery root and copy the model into the target model directory when those paths are writable.

```sh
work=output/modular-chibi-parts/body-mask/work
patch --dry-run -p1 < "$work/dressup-integration.patch"
patch -p1 < "$work/dressup-integration.patch"
cp "$work/base_body_regions.glb" models/chibi-dressup/base_body_regions.glb
npm test
```

Round 2 gestures use quaternion tracks and, for eight compact poses, finger scale tracks. The staged dress-up rig supports both and restores both properties on the next pose or on gesture removal. No gesture binary change is needed.

## Blender 5.1.2 results

**Both garments fail the masked collision and opening gates.** Both have zero collisions in rest. The largest opening result for Hoodie v3 is 2.050% on walk. The largest for T-shirt v3 is 6.964% in rest. In those views, the highest exposed count comes from the torso in both garments. The T-shirt's two upper-arm regions also account for 686 of its 1,131 exposed pixels.

| Clip | Hoodie vertices | Hoodie vertex min | Hoodie triangle pairs | Hoodie triangle min | T-shirt vertices | T-shirt vertex min | T-shirt triangle pairs | T-shirt triangle min |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| rest | 0 | 0.0025 | 0 | 0.0025 | 0 | 0.0046 | 0 | 0.0046 |
| walk | 45 | -0.0153 | 285 | -0.0200 | 23 | -0.0063 | 73 | -0.0063 |
| run | 27 | -0.0130 | 215 | -0.0130 | 23 | -0.0081 | 54 | -0.0081 |
| wave | 22 | -0.0050 | 220 | -0.0050 | 25 | -0.0055 | 72 | -0.0052 |
| jump | 28 | -0.0067 | 220 | -0.0062 | 30 | -0.0076 | 79 | -0.0081 |
| idle | 33 | -0.0045 | 223 | -0.0045 | 25 | -0.0059 | 74 | -0.0059 |
| nod | 25 | -0.0044 | 221 | -0.0046 | 26 | -0.0052 | 75 | -0.0053 |
| dance | 2 | -0.0011 | 17 | -0.0021 | 0 | 0.0028 | 0 | 0.0028 |

Opening measurements use the worst ratio per clip. Each cell gives exposed pixels / silhouette pixels followed by the frame, azimuth and elevation.

| Clip | Hoodie v3 | T-shirt v3 |
| --- | --- | --- |
| rest | 278/16475 (1.687%), rest / 0° / -12° | 1131/16241 (6.964%), rest / 0° / 4° |
| walk | 316/15412 (2.050%), 47 / 0° / -12° | 1053/15125 (6.962%), 47 / 0° / 4° |
| run | 269/13587 (1.980%), 5 / 45° / -12° | 1052/15419 (6.823%), 15 / 0° / -12° |
| wave | 290/14847 (1.953%), 5 / 0° / -12° | 996/14600 (6.822%), 5 / 0° / 4° |

Full measurements are in the [hoodie vertex report](hoodie-v3/motion_check_masked.json), [hoodie triangle report](hoodie-v3/motion_check_tri_masked.json), [T-shirt vertex report](tshirt-v3/motion_check_masked.json) and [T-shirt triangle report](tshirt-v3/motion_check_tri_masked.json).

| Input or artifact | SHA-256 |
| --- | --- |
| Body source | `cc06cbac9befd86a0cf0455f76d76c68dfe215d6db7711c32d7d1c5fac613b96` |
| Region GLB | `20f522f6d725d72d23a47a934009c438b1fdf9d8d2fe0322c0352f2a386174c9` |
| Motion source | `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410` |
| Hoodie v3 | `29cc22b68ffb16f5c91ed550ab23851f37c9841fbcd211a96d35450bb342868e` |
| T-shirt v3 | `803060a461f42c27c1255ed9deeb828d3a1d4e62ef72817dddbdbb37dd744ba3` |

## Integration verification

The isolated repository passed all 751 tests from `npm test`, including i18n and seven dress-up tests. The offline Vite production build completed with a chunk-size warning. The generated dress-up bundle references `base_body_regions-FpbC0YXD.glb`; its bytes match the delivered GLB. A Node Three.js test loaded the real model and wardrobe files, checked that all region meshes shared the original 65-joint skeleton, compared the oriented triangle data and exercised all seven clips with Round 2 hand gesture tracks. Browser drawing and interaction were not run.

The GLB byte check also verified the 65 joint node definitions, inverse bind matrices and embedded image bytes against the source. The Blender argument check covered the JSON sidecar, CLI precedence and the legacy first argument.
