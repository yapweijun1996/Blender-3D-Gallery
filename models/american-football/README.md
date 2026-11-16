# American Football

Original, brand-neutral sports asset. Category: Sports (browse: Parks & Recreation). No external assets, fonts, logos, text, trademarks or product markings.

Real scale: NFL professional size midpoint: length 282.575 mm (11–11.25 in), long circumference 717.55 mm (28–28.5 in), short circumference 536.575 mm (21–21.25 in). The task’s approximate 11 in length is represented by the official range midpoint. Dimension source: [official rules / federation reference](https://operations.nfl.com/rules-officiating/nfl-football-basics/football-terms).

Four separately editable brown leather panels with inward Solidify thickness, a continuous inset seam bed, one white leather lace strip, eight crossing lace curves and one long lace curve. A 1024×512 tangent-space normal map is Cycles-baked from original 3D Voronoi grain and embedded as JPEG. The profile is a pointed modified prolate spheroid numerically fitted to both circumference midpoints.

The compressed `.blend` preserves all named editable components and live modifiers where used. Export evaluates modifiers and curves into a temporary triangulated single mesh, one primitive per material; the saved source stays editable. Studio cameras and lights are excluded from the GLB. Units are metres; Blender +Z up / -Y front becomes glTF +Y up / +Z front. The origin is the floor contact point under the centre. The long axis lies along X.

Run from the repository root:

```sh
blender --background --python-exit-code 1 --python models/american-football/generate.py
node models/american-football/validate.mjs
blender --background --python-exit-code 1 --python models/american-football/inspect_sources.py
```

Append `-- --skip-render` for a factory-reset rebuild without previews. Append `-- --export-source --skip-render` to export saved manual edits. Append `-- --export-source --previews-only` to render saved geometry without replacing the GLB. Each folder is self-contained; no other model generator is required.

`validate.mjs` writes `reports/khronos.json` and `reports/assets.json`: Khronos 0 errors / 0 warnings, hard budget 40,000 triangles / 1,572,864 bytes (target ≤1 MB), one mesh, correct root units/axes, floor contact and centred bounds, finite attributes, nondegenerate triangles, non-metal PBR, embedded JPEG images only, no external references, cameras, lights or animations. It checks model-specific counts using exported mesh connectivity and dimension samples. Circumferences are checked by integrating the actual parametric profile; dimensional tolerance is 0.1 mm on length/width, 0.2 mm on rugby height, or 4.5 mm on football height to allow raised laces.

`inspect_sources.py` reopens the source, asserts key objects/modifiers, reimports the GLB and checks triangle counts (`reports/sources.json`), without saving or changing the source file. `reports/source-geometry.json` records construction parameters. `reports/reproducibility.json` compares two independent factory-reset `--skip-render` builds by per-primitive vertex/triangle counts and vertex positions rounded to 10 micrometres; byte identity is not required. The preserved final outputs are restored after comparison. `reports/mcp-session.json` records GUI prototype and viewport inspection calls, including any MCP failures.

Preview PNGs are hero, front, side and 3q, rendered in the template’s slate studio with Cycles, 32 samples, 900×900; hero WebP uses quality 86. All four PNGs are visually reviewed.

Approximations: The parametric leather contour approximates inflated leather; it is not a manufacturer drawing. Grain affects shading only. Lace ends are buried in the shell; individual punched holes and internal bladder are omitted. Static visual asset; no physics, aerodynamic, mass, rebound or certification testing. Browser/WebGL, WebKit, physical Android and iOS are NOT TESTED. No deployment or publication is claimed. Owner-project reuse is authorized; public redistribution terms are unspecified.

In the supplied sandbox, Blender's PulseAudio shutdown worker hangs after completed work. The background scripts flush output and exit directly only after all exports/renders or inspection assertions finish successfully; Python exceptions still propagate to `--python-exit-code 1`. This avoids the unrelated audio cleanup hang.
