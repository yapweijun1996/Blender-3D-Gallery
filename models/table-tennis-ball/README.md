# Table Tennis Ball (40 mm)

Original, brand-neutral table tennis ball (40 mm). Category: Sports (browse: Parks & Recreation). No external assets, fonts, text, logos or product markings. Static visual asset; no physics.

Real scale: ITTF Statutes 2026, Laws of Table Tennis 2.3.1: spherical ball, diameter 40 mm. Fixed nominal size, so no range midpoint applies. Source: [ITTF Statutes 2026, Laws of Table Tennis 2.3.1](https://documents.ittf.sport/sites/default/files/public/2026-02/2026_Statutes_v1_consolidated_clean.pdf). Dimensions refer to the spherical skin; raised threads can extend up to 1.2 mm beyond that nominal diameter. Polygon sampling slightly reduces the extents. The validator allows ±0.10 mm for tennis, ±0.06 mm for table tennis, and ±1.2 mm for balls with raised threads; it additionally checks all skin vertices against nominal radius within 0.06 mm; reports contain actual dimensions.

White matte ABS sphere with a faint equatorial join: smoothly recessed by at most 0.03 mm. A very subtle baked surface normal gives matte plastic texture. No text, stars, logos or stamps.

The `.blend` retains individually editable cover, seam and thread meshes with live `Export triangulation` modifiers. A Cycles-baked 1024×512 tangent-space normal map is preserved at `sources/textures/table-tennis-ball_grain_normal.png` and embedded as JPEG in the GLB. Export joins evaluated copies into one mesh with one primitive per material, leaving source parts editable. The ball is an opaque outer shell; wall thickness, mass, bounce and interior are not modeled. The two molded hemispheres are represented by one continuous sphere with a shallow join. The groove is deliberately subtle.

Units are metres. Blender +Z up / -Y front; GLB +Y up / +Z front (`export_yup=True`). Root `ASSET_TableTennisBall` has units and axis custom properties. Origin is the actual floor contact point under the centre of the exported bounds. Tiny horizontal adjustments balance stitch protrusions about X/Z; source root properties record these adjustments. Studio lights and camera are never exported.

Run from the repository root:

```sh
blender --background --python-exit-code 1 --python models/table-tennis-ball/generate.py
node models/table-tennis-ball/validate.mjs
blender --background --python-exit-code 1 --python models/table-tennis-ball/inspect_sources.py
```

To export saved manual edits, append `-- --export-source --skip-render`. To rebuild without rendering, append `-- --skip-render`. To render saved geometry only, append `-- --export-source --previews-only`. `--previews-only` alone rebuilds the source but skips export. `config.json` contains the deterministic model parameters. No generation-time downloads or external assets are used.

`validate.mjs` writes `reports/khronos.json` and `reports/assets.json`: Khronos 0 errors / 0 warnings, budget limits, root axes/units, floor contact and centring, real dimensions, embedded JPEG normal map, finite attributes and nondegenerate triangles. It loads geometry with three GLTFLoader after removing texture bindings for Node (image decoding is not tested). Connected components verify two cover halves and exact paired-stitch counts for tennis/baseball/softball, six cricket stitch rows with two quarter seams, or the faint table-tennis join. `inspect_sources.py` reopens the source, asserts editable objects/modifiers and normal map, re-imports the GLB and matches triangle counts without changing the saved source.

Preview PNGs are hero, front, side and 3q (Cycles, 32 samples, 900×900); hero WebP uses quality 86. `reports/reproducibility.json` compares two independent factory-reset `--skip-render` builds using per-primitive counts and vertex positions rounded to 10 micrometres, then restores the reviewed outputs. `reports/mcp-session.json` records interactive prototypes, saved-source inspection and MCP errors.

Not verified: browser/WebGL image decoding and gallery integration, WebKit, physical Android/iOS devices, manufacturer cutting patterns, real material tests, mass, rebound, pressure, physical playability or regulatory certification. Visual review remains required. Owner-project reuse is authorized; public redistribution terms are unspecified.

Preview isolation: rendering reopens the saved editable source after export, avoiding temporary-export dependency state.

Host runtime note: this worker has a PulseAudio teardown hang even with audio disabled. Successful headless runs flush logs and exit after synchronous saves, exports, renders and checks; interactive MCP execution does not use that exit path.
