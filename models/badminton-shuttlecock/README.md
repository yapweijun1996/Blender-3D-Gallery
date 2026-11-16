# Badminton Shuttlecock (Feather)

Original, brand-neutral sports asset. Category: Sports (browse: Parks & Recreation). No external assets, fonts, logos, text, trademarks or product markings.

Real scale: BWF Laws 2.2.1–2.2.5 midpoints: 16 feathers, 66 mm feather length measured from the top of the base (62–70), 63 mm feather-tip circle (58–68), and 26.5 mm base diameter (25–28). The rounded base is 22 mm tall. Overall height is approximately 84.57 mm: the 62–70 mm rule refers to feather length above the base, not total shuttlecock height. Dimension source: [official rules / federation reference](https://system.bwfbadminton.com/documents/folder_1_81/Regulations/Laws/Part%20II%20Section%201A%20-%20Laws%20of%20Badminton%20-%20May%202017.pdf).

Sixteen separately editable cupped solid feather vanes with live Solidify modifiers, sixteen bevelled quill curves, fine geometric barb strokes, two closed thread-binding curves, and a white-covered cork base with a true hemispherical bottom. All feathers are thin opaque geometry; no alpha textures or text.

The compressed `.blend` preserves all named editable components and live modifiers where used. Export evaluates modifiers and curves into a temporary triangulated single mesh, one primitive per material; the saved source stays editable. Studio cameras and lights are excluded from the GLB. Units are metres; Blender +Z up / -Y front becomes glTF +Y up / +Z front. The origin is the floor contact point under the centre. The symmetry axis is vertical.

Run from the repository root:

```sh
blender --background --python-exit-code 1 --python models/badminton-shuttlecock/generate.py
node models/badminton-shuttlecock/validate.mjs
blender --background --python-exit-code 1 --python models/badminton-shuttlecock/inspect_sources.py
```

Append `-- --skip-render` for a factory-reset rebuild without previews. Append `-- --export-source --skip-render` to export saved manual edits. Append `-- --export-source --previews-only` to render saved geometry without replacing the GLB. Each folder is self-contained; no other model generator is required.

`validate.mjs` writes `reports/khronos.json` and `reports/assets.json`: Khronos 0 errors / 0 warnings, hard budget 40,000 triangles / 1,572,864 bytes (target ≤1 MB), one mesh, correct root units/axes, floor contact and centred bounds, finite attributes, nondegenerate triangles, non-metal PBR, embedded JPEG images only, no external references, cameras, lights or animations. It checks model-specific counts using exported mesh connectivity and dimension samples. Dimension tolerance is 0.5 mm on total height, 1 mm on feather-tip extents, and 0.1 mm on cork diameter; the lower cork vertices must lie on a hemisphere.

`inspect_sources.py` reopens the source, asserts key objects/modifiers, reimports the GLB and checks triangle counts (`reports/sources.json`), without saving or changing the source file. `reports/source-geometry.json` records construction parameters. `reports/reproducibility.json` compares two independent factory-reset `--skip-render` builds by per-primitive vertex/triangle counts and vertex positions rounded to 10 micrometres; byte identity is not required. The preserved final outputs are restored after comparison. `reports/mcp-session.json` records GUI prototype and viewport inspection calls, including any MCP failures.

Preview PNGs are hero, front, side and 3q, rendered in the template’s slate studio with Cycles, 32 samples, 900×900; hero WebP uses quality 86. All four PNGs are visually reviewed.

Approximations: The 66 mm feather length follows the shaft centreline from the top of the cork. The full outer tip envelope can be less than 1 mm larger than the 63 mm shaft-tip circle because quills and vanes have thickness. Barbs are a sparse geometric suggestion, not individual microscopic fibres. Feather asymmetry, knots and natural wear are simplified. Static visual asset; no physics, aerodynamic, mass, rebound or certification testing. Browser/WebGL, WebKit, physical Android and iOS are NOT TESTED. No deployment or publication is claimed. Owner-project reuse is authorized; public redistribution terms are unspecified.

In the supplied sandbox, Blender's PulseAudio shutdown worker hangs after completed work. The background scripts flush output and exit directly only after all exports/renders or inspection assertions finish successfully; Python exceptions still propagate to `--python-exit-code 1`. This avoids the unrelated audio cleanup hang.
