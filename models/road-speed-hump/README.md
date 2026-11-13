# Road Speed Hump

V2.1 backlog 396. Modular low rounded rubber speed-hump assembly with alternating independently editable segments and inset anchor heads.

## Files and conventions

- Editable source: `sources/road-speed-hump.blend`.
- Optimized export: `exports/road-speed-hump.glb`.
- Hero, front and rear renders: `previews/`.
- Metadata: `metadata/road-speed-hump.json`.
- Verification and limits: [verification.md](verification.md).

Created with Blender 4.0.2 using procedural Python. Units are metres, Blender +Z / glTF +Y up, and Blender -Y / glTF +Z front. Components and materials remain independently editable.

## Reproduction

Run from the repository root using the project's Blender environment:

```sh
blender --background --python models/road-speed-hump/generate.py
blender --background --python models/road-speed-hump/generate.py -- --export-source
blender --background --python models/road-speed-hump/render_views.py
python3 models/road-speed-hump/prepare_previews.py
node models/road-speed-hump/validate.mjs
blender --background --python models/road-speed-hump/inspect_source.py
node models/road-speed-hump/verify_source_edit.mjs
```

The first command regenerates source and export. Use `--export-source` to export the existing source while preserving manual source edits. Inspection and validation commands write evidence; use a copied fixture when preserving historical reports.

Original illustrative visual asset, not an official brand or a traffic, structural, accessibility or electrical certification. No runtime machinery or animation is implemented. Physical Android/iOS are not tested. Public redistribution terms have not been specified.
