# GJH Chibi Visitor

The Blender-built GJH Chibi Visitor is the primary gallery model. Three earlier Unity experiments remain as independent comparison builds; their IDs, GLBs, source files, and preview files are preserved.

## Assets

| Gallery asset | Build | GLB bytes | Triangles | Vertices | Animation clips |
| --- | --- | ---: | ---: | ---: | ---: |
| GJH Chibi Visitor | Blender 5.2.3 LTS | 694,260 | 38,628 | 19,710 | 0 |
| GJH Chibi Visitor (Unity experiment, terra) | Unity 6000.0.85f2 | 38,328 | 10,848 | 800 | 0 |
| GJH Chibi Visitor (Unity experiment, sol) | Unity 6000.0.85f2 | 135,980 | 14,352 | 3,236 | 0 |
| GJH Chibi Visitor (Unity experiment, astra) | Unity 6000.0.85f2 | 100,344 | 14,736 | 2,272 | 0 |

Measurements come from the packaged GLBs. Triangle counts include mesh instances in the scene; vertex counts are unique stored position accessors.

The Blender folder also contains exports/gjh-chibi-visitor-blender-kit.glb, an all-modules reference library. It measures 3,068,504 bytes, 166,044 triangles, 95,232 vertices, and zero animation clips. The catalog registers the default GLB; the kit remains in the source folder for inspection.

## Blender source and reproduction

See [blender/README.md](blender/README.md) for the generator, editable source, measured exports, preview camera, and reproduction details.

From models/gjh-chibi-visitor/blender/, reproduce the Blender source, GLBs, and WebP views with:

    blender --background --python generate.py

Use Blender **5.2.3 LTS** for the recorded build. The generator does not require the private character-sheet image. It skips the optional side-by-side sheet comparison when that image is absent.

## Unity experiments

The terra, sol, and astra entries are earlier experimental comparisons generated independently in Unity. Their source files remain at terra/source/ChibiBuilder.cs, sol/source/ChibiBuilder.cs, and astra/source/ChibiBuilder.cs, with Unity 6000.0.85f2 and glTFast 6.21.0 recorded in each metadata file. Each is an independent comparison build with its own geometry.

The variants differ in face and clothing details: terra uses sharper chevron eyes and a compact chest treatment; sol has a broader screen, rounded hood roll, and layered hoodie; astra has more layered headphone rings and clothing accents. Each GLB uses the GJHChibiVisitor root, +Y up, +Z forward, and no animation clips.

## Rights and fidelity

All four catalog entries use the same rights statement: “Original asset; reuse in the owner's projects is authorized. Public redistribution terms have not been specified.” Gallery downloads are disabled.

The owner's character-sheet image is private and is not redistributed. The Blender model is a close procedural interpretation; exact matching remains unverified. The symmetric standing pose omits the hero illustration's waving hand, tilt, and perspective; the fins are thicker and more angular in three-quarter views; and the visor and physical reflections differ from the painted reference. The hoodie collar, cuffs, shorts, shoes, pocket seam, and Bfont chest lettering are simplified interpretations. Uniform inverted-hull outlines and PBR shading differ from variable hand-drawn linework and cel shading. Alternate expressions, outfits, and accessories remain available in source builders and the kit library. The gallery displays the static default model without runtime wardrobe switching or facial transitions.

The Unity comparisons also follow the written design reference. Their accuracy notes record the missing private sheet and each model's simplifications.
