# Bowling Ball (Ten-Pin)

Original, brand-neutral bowling ball. Category: Sports (browse: Parks & Recreation). No external assets, fonts, text, logos or product markings.

Real scale: 215.9 mm (8.5 in) diameter, explicitly requested at the lower end of the USBC 8.500–8.595 in manufacturing range rather than its midpoint. [USBC Equipment Specifications Manual](https://bowl.com/getmedia/08ef148d-c0e4-4e00-9e0d-855ba4729ad5/equipment-specs-manual.pdf?v=20250716T14001).

Editable UV sphere with three live manifold Boolean cylindrical cutters. Finger bores are 20 mm diameter and 55 mm deep, with a 6.5 mm edge-to-edge surface bridge (about 26.46 mm centre chord); the thumb bore is 26 mm diameter and 65 mm deep. Both thumb-to-finger spans are 108 mm, measured edge to edge along the shortest spherical surface arc. Radial cylindrical lip angles are asin(bore radius / ball radius); the common grip rotation places the fingers above the thumb on the front hemisphere so the hero and front previews show all three openings. These grip values implement the FIX-1 review specification; they are an illustrative adult conventional grip, not a fit to a particular hand. Generic navy and plum sinusoidal marbling is analytically baked from spherical coordinates to a 1024×512 base-colour PNG and embedded as JPEG. Resin roughness 0.10 with a 0.35 clear coat.

The compressed `.blend` preserves editable geometry and any live modifiers. Export evaluates temporary copies, welds Boolean intersection vertices within 0.1 micrometre, dissolves degenerate edges within 0.01 micrometre, and triangulates, leaving the saved source unchanged. Holes and valves remain separate editable features; the exported shell uses one primitive per material. Studio lights and camera are never exported. Units are metres; the root is at the floor contact point under the object centre. Blender uses +Z up / -Y front; GLB uses +Y up / +Z front (`export_yup=True`).

Run from the repository root:

```sh
blender --background --python-exit-code 1 --python models/bowling-ball/generate.py
node models/bowling-ball/validate.mjs
blender --background --python-exit-code 1 --python models/bowling-ball/inspect_sources.py
python3 models/bowling-ball/reproduce.py
```

Append `-- --skip-render` to rebuild without previews, `-- --export-source --skip-render` to export saved edits, or `-- --export-source --previews-only` to render saved geometry. `--previews-only` alone factory-rebuilds the source and renders without exporting. No network access is used. The generator flushes output and exits directly after successful background work to avoid this host’s PulseAudio teardown hang; interactive execution returns normally.

`validate.mjs` writes `reports/khronos.json` and `reports/assets.json`: Khronos 0 errors / 0 warnings, 40,000-triangle and 1,572,864-byte hard budgets, root name and units/front-axis properties, finite vertex attributes, nondegenerate triangles, embedded JPEG images only, dimensions within 0.8%, floor datum within 0.3% of diameter, centred X/Z and model-specific features. The dimensional allowance covers tessellation, recessed seams/dimples and small valve protrusions. Golf validation independently counts 362 radial mesh minima and ray-tests all dimple recesses; bowling checks all three bore depths and surrounding skin, 20/20/26 mm bore diameters, a 6–7 mm finger bridge and both 108 mm surface spans within 1 mm by ray-bisecting the near lips in the exported mesh (0.4 mm radial skin threshold covers sphere tessellation); analytic great-circle checks additionally verify the design values; beach validation counts six connected coloured gores and two separate shell caps. Medicine-ball validation checks the valve and both textured materials; puck validation checks its proportions and normal-textured band. Node GLTFLoader parses a geometry copy without image bindings; it does not decode the appearance.

`inspect_sources.py` reopens the source, asserts editable features/modifiers, re-imports the GLB, checks its triangle count and confirms the source hash is unchanged (`reports/sources.json`). `reproduce.py` runs two factory-reset builds, compares per-primitive counts and sorted positions rounded to one micrometre, and restores the delivery files (`reports/reproducibility.json`). Byte identity is not required. MCP tools and failures are recorded in `reports/mcp-session.json`.

Preview PNGs are hero, front, side and 3q, rendered at 900×900 with Cycles, 32 samples, seed 0 and the template slate studio style. Hero WebP quality is 86. All four PNGs receive visual review.

Accuracy and limitations: Grip dimensions are an illustrative adult conventional span, not fitted to a hand. Cylindrical flat-bottom bores omit bevels, fingertip inserts and internal core structure. The analytic swirl is an original visual approximation of poured reactive resin. No mass, balance, oil interaction or performance is simulated. Browser/WebGL, WebKit and physical Android/iOS checks are NOT TESTED. These are draft visual assets, not interactive or physically certified products. Owner-project reuse is authorized; public redistribution terms are unspecified.
