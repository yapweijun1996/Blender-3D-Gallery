# Proton Saga (1985) — reference-led panel reconstruction

This draft rebuilds the first-generation sedan against the two reference images supplied in this conversation. The mesh has separate front wings, front and rear doors, and rear-quarter panels on both sides, with fitted shut lines, folded edges, wheel arches and wheelhouse liners. The roof, glazing, bumpers, grille, lamps, wheels and basic cabin remain editable Blender objects.

## Materials and provenance

The two images in `textures/` are the user-provided reference images. Their pixels are used in the front lamps, indicators, rear-lamp faces and steel wheel surfaces; the original images are packed into the Blender source and compressed full-image copies are embedded in the GLB. This is a real 3D model with image-based surface textures. **Rights to redistribute those reference images publicly have not been verified; verify them before any public release.** No third-party mesh is included.

The Blender presentation uses the bundled Studio environment image. Blender's `datafiles/studiolights/world/license.txt` identifies its bundled HDRIs as CC0, created by Greg Zaal / Poly Haven. It is packed in `scene.blend` for the render and is not part of the GLB. The browser viewer has its own lighting and therefore looks different from the Blender renders.

The source images are visual guides, not a measured factory blueprint. Panel contours, window reflections, tire construction, cabin detail and materials remain approximations; no 100% or factory-dimensional match is claimed. The original-size source reference, especially the small rear and side views, limits recoverable detail.

## Files and regeneration

- `scene.blend`: editable Blender source with packed lighting and reference images.
- `exports/proton-saga-1985.glb`: self-contained export for a 3D viewer.
- `preview.webp`, `view-front.webp`, `view-rear.webp`, `view-left.webp`, `view-right.webp`: renders of the same vehicle.
- `review.html`: local, side-by-side reference and render comparison.
- `metadata.json` and `reports/`: asset metadata and validation evidence.

Requires Blender 5.1.2, `cwebp` at `/opt/homebrew/bin/cwebp`, and Blender's bundled `studio.exr` at the path used by `generate.py`. From this directory:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python generate.py
```

A normal run generates all five 1536 × 1024 renders with 48 Cycles samples and denoising, a fresh GLB and the editable source. `-- --quick --views preview,view-front` is a low-resolution, partial authoring render; run the normal command before replacing a complete set. Geometry metrics and validation reports must be refreshed after regeneration.

`ASSET_Proton_Saga_1985` is the GLB root. Blender -X is the vehicle front, -Y is left and +Z is up. The gallery metadata keeps the existing preview rotation. Opaque export copies are batched by material while source panels remain separate.

## Verification boundary

See `reports/rebuild-verification.json`, `reports/source-validation.json` and `reports/gltf-validation.json`. The local gallery has four vehicle-view controls. Desktop, tablet and emulated mobile initial-open checks covered rendering, controls and closing; a 320 px check and a separate navigation/reload run encountered an intermittent Chromium/Playwright `net::ERR_ABORTED` event while the model still rendered. The network-event cause and complete reload verification remain unresolved. No physical phone was tested.

Source mesh inspection, validator results and browser view testing establish only the specific technical checks recorded there; they do not certify likeness or release readiness. The GLB contains the user-supplied image data. The earlier `docs/proton-saga-1985-rebuild.md` describes the previous reconstruction; this file and these reports describe the present revision.
