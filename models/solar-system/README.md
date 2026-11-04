# Solar System Collection

17 independently loadable Blender-created GLBs, source scenes, baked PBR textures and scientific metadata. Created with Blender 5.1.2 through successful Blender MCP calls on 2026-11-04. The collection is integrated with Gallery; the optional `?page=solar` demo loads assets on demand. Production publication was authorized on 2026-11-04. The Pages workflow and live site establish deployment state.

See the [delivery report](reports/REPORT.md) for file paths, measured triangles/bytes/texture memory, reproducibility, validation, screenshots, source attribution, scientific approximations and remaining limits.

- `exports/`: 17 standalone GLBs with embedded images, no cameras, studio lights or fixed comet tail.
- `sources/`: 17 independent `.blend` files with packed images and preview studio.
- `scripts/generate.py`: shared deterministic Blender generator; pass asset IDs after `--`. It refuses existing GLB destinations.
- `reference/`: retained image inputs and exact URL/hash provenance; downloads contain no executable scripts.
- `textures/`: baked albedo, alpha and tangent normal maps.
- `previews/`: Blender PNG/WebP renders and two neutral Three.js views per asset.
- `metadata/`: authoritative physical reference properties, display conventions, measured metrics, attribution and accuracy limits. The catalog loads these at build time.
- `reports/`: individual machine reports, source-reopen results, hash-bound visual review, contact sheets and browser regression evidence.

Source images retain their respective NASA/JPL/USGS/JHUAPL/SwRI/ASU terms and credits. The owner authorized repository and Gallery publication on 2026-11-04; no separate redistribution license has been selected for original geometry. This collection is procedural artwork incorporating source maps, not NASA-reviewed scientific imagery. No scientific measurement should be derived from the display meshes.
