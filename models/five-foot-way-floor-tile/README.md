# Five-Foot-Way Floor Tile

V2.1 backlog 398. Modular shophouse five-foot-way tile panel with individually editable terracotta-and-cream diamond inlays and geometric border strips.

## Files and conventions

- Editable source: `sources/five-foot-way-floor-tile.blend`.
- Optimized export: `exports/five-foot-way-floor-tile.glb`.
- Hero, front and rear renders: `previews/`.
- Metadata: `metadata/five-foot-way-floor-tile.json`.
- Verification and limits: [verification.md](verification.md).

Created with Blender 4.0.2 using procedural Python. Units are metres, Blender +Z / glTF +Y up, and Blender -Y / glTF +Z front. Components and materials remain independently editable.

## Reproduction

Run from the repository root using the project's Blender environment:

```sh
blender --background --python models/five-foot-way-floor-tile/generate.py
blender --background --python models/five-foot-way-floor-tile/generate.py -- --export-source
blender --background --python models/five-foot-way-floor-tile/render_views.py
python3 models/five-foot-way-floor-tile/prepare_previews.py
node models/five-foot-way-floor-tile/validate.mjs
blender --background --python models/five-foot-way-floor-tile/inspect_source.py
node models/five-foot-way-floor-tile/verify_source_edit.mjs
```

The first command regenerates source and export. Use `--export-source` to export the existing source while preserving manual source edits. Inspection and validation commands write evidence; use a copied fixture when preserving historical reports.

Original illustrative visual asset, not an official brand or a traffic, structural, accessibility or electrical certification. No runtime machinery or animation is implemented. Physical Android/iOS are not tested. Public redistribution terms have not been specified.
