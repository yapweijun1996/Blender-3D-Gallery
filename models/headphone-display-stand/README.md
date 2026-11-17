# Headphone Display Stand

Original brand-neutral S13 / P2 floor fixture. Six generic over-ear headphones
(two black, two white, two grey), six curved J hooks, padded saddles, blank header,
lower shelf and a small blank price card. All geometry and materials are procedural;
there are no external assets, textures, fonts, logos or product packaging.

Metres. Origin is the floor centre. Blender +Z up / -Y front converts to glTF +Y up /
+Z front. The measured envelope is 0.600 m wide × 0.400 m deep × 1.400 m high.
The editable source has separate fixture parts and six `HEADPHONE_01` through
`HEADPHONE_06` groups. Export evaluates the saved source and merges by material:
three opaque meshes / primitives, three shared materials, 18,084 triangles and
431,772 GLB bytes. No animation or audio behavior is implied.

Run from the repository root with Blender 5.2.3:

```sh
/opt/homebrew/bin/blender --background --threads 4 --python-exit-code 1 --python models/headphone-display-stand/generate.py
node models/headphone-display-stand/validate.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/headphone-display-stand/inspect_sources.py
node models/headphone-display-stand/verify_source_edit.mjs
npm run validate:assets
npm test
npm run build
node models/headphone-display-stand/check_browser.mjs
git checkout -- models/demo-beverage-can/reports/structure-motion.json
```

Add `-- --skip-render` for a geometry-only rebuild. To export manual saved source
edits without regenerating geometry, use `-- --export-source --skip-render`.
The editability check uses a separate copy in `/tmp/headphone-display-stand-source-edit`;
`HEADPHONE_EDIT_DIR` overrides this location. The browser check uses the built site
and saves the 1440×900 page screenshot to `~/Documents/MallQueue/reports/`.

`reports/assets.json` and `metadata/headphone-display-stand.json` contain measured
GLB values; `reports/sources.json` records the native-source inspection and saved
edit test. `reports/acceptance.json` records the executed repository and browser
checks; `reports/browser.json` identifies the loaded GLB and page screenshot.
Four PNG/WebP previews are in `previews/`. Rebuild reproducibility is
scoped to the recorded Blender/exporter version. Source `.blend` byte identity is
not promised across saves.

Existing category: Equipment. This asset has its own collection appended to the
catalog. Local review status is draft. Full mall assembly performance, physical
Android/iOS and WebKit remain unverified. Owner-project reuse is authorized;
public redistribution terms are unspecified.
