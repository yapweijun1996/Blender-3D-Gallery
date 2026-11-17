# Seasonal CNY Decor

Original brand-neutral seasonal mall decoration: two ribbed red hanging lanterns
with tassels, a one-metre potted tangerine plant with 16 oranges and 81 leaves,
two blank red banners and a small two-tier stand with six plain red envelopes.
Three shared solid colours: festive red, tangerine green and golden orange.
Existing category: Mall Fixtures. Independent collection appended to the catalog.

Metres; origin at the full set's floor centre. Blender +Z up / -Y front becomes
glTF +Y up / +Z front. Editable source groups store suspension anchors in Blender
coordinates. The consuming scene supplies ceiling mounts and theme-switching
logic. This is static decoration with no animation, collision or runtime switch.

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/seasonal-cny-decor/generate.py
node models/seasonal-cny-decor/validate.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/seasonal-cny-decor/inspect_sources.py
node models/seasonal-cny-decor/verify_source_edit.mjs
python3 models/seasonal-cny-decor/verify_rebuild.py
npm run validate:assets
npm test
npm run build
node models/seasonal-cny-decor/check_page.mjs
```

Requires Blender 5.2.3. Generator uses no random inputs, external geometry,
images, textures, fonts, characters, text or brands. Source/export/studio layout
and layered quality gate follow `self-checkout-machine`; delivery copies are
batched by component and material into eight mesh objects and 13 primitives.
The source retains separately editable components. Studio floor, lights and
camera are excluded from GLB. `-- --export-source --skip-render` exports saved
source edits. Triangle index ordering is canonicalized without changing any
triangle or winding, eliminating the Blender exporter's observed ordering drift.

Measured export and source evidence: `reports/assets.json`, `reports/sources.json`.
`reports/acceptance.json` records local gate results and limitations. Initial
reproducibility failure is retained as historical evidence; the final isolated
generator-only check compares the complete exported bytes.

Similar existing assets include `chinese-lantern`,
`chinese-new-year-kumquat-tree`, `chinese-new-year-lantern-arch`,
`chinese-new-year-mandarin-orange-basket` and
`chinese-new-year-red-packet-display`. No existing asset provides this complete
requested decoration group with its blank banners and size/material constraints.
This new original asset follows the owner's explicit override; existing models
are unchanged. No Singapore Fish collection entry.

Preview renders and the 1440x900 Chromium model page are visually inspected.
Desktop headless evidence does not verify physical phones, WebKit, installation
mounts or performance of a complete 17-shop mall under its 200-draw-call budget.
Original asset; reuse in the owner's projects authorized. Public redistribution
terms are unspecified; gallery downloading is disabled.
