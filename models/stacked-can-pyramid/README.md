# Stacked Can Pyramid — P1

Original warm, glossy, blank-label supermarket display for S07, S09, S10 and
S11. Six square tiers (36/25/16/9/4/1) contain 91 smooth-shaded cylindrical cans
on a low chamfered plinth. No readable text, logos, textures or external assets.
The optional concept board `docs/references/gjh-mall-concept-board.png` was not
present in this checkout; the owner's written P1 style is the reference.

Original asset; reuse in the owner's projects is authorized.

P1 supersedes the previous 20,000-triangle / 3-material budget. Each prop is
**1.0 m wide × 1.4 m high × 1.0 m deep**, 6,988 triangles including its 12-triangle
collider (6,976 visible), two materials and **two visible draw calls**. Can
sections were reduced from ten to eight sides, with five profile rings and
smooth cylindrical label bands. Seams, lids and plinth share warm satin metal.
One unit is one metre; floor-centre origin. Blender +Z up / -Y front exports to
glTF 2.0 +Y up / +Z front.

| Variant | GLB | Gallery ID | Label material |
| --- | --- | --- | --- |
| Warm coral | `exports/optimized.glb` | `stacked-can-pyramid` | `variant_a` |
| Jade | `exports/optimized-variant-b.glb` | `stacked-can-pyramid-variant-b` | `variant_b` |

Both use the existing collection, viewer, registration contract and validators.
The original ID and URL remain intact. The editable `.blend` has 91 linked can
objects sharing one mesh and two materials. Each export merges the visible
cans and plinth into `DISPLAY_MergedCansAndPlinth`. Variants have identical
geometry; only the blank band colour changes. Changing the shared can mesh
edits every can; make a mesh single-user for individual geometry edits.

The source `collider_box` is hidden in viewport/render and has no material.
Core glTF has no hidden-node flag, so each GLB stores it exclusively in the
opt-in `COLLISION_ONLY` scene at index 1, outside the default visible scene.
It is a conservative 1.0 × 1.4 × 1.0 m walk-blocking box; a consumer can load
`gltf.scenes[1]` for physics data without adding it to a rendered scene.

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/stacked-can-pyramid/generate.py
node models/stacked-can-pyramid/convert-preview.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/stacked-can-pyramid/inspect_sources.py
node models/stacked-can-pyramid/verify_source_edit.mjs
node models/stacked-can-pyramid/validate.mjs
npm test
npm run build
node models/stacked-can-pyramid/check-browser.mjs
```

Append `-- --export-source --skip-render` to export saved source edits to both
GLBs, or `-- --skip-render` to rebuild without renders. The primary export
preserves saved material edits; variant B changes only the band colour/name.
`front.png` and `3q.png` are Blender renders; the `variant-b-` files show jade.
`hero.webp` and `variant-b-hero.webp` are lightweight gallery thumbnails.
`previews/contact-1440.png` and `contact-390.png` show front and three-quarter
views of both real GLBs in a browser. Evidence and tested hashes are in
`reports/`. Physical devices and full assembled-mall performance are unverified.
Public redistribution terms are recorded in `LICENSE.md`.
