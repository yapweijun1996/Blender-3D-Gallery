# Tripo tan lace-up boots

[Blender scene](shoes_boots_v1.blend) · [Skinned GLB](shoes_boots_v1.glb) ·
[Builder](fit_shoes.py) · [Three-quarter preview](qa/boots_preview.png) ·
[Front](qa/boots_front.png) · [Side](qa/boots_side.png) · [Underside](qa/boots_underside.png)

The source is one Tripo mesh containing two boots and a few small hardware islands.
In Blender the source toes point near **−X**, at 184.61° on the left and 184.20°
on the right measured counterclockwise from +X in the XY plane. Each boot was
aligned independently to **−Y forward**, with the character's left boot at +X.
The outside leather, toe cap, stitched welt, laces, eyelets, buckles and tread retain
the Tripo material and exterior UVs. Three texture maps were resized to 1024 ×
1024. The source's shallow lining was replaced with a fitted cavity and a
triangulated footbed that use a patch of the same atlas. The closed sole retains
a shallow arch and a broad planar tread.

The exported scene contains one skinned mesh and no animation clips. Its 65
joint names, order and inverse bind matrices match the base-body GLB. Each
vertex has at most three nonzero influences. The lower boot follows Foot with a
smooth ToeBase blend at the ball. Leg contributes around the ankle and shaft.
The native armature preserves the master's pose-bone rotation modes. The editable
native file contains a hidden Base_Body fit reference and packed textures.

| Deliverable | Size |
| --- | ---: |
| `shoes_boots_v1.glb` | 4,663,012 bytes |
| `shoes_boots_v1.blend` | 5,466,552 bytes |
| Triangle count for the pair | 3,437 |
| Khronos glTF Validator 2.0.0-dev.3.10 | 0 errors, 0 warnings |

[Asset contract](qa/asset_contract.json) · [Khronos report](qa/validator.json)

## Vertex checker RESULT

[Raw log](qa/motion_check.txt) · [JSON](qa/motion_check.json)

| Case | Max vertices inside | Min signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.002864 |
| walk | 0 | 0.0024 |
| run | 0 | 0.0020 |
| wave | 0 | 0.0026 |
| jump | 0 | 0.0026 |
| idle | 0 | 0.0026 |
| nod | 0 | 0.0026 |
| dance | 0 | 0.0025 |

## Triangle-overlap checker RESULT

[Raw log](qa/motion_check_tri.txt) · [JSON](qa/motion_check_tri.json)

| Case | Max overlap pairs | Min signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.002864 |
| walk | 0 | 0.0016 |
| run | 0 | 0.0020 |
| wave | 0 | 0.0026 |
| jump | 0 | 0.0026 |
| idle | 0 | 0.0026 |
| nod | 0 | 0.0026 |
| dance | 0 | 0.0025 |

The exported GLB also passed **674** pose samples, including quarter frames of
walk and run and every integer frame of the other clips. There were zero interior
vertices and zero body/boot triangle overlaps. The minimum signed distance was
**1.075 mm at walk frame 16.5**. The verification reimports the export and uses
the full body, including the thighs. The fit bakes corrections from the worst
poses and examines actual triangle intersection segments as well as vertices.
[Dense BVH report](qa/dense_check.json) · [Checker inputs and export hash](qa/checker_manifest.json)

## Sole coverage

All **14 views** reported **0 body-colour pixels through the sole** and
**0 selected plantar pixels through or around it**. The tested lifted-foot
frames were walk 17, 19 and 31, and run 4, 12 and 19. Every frame has a below
and a lateral view. Walk 19 and run 4 also have medial views. The body-only
controls projected 31,189–90,437 selected plantar pixels. The mask uses green
for the selected plantar region, magenta for the remaining body, red for the
boot upper and blue for the sole. A separate shoe-only render identifies
the fully covered sole pixels and any enclosed gaps. This avoids attributing
partially covered exterior antialiasing samples to a hole.

[Mask counts, hashes and cameras](qa/skin_check.json) ·
[Walk 19 below](qa/walk_19_underside_skin.png) ·
[Run 4 below](qa/run_4_underside_skin.png) ·
[Run 4 lateral](qa/run_4_side_skin.png) · [Run 4 medial](qa/run_4_medial_skin.png)

## Rest geometry and visible differences

| Measurement | Left | Right |
| --- | ---: | ---: |
| Bare foot length | 192.38 mm | 192.38 mm |
| Outsole length | 213.76 mm | 212.18 mm |
| Minimum radial outsole overhang | 6.36 mm | 6.63 mm |
| Sole boundary / nonmanifold edges after weld | 0 / 0 | 0 / 0 |
| Upper lining clearance, min / median / max | 3.28 / 5.35 / 10.39 mm | 2.86 / 5.33 / 10.96 mm |
| Shaft high point / rear collar | 145.00 / 92.40 mm | 145.00 / 92.16 mm |
| Lowest outsole point | −15.43 mm | −15.40 mm |

Both bare soles touch Z=0 in the master. A closed sole with clearance under
the same skin necessarily extends below that plane. The broad tread rests at
about Z=−14 mm, with a small local deviation from the clearance bake. The
module uses the master's origin and inverse binds. Ground alignment would use
a +15.43 mm root offset on the assembled character for the lowest rest tread.

The rear collar is cut down for the thigh during the deep heel lift in run.
This makes the opening more sloped and faceted than the reference's padded
ring. Two local liner/exterior contacts per boot remain near the upper side
panels around Z=115 mm. These are layered boot surfaces in the native mesh.
The body/boot overlap checks and all sole masks are clear. Independent visual
review verified the rounded toe volumes, continuous cream welt, laces, eyelets
and outward-facing buckles on the exact final GLB. Small angular welt
transitions and a pale texture/shading mark on a side panel remain.

[Rest geometry](qa/rest_geometry.json) · [Native lining measurements](qa/native_lining.json) ·
[Walk](qa/walk.png) · [Run](qa/run.png) · [Wave](qa/wave.png) · [Jump](qa/jump.png)

[Before toe repair](qa/toe_before_polish.png) · [After toe repair](qa/boots_preview.png)

The before image was rendered from GLB SHA-256 `f4c3c2086ee8955f68bac9b6b010fd97ac3b5188d5ed6a2dca391beeb05c7d4b`.

## Rebuild and verify

Run from this directory in Blender 5.1.2. The local wrapper uses the supplied
guarded Blender launcher and keeps temporary files under `work/`. With a
working standalone Blender executable, use `blender -b -noaudio
--python-exit-code 1` in place of the wrapper.

```sh
zsh work/blender-local --python fit_shoes.py
zsh work/blender-local --python work/verify_shoes.py -- shoes_boots_v1.glb qa
```

A fresh full rebuild from the three inputs produced a byte-for-byte match for
the final GLB.

The QA runner uses Cycles CPU for the supplied checker render block and
preserves the geometry predicates and pose sampling. It writes each
checker's original JSON schema under a distinct filename. The triangle
check skips a second copy of the identical checker renders.

```sh
node -e 'const fs=require("node:fs");const crypto=require("node:crypto");const v=require("../../../../node_modules/gltf-validator");const uri=process.argv[1], bytes=fs.readFileSync(uri);v.validateBytes(bytes,{uri}).then(r=>{r.export_sha256=crypto.createHash("sha256").update(bytes).digest("hex");fs.writeFileSync("qa/validator.json",JSON.stringify(r,null,2)+"\n");process.exitCode=+(!!(r.issues.numErrors||r.issues.numWarnings));});' shoes_boots_v1.glb
```

| File | SHA-256 |
| --- | --- |
| Final GLB | `3a8ebccd7404ac3d13389dfc1a26abb7cac4539057921894781d461bcb207ea6` |
| Source GLB | `cbc65ac2acc39a84e670cf1e3830725782c279d12fbbdd70a9437d59dd565163` |
| Master Blender scene | `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f` |
| Motion GLB | `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410` |
| Reference PNG | `c9828014489c7c0d4f177b98264e3c8a0d39b76825bec32d680581939a670ca8` |
