# Medicine and Health Box Display

Original static S05/S12 P2 retail fixture: five tiers, twenty plain folded cartons and six opaque supplement bottles. Blank header and price rails; solid coloured bands only. No text, logos, medical crosses, external assets or real product packaging.

Metres; origin at the floor centre of the plinth. Blender +Z up and -Y front; glTF +Y up and +Z front. Editable named source parts are batched into three opaque meshes with three shared vertex-colour materials for delivery. No textures, animation, decoder dependency or application code changes.

From this folder:

```sh
/opt/homebrew/bin/blender --background --python generate.py
node encode_preview.mjs
/opt/homebrew/bin/blender --background --python generate.py -- --export-source --skip-render
/opt/homebrew/bin/blender --background --python inspect_sources.py
node validate.mjs --update-metadata
```

The first command rebuilds the source deterministically; `--export-source` preserves saved source edits. `--skip-render` skips the four PNG renders. The source inspector reopens the source, checks closed parts and product contacts/clearances, and saves a disposable edit in the system temporary directory. The Node gate independently loads and validates both GLBs and confirms the controlled edit.

Repository gates: `npm run validate:assets`, `npm test`, `npm run build`; then `node models/medicine-health-box-set/verify_page.mjs` from the repository root. Measured geometry, source proof, reproducibility, visual review and headless Chromium evidence are in `reports/`. Metadata carries actual measurements, with budgets separately identified as limits.

Static visual asset only. No stocking/purchase interaction, physical load certification, assembled 17-shop mall performance, WebKit or physical mobile testing. Local review does not establish publication; public redistribution terms remain unspecified.
