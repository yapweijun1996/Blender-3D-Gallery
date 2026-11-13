# MRT Station Entrance

Generic above-ground MRT station approach module with elevated landing, six approach steps, canopy, side balustrades and replaceable station label. Not a replica of a specific station or an accessibility-certified design. Original illustrative asset, not engineering or safety certification.

## Reproduce
From repository root:

- Blender: --background --threads 2 --python-exit-code 1 --python models/mrt-station-entrance/generate.py
- Preserve manual source edits: same command with -- --export-source.
- Render exported GLB: use models/mrt-station-entrance/render_views.py.
- Structural validation: node scripts/validate325341.mjs 341
- Source edit proof: BATCH_ASSET_ID=341 Blender --background --threads 2 --python-exit-code 1 --python scripts/inspect-batch325341.py; node scripts/test-batch325341-source-edit.mjs

Metres; Blender +Z up/-Y front, GLB +Y up/+Z front. Independent source meshes/materials. Movable nodes use source pivots and verified GLB animation where applicable; Gallery has orbit/zoom/reset but no new component-control UI. Physical Android/iOS NOT TESTED. No deployment. See verification.md and reports.
