# GJH Chibi Visitor

The Blender R6 model is the primary gallery entry. Three earlier Unity experiments remain as independent comparisons; their IDs, GLBs, source files, and previews are preserved.

## Blender R6 measured exports

| Export | Blender | GLB bytes | Triangles | Vertices | Height (m) | Joints | Animation clips |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| GJH Chibi Visitor | 5.2.3 LTS | 1,046,056 | 39,052 | 19,960 | 0.999999939 | 14 | Wave 1.5 s, Idle 2.5 s, Blink 3.0 s |
| Neutral stand | 5.2.3 LTS | 988,716 | 38,084 | 19,442 | 1.000000000 | 14 | Wave 1.5 s, Idle 2.5 s, Blink 3.0 s |
| All-modules kit | 5.2.3 LTS | 4,334,380 | 167,780 | 103,151 | 1.000000000 | 14 | Wave 1.5 s, Idle 2.5 s, Blink 3.0 s |

Measurements are decoded from the GLBs. Triangle counts include each mesh instance in the scene; vertex counts sum unique stored POSITION accessors. The default remains below 40,000 triangles and 2 MiB. The stand meets the same limits, and the kit is below 5 MiB. Kit bounds include the complete display row. Full-precision bounds and measurements are in [Blender metadata](blender/metadata.json).

The earlier Unity comparison assets are unchanged:

| Gallery asset | Unity | GLB bytes | Triangles | Vertices | Animation clips |
| --- | --- | ---: | ---: | ---: | ---: |
| GJH Chibi Visitor (terra experiment) | 6000.0.85f2 | 38,328 | 10,848 | 800 | 0 |
| GJH Chibi Visitor (sol experiment) | 6000.0.85f2 | 135,980 | 14,352 | 3,236 | 0 |
| GJH Chibi Visitor (astra experiment) | 6000.0.85f2 | 100,344 | 14,736 | 2,272 | 0 |

## Animation

The default GLB is skinned and contains `Wave`, `Idle`, and `Blink`. The neutral stand and kit also include the same 14-joint skeleton and clips. The default's `Wave` entry and loop endpoint differ from its unanimated rest pose; consuming runtimes should blend into and out of `Wave` to avoid a visible pose pop. Gallery playback controls were not added.

## Blender source and reproduction

The Blender source folder contains the editable scene, deterministic generator, three exports, and four WebP previews. From `models/gjh-chibi-visitor/blender/`, regenerate the source scene, GLBs, and renders with:

```sh
blender --background --python generate.py
python3 convert-previews.py
```

Blender 5.2.3 LTS is the measured generator version. The generator uses no private image or external texture. A clean temporary-directory run containing only `generate.py`, with no design sheet and no R3/R4/R5 folders, regenerated the three shipped GLBs with matching SHA-256 hashes. See [Blender README](blender/README.md) for the exact measurements and the Wave blending note.

## Unity experiments

The terra, sol, and astra entries are earlier independent comparison builds made in Unity. Their source files remain at `terra/source/ChibiBuilder.cs`, `sol/source/ChibiBuilder.cs`, and `astra/source/ChibiBuilder.cs`; each records Unity 6000.0.85f2 and glTFast 6.21.0.

## Rights and remaining differences

The private character sheet and sheet-comparison images are not included. Exact fidelity and independent art approval are not claimed. R6 retains projecting hood-collar tips, thinner-than-reference ear fins in side view, and a simplified hand, helmet, visor, headphones, clothing, footwear, and lettering. PBR shading and uniform outlines differ from the illustrated surface and linework. The original fewer-than-15,000-triangle target remains unmet; the default satisfies the current gallery budget instead.
