# Escalator Detail

Original static escalator for the GJH Virtual Mall, in the existing **Mall Fixtures**
category. This is a distinct lightweight 3.6 m rise module. The existing `escalator`
has a 3 m rise, 65,394 triangles and animated circulation; `mall-escalator-landing`
and `mall-escalator-handrail` are partial subsystems. See `reports/duplicate-search.json`.

Metres; Blender +Z up and -Y front exports to glTF +Y up and +Z front. The root
is at the floor centre of the 6 m footprint; lower entry is +Z. Nominal clear
tread width is 1 m; outside casing width is 1.32 m. Lower/upper deck ribs are
approximately 0.103/3.703 m above the datum, a 3.6 m difference. Twenty-two rigid
steps span a 5.1 m flight. Each end has two deck-flush treads, with risers opening
through 0.05, 0.12 and 0.19 m before the central 0.222 m risers; the upper end
reverses this transition. Pitch is approximately 0.232 m. Actual exported
measurements and hashes are in `reports/assets.json` and metadata. Fitting the
flattened terminals into this compact footprint makes the central incline
approximately 43.7 degrees; this remains a visual study, not an engineered installation.
The revised GLB measures 843,808 bytes and 18,500 triangles, with three shared
materials, 28 stored meshes and 29 rendered primitives.

`STEPS_FutureMotion` contains `STEP_001` through `STEP_022`, each a separate mesh
with a pivot at the tread centre. Fixed meshes batch the chassis, handrails,
16 glass panels, landing plates, two toothed comb plates and one blank signpost.
The signpost has steel and graphite primitives. All geometry shares three
materials. Glass is alpha blended, without screen-space transmission. Static
rest geometry has no return-step chain, animation, collider or passenger logic.
Future circulation must author the hidden return route and animate the landing transitions.

Advisor round 1 replaces the abrupt terminal steps with the flattened transitions
and reshapes the metal skirts, glass channels and handrails along a shared height
path. Raised continuous skirts hide the tread sides from both directions. The
delivery gate checks actual tread/comb levels and raycasts the exported casing at
396 positions across both sides of all steps, including the terminal edges.

Build from this directory:

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python generate.py
sips -s format jpeg -s formatOptions 90 previews/hero.png --out previews/hero.jpg
node validate.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python inspect_sources.py
/opt/homebrew/bin/blender --background --python-exit-code 1 --python verify_rebuild.py
```

Append `-- --export-source --skip-render` to `generate.py` to export saved edits
without regenerating. The inspector edits a disposable source copy, never the
canonical source. It verifies manifold source parts and identical saved-source
re-export. No random inputs or downloaded dependencies are used for geometry.

From repository root:

```sh
npm run validate:assets
npm test
git checkout -- models/demo-beverage-can/reports/structure-motion.json
npm run build
node models/escalator-detail/browser-check.mjs
```

Hero, front, side and reverse three-quarter previews are reviewed visually.
Evidence is local; the full 17-shop mall, its aggregate 200 draw-call budget,
physical devices, WebKit and transport/safety engineering are unverified.
No gallery UI changes, publication or push are included.
