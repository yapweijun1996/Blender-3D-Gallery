# GJH interior dressing, round two

One static Blender 5.1 GLB per shop supplements the original tier-specific anchor. Each detail GLB uses slot-local metres at the lot origin. All tiers reuse the same dressing. The physical envelopes, tier selection and model-backed displays are defined in the web project. The model files refer to the adjacent 256 × 256 `showroom-atlas.png`.

Set `GALLERY` to the Blender-3D-Gallery checkout, `STORE_ASSETS` to the web checkout's `demos/corporate/gjh/v11/assets`, and `BLENDER` to Blender 5.1. On headless macOS, use the process-local guard invocation documented in the gallery's `docs/gjh-v11-interiors-build.md`. Blender reads the existing gallery lantern and plate profiles. The original anchor pipeline remains in `scripts/gjh_interiors/build.py` in that repository.

```sh
python3 scripts/gjh_interiors/illustrate.py "$STORE_ASSETS/brands" "$STORE_ASSETS/interiors/showroom-atlas.png"
"$BLENDER" -b -noaudio --factory-startup --disable-autoexec --python-exit-code 1 \
  --python scripts/gjh_interiors/build_rooms.py -- --gallery "$GALLERY" --output "$STORE_ASSETS/interiors"
node scripts/gjh_interiors/package_rooms.mjs --gallery "$GALLERY" --output "$STORE_ASSETS/interiors"
node scripts/gjh_interiors/package_rooms.mjs --check --gallery "$GALLERY" --output "$STORE_ASSETS/interiors"
```

Illustration uses Pillow. Packaging uses the Blender gallery's installed `gltf-validator`. It validates the 42 original GLBs and 17 new GLBs with the real external image, measures every mesh instance, and writes the combined manifest and compact loader index. The manifest binds the print sheet, registered logo source images and gallery derivatives to SHA-256 hashes. Rebuild the web gallery and run its interior tests after packaging.

The Blender delivery in `exports/gjh-v11-interiors-round2` contains only the new room files and their shared sheet. To rebuild it, use that directory as the Blender output, copy in the shared sheet first, and pass `--models-only --brands "$STORE_ASSETS/brands"` to the packager. It reads the 42 reference anchors from the gallery's original export directory. The gallery branch ships the shared sheet so model rebuilding can also start directly from that image.
