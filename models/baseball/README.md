# Baseball

Original, brand-neutral baseball. Category: Sports (browse: Parks & Recreation). No external assets, fonts, text, logos or product markings. Static visual asset; no physics.

Real scale: MLB Official Baseball Rules, rule 3.01: circumference 9–9.25 inches; midpoint 9.125 in = 231.775 mm, diameter 73.776 mm. The Library of Congress confirms 108 double stitches. Source: [MLB Official Baseball Rules, rule 3.01](https://blogs.loc.gov/loc/2018/03/baseballs-the-heart-of-the-matter/). Dimensions refer to the spherical skin; raised threads can extend up to 1.2 mm beyond that nominal diameter. Polygon sampling slightly reduces the extents. The validator allows ±0.10 mm for tennis, ±0.06 mm for table tennis, and ±1.2 mm for balls with raised threads; it additionally checks all skin vertices against nominal radius within 0.06 mm; reports contain actual dimensions.

Two separate white leather figure-eight covers, narrow recessed seam, and exactly 108 V-shaped double stitches (216 separate red tube strands), with capped ends embedded into the cover. Subtle leather grain is a baked normal map.

The `.blend` retains individually editable cover, seam and thread meshes with live `Export triangulation` modifiers. A Cycles-baked 1024×512 tangent-space normal map is preserved at `sources/textures/baseball_grain_normal.png` and embedded as JPEG in the GLB. Export joins evaluated copies into one mesh with one primitive per material, leaving source parts editable. The spherical two-lobed cover boundary is an original approximation, not a manufacturing cutting pattern. Thread cross-sections are six-sided and stylized; no interior core, individual thread fibers or stitch holes are modeled.

Units are metres. Blender +Z up / -Y front; GLB +Y up / +Z front (`export_yup=True`). Root `ASSET_Baseball` has units and axis custom properties. Origin is the actual floor contact point under the centre of the exported bounds. Tiny horizontal adjustments balance stitch protrusions about X/Z; source root properties record these adjustments. Studio lights and camera are never exported.

Run from the repository root:

```sh
blender --background --python-exit-code 1 --python models/baseball/generate.py
node models/baseball/validate.mjs
blender --background --python-exit-code 1 --python models/baseball/inspect_sources.py
```

To export saved manual edits, append `-- --export-source --skip-render`. To rebuild without rendering, append `-- --skip-render`. To render saved geometry only, append `-- --export-source --previews-only`. `--previews-only` alone rebuilds the source but skips export. `config.json` contains the deterministic model parameters. No generation-time downloads or external assets are used.

`validate.mjs` writes `reports/khronos.json` and `reports/assets.json`: Khronos 0 errors / 0 warnings, budget limits, root axes/units, floor contact and centring, real dimensions, embedded JPEG normal map, finite attributes and nondegenerate triangles. It loads geometry with three GLTFLoader after removing texture bindings for Node (image decoding is not tested). Connected components verify two cover halves and exact paired-stitch counts for tennis/baseball/softball, six cricket stitch rows with two quarter seams, or the faint table-tennis join. `inspect_sources.py` reopens the source, asserts editable objects/modifiers and normal map, re-imports the GLB and matches triangle counts without changing the saved source.

Preview PNGs are hero, front, side and 3q (Cycles, 32 samples, 900×900); hero WebP uses quality 86. `reports/reproducibility.json` compares two independent factory-reset `--skip-render` builds using per-primitive counts and vertex positions rounded to 10 micrometres, then restores the reviewed outputs. `reports/mcp-session.json` records interactive prototypes, saved-source inspection and MCP errors.

Not verified: browser/WebGL image decoding and gallery integration, WebKit, physical Android/iOS devices, manufacturer cutting patterns, real material tests, mass, rebound, pressure, physical playability or regulatory certification. Visual review remains required. Owner-project reuse is authorized; public redistribution terms are unspecified.

Preview isolation: rendering reopens the saved editable source after export, avoiding temporary-export dependency state.

Host runtime note: this worker has a PulseAudio teardown hang even with audio disabled. Successful headless runs flush logs and exit after synchronous saves, exports, renders and checks; interactive MCP execution does not use that exit path.
