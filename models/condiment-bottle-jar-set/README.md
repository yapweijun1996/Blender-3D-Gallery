# Soy-Style Bottle Display Rack

Original S02 P2 model: sixteen generic bottles on a three-tier rack with a blank
header. Bottom to top: five large, five medium and six small bottles. Plain caps
and blank earth-tone colour bands have no text or brand marks. Peanut-butter jars
are excluded. The stable task ID is `condiment-bottle-jar-set`.

Metres, floor-centre origin; Blender +Z up / -Y front; glTF +Y up / +Z front.
The editable source retains separate rack parts, bottle bodies and caps. Blank
bands are flush material face regions on closed bottle meshes, avoiding depth
fighting from overlapping label shells in lower-precision browser depth buffers.
The delivery export batches those parts into three shared material primitives.
Vertex colours supply the blank band colours without extra materials or textures.
Opaque amber shells approximate dark liquid for low-cost mall rendering.

Advisor round 1 raises the middle and top shelf surfaces to 0.500 m and 0.820 m,
while retaining the 0.30/0.22/0.12 m bottle heights and 1.10 m rack height.
Measured cap clearance below the next shelf is 81 mm on the bottom tier and
76 mm on the middle tier; the lower front price rails leave 75 mm and 70 mm.
The source inspection checks both overhead clearance and front access, so the
previous 16 mm bottom shelf gap fails the gate.
The rebuilt GLB remains 14,092 triangles, 13,848 vertices and 586,196 bytes:
one mesh, three shared materials/primitives, no images and no animations.
The existing catalog entry has no changed numerical fields and is retained.

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/condiment-bottle-jar-set/generate.py
node models/condiment-bottle-jar-set/convert-preview.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/condiment-bottle-jar-set/inspect_sources.py
node models/condiment-bottle-jar-set/verify_source_edit.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/condiment-bottle-jar-set/verify_rebuild.py
node models/condiment-bottle-jar-set/validate.mjs
npm run validate:assets
npm test
npm run build
node models/condiment-bottle-jar-set/check-browser.mjs
```

Append `-- --export-source --skip-render` to export saved edits, or `-- --skip-render`
to rebuild geometry without rendering. PNG previews are rendered by Blender;
`hero.webp` is a Chromium encoding for the existing catalog. Evidence and measured
statistics are in `reports/` and `metadata/`. Static visual asset only; collision,
product interaction, physical devices and complete mall performance are unverified.
