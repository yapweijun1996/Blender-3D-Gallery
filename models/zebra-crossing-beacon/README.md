# Zebra Crossing Beacon

V2.1 backlog 395. Illustrative striped crossing-beacon pole with independent amber globe, collar and service hatch; static and not a regulatory device.

## Files and conventions

- Editable source: `sources/zebra-crossing-beacon.blend`.
- Optimized export: `exports/zebra-crossing-beacon.glb`.
- Hero, front and rear renders: `previews/`.
- Metadata: `metadata/zebra-crossing-beacon.json`.
- Verification and limits: [verification.md](verification.md).

Created with Blender 4.0.2 using procedural Python. Units are metres, Blender +Z / glTF +Y up, and Blender -Y / glTF +Z front. Components and materials remain independently editable.

## Reproduction

Run from the repository root using the project's Blender environment:

```sh
blender --background --python models/zebra-crossing-beacon/generate.py
blender --background --python models/zebra-crossing-beacon/generate.py -- --export-source
blender --background --python models/zebra-crossing-beacon/render_views.py
python3 models/zebra-crossing-beacon/prepare_previews.py
node models/zebra-crossing-beacon/validate.mjs
blender --background --python models/zebra-crossing-beacon/inspect_source.py
node models/zebra-crossing-beacon/verify_source_edit.mjs
```

The first command regenerates source and export. Use `--export-source` to export the existing source while preserving manual source edits. Inspection and validation commands write evidence; use a copied fixture when preserving historical reports.

Original illustrative visual asset, not an official brand or a traffic, structural, accessibility or electrical certification. No runtime machinery or animation is implemented. Physical Android/iOS are not tested. Public redistribution terms have not been specified.
