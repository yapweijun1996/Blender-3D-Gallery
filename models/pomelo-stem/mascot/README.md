# Pomelo STEM Mascot — R6

The registered Pomelo STEM Mascot is an original procedural Blender character with a skinned 20-joint rig. This folder contains the editable scene, generator, default/stand/kit GLBs, five gallery views, and eight animation strips. The six expression figures in the kit are static alternatives, not runtime expression controls.

## Reproduce

Use Blender 5.2.3 LTS from this directory:

```sh
blender --background --python-exit-code 1 --python generate.py
python3 convert-previews.py
node validate.mjs
```

The generator uses Blender's bundled `bpy`, `bmesh`, NumPy, and `mathutils`. It does not read or pack a design sheet and does not require R3/R4 folders; the optional historical comparison is skipped when its baseline renders are absent. `--no-render` writes the `.blend` and all three GLBs without inspection renders. The preview converter uses Python Pillow.

The generator was also run headlessly in a temporary directory containing only `generate.py`, with no design sheet or R3/R4 folders. The regenerated default, stand, and kit GLB SHA-256 hashes matched the shipped files. This confirms byte reproducibility with Blender 5.2.3 LTS on the tested platform; it does not claim byte-identical `.blend` files or rendered previews.

## Measured exports

Measurements are decoded from the shipped GLBs. Triangle totals include mesh instances; vertex totals sum unique stored POSITION accessors. Bounds use glTF X/Y/Z metres in the rest pose.

| Export | Bytes | Triangles | Vertices | Joints | Clips |
| --- | ---: | ---: | ---: | ---: | ---: |
| Registered default | 1,007,676 | 39,832 | 20,476 | 20 | 5 |
| Neutral stand | 1,008,012 | 39,832 | 20,476 | 20 | 5 |
| Six-expression kit | 4,481,948 | 277,820 | 142,500 | 26 | 5 |

All three exports validate with 0 Khronos errors and 0 warnings. The default and stand are below 40,000 triangles and 2 MiB; the kit is below 5 MiB. The default bounds are X `[-0.387845635, 0.387845635]`, Y `[0, 1.000000119]`, and Z `[-0.266617000, 0.270411611]` metres. Full-precision bounds and measurements are recorded in `metadata.json` and checked by `validate.mjs`.

## Animation clips

| Clip | Duration | Description |
| --- | ---: | --- |
| `Idle` | 2.5 s | Gentle breathing and leaf sway. |
| `Wave` | 1.5 s | Raised greeting with forearm wobble, body lean, head tilt, leaf follow-through, and slight foot compression. |
| `Blink` | 3.0 s | Looping eye blink. |
| `Cheer` | 1.6 s | Compact raised fists, a 6.5 cm hop, slight back lean, and settle. |
| `Jump` | 1.2 s | Anticipation tuck, push-off, 17.5 cm airborne clearance, landing tuck, and settle. |

The default, stand, and kit GLBs each contain all five clips. Cheer and Jump return to the rest pose at their endpoints. Wave loop velocity continuity has not been proven; runtimes should blend into and out of Wave. The Gallery reports five animations in the model details panel but has no clip playback controls.

## Remaining differences and integration notes

This is a procedural interpretation, not an exact reconstruction or an independently approved match. No visual-similarity percentage is measured. The accepted middle yellow-green palette is retained, while the fruit and face contours remain more regular than the reference. Cheer raises compact fists to the lower-cheek area; the preserved short arms do not reach over the oversized head. Existing fitted overlaps and neck shading remain. Sampled checks do not prove continuous-time collision safety or arbitrary clip blends.

The outlines are inverted hulls and require backface culling; disable their shadow casting in consuming renderers. Skinned meshes are scene roots alongside the named `PomeloStemMascot` rig anchor, so move the whole GLB scene. The default and stand use 20 joints; the kit has 26, including six expression-mount joints.

## Provenance and rights

The Blender source and GLBs contain original character geometry and materials; no reference image is used as a texture or packed into the `.blend`. Generic mesh/export helpers were adapted from an authorized read-only example. No third-party model is included. Public redistribution terms have not been specified; Gallery downloads are disabled.
