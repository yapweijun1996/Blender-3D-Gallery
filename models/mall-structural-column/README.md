# Mall Structural Column

Selected V2.1 P0 item 427, batch item 8/10. One logical original visual architecture asset, not a certified structural system.

A simple 3.00 m tall square column with eight separately editable warm-ivory cladding panels around a 0.44 m core, a charcoal 0.60 m square plinth, two narrow shadow reveals and an ivory cap. The palette complements the existing warm terrazzo floor and ivory ceiling.

## Dimensions and assembly

- Overall Blender X/Y/Z: 0.60 / 0.60 / 3.00 m. glTF X/Y/Z: 0.60 / 3.00 / 0.60 m.
- Shaft cladding envelope: 0.50 m square; cladding thickness 20 mm.
- Plinth height 0.20 m, cap height 0.16 m, reveals 20 mm, horizontal cladding seam 8 mm.
- Origin is bottom centre, Blender Z=0 / glTF Y=0. The two named connector empties mark bottom and top.
- Place on the finished floor. The example positions floor-module bottoms at Y=-0.03, making their top Y=0; the column root stays Y=0.
- Ceiling underside is Y=3.00. Omit the full 1.20 m ceiling bay above the column, leaving a deliberately reserved 0.30 m gap between the 0.60 m cap and neighbouring modules. This is a scene-layout opening, not a fabricated closure or structural connection.
- The two-column example uses 3.60 m centre spacing and 3.00 m between plinth edges. Exact glTF placements are in layouts.json. Convert glTF (x,y,z) to Blender (x,-z,y).
- The assembly previews include the actual existing floor and ceiling GLBs. They are context, not additional assets or variants. The shipped column GLB contains only column parts.

## Edit and reproduce

Requires Blender 4.0.2 or compatible, Python/Pillow for WebP conversion, and the project's Node dependencies for validation.

```sh
blender --background --threads 2 --python-exit-code 1 --python models/mall-structural-column/generate.py -- --skip-render
node models/mall-structural-column/validate.mjs
blender --background --threads 2 --python-exit-code 1 --python models/mall-structural-column/render_views.py
python3 models/mall-structural-column/prepare_previews.py
npm test
npm run build
node scripts/test-mall-structural-column.mjs
npm run test:library
```

The generator is self-contained; dimensions are editable constants at its top. Normal generation replaces the .blend. To preserve manual source edits, use --export-source --skip-render. The .blend retains 13 independent closed mesh objects, editable bevels, three named materials, units and connector empties. No animation or runtime interaction is claimed.

inspect_sources.py accepts an optional isolated output directory after --. It reopens the shipped source, verifies it and writes a copy with only the front lower cladding narrowed 20 mm and ivory roughness adjusted. Re-export the copy with --export-source and run verify_source_edit.mjs against that directory. This proof leaves the shipped source and the other 12 mesh geometries untouched.

## Scope and rights

Original procedural geometry and materials. No third-party artwork or textures. Owner-project reuse is authorized; public redistribution is unspecified and Gallery download remains false. This visual asset does not provide load-bearing, safety, building-code, fabrication or installation certification. Actual Android/iOS remain NOT TESTED, overall NEEDS REVIEW. See verification.md for measured local evidence.
