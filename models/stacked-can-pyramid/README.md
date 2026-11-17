# Stacked Can Pyramid

Original blank tin-can display for supermarket stores S07, S09, S10 and S11.
Six square tiers (36/25/16/9/4/1 cans) rest on a low chamfered neutral plinth.
Muted jade bodies and satin tinplate seams/lids have no text or logos. No external
assets or textures. Static visual prop; scene placement and collision are separate.

Metres, floor-centre origin; Blender +Z up / -Y front; glTF +Y up / +Z front.
The source retains 91 linked ten-sided can instances. The export batches cans
into two material primitives plus one plinth primitive to keep draw calls low.
Shared source mesh edits affect every can; make a mesh single-user for variants.

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/stacked-can-pyramid/generate.py
node models/stacked-can-pyramid/convert-preview.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/stacked-can-pyramid/inspect_sources.py
node models/stacked-can-pyramid/verify_source_edit.mjs
node models/stacked-can-pyramid/validate.mjs
npm run validate:assets
npm test
npm run build
node models/stacked-can-pyramid/check-browser.mjs
```

Append `-- --export-source --skip-render` to re-export saved source edits, or
`-- --skip-render` to regenerate without preview rendering. PNG previews are
rendered in Blender; `hero.webp` is a lightweight conversion for the catalog.
Measured delivery evidence is in `reports/`. Physical devices and the assembled
mall's frame rate are unverified. Rights are recorded in `LICENSE.md`.
