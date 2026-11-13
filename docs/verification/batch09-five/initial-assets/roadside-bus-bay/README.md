# Roadside Bus Bay

Backlog 400. Original modular visual asset for Singapore/Malaysia-inspired scenes, not an official installation or construction standard.

## Reproduction
From the repository root with Blender 4.0.2:
- Generate: `blender -b --python models/roadside-bus-bay/generate.py`
- Export manual source edits: append `-- --export-source` to the command above.
- Render actual exported GLB: `blender -b --python models/roadside-bus-bay/render_views.py`
- Validate: `node models/roadside-bus-bay/validate.mjs`
- Source-edit proof: run `inspect_source.py` in Blender, then `node models/roadside-bus-bay/verify_source_edit.mjs`.

Blender +Z/glTF +Y up; Blender -Y/glTF +Z front; metre units and ground-plane origin. Meshes/materials remain separately editable. Use copied fixtures for validators because they write evidence.

Source: `sources/roadside-bus-bay.blend`; GLB: `exports/optimized.glb`; hero/front/rear/side previews: `previews/`; metadata: `metadata/roadside-bus-bay.json`.

Budget: less than 307,200 GLB bytes and 8,000 triangles. Owner-project reuse authorized; public redistribution terms unspecified. No third-party models, textures, logos or fonts. No runtime gate operation, traffic logic, physics, electrical or construction certification is implemented. Physical Android/iOS and Safari/WebKit are NOT TESTED.

Current production status: generation and validation pending.
