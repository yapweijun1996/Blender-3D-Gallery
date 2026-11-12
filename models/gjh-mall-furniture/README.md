# GJH Mall Furniture

Two original Blender-authored furniture assets for the owner's Webpage-Design-Gallery GJH V11 virtual mall. They are decorative concepts, not official GJH products. No third-party images, fonts, models or procedural script dependencies are used.

| Asset | Dimensions (glTF X/Y/Z, metres) | Triangles | GLB bytes | Materials |
| --- | --- | ---: | ---: | ---: |
| Lounge bench | 2.580 / 1.3175 / 0.922 | 5,640 | 234,288 | 5 |
| Areca-inspired planter | 1.2301 / 2.3476 / 1.1916 | 5,160 | 119,760 | 6 |

`reports/assets.json` records measurements from the actual exported GLBs, including SHA-256, world-space bounds and Khronos validator results. Both exports are self-contained, texture-free glTF 2.0 with opaque/double-sided PBR materials and no animation, compression decoder, cameras or lights. Each uses one named root and one merged mesh with separate material primitives. Editable parts and the preview studio remain in the source `.blend`.

## Author and reproduce

Authoring environment: Blender 5.2.3 LTS, macOS ARM64; deterministic geometry, no random seed. The generator writes only this collection's sources, exports and rendered PNGs. Review any generator before running it. From the repository root:

```sh
blender --background --python models/gjh-mall-furniture/generate.py
blender --background --python models/gjh-mall-furniture/inspect_sources.py
# Optional authoring dependency: Python 3 + Pillow, outside the website runtime.
python models/gjh-mall-furniture/prepare_previews.py
npm ci
node models/gjh-mall-furniture/validate.mjs
npm test
npm run build
node scripts/test-gjh-furniture.mjs
```

Blender renders are converted to lightweight WebP thumbnails; intermediate PNGs are ignored. The website build uses checked-in exports and previews and never executes Blender. Re-rendering may vary slightly across Blender versions or hardware. Compare exported geometry, materials and measured bounds as well as bytes.

Blender uses +Z up; export converts to glTF +Y up. The origin is at floor centre. Bench back is glTF +Z; its front is -Z. V11 rotates the bench by PI for the opposite seating direction. The planter's nominal height is 2.3476 m; V11 applies its existing placement height multipliers. Physics remains owned by the consumer rather than being inferred from decorative leaf or upholstery triangles.

## Reuse and rights

Original asset; reuse in the owner's projects is authorized. Public redistribution terms have not been specified. Gallery download buttons are disabled; public interactive viewing still serves the GLBs. No CC0, MIT artwork license, endorsement or fabrication accuracy is implied.

Use the exact files under `exports/`. A consumer should pin the upstream commit, record export hashes, retain this attribution, load once and instance repeated placements. The mall keeps its procedural furniture as a per-asset fallback when an export cannot load. It does not pull GitHub assets at runtime and does not add model files to the gallery's offline installation pack.

## Verification

See [verification.md](verification.md) for executed checks, screenshots and limits. A PR is a proposed library addition; it does not itself prove a GitHub Pages deployment.

The material/export pipeline follows the [Blender glTF documentation](https://docs.blender.org/manual/en/5.0/addons/import_export/scene_gltf2.html): mesh geometry and Principled metallic/roughness material values are exported directly.
