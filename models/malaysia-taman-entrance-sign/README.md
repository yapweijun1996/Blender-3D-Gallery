# Malaysia Taman Entrance Sign

Neighbourhood entrance monument with two pillars, editable signboard, original roof motif, replaceable label bars and decorative base. No real taman name or official branding. Original illustrative asset, not engineering or safety certification.

## Reproduce
From repository root:

- Blender: --background --threads 2 --python-exit-code 1 --python models/malaysia-taman-entrance-sign/generate.py
- Preserve manual source edits: same command with -- --export-source.
- Render exported GLB: use models/malaysia-taman-entrance-sign/render_views.py.
- Structural validation: node scripts/validate325341.mjs 340
- Source edit proof: BATCH_ASSET_ID=340 Blender --background --threads 2 --python-exit-code 1 --python scripts/inspect-batch325341.py; node scripts/test-batch325341-source-edit.mjs

Metres; Blender +Z up/-Y front, GLB +Y up/+Z front. Independent source meshes/materials. Movable nodes use source pivots and verified GLB animation where applicable; Gallery has orbit/zoom/reset but no new component-control UI. Physical Android/iOS NOT TESTED. No deployment. See verification.md and reports.
