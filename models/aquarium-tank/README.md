# Aquarium Tank

Original, brand-neutral P3 atrium aquarium in the existing **Mall Fixtures** category.
The measured footprint is 2.00 x 0.80 m, overall height 1.423 m, with a 0.80 m
glass tank on a low two-door cabinet. Includes clear lids, a visual light bar,
transparent water, sand/gravel, rocks and aquatic plants. No fish or text.

Source uses metres, +Z up and -Y front; GLB uses +Y up and +Z front. The root
`ASSET_AquariumTank` is at the floor centre. Editable source components are
preserved; the export merges them into three meshes with three shared materials.
Glass and water use alpha blending without a transmission pass. The opaque
palette uses vertex colours. No external models, textures or fonts are used.

`ANCHOR_Fish` is the intended origin for a separately supplied, scaled koi at
glTF `[0, 0.98, 0.05]` m. The reserved swim box is approximately
`[-0.38, 0.80, -0.18]` to `[0.38, 1.18, 0.22]` m. Actual exported opaque triangles
are tested against that box. Fit the entire fish and its motion envelope inside
it; this visual asset is not an animal-care or engineering specification.

Run from the repository root:

```sh
/opt/homebrew/bin/blender --background --python models/aquarium-tank/generate.py
node models/aquarium-tank/prepare_previews.mjs
/opt/homebrew/bin/blender --background --python models/aquarium-tank/inspect_sources.py
node models/aquarium-tank/validate.mjs --source-edit
npm run validate:assets
npm test
npm run build
node models/aquarium-tank/check_browser.mjs
```

Seed: `5283`. Rebuild deterministically from procedural geometry. To preserve
manual source edits, export the saved `.blend` using
`generate.py -- --export-source --skip-render`; rebuilding replaces source edits.
The source inspection exports an unsaved, controlled door edit to `/tmp` and
independently reloads it through the asset gate. Studio geometry and lights are
excluded from GLB exports. `--views=front,side` selects render views.

Measured export: 7,440 triangles, 17,088 vertices, 661,300 bytes; no textures,
animation, fish, refraction, water simulation or exported lights. See
`reports/assets.json`, `reports/khronos.json`, `reports/sources.json`,
`reports/browser.json` and `reports/checks.json` for executed checks and limits.
The overall gate remains **NEEDS REVIEW** for manager review. Physical devices,
WebKit, full-mall performance and a fish-in-tank assembly are not verified.

Duplicate search covered catalog id/name/tags and 633 metadata files. No close
aquarium match was found. Existing `pond` is a 3.2 x 2.2 m low outdoor basin;
`malaysia-outdoor-water-tank` is an opaque utility tank; the courtyard fountain
and separate `fish-koi` serve different roles. No existing asset was changed.
