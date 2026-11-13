# Road Kerb Module

V2.1 backlog 397. One-metre precast-style kerb with a chamfered upper traffic face, separate mortar bed and end connection datums.

## Files and conventions

- Editable source: `sources/road-kerb-module.blend`.
- Optimized export: `exports/road-kerb-module.glb`.
- Hero, front and rear renders: `previews/`.
- Metadata: `metadata/road-kerb-module.json`.
- Verification and limits: [verification.md](verification.md).

Created with Blender 4.0.2 using procedural Python. Units are metres, Blender +Z / glTF +Y up, and Blender -Y / glTF +Z front. Components and materials remain independently editable.

## Reproduction

Run from the repository root using the project's Blender environment:

```sh
blender --background --python models/road-kerb-module/generate.py
blender --background --python models/road-kerb-module/generate.py -- --export-source
blender --background --python models/road-kerb-module/render_views.py
python3 models/road-kerb-module/prepare_previews.py
node models/road-kerb-module/validate.mjs
blender --background --python models/road-kerb-module/inspect_source.py
node models/road-kerb-module/verify_source_edit.mjs
```

The first command regenerates source and export. Use `--export-source` to export the existing source while preserving manual source edits. Inspection and validation commands write evidence; use a copied fixture when preserving historical reports.

Original illustrative visual asset, not an official brand or a traffic, structural, accessibility or electrical certification. No runtime machinery or animation is implemented. Physical Android/iOS are not tested. Public redistribution terms have not been specified.
