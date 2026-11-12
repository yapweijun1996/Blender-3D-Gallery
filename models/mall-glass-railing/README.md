# Modular glass railing kit

One logical model kit, with three independently usable assets: a standalone post and 1 m / 2 m centre-spaced straight bays. Original graphite aluminium, champagne trim and sea-green glass. Blender 4.0.2, real metre units, Blender +Z up / glTF +Y up, floor-centred origins. Front is Blender -Y / glTF +Z; both faces have symmetric geometry.

**Overall: NEEDS REVIEW.** Structural/source/visual checks passed, but the strict gallery browser gate failed one of nine cases with an unfiltered GLB request abort. Actual Android and iOS browsers have not been tested. Nothing here asserts deployment readiness. See [verification.md](verification.md).

| Asset | GLB bytes | Triangles | Primitives | Dimensions, glTF X/Y/Z metres |
| --- | ---: | ---: | ---: | --- |
| Post | 57,548 | 1,024 | 3 | 0.160 / 1.120 / 0.160 |
| 1 m bay | 175,864 | 3,236 | 10 | 1.160 / 1.121 / 0.160 |
| 2 m bay | 175,864 | 3,236 | 10 | 2.160 / 1.121 / 0.160 |

The saved sources retain 16 / 43 / 43 independently editable mesh parts and named materials. Optimized exports merge evaluated geometry within reusable named modules, retaining material primitives. Studio objects are source-only, never exported. No textures, animations, physics, engineering calculations, building-code compliance or barrier safety certification are provided.

## Assembly

- Standalone post: extract `MODULE_Post`, with its floor-centred local origin.
- Each bay: `MODULE_Post_Left`, `MODULE_Post_Right`, `MODULE_Infill`.
- An infill includes the glass, clamps, lower rail and handrail. Keep its original local coordinates.
- For repeated bays, instance **one post per unique joint**, then extract only the infill from the chosen bay GLB. Do not chain complete bays, which would overlap endpoint posts.
- `layouts.json` gives a three-bay 1 m line and a mixed 2 m / 1 m right-angle assembly. Coordinates are glTF metres and Y rotations are radians. The four-way square post supports the shown orthogonal joints.
- Handrail centre is 1.095 m high. Infill endpoints meet post side faces 0.026 m from each post centre. The designed gasket/clamp contact is 0.5 mm; other intermodule intersections above the documented tolerance fail validation.
- Length is **post-centre spacing**, not overall width. Do not stretch glass or arbitrary joint angles.

The validator loads real GLBs through Three.js, checks transformed connector faces, and reconstructs connected geometric pieces for conservative pairwise AABB clearance checks. See `reports/assembly.json`. This is a static integration recipe, not a runtime railing editor.

## Glass and previews

The GLB uses standard double-sided `BLEND` material with alpha 0.28, roughness 0.16 and thin tinted edge strips. It is intentionally alpha transparency rather than physically refractive/transmissive glass, for current-viewer compatibility. A closed thin box can blend both its front and back faces.

Primary PNG/WebP renders, front and rear WebP views, and an assembly WebP are included in `previews/`. Additional PNG render intermediates are reproducible and ignored. The assembly preview imports the actual exported GLBs. The material diagnostic uses an unchanged shipped GLB with a checker target behind it, compared with opaque and hidden controls; the checker is not part of the shipped model.

## Reproduce

From the repository root, with Blender 4.0.2, Python Pillow, Node 22 and installed project dependencies:

```sh
blender --background --python-exit-code 1 --python models/mall-glass-railing/generate.py
blender --background --python-exit-code 1 --python models/mall-glass-railing/render_views.py
python3 models/mall-glass-railing/prepare_previews.py
blender --background --python-exit-code 1 --python models/mall-glass-railing/inspect_sources.py
node models/mall-glass-railing/validate.mjs
npm test
npm run build
node scripts/test-mall-glass-railing.mjs
node scripts/test-mall-glass-material.mjs
npm run test:library
```

After editing a saved source, use `generate.py -- --export-source` to export and render the edited geometry/materials. Running without that option rebuilds and replaces the authored sources. Preserve your own copy before rebuilding. `test_source_edit.py -- /fresh/isolated/directory`, followed by the copied generator with `--export-source` and `verify_source_edit.mjs /fresh/isolated/directory`, verifies an isolated material edit without changing the shipped sources.

Geometry parameters are deterministic; exporter/render bytes may vary with toolchain versions. Committed SHA-256 values identify the verified files.

## Rights

Original geometry and materials authored for Blender-3D-Gallery, with no external models, artwork or textures. Reuse in the owner's projects is authorized. Public redistribution terms have not been specified. Existing license wording and disabled public downloads are preserved. This generic mall kit does not claim a Singaporean or Malaysian regulatory standard.
