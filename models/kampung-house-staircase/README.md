# Kampung House Staircase

Six-tread open-riser timber staircase with sloping stringers, two handrails and rear supports for modular kampung-house assembly. Original illustrative asset, not engineering or safety certification.

## Reproduce
From repository root:

- Blender: --background --threads 2 --python-exit-code 1 --python models/kampung-house-staircase/generate.py
- Preserve manual source edits: same command with -- --export-source.
- Render exported GLB: use models/kampung-house-staircase/render_views.py.
- Structural validation: node scripts/validate325341.mjs 331
- Source edit proof: BATCH_ASSET_ID=331 Blender --background --threads 2 --python-exit-code 1 --python scripts/inspect-batch325341.py; node scripts/test-batch325341-source-edit.mjs

Metres; Blender +Z up/-Y front, GLB +Y up/+Z front. Independent source meshes/materials. Movable nodes use source pivots and verified GLB animation where applicable; Gallery has orbit/zoom/reset but no new component-control UI. Physical Android/iOS NOT TESTED. No deployment. See verification.md and reports.
