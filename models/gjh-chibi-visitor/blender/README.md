# GJH Chibi Visitor — Blender primary

This folder contains the primary Blender-built model and reproducible source for round two. The catalog registers the static wave pose as `gjh-chibi-visitor-blender`; the neutral stand and all-modules kit are included for inspection only. The model is an original procedural interpretation of the owner's concept, and exact matching to the private character sheet remains unverified.

## Files

- `generate.py`: procedural geometry, materials, exports, and rendered PNG views.
- `convert-previews.py`: converts the rendered PNG masters to gallery WebP previews.
- `gjh-chibi-visitor.blend`: editable R2 source scene and named hierarchy.
- `exports/gjh-chibi-visitor-blender.glb`: default static wave pose, registered in the gallery.
- `exports/gjh-chibi-visitor-blender-stand.glb`: neutral standing alternative.
- `exports/gjh-chibi-visitor-blender-kit.glb`: standing model and visible mounts for all 13 modules.
- `previews/front.webp`, `side.webp`, `back.webp`, and `3q.webp`: 1024 × 1024 views of the default wave export.
- `metadata.json`: measured default-export metrics and bounds, display settings, attribution, and accuracy notes.

## Reproduce

Use Blender **5.2.3 LTS**. From this directory, run:

    blender --background --python generate.py

The generator uses Blender's bundled `bpy`, `bmesh`, and NumPy modules. It recreates the editable scene, wave, stand, and kit GLBs, 1024 × 1024 PNG views, and `reports/generation.json`. The optional character-sheet comparison is skipped with a log message when `design-sheet.png` is absent. The optional R1 comparison is skipped with a log message when `reports/r1/previews/front.png` is absent. Neither reference image is included here or embedded in the scene.

The tracked previews are WebP conversions of the generated PNGs. With Python Pillow installed, run:

    python3 convert-previews.py

This uses WebP quality 88 for the 1024 × 1024 front thumbnail (34,830 bytes, under 150 KiB) and quality 86 for the other views.

The GLBs use glTF 2.0, native metres, +Y up, +Z front, and a scene root named `GJHChibiVisitor`. They are self-contained, texture-free, static, and unrigged. Purple emission uses `KHR_materials_emissive_strength`.

## Measured exports

| Export | Bytes | Triangles | Vertices | Animation clips |
| --- | ---: | ---: | ---: | ---: |
| Default wave | 705,712 | 39,332 | 20,062 | 0 |
| Neutral stand | 705,616 | 39,332 | 20,062 | 0 |
| All-modules kit | 3,083,148 | 167,452 | 95,936 | 0 |

Triangle counts include each mesh instance in the scene. Vertex counts sum unique stored position accessors. The gallery default is below the R2 checks of 40,000 triangles and 2 MiB. The stand uses the same checks. The kit is below 175,000 triangles and 5 MiB; it is not registered in `models/catalog.json`. The Khronos glTF Validator reports zero errors and zero warnings for each export.

In generated `reports/roundtrip.json`, triangle and bounds fields describe the character only; the inspection excludes the kit's 13-mount row. Those fields are not whole-kit measurements. The complete kit export, including its mounts, measures 167,452 triangles as listed above.

The default wave's measured glTF bounds are X -0.439159 to 0.361410 m, Y 0.000000001 to 0.999999996 m, and Z -0.234867 to 0.238147 m. The measured height is 0.999999995 m, reported as **1.0 m** when rounded. The raised anatomical left hand reaches Y 0.571054 m; it does not extend above the helmet in this build. Both shoes touch the floor within measurement tolerance.

## Gallery presentation

`display.previewCameraDirection` is `[0, 0.1, 1]`, a near-front view that keeps the face, chest lettering, and raised hand visible. The gallery normalizes this direction and fits camera distance automatically. `docs/assets.md` defines no camera-distance or zoom override, so the metadata does not invent one. The task report records this remaining framing limitation.

## Character-sheet fidelity

R2 adds a static, mildly leaned wave with the anatomical left hand raised and a stepping right leg. It is not an articulated elbow or animated wave; the pose and perspective remain milder than the hero illustration. Raised purple Bfont lettering is larger and bolder but is not an exact trace of the illustrated chunky mark. The wider, thicker happy arcs emit purple light, though renderer-dependent bloom is not guaranteed.

The helmet contours, visor shoulders, collar, and fins remain regular geometric forms. The collar and fins are angular from side and rear views, and physical screen reflections differ from painted highlights. Cloth folds, cuffs, shorts, shoes, and the pocket seam are simplified. Uniform inverted-hull outlines do not reproduce variable pen pressure, and the PBR response is not cel shading. Expressions, outfits, and accessories remain separate source/kit modules without gallery wardrobe switching or animated facial transitions. The private character sheet is not redistributed, and exact fidelity remains unverified.
