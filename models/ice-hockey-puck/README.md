# Ice Hockey Puck

Original, brand-neutral ice hockey puck. Category: Sports (browse: Parks & Recreation). No external assets, fonts, text, logos or product markings.

Real scale: 76.2 mm diameter × 25.4 mm thickness (3 × 1 in), following the dimensioned puck drawing in [IIHF Official Rule Book 2026/27, Appendix III](https://blob.iihf.com/iihf-media/iihfmvc/media/downloads/rule%20book/2026-27_iihf_rule_book.pdf).

Editable 128-sided cylinder with live 0.65 mm three-segment edge bevel. Near-black satin faces and a rubber edge band using an original 1024×512 normal map analytically baked from two crossed diagonal wave height gradients. PNG retained in sources; GLB embeds JPEG. Both materials use linear base colour (0.0025, 0.0030, 0.0035), metallic 0, roughness 0.72 and reduced specular IOR level 0.08 to approximate a porous carbon-filled rubber surface with broad, weak reflections. Studio lights are unchanged. Lying flat on its lower face. This asset is a puck, not a ball.

The compressed `.blend` preserves editable geometry and any live modifiers. Export evaluates temporary triangulated copies, leaving the saved source unchanged. Holes and valves remain separate editable features; the exported shell uses one primitive per material. Studio lights and camera are never exported. Units are metres; the root is at the floor contact point under the object centre. Blender uses +Z up / -Y front; GLB uses +Y up / +Z front (`export_yup=True`).

Run from the repository root:

```sh
blender --background --python-exit-code 1 --python models/ice-hockey-puck/generate.py
node models/ice-hockey-puck/validate.mjs
blender --background --python-exit-code 1 --python models/ice-hockey-puck/inspect_sources.py
python3 models/ice-hockey-puck/reproduce.py
```

Append `-- --skip-render` to rebuild without previews, `-- --export-source --skip-render` to export saved edits, or `-- --export-source --previews-only` to render saved geometry. `--previews-only` alone factory-rebuilds the source and renders without exporting. No network access is used. The generator flushes output and exits directly after successful background work to avoid this host’s PulseAudio teardown hang; interactive execution returns normally.

`validate.mjs` writes `reports/khronos.json` and `reports/assets.json`: Khronos 0 errors / 0 warnings, 40,000-triangle and 1,572,864-byte hard budgets, root name and units/front-axis properties, finite vertex attributes, nondegenerate triangles, embedded JPEG images only, dimensions within 0.8%, floor datum within 0.3% of diameter, centred X/Z and model-specific features. The dimensional allowance covers tessellation, recessed seams/dimples and small valve protrusions. Golf validation independently counts 362 radial mesh minima and ray-tests all dimple recesses; bowling checks all three bore depths and surrounding skin; beach validation counts six connected coloured gores and two separate shell caps. Medicine-ball validation checks the valve and both textured materials; puck validation checks its proportions, normal-textured band, near-black linear base colour and satin roughness. Node GLTFLoader parses a geometry copy without image bindings; it does not decode the appearance.

`inspect_sources.py` reopens the source, asserts editable features/modifiers, re-imports the GLB, checks its triangle count and confirms the source hash is unchanged (`reports/sources.json`). `reproduce.py` runs two factory-reset builds, compares per-primitive counts and sorted positions rounded to one micrometre, and restores the delivery files (`reports/reproducibility.json`). Byte identity is not required. MCP tools and failures are recorded in `reports/mcp-session.json`.

Preview PNGs are hero, front, side and 3q, rendered at 900×900 with Cycles, 32 samples, seed 0 and the template slate studio style. Hero WebP quality is 86. All four PNGs receive visual review.

Accuracy and limitations: The diamond band is normal detail only; side silhouette stays cylindrical. The sampled crosshatch is a simplified moulded grip pattern, not a manufacturer drawing. No logos, mass, friction, freezing behaviour or physics are simulated. Browser/WebGL, WebKit and physical Android/iOS checks are NOT TESTED. These are draft visual assets, not interactive or physically certified products. Owner-project reuse is authorized; public redistribution terms are unspecified.
