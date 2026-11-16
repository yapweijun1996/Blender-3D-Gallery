# GJH Chibi Visitor — Blender primary, round 3

This folder contains the primary Blender-built model and its procedural source. The catalog registers the static R3 wave as `gjh-chibi-visitor-blender`; the neutral stand and all-modules kit are included for inspection. This is an original procedural interpretation of a private character sheet, not an exact or independently approved match.

## Files

- `generate.py`: deterministic procedural geometry, materials, three GLB exports, and studio renders.
- `convert-previews.py`: converts generated PNG renders to the four gallery WebP previews.
- `gjh-chibi-visitor.blend`: editable R3 source scene with the wave, stand, and module kit.
- `exports/gjh-chibi-visitor-blender.glb`: registered default wave.
- `exports/gjh-chibi-visitor-blender-stand.glb`: neutral standing version.
- `exports/gjh-chibi-visitor-blender-kit.glb`: standing character with 13 visible module mounts.
- `previews/front.webp`, `side.webp`, `back.webp`, and `3q.webp`: 1024 × 1024 views of the default export.
- `metadata.json`: measured GLB sizes, triangle and vertex counts, bounds, height, and Blender version.

## Reproduce

Use Blender **5.2.3 LTS** from this directory:

    blender --background --python generate.py

The generator uses Blender's bundled `bpy`, `bmesh`, and NumPy modules. It creates the `.blend`, all three GLBs, studio PNG renders, and `reports/generation.json`. The character-sheet and R2 comparison images are optional; when absent, the generator prints `OPTIONAL_COMPARISON_SKIPPED` and completes the regular exports.

R3 reproduction was checked in a fresh temporary directory containing only `generate.py`, with no `design-sheet.png` and no `reports/r2/`. Blender completed both optional comparison skips, generated all three GLBs, and each generated SHA-256 matched the shipped GLB. The saved blend and GLBs do not embed the private character sheet.

The gallery previews are WebP conversions of the rendered PNGs. With Python Pillow installed, run:

    python3 convert-previews.py

The front preview is **35,128 bytes**, below 150 KiB. The other views use WebP quality 86.

## Measured exports

Measurements below are decoded from the shipped GLBs. Triangle counts include each mesh instance in the scene. Vertex counts sum unique stored POSITION accessors. All three exports are self-contained glTF 2.0, texture-free, static, and unrigged, with metres, +Y up, +Z front, and the `GJHChibiVisitor` root. Purple emission uses `KHR_materials_emissive_strength`.

| Export | Bytes | Triangles | Vertices | Animation clips | Measured height (m) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Default wave | 720,372 | 39,564 | 20,212 | 0 | 0.999999917 |
| Neutral stand | 695,076 | 38,916 | 19,858 | 0 | 1.000000001 |
| All-modules kit | 3,115,608 | 169,444 | 96,952 | 0 | 1.000000001 |

The default and stand are each below 40,000 triangles and 2 MiB. The kit is below 5 MiB; its size and bounds include all 13 mounts. Full-precision measurements are stored in `metadata.json` and checked by `../validate.mjs`.

| Export | Minimum glTF XYZ (m) | Maximum glTF XYZ (m) |
| --- | --- | --- |
| Wave | (-0.318953, 0.000000, -0.230665) | (0.526400, 1.000000, 0.231137) |
| Stand | (-0.393164, 0.000000, -0.234609) | (0.393164, 1.000000, 0.235378) |
| Whole kit | (-4.901769, 0.000000, -2.396770) | (4.901769, 1.000000, 0.235378) |

The default raised mitten reaches Y=0.596196731 m. The measured model height is 0.999999917 m (1.000 m rounded). Both physical shoe surfaces and inverted-hull outlines meet Y=0 within 0.000001 m. The whole kit spans approximately 9.803539 × 1.000000 × 2.632147 m because its 13 mounts are arranged in a display row.

## R3 changes and remaining differences

R3 rebuilds the hood as a rounded roll and covered inner cowl, softens the folded collar, thins and rounds the swept fins, bends the raised sleeve and mitten, leans the body and head, and gives the feet a clearer step. The stand and kit remain neutral. Lavender fin gradients export in `COLOR_0`; violet and lavender emission and wider inverted-hull outlines remain present in the GLBs.

The hood collar still has projecting tips. The fins are thinner than the character sheet shows in side view, and the raised hand overlaps the headphone silhouette. The wave is a baked pose, not a rigged or animated gesture. Helmet and visor contours, headphones, folds, boots, shorts, and Bfont lettering remain simplified. PBR highlights and uniform outlines differ from the illustration; bloom depends on the renderer. The private sheet is not redistributed, and no exact-fidelity score or independent art approval is claimed.

The metadata records measured geometry and file values only. The stand and kit remain local source-folder alternatives; the catalog registers only the default wave.
