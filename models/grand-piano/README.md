# Grand Piano with Bench

Original, brand-neutral static baby grand for the S15 showroom podium (P1), in the existing Equipment category. The existing electronic-keyboard is a different 61-key digital instrument on an X-frame; discovery found no grand-piano duplicate. No external assets, fonts, textures, logos or lettering.

The curved black-lacquer case has 88 keys, A0-C8 inclusive (52 notched white keys and 36 raised black keys), a lid held open on a fixed prop, an open music desk, a three-pedal lyre, three tapered legs with casters, and a matching four-legged bench. The brass harp and string courses are illustrative simplified geometry. There is no sound, key actuation, lid animation or gameplay behavior.

Measured GLB: 15,180 triangles, 523,560 bytes, three meshes/primitives and three shared materials. No textures or animations. Coordinates below are glTF XYZ: width, height, depth, in metres.

- Piano: 1.500 × 1.811860 × 1.750, including the raised lid. Case top: 0.993 m; the approximately 1 m brief describes the case, not the raised lid.
- Complete piano and bench: 1.500 × 1.811860 × 2.345. Bench: 0.660 × 0.550 × 0.360.
- Origin: floor centre of the complete footprint. glTF +Y up / +Z front; Blender +Z up / -Y front. The piano footprint is offset behind the origin to accommodate the bench.

The `.blend` retains 232 independently editable meshes. Export merges evaluated temporary copies by material and leaves saved authoring parts intact. A clean independent rebuild produced byte-identical GLB output in Blender 5.2.3 LTS. Preview PNGs are hero/front/side/3q; hero.webp is the card derivative. Studio objects are excluded from GLB export.

Run from the repository root:

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/grand-piano/generate.py
node models/grand-piano/validate.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/grand-piano/inspect_sources.py
node models/grand-piano/verify_source_edit.mjs
npm run validate:assets
npm test
npm run build
node models/grand-piano/check_browser.mjs
```

Append `-- --skip-render` for a fresh rebuild without previews, `-- --export-source --skip-render` to export saved manual edits, or `-- --export-source --previews-only` to render saved geometry. Source-edit inspection writes disposable copies in the system temporary directory. Restore `models/demo-beverage-can/reports/structure-motion.json` after npm test before committing; stage only this asset folder and models/catalog.json.

See reports/assets.json for measured envelopes and GLB SHA-256, khronos.json for format validation, sources.json for closed manifold source and saved-edit verification, reproducibility.json for the independent rebuild, browser.json for the real Chromium load/draw checks, and checks.json for executed gates and limitations. Component membership is checked against actual merged GLB positions. Source manifold checks do not establish all pairwise intersection clearances.

Overall status remains draft / NEEDS REVIEW. Human art approval, physical mobile devices, WebKit, complete S15 placement and target-hardware performance are unverified. Owner-project reuse is authorized; public redistribution terms remain unspecified. No gallery UI, existing model, workflow or deployment changes are included.
