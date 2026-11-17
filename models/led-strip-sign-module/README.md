# LED-Strip Sign Module

Original P2 blank shop sign for the GJH Virtual Mall. Existing fascia modules lack a recessed emissive ring and matching rear wall bracket; this asset has its own identity and collection. See `reports/duplicate-search.json` for the catalog and metadata search.

The measured enclosure is approximately 2.4 x 0.6 x 0.12 m (width, height, depth). Rear mounting cleats add 0.025 m, giving a full 2.4 x 0.6 x 0.145 m envelope. The root is at the bottom footprint centre: metres, glTF +Y up, +Z front (Blender +Z up, -Y front). Raise the root to the shop-sign installation height; the asset includes no wall or floor.

`ASSET_LedStripSignModule` contains four single-material delivery meshes:

- `SIGN_Housing`: graphite enclosure and protective front lip.
- `SIGN_BlankFace`: blank porcelain panel, without lettering or logos.
- `SIGN_LedStrip`: continuous warm-white HDR emissive perimeter, recessed 6 mm below the outer lip. Both glTF node and mesh retain this exact name.
- `SIGN_WallBracket`: separate rear two-rail cleat assembly with four actual mounting slots. It shares the porcelain material with the face. The rear-most plane is measured in metadata as `interface.wall_plane_gltf_z`.

Select `SIGN_LedStrip` for the consuming mall's selective Bloom, or adjust its material's emissive intensity. The GLB supplies emission; Bloom is scene-owned post-processing. No gallery UI or renderer changes are included. Four primitives use three shared materials, with no textures, external resources or animations. This does not measure the complete mall's 200 draw-call budget.

Rebuild with Blender 5.2.3:

```sh
cd models/led-strip-sign-module
/opt/homebrew/bin/blender --background --python generate.py
node validate.mjs --update-metadata
/opt/homebrew/bin/blender --background --python-exit-code 1 --python inspect_sources.py -- --edit-copy
node verify_source_edit.mjs
```

The generator uses no randomness or external assets. It saves the editable native source before batching into four delivery meshes. Previews reimport the actual GLB. To export saved source edits without rebuilding, append `-- --export-source`; add `--skip-render` to omit previews. `inspect_sources.py` edits only a copy under `reports/source-edit/`.

Repository checks from the root are `npm run validate:assets`, `npm test`, and `npm run build`. Exact measured counts, Khronos results, native-source checks and local Chromium evidence are under `reports/`; metadata records tested scope. Full-mall Bloom/integration, physical devices, WebKit, installation certification and publication remain unverified. Public redistribution terms are unspecified; owner-project reuse is authorized.
