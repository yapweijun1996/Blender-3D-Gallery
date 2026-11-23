# Purple star high-top sneakers

A mirrored pair of basic ankle-high sneakers for the GJH Chibi master. The
pair uses a purple upper, ivory midsole and toe panel, dark purple tread,
two lace bars and one lateral star on each shoe. Materials use constant colors.
The editable Blender scene contains the pair and its armature.

## Rest measurements and fit

The master body has 8,006 triangles. Blender uses meters, +Z up and −Y forward.
Both feet reach the z=0 plane. The sole band is 18 mm nominal. Each sneaker
has nine tread triangles flat at z=0, with raised toe and heel transitions.
The two shoe meshes mirror around x=0.000722 m and the character's left shoe is
at +X. The sampled main upper shell, including the cuff and excluding raised
decorations, stands 3.03–9.11 mm from the rest body.

| Landmark | Left (x, y, z), m | Right (x, y, z), m |
| --- | --- | --- |
| Foot head | (0.080761, 0.009761, 0.064422) | (−0.075413, 0.009761, 0.064422) |
| ToeBase head | (0.080761, −0.068326, 0.017570) | (−0.075413, −0.068326, 0.017570) |
| Toe_End head | (0.080761, −0.120762, 0.017570) | (−0.075413, −0.120762, 0.017570) |
| Body sole minimum z | 0 | 0 |

The midfoot is weighted primarily to Foot, with smooth forefoot transition
to ToeBase. The far forefoot averages 98% ToeBase. The heel and cuff blend in
Leg weights to accommodate the master ankle flex. Pose bones retain their
original quaternion rotation modes.

## Export and checks

The GLB contains one skinned mesh with both shoes, five material primitives,
and one skin. The 65 `mixamorig:*` joint names, order and inverse-bind matrices
match the base body GLB. Each vertex uses one to three joint influences.
The file contains zero animations and zero image textures. Coordinates retain
the master origin, with glTF +Y up and +Z forward.

Khronos glTF Validator 2.0.0-dev.3.10 reported **0 errors and 0 warnings**.
The final GLB rebuilt byte-for-byte in Blender 5.1.2. Blender's native save
serialization can vary between runs.

| Clip | Max vertices inside | Min signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.000890136 |
| walk | 0 | 0.0009 |
| run | 0 | 0.0008 |
| wave | 0 | 0.0009 |
| jump | 0 | 0.0009 |
| idle | 0 | 0.0009 |
| nod | 0 | 0.0009 |
| dance | 0 | 0.0009 |

The supplied checker measures rest plus 12 samples per clip. A separate
whole-frame pass also found all shoe vertices at least 0.0005 m outside the
body in all seven clips. The macOS background invocation aborted when
Workbench tried to open a GUI render context. The CPU fallback runs the same
checker with the renderer switched to Cycles. The motion sampling, BVH
measurements, camera, filenames and JSON schema are preserved.

Floor clearance was checked every quarter frame on the exported GLB, with
225 samples per foot for walk and 121 per foot for run. The measured margin is
shoe minimum z minus the lesser of ground z and the corresponding body foot
minimum z. Positive values mean the shoe adds no floor penetration.

| Clip | Side | Worst frame | Margin (m) | Shoe minimum z (m) | Body foot minimum z (m) |
| --- | --- | ---: | ---: | ---: | ---: |
| walk | Left | 43.25 | 0.00016990 | −0.00933998 | −0.00950988 |
| walk | Right | 22.00 | 0.00016990 | −0.00443782 | −0.00460772 |
| run | Left | 7.25 | 0.00016993 | 0.00016993 | 0.00098305 |
| run | Right | 2.50 | 0.00016993 | 0.00016993 | 0.00006034 |

## Remaining limitations

Independent visual review found the reference cues legible in the preview and
the shoes centered on the feet in the tested poses. The collar, laces and toe
edges have a simpler, more faceted profile than the reference. Expanded tread
coverage reduced skin showing through the raised sole. Small relief windows and
local sole overlaps still expose skin from underneath in walk and run. An
additional triangle-centroid probe on integer frames found about 2.08 mm of
local overlap at a right tread face in run frame 4. The checker table reports
the requested vertex measurements.

## Rebuild

Run from this directory with Blender 5.1.2. The rebuild reads
`../master/GJH_Chibi_Master_rigged.blend` and
`../../../models/tripo-chibi-motion/motion.glb`. Keep the supplied
`motion_check.py` next to the builder.

```sh
blender -b -noaudio --python-exit-code 1 --python make_shoes.py
```

The default rebuild writes both assets, motion JSON, four motion renders and
the standalone preview. Pass `-- --assets-only` to omit QA or
`-- --qa-only` to rerun QA on the existing GLB. The preview uses an orthographic
front three-quarter camera with CPU Cycles.

To repeat the validator from the gallery repository root, use the installed
Node package.

```sh
node -e 'const fs = require("node:fs"); const v = require("gltf-validator"); v.validateBytes(new Uint8Array(fs.readFileSync(process.argv[1]))).then(r => { console.log(r.issues); process.exitCode = Number(!!(r.issues.numErrors || r.issues.numWarnings)); });' output/modular-chibi-parts/shoes-sol/shoes_sneaker_v1.glb
```

## Delivered files

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `make_shoes.py` | 27,999 | `83cda7bbd3f110f06834e02ea7808640188c8ad0ba6feea295cdd7dd1ff70a35` |
| `shoes_sneaker_v1.blend` | 188,303 | `7f8e5c4ec6d402371c30e7c7817c283145000fbc7879423f859f2a842a6c55d7` |
| `shoes_sneaker_v1.glb` | 131,708 | `feb5e9b43d3780bee40e183c516ed4ed527c2000686653e92c462efab860132b` |
| `motion_check.py` | 3,117 | `5e5b269858431688f2f853a38230227362cb88faf9aa2f588e514840486e96d8` |
| `motion_check.json` | 182 | `b3bab8dcbe1496a3077ef283e47217eab27040e55cc88de823901c9ea7433988` |
| `walk.png` | 301,271 | `74a202f370a0c8f3129819e3cc9bfa07655c3cbe8835d6e38ccd81be12917674` |
| `run.png` | 293,528 | `2f19a58d6a3e1fe46d79714c03330ffd54a28faf67999c2b6c07a0c478628c1f` |
| `wave.png` | 298,852 | `3b77e8123db738fd85c88a67bc205c6ceb56c84cbe1b99729fab78e87cc90035` |
| `jump.png` | 300,029 | `1524ad025eeebee4a7e520820f003fb2fcbc83077b2105824ce976647d758707` |
| `sneaker_preview.png` | 513,767 | `061cb9a156db5e0ab19925fd74e4a8ed056c6011f2b6f15ae46c80536098078b` |

The mesh has **2,864 triangles** for the pair.

The style reference is `../white-bg/shoes-01-purple-star-hightop.png`
`046ce39fb5d0e7477143628fa6432fd26590b3d61d503afbb7c1a72b35dd5f67`.
