# Kampung Zinc Roof

Thin solid corrugated zinc roof sheet measuring 2.4 by 1.2 metres, with independent roof fasteners. Original illustrative asset, not engineering or safety certification.

## Reproduce
From repository root:

- Blender: --background --threads 2 --python-exit-code 1 --python models/kampung-zinc-roof/generate.py
- Preserve manual source edits: same command with -- --export-source.
- Render exported GLB: use models/kampung-zinc-roof/render_views.py.
- Structural validation: node scripts/validate325341.mjs 334
- Source edit proof: BATCH_ASSET_ID=334 Blender --background --threads 2 --python-exit-code 1 --python scripts/inspect-batch325341.py; node scripts/test-batch325341-source-edit.mjs

Metres; Blender +Z up/-Y front, GLB +Y up/+Z front. Independent source meshes/materials. Movable nodes use source pivots and verified GLB animation where applicable; Gallery has orbit/zoom/reset but no new component-control UI. Physical Android/iOS NOT TESTED. No deployment. See verification.md and reports.
