# Rugby Ball (Size 5)

Original, brand-neutral sports asset. Category: Sports (browse: Parks & Recreation). No external assets, fonts, logos, text, trademarks or product markings.

Real scale: World Rugby Law 2 size-5 midpoints: length 290 mm (280–300), end-to-end circumference 755 mm (740–770), width circumference 600 mm (580–620), giving a 190.986 mm body width. Dimension source: [official rules / federation reference](https://passport.world.rugby/media/dafo2cbl/2501en-world-rugby-laws-2025-compressed.pdf).

Four separately editable white rubber panels with inward Solidify thickness and recessed seam beds. Two simple teal transverse colour bands are assigned to real panel faces. Original grip grain is Cycles-baked into a 1024×512 tangent-space normal map, embedded as JPEG. A modified prolate profile is numerically fitted to both circumference midpoints; the lower aspect ratio makes this oval blunter than the football.

The compressed `.blend` preserves all named editable components and live modifiers where used. Export evaluates modifiers and curves into a temporary triangulated single mesh, one primitive per material; the saved source stays editable. Studio cameras and lights are excluded from the GLB. Units are metres; Blender +Z up / -Y front becomes glTF +Y up / +Z front. The origin is the floor contact point under the centre. The long axis lies along X.

Run from the repository root:

```sh
blender --background --python-exit-code 1 --python models/rugby-ball/generate.py
node models/rugby-ball/validate.mjs
blender --background --python-exit-code 1 --python models/rugby-ball/inspect_sources.py
```

Append `-- --skip-render` for a factory-reset rebuild without previews. Append `-- --export-source --skip-render` to export saved manual edits. Append `-- --export-source --previews-only` to render saved geometry without replacing the GLB. Each folder is self-contained; no other model generator is required.

`validate.mjs` writes `reports/khronos.json` and `reports/assets.json`: Khronos 0 errors / 0 warnings, hard budget 40,000 triangles / 1,572,864 bytes (target ≤1 MB), one mesh, correct root units/axes, floor contact and centred bounds, finite attributes, nondegenerate triangles, non-metal PBR, embedded JPEG images only, no external references, cameras, lights or animations. It checks model-specific counts using exported mesh connectivity and dimension samples. Circumferences are checked by integrating the actual parametric profile; dimensional tolerance is 0.1 mm on length/width, 0.2 mm on rugby height, or 4.5 mm on football height to allow raised laces.

`inspect_sources.py` reopens the source, asserts key objects/modifiers, reimports the GLB and checks triangle counts (`reports/sources.json`), without saving or changing the source file. `reports/source-geometry.json` records construction parameters. `reports/reproducibility.json` compares two independent factory-reset `--skip-render` builds by per-primitive vertex/triangle counts and vertex positions rounded to 10 micrometres; byte identity is not required. The preserved final outputs are restored after comparison. `reports/mcp-session.json` records GUI prototype and viewport inspection calls, including any MCP failures.

Preview PNGs are hero, front, side and 3q, rendered in the template’s slate studio with Cycles, 32 samples, 900×900; hero WebP uses quality 86. All four PNGs are visually reviewed.

Approximations: The contour approximates an inflated competition ball, not a manufacturer drawing. Grip pimples are represented by an irregular baked Voronoi normal map; the silhouette is smooth. Bands follow the mesh grid and are intentionally generic. Static visual asset; no physics, aerodynamic, mass, rebound or certification testing. Browser/WebGL, WebKit, physical Android and iOS are NOT TESTED. No deployment or publication is claimed. Owner-project reuse is authorized; public redistribution terms are unspecified.

In the supplied sandbox, Blender's PulseAudio shutdown worker hangs after completed work. The background scripts flush output and exit directly only after all exports/renders or inspection assertions finish successfully; Python exceptions still propagate to `--python-exit-code 1`. This avoids the unrelated audio cleanup hang.
