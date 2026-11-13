# Street Utility Pole

V2.1 backlog 399. Tapered utility pole with independent crossarm, three ceramic insulators and service box; no energized wiring or certified electrical layout.

## Files and conventions

- Editable source: `sources/street-utility-pole.blend`.
- Optimized export: `exports/street-utility-pole.glb`.
- Hero, front and rear renders: `previews/`.
- Metadata: `metadata/street-utility-pole.json`.
- Verification and limits: [verification.md](verification.md).

Created with Blender 4.0.2 using procedural Python. Units are metres, Blender +Z / glTF +Y up, and Blender -Y / glTF +Z front. Components and materials remain independently editable.

## Reproduction

Run from the repository root using the project's Blender environment:

```sh
blender --background --python models/street-utility-pole/generate.py
blender --background --python models/street-utility-pole/generate.py -- --export-source
blender --background --python models/street-utility-pole/render_views.py
python3 models/street-utility-pole/prepare_previews.py
node models/street-utility-pole/validate.mjs
blender --background --python models/street-utility-pole/inspect_source.py
node models/street-utility-pole/verify_source_edit.mjs
```

The first command regenerates source and export. Use `--export-source` to export the existing source while preserving manual source edits. Inspection and validation commands write evidence; use a copied fixture when preserving historical reports.

Original illustrative visual asset, not an official brand or a traffic, structural, accessibility or electrical certification. No runtime machinery or animation is implemented. Physical Android/iOS are not tested. Public redistribution terms have not been specified.
