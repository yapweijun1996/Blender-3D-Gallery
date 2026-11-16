# GJH Chibi Visitor

The Blender-built GJH Chibi Visitor is the primary gallery model. Three earlier Unity experiments remain as independent comparison builds; their IDs, GLBs, source files, and preview files are preserved.

## Assets

| Gallery asset | Build | GLB bytes | Triangles | Vertices | Animation clips |
| --- | --- | ---: | ---: | ---: | ---: |
| GJH Chibi Visitor, round-two wave | Blender 5.2.3 LTS | 705,712 | 39,332 | 20,062 | 0 |
| GJH Chibi Visitor (Unity experiment, terra) | Unity 6000.0.85f2 | 38,328 | 10,848 | 800 | 0 |
| GJH Chibi Visitor (Unity experiment, sol) | Unity 6000.0.85f2 | 135,980 | 14,352 | 3,236 | 0 |
| GJH Chibi Visitor (Unity experiment, astra) | Unity 6000.0.85f2 | 100,344 | 14,736 | 2,272 | 0 |

Measurements come from the packaged GLBs. Triangle counts include mesh instances in the scene; vertex counts are unique stored position accessors.

The wave GLB has measured glTF bounds of X -0.439159 to 0.361410 m, Y 0 to 1.000000 m, and Z -0.234867 to 0.238147 m. Its measured height is 0.999999995 m (1.0 m rounded); the raised left hand reaches Y 0.571054 m. The neutral stand measures 705,616 bytes, 39,332 triangles, 20,062 vertices, and zero animation clips.

The Blender folder also contains exports/gjh-chibi-visitor-blender-kit.glb, an all-modules reference library. It measures 3,083,148 bytes, 167,452 triangles, 95,936 vertices, and zero animation clips. It stays below the 175,000-triangle and 5 MiB kit checks. The catalog registers only the default wave GLB; the stand and kit remain in the source folder for inspection.

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

The owner's character-sheet image is private and is not redistributed. The Blender default now has a static, mildly leaned wave with the anatomical left hand raised and the right leg stepping forward; it is not an articulated or animated gesture, and its asymmetry and perspective are milder than the illustration. The larger raised purple Bfont lettering is still not an exact trace of the chunky illustrated mark. The broader happy arcs emit purple light, while bloom depends on the renderer. The helmet, visor shoulders, collar, and fins remain regular geometric forms; fins and collar are angular in side and rear views, and physical screen reflections differ from painted highlights. Cloth folds, cuffs, shorts, shoes, and the pocket seam are simplified. Uniform inverted-hull outlines and PBR shading differ from variable hand-drawn linework and cel shading. Alternate expressions, outfits, and accessories remain separate source/kit modules without gallery wardrobe switching or animated facial transitions. Exact fidelity to the private sheet remains unverified.

The Unity comparisons also follow the written design reference. Their accuracy notes record the missing private sheet and each model's simplifications.
