# Instant Noodle Pack Display

Original static S06 / P2 floor-standing hanging-bag fixture. Four rows of five
solid-colour pillow bags hang by real holes in their top heat seals. Open rear
frame, continuous upturned hooks, blank header and four blank price rails.
No logos, printed text, third-party models, textures or external inputs.

Metres; floor-centred origin; Blender +Z up / -Y front; glTF +Y up / +Z front.
The measured envelope and statistics are in `metadata/instant-noodle-pack-display.json`
and `reports/assets.json`. The editable source retains individually named packs,
seals, hooks and frame parts; the GLB batches these into three material meshes.
Vertex colours share the three opaque materials across every bag and frame part.
The studio floor, lights and camera are excluded from the export.

From this folder, rebuild with:

```sh
/opt/homebrew/bin/blender --background --python generate.py
```

Export saved source edits without rebuilding geometry:

```sh
/opt/homebrew/bin/blender --background --python generate.py -- --export-source --skip-render
```

The procedural rebuild replaces source edits. Export-only preserves them.
Inspect source and a disposable edit, then independently measure the edited GLB:

```sh
/opt/homebrew/bin/blender --background --python inspect_sources.py
node verify_source_edit.mjs
node validate.mjs --update-metadata
```

From the repository root, run `npm run validate:assets`, `npm test` and
`npm run build`. Restore the tracked demo beverage-can report after tests.
The local Chromium page check is reproducible with
`node models/instant-noodle-pack-display/check_browser.mjs` after the build.
See `reports/acceptance.json` for results and limitations, and
`reports/duplicate-search.json` for the pre-build inventory reconciliation.

This is a static visual asset. It supplies no purchase behavior, collision model,
film physics or load certification. Physical phones, WebKit and the assembled
17-shop mall draw-call/performance budget are not verified by an individual page.
Owner-project reuse is authorized; public redistribution terms remain unspecified.
