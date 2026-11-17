# Atrium Chandelier

Original brand-neutral P2 hanging ornament for the GJH Virtual Mall. Three
concentric, vertically stepped light rings carry 12 + 8 + 4 faceted drops.
Nine slender suspension rods connect the rings to a compact ceiling plate.
The warm-white emissive delivery mesh is named `LIGHT_Ring`.

Measured delivered envelope: **3.0 × 2.0 × 3.0 m** (glTF X/Y/Z), **13,836
triangles**, **481,624 bytes**, **3 mesh primitives**, **3 shared materials**.
No textures, animations, external assets, readable text or brand marks.
The 24 smoke-blue crystal-like pendants are compact opaque reflective gems,
with a short crown, offset girdle and short pavilion tip. Nominal drop lengths are
0.24 / 0.28 / 0.31 m; maximum circumscribed diameters are 0.076 / 0.080 / 0.084 m.
Their darker base color and sharp reflections preserve facet contrast in the
gallery studio without transparency sorting or transmission passes. The inner
wires are longer so the lowest tips retain the Y=0 datum. Three opaque model
draws per ordinary render pass do not establish the assembled mall's 200 draw-call budget.

The root is at the floor centre of the unplaced module, with its lowest pendant
tips at Y=0 and ceiling contact at Y=2. Raise the root to the intended hanging
height. Blender +Z up/front -Y exports to glTF +Y up/front +Z. The ring layout
is radially symmetric. Scene lighting, Bloom, switching and placement belong
to the consuming scene; no electrical or suspension simulation is supplied.

Folder layout, selected-root export and quality gate follow the
`self-checkout-machine` template. Source parts remain individually editable;
the export batches an evaluated copy by material. `--export-source` exports
saved manual changes without rebuilding them. No random inputs are used.

Run from the repository root:

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/atrium-chandelier/generate.py
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/atrium-chandelier/generate.py -- --export-source --skip-render
node models/atrium-chandelier/validate.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/atrium-chandelier/inspect_sources.py
node models/atrium-chandelier/verify_source_edit.mjs
npm run validate:assets
npm test
npm run build
node models/atrium-chandelier/verify_page.mjs
```

The source-edit proof writes its edited copy to the OS temporary directory.
Page verification saves `~/Documents/MallQueue/reports/atrium-chandelier-page.png`.
See `reports/` for measured geometry, Khronos, source-edit, reproducibility,
visual and browser evidence. Advisor round 1 reduced pendant mass and replaced
the white pearl finish with smoke-blue facets; the actual gallery page and
zoomed view were inspected. Catalog metrics are derived from the GLB, so the
existing catalog entry needs no edit. `reports/acceptance.json` records repository checks.

Search of existing catalog IDs, names and tags and all metadata found no exact
match. Related recessed `mall-ceiling-light-module`,
`neighbourhood-pasar-malam-light-string` and `led-strip-sign-module` do not
provide this chandelier's object and features. This asset is appended as its own
collection in the existing **Mall Fixtures** category.

Physical mobile devices, WebKit, complete-mall installation, scene illumination
and full-scene performance remain unverified. Public redistribution terms are
unspecified; reuse in the owner's projects is authorized.
