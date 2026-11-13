# Village Wooden Fence

Two-metre timber fence section with thirteen pickets, two horizontal rails and end posts. Original illustrative asset, not engineering or safety certification.

## Reproduce
From repository root:

- Blender: --background --threads 2 --python-exit-code 1 --python models/village-wooden-fence/generate.py
- Preserve manual source edits: same command with -- --export-source.
- Render exported GLB: use models/village-wooden-fence/render_views.py.
- Structural validation: node scripts/validate325341.mjs 337
- Source edit proof: BATCH_ASSET_ID=337 Blender --background --threads 2 --python-exit-code 1 --python scripts/inspect-batch325341.py; node scripts/test-batch325341-source-edit.mjs

Metres; Blender +Z up/-Y front, GLB +Y up/+Z front. Independent source meshes/materials. Movable nodes use source pivots and verified GLB animation where applicable; Gallery has orbit/zoom/reset but no new component-control UI. Physical Android/iOS NOT TESTED. No deployment. See verification.md and reports.
