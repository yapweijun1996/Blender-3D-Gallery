# Mall Service Desk

Original decorative service counter and sign for the owner's mall asset library. Jade panels, walnut worktops, champagne-brass detailing, an open staff side and a lower guest-counter section. No functional service workflow or accessibility certification is implied.

## Files and reproduction

- Real editable Blender source: sources/mall-service-desk.blend
- Standalone glTF 2.0 export: exports/mall-service-desk.glb
- Rendered preview: previews/mall-service-desk.webp
- Measurements and source checks: reports/assets.json and reports/sources.json

Authored with Blender 4.0.2, Ubuntu ARM64, CPU Cycles. Deterministic geometry, no random seed or external textures/models/fonts; labels use bundled Bfont. From the repository root:

    blender --background --python models/mall-service-desk/generate.py
    blender --background --python models/mall-service-desk/inspect_sources.py
    python3 models/mall-service-desk/prepare_previews.py
    node models/mall-service-desk/validate.mjs
    npm test
    npm run build
    node scripts/test-mall-service-desk.mjs

Preview conversion requires Pillow; validation uses the repository Node dependencies. Website builds use checked-in assets and do not execute Blender. Render pixels may vary across versions/hardware. Measured GLB: 2.880 × 1.870 × 0.961 m (X/Y/Z), 8,024 triangles, 245,748 bytes, five material primitives. Origin is floor centre, Blender +Z/glTF +Y up; front is Blender +Y/glTF -Z.

Edit SERVICE and HOW CAN WE HELP? text in the named FONT source objects or generator. GLB text is mesh geometry, not a runtime editable widget. Studio camera, lighting and ground stay out of the export. After source design changes, use the generator as the reproducible source of truth and regenerate/validate metadata hashes and previews.

## Rights

Original asset; reuse in the owner's projects is authorized. Public redistribution terms have not been specified. Gallery downloads remain disabled; interactive viewing still serves GLB bytes. No CC0/MIT artwork license, mall endorsement or fabrication suitability is implied.

See verification.md for executed checks and limits. This separate local branch is based on main 4c9f57ed and does not modify or depend on the pending mall-essentials branch.
