# Proton Saga (1985) — reference-led panel reconstruction

This draft rebuilds the first-generation sedan against the two reference images supplied in this conversation. The mesh has separate front wings, front and rear doors, and rear-quarter panels on both sides, with fitted shut lines, folded edges, wheel arches and wheelhouse liners. The roof, glazing, bumpers, grille, lamps, wheels and basic cabin remain editable Blender objects.

## Proportion pass

This revision moves the rear axle and its wheel opening forward by 0.05 model units, shortens the rear roof edge by approximately 0.052 units, narrows the roof by 10%, and adjusts the bonnet crown. All adjoining upper cabin meshes receive the same gradual deformation to preserve their joins. The axle change affects both wheel assemblies and wheelhouses. These are model-space changes guided by the supplied images, not verified factory dimensions. `review.html` compares all four current views with the references.

## Lamp and grille pass

The front grille now has three bright-edged horizontal rails and a larger heritage shield. The headlights have separate, shallow clear covers and fine surrounds; the front indicator ribs are lighter. The rear lamps retain red, clear and amber sections with narrower gaps and without the former dark cross-hatching. `view-rear-3q.webp` adds a rear three-quarter inspection render. These features remain artistic approximations using the supplied reference photographs.

## Wheel pass

The four rims now use modeled silver pressed metal with actual ventilation openings and separate gently domed covers. The wheel assemblies retain their previous tire dimensions, axle positions and arch clearances. This is a visual reconstruction; the GLB batches opaque pieces and does not provide independent wheel pivots.

## Materials and provenance

The two images in `textures/` are the user-provided reference images. Their pixels are used in the front lamps, indicators and rear-lamp faces; the original images are packed into the Blender source and compressed full-image copies are embedded in the GLB. This is a real 3D model with image-based surface textures. **Rights to redistribute those reference images publicly have not been verified; verify them before any public release.** No third-party mesh is included.

The Blender presentation uses the bundled Studio environment image. Blender's `datafiles/studiolights/world/license.txt` identifies its bundled HDRIs as CC0, created by Greg Zaal / Poly Haven. It is packed in `scene.blend` for the render and is not part of the GLB. The browser viewer has its own lighting and therefore looks different from the Blender renders.

The source images are visual guides, not a measured factory blueprint. Panel contours, window reflections, tire construction, cabin detail and materials remain approximations; no 100% or factory-dimensional match is claimed. The original-size source reference, especially the small rear and side views, limits recoverable detail.

## Files and regeneration

- `scene.blend`: editable Blender source with packed lighting and reference images.
- `exports/proton-saga-1985.glb`: self-contained export for a 3D viewer.
- `preview.webp`, `view-rear-3q.webp`, `view-front.webp`, `view-rear.webp`, `view-left.webp`, `view-right.webp`: renders of the same vehicle.
- `review.html`: local, side-by-side reference and render comparison.
- `metadata.json` and `reports/`: asset metadata and validation evidence.

Requires Blender 5.1.2, `cwebp` at `/opt/homebrew/bin/cwebp`, and Blender's bundled `studio.exr` at the path used by `generate.py`. From this directory:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python generate.py
```

A normal run generates all six 1536 × 1024 renders with 48 Cycles samples and denoising, a fresh GLB and the editable source. `-- --quick --views preview,view-front` is a low-resolution, partial authoring render; run the normal command before replacing a complete set. Geometry metrics and validation reports must be refreshed after regeneration.

`ASSET_Proton_Saga_1985` is the GLB root. Blender -X is the vehicle front, -Y is left and +Z is up. The gallery metadata keeps the existing preview rotation. Opaque export copies are batched by material while source panels remain separate.

## Verification boundary

See `reports/rebuild-verification.json`, `reports/source-validation.json` and `reports/gltf-validation.json`. The local gallery has four vehicle-view controls. A current Chromium/Playwright mobile run reported `net::ERR_ABORTED` while the model and all four views rendered; a separate Vite preview run completed successfully. The intermittent cause has not been established. Current checks and their scope are listed in the report; no physical phone was tested.

Source mesh inspection, validator results and browser view testing establish only the specific technical checks recorded there; they do not certify likeness or release readiness. The GLB contains the user-supplied image data. The earlier `docs/proton-saga-1985-rebuild.md` describes the previous reconstruction; this file and these reports describe the present revision.
