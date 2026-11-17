# Atrium Fountain

Original P3 GJH Mall water feature in the existing **Mall Fixtures** category.
The 5 m circular stone basin has a 0.8 m coping, two centre bowls, eight bronze
nozzles and eight translucent parabolic water arcs. The centre finial reaches
2.15 m. No external assets, textures, brands, readable text or fluid simulation.

The folder layout, selected-root export, source-edit mode and quality gate
follow `self-checkout-machine`. Source geometry stays separately editable;
export copies consolidate into five mesh primitives and three shared materials.
The stone palette uses vertex colours; the water uses lightweight alpha blending.
Studio floor, lights and camera are excluded from the GLB.
The gallery card uses a 13,616-byte WebP derivative; all four rendered PNGs remain
available for visual inspection.

```sh
/opt/homebrew/bin/blender --background --python models/atrium-fountain/generate.py
node models/atrium-fountain/make-thumbnails.mjs
node models/atrium-fountain/validate.mjs
npm run validate:assets
npm test
npm run build
node models/atrium-fountain/check-page.mjs
```

Rebuilds are deterministic and replace the source. To export saved manual edits:

```sh
/opt/homebrew/bin/blender --background --python models/atrium-fountain/generate.py -- --export-source --skip-render
```

The source-edit probe writes an edited copy under `/tmp` and independently
checks the 20 mm jet translation; delivery stays intact:

```sh
/opt/homebrew/bin/blender --background --python models/atrium-fountain/inspect_sources.py
node models/atrium-fountain/validate.mjs --source-edit
```

Use `--render-only --views=hero,front,side,3q` to select previews. Metres;
native Blender +Z up/front -Y; exported glTF +Y up/front +Z. The asset root is
`ASSET_AtriumFountain`, at floor centre, with identity position and scale.
Radial geometry has no preferred visible front.

`WATER_Jets` is one independently addressable mesh with eight disconnected tubes.
`WATER_Surface` is the separate 6 mm main-basin water disc. `WATER_BowlPools`
contains the two small pool discs. Water nodes use floor-centre origins and the
same shared translucent material. The consumer must clone a material for
independent shader animation. No animation clips are included; deform water
vertices or animate/replace the material in the mall runtime. Rigid translation
of the full jets may detach their ends from nozzles/bowls.

Existing `mosque-courtyard-fountain` is smaller and has no eight arcing jets;
`aquarium-tank` is a different water-feature function. Neither is an exact match.
Search evidence is in `reports/existing-model-search.json`.

Measured export data and Khronos results: `reports/assets.json` and
`reports/khronos.json`. Repository/browser checks: `reports/checks.json` and
`reports/chromium.json`. Preview PNGs are reviewed visually before local delivery.
The initial gate failure is preserved in `reports/gate-initial.log`: the first
jet trajectory ended against the bowl wall; the final trajectory reaches water.

Status remains draft / needs owner review. Physical devices, WebKit, actual
mall animation, combined 17-shop performance and installation safety are not
verified. Browser draw calls describe this model viewer only. No publication
or push is part of this delivery. Rights are in `LICENSE.md`.
