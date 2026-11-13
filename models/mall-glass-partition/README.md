# Mall Glass Partition

Selected V2.1 P0 item 426, batch item 7/10. One logical original asset: a static, full-height glazed partition for Singapore/Malaysia mall scenes. It is not the existing guardrail, a door, or an alternative copy of either kit.

## Dimensions and components

Standalone bay: **1.20 m wide × 2.40 m high × 0.06 m deep**. Post-centre repeat pitch: **1.14 m**. Fifteen individually editable closed mesh components: two square end posts, floor/ceiling tracks, centre mullion, two transoms, four 10 mm glazing panes, four front/back visibility bands. Three named materials use the existing coherent charcoal frame, pale-aqua glass and frosted-band palette. No outside geometry, textures, fonts or artwork.

Blender metres +Z up; GLB metres +Y up. Ground origin at the standalone bay's floor midpoint. Glass is alpha-blended PBR at 0.22 opacity, not physically refractive glass. No clips, motor, articulation, runtime interactions, exported lights or decoder dependency. A generic visual concept, not structural, safety, fire, accessibility, installation or building-code certification.

## Repeat and corner joints

Ground-plane connector empties are at local X ±0.57 m. Align the incoming CONNECTOR_Left with the preceding CONNECTOR_Right, then **remove incoming POST_Left**. The preceding POST_Right is the one shared post. Do not simply overlap complete bays.

- Straight bay roots: (0,0,0), (1.14,0,0), (2.28,0,0), glTF coordinates.
- Three-bay corner: third root (1.71,0,0.57), rotation about Y −90°, after roots (0,0,0) and (1.14,0,0).
- Opposite corner: second root (0.57,0,−0.57), Y +90°, after root (0,0,0).

`layouts.json` records exact transforms and expected bounds. Blender maps glTF positions (x,y,z) to (x,−z,y), with rotationY mapped to rotation Z using the same sign. Square shared posts meet the shortened tracks/panes at their faces. `validate.mjs` loads the actual GLB, builds each arrangement, checks connector alignment, one post per joint, bounds and every mesh pair for unwanted overlap. These are visualization joint conventions, not engineered connectors.

## Reproduce

Blender 4.0.2, Node 22, Python/Pillow, locked project dependencies:

    blender --background --threads 2 --python-exit-code 1 --python models/mall-glass-partition/generate.py -- --skip-render
    blender --background --threads 2 --python-exit-code 1 --python models/mall-glass-partition/render_views.py
    python3 models/mall-glass-partition/prepare_previews.py
    blender --background --threads 2 --python-exit-code 1 --python models/mall-glass-partition/inspect_sources.py
    node models/mall-glass-partition/validate.mjs
    npm test
    npm run build
    node scripts/test-mall-glass-partition.mjs
    node scripts/test-mall-partition-glass.mjs
    npm run test:library

Normal generation replaces source. Back up edits first. `--export-source --skip-render` reopens and exports the saved source without rebuilding. Export only deduplicates exactly equal material definitions; component nodes and geometry remain editable. This is a compact, decoder-free optimized GLB.

For the real source-edit proof, pass a fresh isolated absolute directory after `inspect_sources.py --`. It reopens the shipped source, raises only BAND_Left_Front top vertices 10 mm and changes frame roughness 0.32→0.5, then saves an isolated source copy. Run that copy's generator with `--export-source --skip-render`, then run `verify_source_edit.mjs /isolated/directory`. The shipped source is unchanged.

## Quality and rights

See [verification](verification.md). Physical Android and iOS are **NOT TESTED**; local viewport emulation is not native device approval. The gallery only provides static viewing with orbit/zoom/reset.

Original geometry and materials authored for Blender-3D-Gallery. Reuse in the owner's projects is authorized. Public redistribution terms have not been specified; download stays disabled. No push, PR, merge, deployment or release is asserted.
