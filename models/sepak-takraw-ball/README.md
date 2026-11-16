# Sepak Takraw Ball

Original, brand-neutral sports asset. Category: Sports (browse: Parks & Recreation). No external assets, fonts, logos, text, trademarks or product markings.

Real scale: Task-selected men’s circumference midpoint 430 mm (420–440), giving a 136.873 mm spherical envelope. The linked School Games Federation of India rules specify 420–440 mm for men and twelve holes / twenty intersections. Some later ISTAF-derived rules instead use 410–430 mm; this model deliberately follows the task’s explicit range. Dimension source: [official rules / federation reference](https://www.sgfi.org.in/Content/FileUpload/PDF/RULES_SEPAKTAKRAW.pdf).

Six original closed synthetic ribbons following the six great circles whose normals are the six antipodal axes of an icosahedron. Their arrangement is the spherical icosidodecahedral layout. Wide ribbons close the twenty triangular regions into junctions and leave twelve pentagonal holes. Each ribbon alternates over and under its five neighbours at ten pairwise crossings, with complementary radial offsets. Ribbons have real thickness and an open hollow centre; no internal sphere or texture opacity.

The compressed `.blend` preserves all named editable components and live modifiers where used. Export evaluates modifiers and curves into a temporary triangulated single mesh, one primitive per material; the saved source stays editable. Studio cameras and lights are excluded from the GLB. Units are metres; Blender +Z up / -Y front becomes glTF +Y up / +Z front. The origin is the floor contact point under the centre. The lattice is hollow and can be seen through.

Run from the repository root:

```sh
blender --background --python-exit-code 1 --python models/sepak-takraw-ball/generate.py
node models/sepak-takraw-ball/validate.mjs
blender --background --python-exit-code 1 --python models/sepak-takraw-ball/inspect_sources.py
```

Append `-- --skip-render` for a factory-reset rebuild without previews. Append `-- --export-source --skip-render` to export saved manual edits. Append `-- --export-source --previews-only` to render saved geometry without replacing the GLB. Each folder is self-contained; no other model generator is required.

`validate.mjs` writes `reports/khronos.json` and `reports/assets.json`: Khronos 0 errors / 0 warnings, hard budget 40,000 triangles / 1,572,864 bytes (target ≤1 MB), one mesh, correct root units/axes, floor contact and centred bounds, finite attributes, nondegenerate triangles, non-metal PBR, embedded JPEG images only, no external references, cameras, lights or animations. It checks model-specific counts using exported mesh connectivity and dimension samples. Dimension tolerance is 1 mm on the spherical envelope for weaving relief and tessellation; rays pass through all twelve opposing pentagonal holes and hit all twenty triangular junction regions.

`inspect_sources.py` reopens the source, asserts key objects/modifiers, reimports the GLB and checks triangle counts (`reports/sources.json`), without saving or changing the source file. `reports/source-geometry.json` records construction parameters. `reports/reproducibility.json` compares two independent factory-reset `--skip-render` builds by per-primitive vertex/triangle counts and vertex positions rounded to 10 micrometres; byte identity is not required. The preserved final outputs are restored after comparison. `reports/mcp-session.json` records GUI prototype and viewport inspection calls, including any MCP failures.

Preview PNGs are hero, front, side and 3q, rendered in the template’s slate studio with Cycles, 32 samples, 900×900; hero WebP uses quality 86. All four PNGs are visually reviewed.

Approximations: Twenty triangular junction regions are distinguished from the thirty pairwise great-circle crossing points. Broad ribbons overlap at the small triangular junction regions; the model approximates pressed synthetic weave and does not simulate deformation/contact. The continuous crown and offsets approximate moulded strip edges. The actual tessellated envelope is centred in X/Z and rests at the minimum mesh vertex; radial extent defines the 430 mm circumference. Static visual asset; no physics, aerodynamic, mass, rebound or certification testing. Browser/WebGL, WebKit, physical Android and iOS are NOT TESTED. No deployment or publication is claimed. Owner-project reuse is authorized; public redistribution terms are unspecified.

In the supplied sandbox, Blender's PulseAudio shutdown worker hangs after completed work. The background scripts flush output and exit directly only after all exports/renders or inspection assertions finish successfully; Python exceptions still propagate to `--python-exit-code 1`. This avoids the unrelated audio cleanup hang.
