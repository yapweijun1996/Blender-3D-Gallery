# GJH Chibi Visitor — Blender R6

This folder contains the primary Blender-built character, its editable scene, deterministic generator, three GLB exports, and four gallery WebP previews. The catalog registers `gjh-chibi-visitor-blender` first in the GJH Chibi Visitor collection. The stand and all-modules kit are local alternatives.

## Files

- `generate.py`: procedural geometry, materials, 14-joint rig, three GLB exports, source scene, and review renders.
- `convert-previews.py`: converts the four generated PNG views into gallery WebP previews.
- `gjh-chibi-visitor.blend`: editable R6 Blender scene. It opens at the Wave entry pose on a 0–45 frame, 30 fps timeline.
- `exports/gjh-chibi-visitor-blender.glb`: registered, skinned default with `Wave`, `Idle`, and `Blink` clips.
- `exports/gjh-chibi-visitor-blender-stand.glb`: neutral standing character with the same rig and clips.
- `exports/gjh-chibi-visitor-blender-kit.glb`: standing character and 13 display mounts, with the same rig and clips.
- `previews/front.webp`, `side.webp`, `back.webp`, and `3q.webp`: views of the unanimated default pose. `front.webp` is 33,940 bytes.
- `metadata.json`: measured file sizes, geometry, bounds, Blender version, clip names and durations, and joint count.

## Reproduce

Use Blender 5.2.3 LTS from this folder:

```sh
blender --background --python generate.py
python3 convert-previews.py
```

The generator uses Blender's bundled `bpy`, `bmesh`, and NumPy modules. It reads no private image, texture, or external font. It creates the `.blend`, all three GLBs, PNG studio views, animation review renders, and a generation report. Historical comparison renders are optional and are skipped when the earlier-round files are absent.

Reproduction was verified in a temporary directory containing only `generate.py`, with no design sheet and no R3, R4, or R5 folders. Blender 5.2.3 LTS completed the headless build, and SHA-256 hashes of all three regenerated GLBs matched the shipped exports. This verifies GLB reproducibility on the measured Blender version and platform; it does not claim byte-identical `.blend` files or rendered PNGs.

## Measured exports

Measurements are decoded from the shipped GLBs. Triangle counts include mesh instances in the scene. Vertex counts sum unique stored POSITION accessors. Bounds use glTF metres, +Y up, and +Z forward. All three GLBs are self-contained and have one 14-joint skin and the same three animation clips.

| Export | Bytes | Triangles | Vertices | Height (m) | Animation clips |
| --- | ---: | ---: | ---: | ---: | --- |
| Default | 1,046,056 | 39,052 | 19,960 | 0.999999939 | Wave 1.5 s, Idle 2.5 s, Blink 3.0 s |
| Neutral stand | 988,716 | 38,084 | 19,442 | 1.000000000 | Wave 1.5 s, Idle 2.5 s, Blink 3.0 s |
| All-modules kit | 4,334,380 | 167,780 | 103,151 | 1.000000000 | Wave 1.5 s, Idle 2.5 s, Blink 3.0 s |

The default is below 40,000 triangles and 2 MiB; the stand meets the same limits, and the kit is below 5 MiB. The kit's bounds include its full display row. Full-precision measurements are recorded in `metadata.json`.

## Animation clips

| Clip | Duration | Description |
| --- | ---: | --- |
| `Wave` | 1.5 s | Raised greeting with a broad forearm swing and delayed body and head follow. |
| `Idle` | 2.5 s | Subtle looping idle motion. |
| `Blink` | 3.0 s | Looping eye blink. |

The default GLB is skinned and stores all three clips in glTF. Looping is controlled by the consuming runtime. The `Wave` entry and repeated endpoint pose differ from the unanimated rest pose. Runtimes should blend into and out of `Wave` to avoid a visible pose pop. In the Gallery model metadata panel, `Animations` reports a count of 3; clip names and durations are listed here and in `metadata.json`. The viewer does not expose animation playback controls.

## Remaining differences

This is an original procedural interpretation, not an exact reconstruction or an independently approved match. The hood collar still has projecting tips, the ear fins remain thinner than the design sheet in side view, and the hand reaches the lower edge of the nearby ear cup at the Wave peak. Helmet and visor contours, headphone details, clothing folds, boots, shorts, and chest lettering remain simplified. PBR shading and uniform outlines differ from the illustrated linework; bloom depends on the renderer. The original design sheet is private and is not included.

The source's original target of fewer than 15,000 triangles is not met. The admitted default instead satisfies the gallery's current asset budget of fewer than 40,000 triangles and 2 MiB. See `metadata.json` for measured values.
