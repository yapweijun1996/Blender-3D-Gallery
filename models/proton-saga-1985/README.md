# Proton Saga (1985) — simplified exterior study

Original Blender interpretation of the first Saga four-door sedan. Includes a crimson body, open wheel arches, separate wheels, rectangular lamps, twin grille bars, four door outlines, handles, mirrors, trim and wipers. Approximate proportions and opaque glazing; no modeled interior, engine, animation or opening panels. This is a simplified heritage illustration, not a measured replica or exact factory trim.

## Reproduce

Requires Blender 5.1.2 and `cwebp`. From the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python models/proton-saga-1985/generate.py
cwebp -q 88 models/proton-saga-1985/preview.png -o models/proton-saga-1985/preview.webp
rm models/proton-saga-1985/preview.png
```

The deterministic generator replaces the GLB, `scene.blend` and intermediate PNG. `metadata.json` and this document are maintained separately and preserved. It exports only the `ASSET_Proton_Saga_1985` hierarchy; studio floor, lights and camera are excluded from GLB. The editable source retains the studio. No seed, external images or downloaded scripts are required. Blender may create a `.blend1` backup when replacing the source; inspect existing work before regeneration.

## Provenance and rights

Reference: [PROTON milestones](https://www.proton.com/corporate/milestones) and [PROTON heritage gallery](https://www.proton.com/happenings/2021/november/proton-unveils-new-brand-gallery). The gallery photograph was viewed for reference and is not bundled. All meshes and materials are original; no official emblem artwork is reproduced. Redistribution terms remain pending owner decision; names identify the subject and imply no endorsement. See `metadata.json` for accuracy limits.

The source and preview are genuine Blender output. Run `npm run validate:assets` after catalog integration for actual glTF errors/warnings and measured geometry. Source existence alone does not establish browser compatibility.
