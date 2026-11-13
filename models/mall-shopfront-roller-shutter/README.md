# Mall Shopfront Roller Shutter

Selected backlog V2.1 P0 item 425. **One logical asset, batch item 6/10.** Original generic metal roller shutter for Singapore/Malaysia mall scenes, distinct from the glazed shopfront door (424).

## Scale and independent parts

- Overall 3.296 m wide × 3.338 m high × 0.690 m deep.
- Slat curtain: 3.0 m wide, 28 separate 96 mm-high slats on 100 mm pitch.
- Clear opening between guide lips: 2.92 m; fully open floor clearance: 2.60 m.
- Blender metres, +Z up; GLB metres, +Y up. Origin is floor midpoint.
- 44 individually editable closed mesh objects and four material groups.
- FRAME_Fixed: six U-guide pieces and five separate removable hood sheets.
- CURTAIN_EditableSlats: SLAT_01 through SLAT_28, BOTTOM_Rail and BOTTOM_Seal.
- ROLLER_Assembly: independent drum and two axle stubs.

Use generate.py pose(lift) with lift from 0 to 2.6 metres in Blender. It raises the bottom rail/seal and positions each slat on a geometric inward spiral around the stationary circular core. Imported GLB objects explicitly switch to XYZ rotation mode before posing. Slat spacing, guide clearance and drum clearance are checked at 53 sampled lifts. This is an editable visual pose helper, **not a physical linkage, motor controller or safety model**.

The normal gallery GLB is closed and static. Gallery orbit/zoom/reset is supported; runtime click-to-open controls and animation clips are **not included**. Closed, part-open and open previews use real exported meshes in the stated poses. mechanism-cutaway hides only hood sheets to show the winding path; it is explicitly a diagnostic cutaway, not the normal full asset.

## Materials and scope

Galvanized silver slats, charcoal powder-coated guides/hood, steel drum/bottom rail and dark rubber floor seal are separate editable Principled materials. No textures, fonts, outside artwork, exported cameras/lights or decoder dependency.

This is a generic visual concept, not a complete installed shutter or a security, fire, structural, accessibility, mechanical or building-code specification.

## Reproduce

Blender 4.0.2, Node 22, Python/Pillow and locked repository dependencies:

    blender --background --threads 2 --python-exit-code 1 --python models/mall-shopfront-roller-shutter/generate.py -- --skip-render
    blender --background --threads 2 --python-exit-code 1 --python models/mall-shopfront-roller-shutter/render_views.py
    python3 models/mall-shopfront-roller-shutter/prepare_previews.py
    blender --background --threads 2 --python-exit-code 1 --python models/mall-shopfront-roller-shutter/inspect_sources.py
    node models/mall-shopfront-roller-shutter/validate.mjs
    npm test
    npm run build
    node scripts/test-mall-shopfront-roller-shutter.mjs
    npm run test:library

Normal generation replaces the source, so back up manual edits first. Use --export-source --skip-render to export the saved .blend without rebuilding geometry. Export collapses only exactly equivalent material definitions; nodes and geometry remain separate.

For the source-edit proof, give inspect_sources.py a fresh isolated absolute output directory after --. It reopens the shipped source, raises the bottom rail's top vertices 2 mm, changes slat roughness from 0.38 to 0.5 and saves a separate .blend. Run that copy's generate.py with --export-source --skip-render, then run this asset's verify_source_edit.mjs with the isolated directory. The shipped source is not changed.

## Quality and rights

See [verification](verification.md). Local visual review PASS. **Physical Android/iOS NOT TESTED**; desktop viewport emulation is not native mobile verification.

Original geometry/materials authored for Blender-3D-Gallery. Reuse in the owner's projects is authorized. Public redistribution terms have not been specified; download remains disabled. No push, PR, merge, deployment or release is asserted.
