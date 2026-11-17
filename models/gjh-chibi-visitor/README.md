# GJH Chibi Visitor

The Blender R7 model is the primary gallery entry and remains first in the collection. Three earlier Unity experiments remain as independent comparisons with their IDs, GLBs, source files, and previews preserved.

## Blender measured exports

| Export | Blender | GLB bytes | Triangles | Vertices | Height (m) | Joints | Animation clips |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| GJH Chibi Visitor | 5.2.3 LTS | 1,078,772 | 39,052 | 19,960 | 0.999999939 | 14 | Wave 1.5 s, Idle 2.5 s, Blink 3.0 s, Cheer 1.6 s, Jump 1.2 s |
| Neutral stand | 5.2.3 LTS | 988,716 | 38,084 | 19,442 | 1.000000000 | 14 | Wave 1.5 s, Idle 2.5 s, Blink 3.0 s |
| All-modules kit | 5.2.3 LTS | 4,334,380 | 167,780 | 103,151 | 1.000000000 | 14 | Wave 1.5 s, Idle 2.5 s, Blink 3.0 s |

Measurements are decoded from the GLBs. Triangle counts include each mesh instance in the scene; vertex counts sum unique stored POSITION accessors. The default remains below 40,000 triangles and 2 MiB. The stand meets the same limits, and the kit is below 5 MiB. Kit bounds include the complete display row. Full-precision bounds and measurements are in [Blender metadata](blender/metadata.json).

## Animation

The default GLB contains five clips: `Wave`, `Idle`, `Blink`, `Cheer`, and `Jump`. Cheer is a compact two-arm raise with a small hop; Jump includes anticipation, an 18 cm flight, landing squash, and recovery. Both new clips begin and end in the static rest pose. The stand and kit exports are unchanged from R6 and retain their original three clips.

Wave intentionally starts away from the bind pose. Runtimes should blend into and out of Wave to avoid a visible pose pop. The Gallery viewer reads animation counts from glTF and currently reports five for the default; it does not expose playback controls.

## Blender source and reproduction

The Blender source folder contains the editable scene, deterministic generator, three exports, and four WebP previews. From `models/gjh-chibi-visitor/blender/`, regenerate the source scene and GLBs with:

```sh
blender --background --python generate.py
python3 convert-previews.py
```

Blender 5.2.3 LTS is the measured generator version. The generator uses no private image, external texture, or external font. The private character sheet and comparison images are not included. See [Blender README](blender/README.md) for the clip details and remaining differences.

## Unity experiments

The terra, sol, and astra entries are earlier independent comparison builds made in Unity. Their source files remain at `terra/source/ChibiBuilder.cs`, `sol/source/ChibiBuilder.cs`, and `astra/source/ChibiBuilder.cs`; each records Unity 6000.0.85f2 and glTFast 6.21.0.

## Rights and remaining differences

This is an original procedural interpretation, not an exact reconstruction or an independently approved match. The hood collar retains projecting tips, ear fins are thinner than the design sheet in side view, and the hand approaches the nearby ear cup at the Wave peak. Helmet and visor contours, headphone details, clothing folds, boots, shorts, and lettering are simplified; PBR shading and uniform outlines differ from the illustrated linework. The original fewer-than-15,000-triangle target remains unmet; the default satisfies the current gallery budget instead. Runtime blending, continuous-time collision, arbitrary accessory combinations, and device performance have not been verified.
