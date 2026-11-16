# GJH Chibi Visitor

The Blender-built model is the primary gallery entry. Three earlier Unity experiments remain as independent comparisons; their IDs, GLBs, source files, and previews are preserved.

## Measured exports

| Gallery asset | Build | GLB bytes | Triangles | Vertices | Animation clips |
| --- | --- | ---: | ---: | ---: | ---: |
| GJH Chibi Visitor, R3 wave | Blender 5.2.3 LTS | 720,372 | 39,564 | 20,212 | 0 |
| GJH Chibi Visitor, neutral stand | Blender 5.2.3 LTS | 695,076 | 38,916 | 19,858 | 0 |
| GJH Chibi Visitor, all-modules kit | Blender 5.2.3 LTS | 3,115,608 | 169,444 | 96,952 | 0 |
| GJH Chibi Visitor (Unity experiment, terra) | Unity 6000.0.85f2 | 38,328 | 10,848 | 800 | 0 |
| GJH Chibi Visitor (Unity experiment, sol) | Unity 6000.0.85f2 | 135,980 | 14,352 | 3,236 | 0 |
| GJH Chibi Visitor (Unity experiment, astra) | Unity 6000.0.85f2 | 100,344 | 14,736 | 2,272 | 0 |

Measurements are decoded from the packaged GLBs. Triangle counts include each mesh instance in the scene; vertex counts sum unique stored POSITION accessors. The registered Blender wave is below 40,000 triangles and 2 MiB. The neutral stand has the same limits. The kit includes the standing character and 13 module mounts and is below 5 MiB; its bounds include the full display row.

The R3 wave bounds are X -0.318953 to 0.526400 m, Y 0.000000 to 1.000000 m, and Z -0.230665 to 0.231137 m. Its measured height is 0.999999917 m, or 1.000 m rounded. The stand height is 1.000000001 m. The whole kit measures 9.803539 × 1.000000 × 2.632147 m including its mounts. Full-precision wave, stand, and kit measurements are in [Blender metadata](blender/metadata.json).

## Blender source and reproduction

The Blender source folder contains the editable scene, deterministic generator, three exports, and four WebP previews. See [blender/README.md](blender/README.md) for the measured bounds, preview conversion, validation, and reproduction instructions.

From `models/gjh-chibi-visitor/blender/`, regenerate the editable source, three GLBs, and PNG renders with:

    blender --background --python generate.py

Blender 5.2.3 LTS is the measured generator version. The generator runs without the private character sheet or archived R2 images; optional comparison renders are skipped when those images are absent. A clean temporary-directory run without either reference reproduced all three shipped GLBs with identical SHA-256 hashes.

To convert the PNG renders into the gallery WebP previews, run `python3 convert-previews.py` in a Python environment with Pillow installed.

## Unity experiments

The terra, sol, and astra entries are earlier independent comparison builds made in Unity. Their source files remain at `terra/source/ChibiBuilder.cs`, `sol/source/ChibiBuilder.cs`, and `astra/source/ChibiBuilder.cs`; each records Unity 6000.0.85f2 and glTFast 6.21.0. They use the `GJHChibiVisitor` root, +Y up, +Z forward, and no animation clips.

## Rights and remaining differences

All four catalog entries use the same rights statement: “Original asset; reuse in the owner's projects is authorized. Public redistribution terms have not been specified.” Gallery downloads are disabled. The private character sheet and sheet-comparison images are not included in this repository.

The R3 Blender default is a static bent-elbow wave with an open mitten, a small body and head lean, and a clearer step. It has no rig or animation. The hood collar still has projecting tips, the fins are thinner than the sheet shows in side view, and the raised hand overlaps the headphone silhouette. Helmet and visor contours, headphone details, clothing folds, boots, shorts, and Bfont lettering remain simplified. PBR shading and uniform outlines differ from the illustrated surface and linework. Exact fidelity and independent art approval are not claimed.

The Unity comparisons remain earlier independent interpretations of the written concept; their accuracy notes document their own simplifications.
