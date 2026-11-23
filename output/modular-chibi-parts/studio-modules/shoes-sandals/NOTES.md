# Tripo purple sandals fitted to the chibi master

[Blender module](shoes_sandals_v1.blend) · [Skinned GLB](shoes_sandals_v1.glb) · [Rebuild](fit_shoes.py) · [Static preview](sandals_preview.png) · [Worn at rest](rest_fit.png)

## Geometry and skin

The source imports with Z up and its toes pointing toward −Y. The sandal at +X is the character's left, with its buckle facing out. The two disconnected shells remain in one mesh object. The build welds coordinate duplicates across source UV seams, seals the seven-edge pinhole next to the left insole, and retains the Tripo atlas, base color, normal and packed roughness/metallic textures. Each of the three maps is 1024 × 1024. The strap and sole material slots share the same shading parameters and images. The slots identify the surfaces in the verification render.

An outline sampled from the actual source tread guides the sole fit. The heel shoulder extends further for the lifted run pose. The closed sole has a recessed bed and a raised dark rim. The upper is shaped as a continuous fit and corrected against the worst captured contacts on both feet. Body skin weights drive the shell through the corresponding Foot and ToeBase, with Leg contribution around the heel and ankle. The action slots are assigned explicitly in Blender 5.1.2. The master quaternion settings and the 65 joint names, order and inverse bind matrices are preserved.

| Fit metric | Left | Right |
| --- | ---: | ---: |
| Master foot length | 192.38 mm | 192.38 mm |
| Fitted sole length | 213.34 mm | 213.41 mm |
| Minimum overhang of projected convex sole outline | 4.93 mm | 4.98 mm |
| Uncovered rays from the actual sole projection at 3 mm overhang | 0 / 2,496 | 0 / 2,496 |
| Lowest sole Z at rest | -13.00 mm | -13.00 mm |

The pair has **3,482 triangles**, **65 joints**, **3 maximum influences per vertex**, one skinned mesh and zero embedded animations. The GLB is **3,303,896 bytes** and the Blender file is **3,247,929 bytes**. The Khronos validator gives **0 errors and 0 warnings**. The reimported, position-welded mesh has 0 open edges and 0 nonmanifold edges. [Export contract](asset_contract.json) · [Fitting evidence](fit_geometry.json) · [Rest geometry report](rest_geometry.json) · [Khronos validator](validator.json)

The source was adaptively subdivided on 236 edges around fold-prone triangles. New UVs interpolate the original atlas.

## Vertex checker RESULT

[Raw RESULT log](motion_check.txt) · [JSON](motion_check.json)

| Pose | Maximum inside vertices | Minimum signed distance (mm) |
| --- | ---: | ---: |
| rest | 0 | 2.234 |
| walk | 0 | 1.900 |
| run | 0 | 2.000 |
| wave | 0 | 2.200 |
| jump | 0 | 2.100 |
| idle | 0 | 2.200 |
| nod | 0 | 2.200 |
| dance | 0 | 2.000 |

## Triangle checker RESULT

[Raw RESULT log](motion_check_tri.txt) · [JSON](motion_check_tri.json)

| Pose | Maximum overlap pairs | Minimum signed distance (mm) |
| --- | ---: | ---: |
| rest | 0 | 2.234 |
| walk | 0 | 1.700 |
| run | 0 | 2.000 |
| wave | 0 | 2.200 |
| jump | 0 | 2.100 |
| idle | 0 | 2.200 |
| nod | 0 | 2.200 |
| dance | 0 | 2.000 |

The reimported GLB was also tested on the entire base body in **674 poses**, at every frame in all seven clips and at all quarter frames of walk and run. The minimum signed vertex distance over these samples was **1.591 mm**. [Dense check](dense_check.json)

## Shoe visibility in walk and run

Cycles CPU renders the target foot in green, other body geometry in magenta, the sole in blue and the straps in red. The below camera tests the entire projected sole including enclosed holes and a two-pixel exterior band. The low lateral camera tests the camera-facing side of the sole and the two pixels beneath its lower edge. From the side, the camera also sees the intentionally open toe and heel above this edge. The far-side rim can project behind that exposed skin. A body-only control confirms the tested pixels would register skin when the sole is absent. [Pixel report and camera settings](skin_check.json)

| Clip and frame | View | Target foot through sole | Target foot around sole | Other body through sole | Body-only control within the test |
| --- | --- | ---: | ---: | ---: | ---: |
| walk 19 (left) | [below](skin/walk_19_left_below.png) | 0 | 0 | 0 | 103,166 |
| walk 19 (left) | [side](skin/walk_19_left_side.png) | 0 | 0 | 0 | 20,795 |
| walk 23 (left) | [below](skin/walk_23_left_below.png) | 0 | 0 | 0 | 101,673 |
| walk 23 (left) | [side](skin/walk_23_left_side.png) | 0 | 0 | 0 | 18,518 |
| run 4 (right) | [below](skin/run_4_right_below.png) | 0 | 0 | 0 | 87,719 |
| run 4 (right) | [side](skin/run_4_right_side.png) | 0 | 0 | 0 | 6,758 |
| run 12 (right) | [below](skin/run_12_right_below.png) | 0 | 0 | 0 | 98,812 |
| run 12 (right) | [side](skin/run_12_right_side.png) | 0 | 0 | 0 | 5,112 |

[Walk](walk.png) · [Run](run.png) · [Wave](wave.png) · [Jump](jump.png) · [Rest side](rest_side.png) · [Rest tread](rest_tread.png)

## Remaining limitations

The supplied foot already reaches Z = 0 at rest. A solid positive-thickness sole with clearance below that point needs to extend below ground in the unchanged master coordinate system. The build prioritizes skin coverage and clearance, leaving the tread below the requested plane. The raised outer rim and length extension maintain the cover at the heel during run. The high rim and its recessed interior bed occupy different vertical levels.

Some of the upper sits looser than the 3–10 mm design range. The median sampled body-facing rest gap is 12.8 mm on the left and 13.1 mm on the right. The shell still has 649 nonadjacent triangle intersection pairs in rest. These are internal to the shoes, separate from the zero intersections with the body. Independent visual review confirmed the recognizable straps, heel loops, open toes and continuous dark tread. The small rest patch and the branched tread patch in run 4 disappeared after subdivision. The straps still render paler than the reference. The tread outline shows facets, with dark triangular folds near the front-strap anchors and a crumpled outer fastener. At run 4 the toe bumper forms a steep ramp and the instep tip points upward. [Independent visual review](visual_review.json)

## Local rebuild

Run from this directory using Blender 5.1.2 with the supplied guard. Workbench exited with code 134 during headless rendering on this setup. The wrapper uses Cycles CPU for the vertex checker's four PNGs. It omits the triangle checker's duplicate PNG stage and runs the same triangle measurement code. Both supplied checker files retain their original hashes.

```zsh
zsh work/run_blender.zsh -t 5 --python fit_shoes.py
zsh work/run_blender.zsh -t 4 --python work/verify_shoes.py -- --checkers-only
zsh work/run_blender.zsh -t 5 --python work/verify_shoes.py
node -e 'const fs = require("node:fs"); const v = require("../../../../node_modules/gltf-validator"); v.validateBytes(new Uint8Array(fs.readFileSync("shoes_sandals_v1.glb")), {uri:"shoes_sandals_v1.glb"}).then(r => { fs.writeFileSync("validator.json", JSON.stringify(r, null, 2) + "\n"); process.exitCode = Number(!!(r.issues.numErrors || r.issues.numWarnings)); });'
```

| Checked file | SHA-256 |
| --- | --- |
| Tripo Studio source GLB | `cf6457bc3667d742a64536123e23cf32c7c85542cb11834fe75cc48e0e30a112` |
| Master rigged Blender scene | `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f` |
| Motion GLB | `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410` |
| Reference PNG | `f2a6d11e6527a8f07386ae5f8058501bf258819ef0da4e3f5681154b03725a55` |
| Delivered GLB | `40137d7b0c8dbebc3e3fc04e92d94425fd3513446ee8f41172f627c63dd26cc4` |
| Delivered Blender file | `6b78bea9257d4d37d02b56a482d13ee17ebf6dfb77c70341a533b7c762781143` |

[Render and report hashes](render_manifest.json)
