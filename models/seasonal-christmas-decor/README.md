# Seasonal Christmas Decor

Original brand-neutral static set for theme switching: a 2.5 m tree including its
faceted star, 27 plain baubles, four wrapped gift boxes and two six-arm hanging
snowflakes. Three shared solid-colour materials: pine, cranberry and champagne.
Existing category: Mall Fixtures. Independent collection; no Singapore Fish entry.

Authoring units are metres, origin at the complete set's floor centre, Blender
+Z up / -Y front, exported glTF +Y up / +Z front. The snowflake cords end at
attachment positions recorded on the editable source groups. Ceiling mounts and
theme-switching application logic belong to the consuming scene. No animation.

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/seasonal-christmas-decor/generate.py
node models/seasonal-christmas-decor/validate.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/seasonal-christmas-decor/inspect_sources.py
node models/seasonal-christmas-decor/verify_source_edit.mjs
npm run validate:assets
npm test
npm run build
```

Requires Blender 5.2.3. No random inputs, downloaded geometry, fonts, images,
textures, brands or text. `generate.py -- --export-source --skip-render` exports
saved source edits without rebuilding. The native source keeps separate geometry;
the GLB batches by functional group and material into eight meshes/primitives.
Measured export values and hashes are in `reports/assets.json`; native source and
controlled edit evidence are in `reports/sources.json`. Studio floor, lights and
camera are excluded from the GLB. Preview renders are presentation derivatives.

The prior `christmas-tree` and `christmas-gift-boxes` cover parts of the subject,
but lack the complete requested set and exceed the three-material budget. This
asset is newly authored procedural geometry, with a distinct ID, under the owner's
explicit instruction. Existing models are unchanged.

Local browser evidence does not verify physical phones, WebKit, or a full mall's
200 draw-call budget. See `reports/acceptance.json` for the verified local scope.

Original asset; owner-project reuse authorized. Public redistribution terms are
unspecified; gallery downloading remains disabled.
