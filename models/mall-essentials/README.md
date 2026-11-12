# Mall Essentials

Four original Blender-created fixtures matching the gallery's jade, champagne-brass and walnut mall furniture. Each has an independent self-contained GLB, editable Blender source and rendered WebP preview.

| Fixture | glTF dimensions X/Y/Z (metres) | Triangles | GLB bytes |
| --- | --- | ---: | ---: |
| Directory kiosk | 0.960 / 2.050 / 0.680 | 5,360 | 178,068 |
| Advertising lightbox | 1.160 / 2.310 / 0.580 | 7,168 | 235,832 |
| Trash bin | 0.620 / 0.960 / 0.646 | 8,088 | 338,232 |
| Display shelf | 1.520 / 1.960 / 0.580 | 5,712 | 172,420 |

Measurements and SHA-256 hashes come from actual exported geometry in [reports/assets.json](reports/assets.json). All four total 924,552 bytes and 26,328 triangles. Each export has 5–6 material primitives, no external textures, cameras, lights, animation, or compression-decoder dependency.

- **Directory kiosk:** illustrative shop blocks, route and location marker, portrait housing, touch-category shapes and rear service cover. The map is fictional and the screen is decorative, not functional software.
- **Advertising lightbox:** a softly emissive poster panel with original geometric campaign artwork and editable labels. Rear panel and fasteners are modeled. Geometry represents a lightbox, not a physical lighting specification.
- **Trash bin:** real open annular aperture, recessed liner and base, walnut slats and separate front badge. It is a decorative concept, not a waste-system or manufacturing specification.
- **Display shelf:** four empty usable shelves, slim supports, brass nosings, diagonal rear braces and a labeled header.

## Reproduce

Authored with Blender **4.0.2**, official Ubuntu 24.04 ARM64 packages, CPU Cycles. The deterministic Python generator uses Blender and its bundled Bfont only. Font outlines become mesh in GLB; labels and component objects remain editable in the source. There are no externally downloaded models, images or fonts.

From the repository root:

```sh
blender --background --threads 4 --python-exit-code 1 --python models/mall-essentials/generate.py
blender --background --python-exit-code 1 --python models/mall-essentials/inspect_sources.py
# Authoring-only Python dependency: Pillow; Blender's exporter also needs NumPy.
python3 models/mall-essentials/prepare_previews.py
npm ci
node models/mall-essentials/validate.mjs
npm test
npm run build
node scripts/test-mall-essentials.mjs
npm run test:library
```

Blender packages normally include/configure their Python dependencies. If using locally extracted Ubuntu packages, set BLENDER_SYSTEM_SCRIPTS and BLENDER_SYSTEM_DATAFILES to their extracted directories, provide NumPy on PYTHONPATH, and launch with --python-use-system-env. No custom toolchain is committed or needed by the website. Rendering may vary by Blender version and hardware. The website consumes checked-in assets; it never executes Blender.

The generator writes only this collection's sources, exports and preview PNGs. Review it before executing it. The preview script converts renders to lightweight WebP. Intermediate PNGs and raw browser captures are ignored. A regeneration changes measured exports; rerun validation and update metadata metrics before committing.

## Coordinates and use

Blender +Z becomes glTF +Y. The origin is at floor centre, with metres as the scene unit. The labeled front is Blender +Y / glTF -Z. Gallery previewRotationY is PI to face the viewer. Each GLB uses a named asset root and one merged evaluated mesh with separate material primitives; the source preserves authored parts and a source-only lighting studio. The bin's front badge makes its depth slightly greater than its body diameter.

These are decorative concepts, not official branded mall products, engineering drawings or accessibility-certified fixtures. No collision, interactive wayfinding or physical-lighting behavior is implied.

## Rights and attribution

Original asset; reuse in the owner's projects is authorized. Public redistribution terms have not been specified. Gallery download controls remain disabled, consistently with the existing original mall furniture. Public interactive viewing serves the GLBs; hiding download controls is not access control or a license grant. No new public artwork license is asserted.

Keep the generator, metadata and attribution with project reuse. Consumers should pin an exact commit and record the hashes. No files were added to other repositories or existing offline installation packs.

See [verification.md](verification.md) for tested behavior and limitations. This is a proposed gallery addition, not a deployment.
