# Electronics Store Display Shelf

Original procedural wall-style cabinet for the GJH Virtual Mall, with three glass-front display tiers, six plain device cartons, a supported tablet, a cylindrical speaker, three coiled cables on J hooks and a blank header. No text, logos, external assets or real packaging. Existing category: Mall Fixtures. Static geometry; doors and electronics have no simulated behavior.

Metres; floor-centre origin; Blender +Z up / -Y front exports to glTF +Y up / +Z front. Native parts stay independently editable; the delivery GLB batches by three shared materials. Ceramic vertex colors provide plain muted colors. Glass uses inexpensive alpha blending without transmission, textures or a decoder. The studio floor, camera and lights are excluded from export.

From the repository root:

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/shelf-electronics-display/generate.py
node models/shelf-electronics-display/validate.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/shelf-electronics-display/inspect_sources.py
node models/shelf-electronics-display/verify_source_edit.mjs
npm run validate:assets
npm test
npm run build
```

Append `-- --export-source --skip-render` to the generator command to export saved edits without rebuilding. Append `-- --view front` to render a single view. Measurements and validation evidence are in `metadata/` and `reports/`. The source-edit probe uses a disposable directory outside the repository. The self-checkout-machine supplies the layout and layered gate pattern.

Similar existing assets are listed in `reports/duplicate-search.json`; none shares this ID. Desktop Chromium evidence applies to this individual asset. Full mall performance, physical phones, WebKit, construction suitability and production publication remain unverified.
