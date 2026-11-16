# Medicine Ball (Rubber, ~6 kg look)

Original, brand-neutral medicine ball. Category: Sports (browse: Parks & Recreation). No external assets, fonts, text, logos or product markings.

Real scale: 280 mm diameter per the task brief. Medicine balls have no universal competition diameter or density; the approximately 6 kg description is a visual size class, not measured mass or a certified standard.

Editable UV sphere with broad teal equatorial band and charcoal poles. A 1024×512 tangent-space normal map sampled from a deterministic periodic height field supplies fine moulded grip texture. Small flattened black rubber fill valve at the front. Maps are original analytical bakes, not external images.

The compressed `.blend` preserves editable geometry and any live modifiers. Export evaluates temporary triangulated copies, leaving the saved source unchanged. Holes and valves remain separate editable features; the exported shell uses one primitive per material. Studio lights and camera are never exported. Units are metres; the root is at the floor contact point under the object centre. Blender uses +Z up / -Y front; GLB uses +Y up / +Z front (`export_yup=True`).

Run from the repository root:

```sh
blender --background --python-exit-code 1 --python models/medicine-ball/generate.py
node models/medicine-ball/validate.mjs
blender --background --python-exit-code 1 --python models/medicine-ball/inspect_sources.py
python3 models/medicine-ball/reproduce.py
```

Append `-- --skip-render` to rebuild without previews, `-- --export-source --skip-render` to export saved edits, or `-- --export-source --previews-only` to render saved geometry. `--previews-only` alone factory-rebuilds the source and renders without exporting. No network access is used. The generator flushes output and exits directly after successful background work to avoid this host’s PulseAudio teardown hang; interactive execution returns normally.

`validate.mjs` writes `reports/khronos.json` and `reports/assets.json`: Khronos 0 errors / 0 warnings, 40,000-triangle and 1,572,864-byte hard budgets, root name and units/front-axis properties, finite vertex attributes, nondegenerate triangles, embedded JPEG images only, dimensions within 0.8%, floor datum within 0.3% of diameter, centred X/Z and model-specific features. The dimensional allowance covers tessellation, recessed seams/dimples and small valve protrusions. Golf validation independently counts 362 radial mesh minima and ray-tests all dimple recesses; bowling checks all three bore depths and surrounding skin; beach validation counts six connected coloured gores and two separate shell caps. Medicine-ball validation checks the valve and both textured materials; puck validation checks its proportions and normal-textured band. Node GLTFLoader parses a geometry copy without image bindings; it does not decode the appearance.

`inspect_sources.py` reopens the source, asserts editable features/modifiers, re-imports the GLB, checks its triangle count and confirms the source hash is unchanged (`reports/sources.json`). `reproduce.py` runs two factory-reset builds, compares per-primitive counts and sorted positions rounded to one micrometre, and restores the delivery files (`reports/reproducibility.json`). Byte identity is not required. MCP tools and failures are recorded in `reports/mcp-session.json`.

Preview PNGs are hero, front, side and 3q, rendered at 900×900 with Cycles, 32 samples, seed 0 and the template slate studio style. Hero WebP quality is 86. All four PNGs receive visual review.

Accuracy and limitations: Diameter and two-tone treatment are generic. Grip grain is a normal map and does not alter the silhouette; the periodic moulded texture compresses near UV poles. The fill valve is a shallow geometric insert, without an internal passage. No mass, bounce, deformation or fill contents are simulated. Browser/WebGL, WebKit and physical Android/iOS checks are NOT TESTED. These are draft visual assets, not interactive or physically certified products. Owner-project reuse is authorized; public redistribution terms are unspecified.
