# Mosquito Patch Pack Display

Original S04 P2 counter fixture in the existing **Mall Fixtures** category.
Two stepped tiers, four lanes each, two regular packs per lane: sixteen
100 x 140 mm blank cards plus one 140 x 196 mm hero card. Each card carries
six generic round patches beneath one shallow clear formed window.
No text, logos, external assets, textures, fonts or real product packaging.

Measured exported envelope: 0.500 m width x 0.300 m depth x 0.350 m height.
Origin is at the floor centre of the footprint; place that origin on a counter.
Blender +Z up / -Y front exports to glTF +Y up / +Z front.
The native source retains individual cards, windows, patches, stock steps and
fixture parts; delivery geometry is batched into three shared material meshes.
All numerical export statistics come from `reports/assets.json` and the metadata.

From this directory:

```sh
/opt/homebrew/bin/blender --background --python generate.py
node make_previews.mjs
/opt/homebrew/bin/blender --background --python inspect_sources.py
node validate.mjs --update-metadata
```

`generate.py -- --export-source --skip-render` re-exports the saved source.
`--skip-render` omits preview rendering. Exceptions produce a nonzero exit.
WebP conversion uses the installed Playwright Chromium image codec.
Source inspection reopens the native file and tests a saved edit in a disposable
temporary copy; it preserves the delivery source. The Node gate checks format,
bounds, finite normals/positions, degeneracy, budgets and the independently
loaded edited GLB. `reports/reproducibility.json` records a second build from
only `generate.py` in a separate directory and a matching GLB SHA-256.

From the repository root:

```sh
npm run validate:assets
npm test
git checkout -- models/demo-beverage-can/reports/structure-motion.json
npm run build
node models/mosquito-patch-pack/check_browser.mjs
```

PNG and WebP hero/front/side/3q views were inspected. The clear PET appearance
uses alpha blending without refraction. Packs intentionally overlap in depth;
rear stock and the lowest hero patches are partly hidden. This is a static
illustrative asset with no chemical, medical, efficacy or safety claim.
Browser evidence is limited to headless Chromium at 1440 x 900; physical mobile,
WebKit and performance of the assembled 17-shop mall remain unverified.
`quality_gate.overall` remains `NEEDS REVIEW` for manager acceptance.
