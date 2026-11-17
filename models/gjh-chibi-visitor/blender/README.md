# GJH Chibi Visitor — Blender R7

R7 adds `Cheer` and `Jump` to the default GLB while preserving the accepted R6 rest geometry, colours, 14-joint armature, skin weights, morph targets, and original `Wave`, `Idle`, and `Blink` data. The neutral stand and kit exports remain byte-identical to R6.

## Files and measured exports

- `generate.py`: procedural geometry, materials, the existing 14-joint rig, five default clips, three GLB exports, the Blender source, and review renders.
- `gjh-chibi-visitor.blend`: editable source scene. It opens at the Wave entry pose on a 0–45 frame, 30 fps timeline.
- `exports/gjh-chibi-visitor-blender.glb`: skinned default with `Wave`, `Idle`, `Blink`, `Cheer`, and `Jump`.
- `exports/gjh-chibi-visitor-blender-stand.glb`: neutral standing character with the original three clips.
- `exports/gjh-chibi-visitor-blender-kit.glb`: standing character and 13 display mounts with the original three clips.
- `previews/front.webp`, `side.webp`, `back.webp`, and `3q.webp`: static gallery views. `front.webp` is 33,938 bytes.
- `metadata.json`: measured bytes, geometry, bounds, Blender version, clips, and joint count.

| Export | Bytes | Triangles | Vertices | Height (m) | Clips |
| --- | ---: | ---: | ---: | ---: | --- |
| Default | 1,078,772 | 39,052 | 19,960 | 0.999999939 | Wave 1.5 s, Idle 2.5 s, Blink 3.0 s, Cheer 1.6 s, Jump 1.2 s |
| Neutral stand | 988,716 | 38,084 | 19,442 | 1.000000000 | Wave 1.5 s, Idle 2.5 s, Blink 3.0 s |
| All-modules kit | 4,334,380 | 167,780 | 103,151 | 1.000000000 | Wave 1.5 s, Idle 2.5 s, Blink 3.0 s |

Counts include mesh instances in the scene. Vertex counts sum unique stored POSITION accessors. Bounds use glTF metres, +Y up, and +Z forward. The default is below 40,000 triangles and 2 MiB; the stand meets the same limits, and the kit is below 5 MiB.

## Animation clips

| Clip | Duration | Motion |
| --- | ---: | --- |
| `Wave` | 1.5 s | Raised greeting with broad forearm swing and delayed body and head follow. |
| `Idle` | 2.5 s | Subtle idle motion. |
| `Blink` | 3.0 s | Eye blink. |
| `Cheer` | 1.6 s | Compact two-arm raise, 5.5 cm hop, slight back-lean, and settle. |
| `Jump` | 1.2 s | Anticipation squat, push-off, 18 cm flight, landing squash, and settle. |

Cheer and Jump begin and end in the static rest pose. Their endpoints match; both soles return to Y=0 within one micrometre. Arms remain compact and are not stretched. The short arms rise beside the lower head but do not reach above the helmet. Jump is 18% of the character's one-metre resting height. The default has no detachable accessory equipped; optional accessories retain their existing torso/head bindings without independent accessory joints.

Looping is controlled by the consuming runtime because glTF has no universal loop flag. Wave intentionally starts and ends away from the bind pose. Runtimes should blend into and out of Wave to avoid a visible pose pop. Cheer and Jump endpoint poses match the static rest pose. The Gallery metadata panel reads five animations from the default GLB; the viewer has no playback controls.

## Reproduce

Use Blender 5.2.3 LTS from this folder:

```sh
blender --background --python generate.py
python3 convert-previews.py
```

The generator uses Blender's bundled `bpy`, `bmesh`, and NumPy modules. It does not read the private design sheet, external models, textures, or fonts. Starting with `generate.py` alone creates the source scene, three GLBs, studio views, and animation review renders. Optional historical comparisons are skipped when their source files are absent. This repository includes only the four static WebP gallery previews; generated review renders and optional animated previews are not packaged.

## Remaining differences

This is an original procedural interpretation, not an exact reconstruction or an independently approved match. The hood collar still has projecting tips, the ear fins are thinner than the design sheet in side view, and the hand approaches the nearby ear cup at the Wave peak. Helmet and visor contours, headphone details, clothing folds, boots, shorts, and chest lettering remain simplified. PBR shading and uniform outlines differ from the illustrated linework; bloom depends on the renderer. Cross-clip blending, continuous-time collision, arbitrary accessory combinations, and runtime/device performance have not been verified. The private design sheet is not included.
