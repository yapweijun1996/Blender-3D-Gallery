# Mall Shopfront Door

Selected backlog V2.1 P0 item 424. **One logical asset**, batch item 5/10. Original, generic glazed double-door module for Singapore/Malaysia mall scenes. Not a complete shop or roller shutter.

## Dimensions and editability

- Overall width 2.10 m, height 2.40 m, depth 0.183 m including pull handles.
- Fixed frame aperture 1.94 × 2.32 m. Each leaf 0.944 × 2.282 m; 12 mm centre gap and 18 mm floor clearance.
- Both leaves open 90°: measured unobstructed projected width including pull hardware is 1.734 m.
- Blender metres +Z up; GLB metres +Y up. Root origin is the floor midpoint of the fixed frame.
- 33 individually editable closed mesh components and four named materials. Studio objects are excluded from export.

FRAME_Fixed remains stationary. HINGE_Left and HINGE_Right contain the respective leaf rails, glass, visibility bands, pull handles and brackets. Their pivot centres are Blender (-0.95,-0.04,0) and (0.95,-0.04,0), or glTF (-0.95,0,0.04) and (0.95,0,0.04).

To open, rotate the left hinge -90° and right hinge +90° about Blender local Z / glTF local Y. If importing the GLB into Blender, set the hinge's rotation mode to XYZ before assigning Euler angles. Source pivots are already Euler-mode. Coaxial hinge bearing interfaces and attached hardware contacts are intentional; the validation separates leaf assemblies from stationary jamb/header geometry.

The gallery is a **static model viewer**. It has orbit/zoom/reset, not click-to-open door controls. No animation clips, controller, automatic door system, exported lights or decoder dependency are included. Open preview is a real articulated copy of the exported GLB, not an animation-player claim.

Glass is transparent alpha-blended PBR at 0.22 opacity, not physically refractive glass. A checker-target test compares unchanged, opaque and hidden glass states. No textures, fonts or outside artwork are used. This is a generic visual concept, not a fire, accessibility, security, structural, installation or building-code specification.

## Reproduce

Blender 4.0.2, Node 22, Python/Pillow and locked project dependencies:

    blender --background --threads 2 --python-exit-code 1 --python models/mall-shopfront-door/generate.py -- --skip-render
    blender --background --threads 2 --python-exit-code 1 --python models/mall-shopfront-door/render_views.py
    python3 models/mall-shopfront-door/prepare_previews.py
    blender --background --threads 2 --python-exit-code 1 --python models/mall-shopfront-door/inspect_sources.py
    node models/mall-shopfront-door/validate.mjs
    npm test
    npm run build
    node scripts/test-mall-shopfront-door.mjs
    node scripts/test-mall-shopfront-glass.mjs
    npm run test:library

Generation rebuilds the source. Back up manual changes first. Use --export-source --skip-render to export the saved .blend without rebuilding it. Export collapses only exactly equivalent material definitions emitted by Blender, preserving all nodes, mesh data and pivots.

To reproduce the source edit proof, pass a fresh isolated absolute output directory after inspect_sources.py --. It reopens the shipped source, raises only left front handle top vertices 20 mm, changes hardware roughness from 0.3 to 0.55, and saves a separate .blend. Run that copy's generator with --export-source --skip-render, then node models/mall-shopfront-door/verify_source_edit.mjs /isolated/path. Shipped files remain unchanged.

## Quality and rights

See [verification](verification.md) for executed checks and review results. **Physical Android/iOS are NOT TESTED**; emulated desktop viewports are not native device verification.

Original geometry and materials authored for Blender-3D-Gallery. Reuse in the owner's projects is authorized. Public redistribution terms have not been specified; download remains disabled. No push, PR, merge or deployment is asserted.
