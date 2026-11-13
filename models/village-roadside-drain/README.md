# Village Roadside Drain

Two-metre rural trapezoidal drainage channel with separate stone edging. Distinct from the urban precast U-shaped drain asset. Original illustrative asset, not engineering or safety certification.

## Reproduce
From repository root:

- Blender: --background --threads 2 --python-exit-code 1 --python models/village-roadside-drain/generate.py
- Preserve manual source edits: same command with -- --export-source.
- Render exported GLB: use models/village-roadside-drain/render_views.py.
- Structural validation: node scripts/validate325341.mjs 336
- Source edit proof: BATCH_ASSET_ID=336 Blender --background --threads 2 --python-exit-code 1 --python scripts/inspect-batch325341.py; node scripts/test-batch325341-source-edit.mjs

Metres; Blender +Z up/-Y front, GLB +Y up/+Z front. Independent source meshes/materials. Movable nodes use source pivots and verified GLB animation where applicable; Gallery has orbit/zoom/reset but no new component-control UI. Physical Android/iOS NOT TESTED. No deployment. See verification.md and reports.
