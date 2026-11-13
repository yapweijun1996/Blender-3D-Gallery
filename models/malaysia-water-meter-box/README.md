# Malaysia Water Meter Box

Compact water-meter enclosure with a hinged opaque door, latch, circular meter and two internal pipe sections. Door opening reveals the meter. Original illustrative asset, not engineering or safety certification.

## Reproduce
From repository root:

- Blender: --background --threads 2 --python-exit-code 1 --python models/malaysia-water-meter-box/generate.py
- Preserve manual source edits: same command with -- --export-source.
- Render exported GLB: use models/malaysia-water-meter-box/render_views.py.
- Structural validation: node scripts/validate325341.mjs 329
- Source edit proof: BATCH_ASSET_ID=329 Blender --background --threads 2 --python-exit-code 1 --python scripts/inspect-batch325341.py; node scripts/test-batch325341-source-edit.mjs

Metres; Blender +Z up/-Y front, GLB +Y up/+Z front. Independent source meshes/materials. Movable nodes use source pivots and verified GLB animation where applicable; Gallery has orbit/zoom/reset but no new component-control UI. Physical Android/iOS NOT TESTED. No deployment. See verification.md and reports.
