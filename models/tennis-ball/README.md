# Tennis Ball

Original, brand-neutral tennis ball. Category: Sports (browse: Parks & Recreation). No external assets, fonts, text, logos or product markings. Static visual asset; no physics.

Real scale: ITF Rules of Tennis 2026, Appendix I, Type 2: diameter 65.4–68.6 mm; midpoint 67.0 mm. Source: [ITF Rules of Tennis 2026, Appendix I, Type 2](https://www.itftennis.com/media/7221/2026-rules-of-tennis-english.pdf). Dimensions refer to the spherical skin; raised threads can extend up to 1.2 mm beyond that nominal diameter. Polygon sampling slightly reduces the extents. The validator allows ±0.10 mm for tennis, ±0.06 mm for table tennis, and ±1.2 mm for balls with raised threads; it additionally checks all skin vertices against nominal radius within 0.06 mm; reports contain actual dimensions.

Two separate optic yellow-green felt halves, bounded by a closed two-lobed S seam. The off-white rubber band is approximately 4.5 mm wide, with latitude offsets corrected for the local seam slope, recessed up to 0.25 mm. Felt is high-roughness with a baked grain normal map and exported sheen.

The `.blend` retains individually editable cover, seam and thread meshes with live `Export triangulation` modifiers. A Cycles-baked 1024×512 tangent-space normal map is preserved at `sources/textures/tennis-ball_grain_normal.png` and embedded as JPEG in the GLB. Export joins evaluated copies into one mesh with one primitive per material, leaving source parts editable. The spherical two-lobed curve approximates a generic tennis seam. Felt fibers are normal detail, without individual silhouette hairs. Band width uses a local tangent approximation to a 4.5 mm spherical offset.

Units are metres. Blender +Z up / -Y front; GLB +Y up / +Z front (`export_yup=True`). Root `ASSET_TennisBall` has units and axis custom properties. Origin is the actual floor contact point under the centre of the exported bounds. Tiny horizontal adjustments balance stitch protrusions about X/Z; source root properties record these adjustments. Studio lights and camera are never exported.

Run from the repository root:

```sh
blender --background --python-exit-code 1 --python models/tennis-ball/generate.py
node models/tennis-ball/validate.mjs
blender --background --python-exit-code 1 --python models/tennis-ball/inspect_sources.py
```

To export saved manual edits, append `-- --export-source --skip-render`. To rebuild without rendering, append `-- --skip-render`. To render saved geometry only, append `-- --export-source --previews-only`. `--previews-only` alone rebuilds the source but skips export. `config.json` contains the deterministic model parameters. No generation-time downloads or external assets are used.

`validate.mjs` writes `reports/khronos.json` and `reports/assets.json`: Khronos 0 errors / 0 warnings, budget limits, root axes/units, floor contact and centring, real dimensions, embedded JPEG normal map, finite attributes and nondegenerate triangles. It loads geometry with three GLTFLoader after removing texture bindings for Node (image decoding is not tested). Connected components verify two cover halves and exact paired-stitch counts for tennis/baseball/softball, six cricket stitch rows with two quarter seams, or the faint table-tennis join. `inspect_sources.py` reopens the source, asserts editable objects/modifiers and normal map, re-imports the GLB and matches triangle counts without changing the saved source.

Preview PNGs are hero, front, side and 3q (Cycles, 32 samples, 900×900); hero WebP uses quality 86. `reports/reproducibility.json` compares two independent factory-reset `--skip-render` builds using per-primitive counts and vertex positions rounded to 10 micrometres, then restores the reviewed outputs. `reports/mcp-session.json` records interactive prototypes, saved-source inspection and MCP errors.

Not verified: browser/WebGL image decoding and gallery integration, WebKit, physical Android/iOS devices, manufacturer cutting patterns, real material tests, mass, rebound, pressure, physical playability or regulatory certification. Visual review remains required. Owner-project reuse is authorized; public redistribution terms are unspecified.

Preview isolation: rendering reopens the saved editable source after export, avoiding temporary-export dependency state.

Host runtime note: this worker has a PulseAudio teardown hang even with audio disabled. Successful headless runs flush logs and exit after synchronous saves, exports, renders and checks; interactive MCP execution does not use that exit path.
