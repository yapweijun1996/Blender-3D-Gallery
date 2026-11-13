# Mall CCTV Camera · V2.1 P0 436

An original visible ceiling-mounted CCTV camera **visual prop only**, in metres. No video capture, network, tracking, hidden surveillance or operating/deployment instructions. Opaque lens surface, not physical optics.

- 13 independent named mesh modules, source pan/tilt pivots, ceiling-plane anchor at zero.
- Source Blender +Z up, -Y front. GLB +Y up, +Z front.
- 140 mm mount diameter; approximately 149 mm hanging height. Default tilt 20 degrees downward.
- Open sources/mall-cctv-camera.blend in Blender 4.0.2. Select PIVOT_Pan local Z or PIVOT_Tilt local X for visual scene pose editing. Housing, base and lens are separately editable.
- interface.json documents the geometry contract. No runtime articulation UI or animations.
- Seven source renders include front, side, underside, mount, alternate pose and ceiling context. Context slab is not exported.
- Metadata, provenance and LICENSE.md preserve existing rights; downloads disabled.

## Reproduce

Run Blender 4.0.2 with --background --threads 2 --python-exit-code 1.
Run generate.py with -- --skip-render, then render_views.py and Python prepare_previews.py.
Run Blender inspect_sources.py, then node validate.mjs and verify_source_edit.mjs from this folder.
Run node --test tests/mall-cctv-camera.test.mjs from the repository root, npm test, npm run build, node scripts/test-mall-cctv-camera.mjs and npm run test:library.

inspect_sources.py reopens the actual delivered source, checks manifold geometry and source articulation clearance, then makes a genuine isolated lens and source-pose edit in a temporary fixture without overwriting the shipped source. Export a manual source edit using generate.py with -- --export-source --skip-render, without procedural regeneration.

Local preparation only. Final merged-base integration PENDING; physical Android/iOS NOT TESTED. See verification.md.
