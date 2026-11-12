# Modular queue stanchions

Original jade-and-champagne-brass mall queue kit, authored in Blender 4.0.2. Includes a standalone post, 1.2 m bay and 2.0 m bay. Measurements are in metres; Blender uses +Z up, exported glTF uses +Y up. All origins are at floor level. No third-party models or textures.

## Contents

Each of `mall-queue-post`, `mall-queue-short`, `mall-queue-long` has an editable `sources/*.blend`, self-contained `exports/*.glb`, `previews/*.webp` and measured `metadata/*.json`. Studio lights, camera and ground are excluded from GLB exports. Blender sources preserve 10/23/23 editable parts.

| Asset | GLB bytes | Triangles | Primitives | Dimensions (x/y/z, glTF metres) |
| --- | ---: | ---: | ---: | --- |
| Post | 97,912 | 3,344 | 3 | 0.370 / 0.976 / 0.370 |
| Short bay | 191,180 | 7,252 | 8 | 1.570 / 0.976 / 0.370 |
| Long bay | 192,444 | 7,252 | 8 | 2.370 / 0.976 / 0.370 |

## Compose queues

The standalone asset contains `MODULE_Post`. Each bay contains independent `MODULE_Post_Left`, `MODULE_Post_Right` and `MODULE_Belt` nodes. Post origins are at each post's floor centre; belt origin is midway between the posts at floor height. The belt is authored along X, with centre height 0.905 m. Four sockets on each post support orthogonal turns. Bay spacing is measured between post centres, not the outer edges of the bases.

Use a complete bay for an isolated barrier. To chain a queue without overlapping posts, instance `MODULE_Post` once at each unique point, and clone only the named `MODULE_Belt` from the selected short/long GLB between points. `layouts.json` gives a straight short queue and a mixed-length right-angle queue, including unique post positions, belt source IDs, midpoint positions and Y rotations in radians. Preserve belt local coordinates when extracting it. A belt extends to 0.073 m from each post centre; do not stretch it arbitrarily or connect it to a different spacing. Tests transform the real exported belt endpoints into these layouts and check socket alignment within 0.00001 m.

This is a static decorative asset kit. There is no runtime queue editor, retraction animation, physics or crowd-control/safety certification. Named modules and layouts are integration hooks, not an implemented interactive feature.

## Reproduce

From the repository root, with Blender 4.0.2, Python Pillow and the project's installed Node dependencies:

```sh
blender --background --python models/mall-queue-stanchions/generate.py
python3 models/mall-queue-stanchions/prepare_previews.py
blender --background --python models/mall-queue-stanchions/inspect_sources.py
node models/mall-queue-stanchions/validate.mjs
npm test
npm run build
node scripts/test-mall-queue-stanchions.mjs
npm run test:library
```

Generator geometry and parameters are deterministic. Blender save/export implementation and preview rendering may vary with toolchain versions; committed SHA-256 values identify the verified files. Raw PNG render intermediates are ignored; WebP thumbnails are committed.

## Rights

Original assets; reuse in the owner's projects is authorized. Public redistribution terms have not been specified. Existing catalog license text and disabled public download behavior are preserved.

See [verification.md](verification.md) for measured checks and the unresolved browser diagnostic.
