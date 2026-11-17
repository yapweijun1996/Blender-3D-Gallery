# Tripo FBX character: 1c818c0d

Status: inspected source and draft GLB, not a published Gallery catalog entry.
The user supplied the source ZIP; creator, generation inputs, and redistribution
license were not provided, so no license is inferred.

## Files and provenance

- Source: `tripo_convert_1c818c0d-87d5-4ff0-a21c-bac7bb1956e7.zip`, SHA-256 `497d5a182dd9d9be570f73decd94949f20c6d58178aa2a628734f26d28aafe9c`. ZIP integrity passed; it contains an FBX and its 4096×4096 JPEG texture.
- `character.blend`: Blender 5.1.2 import with packed texture and both source Actions. Its active Action is `sit`; the NLA tracks are muted for single-action preview. SHA-256 `aeb14adef3cf379ad046fb37b2da753f1165f257e337aa3c888f07d43c99d764`.
- `character.glb`: 4,100,584 bytes; one textured skinned mesh, 10,522 triangles, 65 joints and two clips, `run` and `sit`. SHA-256 `9be21905d15e24b4486fed6815282272bb0df54890e1e3910644f9e73730e595`.
- `review/`: actual GLB rendered in desktop Chromium/Three.js at five sampled times per clip. Camera follows and reframes the character, so screenshots alone do not show world translation.

## Inspection and limitations

The source imports as one mesh with 5,470 vertices and 5,924 faces, one UV map,
one material and a 65-bone armature. All vertices have bone weights; sums range
from 0.999999955 to 1.000000038 and each vertex has one to four influences.
There are 399 boundary edges, 400 non-manifold edges in total, no wire edges,
and no zero-area faces. The mesh is therefore not a closed manifold; no repair
was attempted. Weight normalization does not itself prove good deformation.

The original `run` runs from frames 1–31 at 24 fps and travels approximately
2.0 m along Blender's negative Y axis. It is not an in-place cycle. After
subtracting mean translation, the corresponding source vertices at the start
and end differ by up to 0.123 m (RMS 0.033 m), so a simple repeat has a pose
and position discontinuity. The `sit` Action runs from frames 1–173 at 24 fps:
it begins seated, leans forward, then returns to a seated pose. Start and end
source vertices differ by up to 0.00531 m; it is not an exact loop. The clip
has no chair, and chair contact, foot contact and collision were not verified.
Sampled mesh bounds reach below Z=0; no ground-contact guarantee is implied.

GLB keyframes start at 1/24 s, so the exported durations are approximately
1.292 s (`run`) and 7.208 s (`sit`), including the leading held interval.
The source actions and skin are retained; no gait, seating, weight or topology
repairs were made. The sampled front-quarter views did not show an obvious
catastrophic deformation; occluded surfaces, all angles and all intermediate
frames were not exhaustively assessed.

## Reproduce and verify

From the repository root, with Blender 5.1.2 and installed npm dependencies:

```sh
blender -b --factory-startup --disable-autoexec -t 4 --python-exit-code 1 --python models/tripo-convert-1c818c0d/export.py
node models/tripo-convert-1c818c0d/validate.mjs
blender -b --factory-startup --disable-autoexec -t 4 --python-exit-code 1 --python models/tripo-convert-1c818c0d/audit-source.py -- /tmp/tripo-source-samples.json
TRIPO_SOURCE_SAMPLES=/tmp/tripo-source-samples.json TRIPO_QA_DIR=/tmp/tripo-qa node models/tripo-convert-1c818c0d/browser-check.mjs
```

The Khronos validator reported zero errors and zero warnings. Desktop Chromium
156 / Three.js loaded the actual GLB and evaluated both clips at five source
frames each, including two half-frame samples for `run`. At each sample, every
source FBX vertex was compared with its closest exported GLB vertex in world
space; the maximum observed difference was 0.0000162 m. This is a one-way
nearest-vertex comparison at ten times, not a proof for every frame or a visual
quality certification. Browser errors were absent in that harness. Gallery
animation controls, Safari, mobile devices, chair fit and continuous playback
were not tested. A 4096 texture exceeds the project's proposed 2048 target.
