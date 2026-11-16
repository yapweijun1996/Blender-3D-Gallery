# Pomelo STEM Mascot — R5

The registered Pomelo STEM Mascot is an original procedural Blender character with a skinned 20-joint rig. The same folder contains the editable scene, deterministic generator, default/stand/kit GLBs, five still previews, and four animation strips. The six expressions are separate figures in the kit; they are not a runtime expression switcher.

## Reproduce

Use Blender 5.2.3 LTS from this directory:

```sh
blender --background --python-exit-code 1 --python generate.py
python3 convert-previews.py
node validate.mjs
```

The generator uses Blender's bundled `bpy`, `bmesh`, NumPy, and `mathutils`. It does not read a design board or require old R3/R4 folders. The optional R3 colour comparison is skipped when its baseline renders are absent. `--no-render` creates the `.blend` and all three GLBs without inspection renders. The preview converter requires Python Pillow.

The generator was also run headlessly in a temporary folder containing only `generate.py`, with no private image or R3/R4 directories. SHA-256 hashes for the regenerated default, stand, and kit GLBs matched the shipped files. This verifies GLB byte reproducibility with Blender 5.2.3 LTS on the tested platform; it does not claim byte-identical `.blend` or rendered previews.

## Measured exports

Measurements are decoded from the shipped GLBs. Triangle totals include mesh instances; vertex totals count unique stored position accessors. Bounds use glTF X/Y/Z metres in the rest pose.

| Export | Bytes | Triangles | Vertices | Joints | Clips |
| --- | ---: | ---: | ---: | ---: | --- |
| Registered default | 967,908 | 39,832 | 20,476 | 20 | 3 |
| Neutral stand | 968,248 | 39,832 | 20,476 | 20 | 3 |
| Six-expression kit | 4,441,836 | 277,820 | 142,500 | 26 | 3 |

The default bounds are X `[-0.387845635, 0.387845635]`, Y `[0, 1.000000119]`, and Z `[-0.266617000, 0.270411611]` metres. The kit bounds include its display row. Khronos validation reports 0 errors and 0 warnings for all three GLBs. The default and stand are below 40,000 triangles and 2 MiB; the kit is below 5 MiB. Full-precision measurements are recorded in `metadata.json` and checked by `validate.mjs`.

## Animation clips

| Clip | Duration | Description |
| --- | ---: | --- |
| `Idle` | 2.5 s | Gentle breathing and leaf sway. |
| `Wave` | 1.5 s | A raised greeting with a forearm wobble, body lean, head tilt, leaf follow-through, and slight foot compression. |
| `Blink` | 3.0 s | Looping eye blink. |

The PNG strips show 12 frames per clip freshly rendered from the exported GLB; Wave has both front and three-quarter strips. Loop velocity continuity for Wave has not been proven. Runtime consumers should blend into and out of Wave to avoid a visible pose pop. The Gallery reports three animations in the model details panel; it does not provide clip playback controls.

## Remaining differences and integration notes

This is a procedural interpretation of a private design, not an exact reconstruction or independently approved match. No visual-similarity percentage is measured. The accepted R4 middle yellow-green `#CBE85A` palette is retained. Fruit and face contours are more regular than the illustration, surface shading and fitted overlaps remain, and the six expression figures are static kit alternatives. The R5 Wave arm uses rounded capsule links with intentional overlap at joints; sampled QA does not prove continuous collision-free motion.

The outlines are inverted hulls and need backface culling; disable their shadow casting in consuming renderers. Skinned meshes are scene roots alongside the named `PomeloStemMascot` rig anchor, so place the whole glTF scene. Default and stand use 20 joints; the kit has 26, including six expression-mount joints.

## Provenance and rights

The Blender source and GLBs contain original character geometry and materials; no reference image is used as a texture or packed into the `.blend`. Generic mesh/export helpers were adapted from an authorized read-only example. No third-party model is included. Public redistribution terms have not been specified; Gallery downloads are disabled.
