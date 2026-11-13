# Mall Floor Tile Module

Selected backlog V2.1, item 421, P0. One logical flooring model toward the ten-model batch, not four models because it contains four slabs.

A simple 1.2 m × 1.2 m repeat module for generic Singapore/Malaysia mall interiors. Four 600 mm-pitch honed ivory terrazzo tiles, restrained original aggregate artwork, eased stone edges and warm-grey grout. Source uses metres and Blender +Z up; GLB uses metres and +Y up. The origin is the centre of the underside at floor height zero.

**Overall: NEEDS REVIEW.** Local structural and browser evidence is in [verification.md](verification.md). Physical Android/iOS coverage is unavailable. This is not a slip-resistance, fire-rating, accessibility, fabrication or building-code specification.

## Components and assembly

- Four independently editable stone meshes, each 596 × 596 × 18 mm, on a 600 mm grid.
- One closed, independently editable grout/support mesh. Support height is 12 mm; filled joints reach 29 mm. Slab tops are at 30 mm, leaving a 1 mm grout recess.
- Separate named grout, stone-body and honed-finish materials. The source packs the original 512 × 512 texture, also supplied separately. No external model, artwork, image or font is used.
- Place the **whole root** at multiples of 1.2 m along GLB X/Z, with Y = 0. Quarter-turn Y rotations are supported. Do not add a second grout border: each outer edge contains half of the 4 mm joint.
- Blender equivalents are X/Y placement and Z-axis rotation. No scaling, runtime floor editor or arbitrary-size transitions are supplied.
- `validate.mjs` loads the actual exported meshes, verifies bounds and surface heights, and tests 3 × 3 straight and quarter-turned arrangements. Sixty adjacent joints are checked per arrangement, including joints across module boundaries.

The export preserves the five named components. It contains an embedded PNG, no external URLs, no camera, light, animation or decoder dependency. Multi-angle previews and the 3 × 3 assembly render import the actual GLB. The gallery's existing elevated initial view exposes the floor surface without changing app behavior.

## Reproduce

Blender 4.0.2, Python with Pillow, Node 22 and the locked project dependencies:

```sh
python3 models/mall-floor-tile/make_texture.py
blender --background --python-exit-code 1 --python models/mall-floor-tile/generate.py -- --skip-render
blender --background --python-exit-code 1 --python models/mall-floor-tile/render_views.py
python3 models/mall-floor-tile/prepare_previews.py
blender --background --python-exit-code 1 --python models/mall-floor-tile/inspect_sources.py
node models/mall-floor-tile/validate.mjs
npm test
npm run build
node scripts/test-mall-floor-tile.mjs
npm run test:library
```

To preserve manual source edits, use `generate.py -- --export-source --skip-render`; without `--export-source`, the generator rebuilds and replaces the source. Back up your own edits before rebuilding. The texture seed is 421; four UV rotations vary the repeated tiles. Geometry is deterministic, while exporter/render bytes can differ between toolchain versions. Report hashes identify the tested files.

The source-edit test accepts a **fresh isolated absolute directory** as the argument to `inspect_sources.py -- /fresh/directory`. It copies the generator, raises only the first saved slab's top vertices by 4 mm, changes finish roughness from 0.32 to 0.48 and saves a separate `.blend`. Run that copied generator with `--export-source --skip-render`, then `verify_source_edit.mjs /fresh/directory`. Shipped sources and exports remain unchanged.

The Node structural loader reads embedded PNG dimensions without rendering pixels. Actual PNG decoding is checked by Pillow and actual material rendering by the strict Chromium gallery test and pixel inspection. Node structural checks are not substituted for browser rendering.

## Rights

Original geometry, materials and seeded artwork authored for Blender-3D-Gallery. Reuse in the owner's projects is authorized. Public redistribution terms have not been specified. Existing license language and disabled public downloads are preserved. No production release is asserted.
