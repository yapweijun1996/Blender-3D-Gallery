# Malaysia Car Porch Roof

Backlog 323. Original modular visual asset for Singapore/Malaysia-inspired scenes, not an official installation or construction standard.

## Reproduction
From the repository root with Blender 4.0.2:
- Generate: `blender -b --python models/malaysia-car-porch-roof/generate.py`
- Export manual source edits: append `-- --export-source` to the command above.
- Render actual exported GLB: `blender -b --python models/malaysia-car-porch-roof/render_views.py`
- Validate: `node models/malaysia-car-porch-roof/validate.mjs`
- Source-edit proof: run `inspect_source.py` in Blender, then `node models/malaysia-car-porch-roof/verify_source_edit.mjs`.

Blender +Z/glTF +Y up; Blender -Y/glTF +Z front; metre units and ground-plane origin. Meshes/materials remain separately editable. Use copied fixtures for validators because they write evidence.

Source: `sources/malaysia-car-porch-roof.blend`; GLB: `exports/optimized.glb`; hero/front/rear/side previews: `previews/`; metadata: `metadata/malaysia-car-porch-roof.json`.

Budget: less than 409,600 GLB bytes and 10,000 triangles. Owner-project reuse authorized; public redistribution terms unspecified. No third-party models, textures, logos or fonts. No runtime gate operation, traffic logic, physics, electrical or construction certification is implemented. Physical Android/iOS and Safari/WebKit are NOT TESTED.

Current production status: generation and validation pending.
