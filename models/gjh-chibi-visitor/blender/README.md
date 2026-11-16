# GJH Chibi Visitor — Blender primary

This folder contains the primary static Blender-built model and its source. The model is an original procedural interpretation of the owner's GJH Chibi Visitor concept; exact matching to the private sheet remains unverified.

## Files

- generate.py: procedural geometry, materials, GLB exports, and four rendered views.
- gjh-chibi-visitor.blend: editable source scene and named character hierarchy.
- exports/gjh-chibi-visitor-blender.glb: default happy-face, white-hoodie character registered in the gallery.
- exports/gjh-chibi-visitor-blender-kit.glb: default character and visible mounts for the 13 module options.
- previews/front.webp, side.webp, back.webp, and 3q.webp: 1024 × 1024 views of the default export.
- metadata.json: measured geometry and file metrics, display settings, attribution, and accuracy notes.

## Reproduce

Use Blender **5.2.3 LTS**. Run this command from this directory:

    blender --background --python generate.py

The generator uses Blender's bundled bpy, bmesh, and NumPy modules. It recreates the editable scene, default and kit GLBs, WebP previews, and reports/generation.json. The optional comparison image is skipped when design-sheet.png is absent. The private sheet is not included in this folder or embedded in the source scene.

The GLBs use glTF 2.0, native metres, +Y up, +Z front, and a scene root named GJHChibiVisitor. The default character is 1.0 m high including fins and outline meshes. It contains no textures, external buffers, or animation clips. Purple emission uses KHR_materials_emissive_strength. The character is static and unrigged.

## Measured exports

| Export | Bytes | Triangles | Vertices | Animation clips |
| --- | ---: | ---: | ---: | ---: |
| Default gallery model | 694,260 | 38,628 | 19,710 | 0 |
| All-modules kit | 3,068,504 | 166,044 | 95,232 | 0 |

Triangle counts include each mesh instance in the scene. Vertex counts sum unique stored position accessors. The Khronos glTF Validator reports zero errors and zero warnings for both exports. The kit is included as a source inspection aid and is not listed in models/catalog.json.

## Character-sheet fidelity

The owner's character-sheet image is private and is not redistributed. This is a close procedural interpretation, not a claim of a 100 percent match. It uses a symmetric standing pose and does not reproduce the hero illustration's waving hand, tilted stance, or expressive perspective. The helmet contours are mathematically regular, and the fins are thicker and more angular at three-quarter angles. The face screen has slightly more rectangular upper shoulders and physical reflections instead of painted highlights.

Purple emission survives export, but rendered brightness and bloom vary by viewer. The hoodie collar is more geometric, the cloth has fewer folds, the pocket seam is a procedural addition, and the Bfont chest lettering is not an exact trace of the illustration. Cuffs, shorts, and shoes are simplified solids. Uniform inverted-hull outlines do not reproduce variable pen pressure, and the PBR material response is not cel shading.

The source builders and kit contain alternate expressions, ears, outfits, and accessories as inspectable modules. The gallery presents the static default model; it does not switch wardrobe options or animate facial transitions. Exact fidelity to the private character sheet remains unverified.
