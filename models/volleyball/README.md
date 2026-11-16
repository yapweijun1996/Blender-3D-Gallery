# Volleyball

Original, brand-neutral volleyball. Category: Sports (browse: Parks & Recreation). No external assets, fonts, text, logos, product markings or downloaded scripts.

Real scale: circumference 660.0 mm, the exact midpoint of the 65–67 cm range in [FIVB Official Volleyball Rules 2025–2028, section 3.1](https://www.fivb.com/wp-content/uploads/2025/01/FIVB-Volleyball_Rules2025_2028-EN-v05.pdf). Nominal skin diameter 210.085 mm (circumference divided by pi). The standard supplies dimensions only; this is an original visual model and carries no certification.

18 spherical strips in six cube-face groups of three. Six muted teal centre strips and twelve ivory strips form a generic non-swirl layout. The `.blend` retains editable `BALL_Panels` and `BALL_RecessedBacking` meshes with explicit tessellation and UVs; no live modifiers are needed. Panel boundaries descend to the seam bed, so channels are geometry. The baked 1024×512 tangent-space normal map at `sources/textures/grip_normal.png` comes from an original 3D Voronoi bump shader baked in Cycles. It is embedded as JPEG in the GLB. Export joins temporary copies into one mesh, one primitive per material, and leaves the saved source unchanged. Non-metal PBR materials have metallic factor zero.

Units are metres. Blender +Z up / -Y front; glTF +Y up / +Z front. Root `ASSET_Volleyball` is at the origin with units and axis properties. Origin is the floor contact point below the ball centre; the lowest actual mesh vertex is Z=0. The studio camera and lights are never exported.

Run from the repository root:

```sh
blender --background --python-exit-code 1 --python models/volleyball/generate.py
node models/volleyball/validate.mjs
blender --background --python-exit-code 1 --python models/volleyball/inspect_sources.py
```

To export saved manual edits, append `-- --export-source --skip-render`. To rebuild without rendering, append `-- --skip-render`. To render saved geometry only, append `-- --export-source --previews-only`. The generator factory-resets the scene for procedural builds. Background jobs exit immediately after completed writes to avoid this workstation’s PulseAudio shutdown hang; exceptions still cause a failing Python exit code.

`validate.mjs` writes `reports/khronos.json` and `reports/assets.json`: Khronos 0 errors / 0 warnings, embedded JPEG normal map, root units and axes, origin and standard midpoint diameter, finite attributes, nondegenerate triangles, real recessed panel edges, exact connected panel counts and material counts, triangle and byte budgets, no animation, cameras or lights. Soccer additionally checks 450 recessed stitch components and black/white material values. `inspect_sources.py` reopens the source, asserts editable geometry and baked image, then re-imports the GLB and compares triangle counts without modifying the source. `reports/reproducibility.json` records two factory-reset builds with `--skip-render`, comparing each primitive’s vertex/triangle counts and rounded positions, then restoring the deliverables. Preview PNGs are hero, front, side and 3q (Cycles, 32 samples, 900×900); hero WebP quality 86. `reports/mcp-session.json` records attempted interactive inspection and any connection failures.

Accuracy and limits: The cube-projected layout approximates traditional sewn 18-panel construction; it is not a manufacturer pattern. Fine grain is baked normal detail only; it does not alter the silhouette. Panel rims are explicit geometry over a recessed spherical bed. No internal bladder, valve, inflation, mass, bounce or physics. Diameter tolerance of 0.8 mm accounts for finite tessellation and rounded panel edges; the actual lowest vertex is translated to Z=0. Browser/WebGL, WebKit and physical Android/iOS checks are NOT TESTED; this asset remains draft and needs independent review. No deployment or publication is claimed. Owner-project reuse is authorized; public redistribution terms are unspecified.
