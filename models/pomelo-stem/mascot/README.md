# Pomelo STEM Mascot

An original fruit mascot built procedurally in Blender. The registered GLB is the static, front-facing happy hero pose. The same folder keeps a neutral standing GLB and a kit with Happy, Laugh, Surprised, Wink, Thinking, and Sad figures; the kit does not add runtime expression switching.

## Reproduction

From this directory, with Blender 5.2.3 LTS installed, run:

```sh
blender --background --python generate.py
python3 convert-previews.py
node validate.mjs
```

The generator writes the editable `.blend`, three GLBs, and PNG inspection renders. The optional comparison pass is skipped when its optional local reference image is absent; that reference is not included here. Pillow is required only for converting the PNG renders to the gallery WebP previews.

## Measured exports

Measurements below come from the packaged GLBs. Triangle totals include mesh instances in the scene; vertex totals count unique stored position accessors. Bounds are in glTF X/Y/Z metres and include the outline geometry.

| Export | Bytes | Triangles | Vertices | Animation clips | Height |
| --- | ---: | ---: | ---: | ---: | ---: |
| Registered hero | 671,820 | 37,616 | 19,228 | 0 | 1.000000011 m |
| Standing | 672,108 | 37,616 | 19,228 | 0 | 1.000000011 m |
| Six-expression kit | 3,608,244 | 264,404 | 134,966 | 0 | 1.000000011 m |

The hero bounds are X `[-0.387587041, 0.387587041]`, Y `[-0.000000002, 1.000000009]`, and Z `[-0.266415060, 0.267061502]`. Small deviations around zero and one are floating-point export precision. The hero and standing exports remain below 40,000 triangles and 2 MiB; the kit remains below 5 MiB. Its triangle total covers seven complete figures.

## Fidelity and scope

This is a procedural interpretation, not an exact reproduction of the owner's design board. A strict independent reviewer estimated visual similarity at about 67%. Colour, hand and foot shape, face depth, and expression scale remain visibly different. The shell reads greener and less lemon-yellow, the cream and shadows are paler, the face inset and mouth are shallower, and the mittens and shoes are simplified. The face and fruit contours are more regular, the hands have no finger articulation, and the pose is more upright than the illustrated hero.

The main proportions meet the board's targets: the head is 63.8% of total height, head width is about 77% of total height, and body width is about 62% of head width. These proportions do not remove the visible surface, colour, and expression differences above. The expressions are separate static figures in the kit, not shape keys or animated transitions. No rig, animation, browser/mobile certification, or human art approval is claimed.

## Provenance and rights

The Blender source and GLBs contain original character geometry and materials; no reference image is used as a texture or packed into the `.blend`. Generic mesh/export helpers were adapted from an authorized read-only example. No third-party model is included. The registered asset uses the same rights wording as the GJH Chibi Visitor assets: “Original asset; reuse in the owner's projects is authorized. Public redistribution terms have not been specified.” Gallery downloads are disabled.
