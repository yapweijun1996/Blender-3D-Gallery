# Escalator Detail

Original static escalator for the GJH Virtual Mall, in the existing **Mall Fixtures**
category. This is a distinct lightweight 3.6 m rise module. The existing `escalator`
has a 3 m rise, 65,394 triangles and animated circulation; `mall-escalator-landing`
and `mall-escalator-handrail` are partial subsystems. See `reports/duplicate-search.json`.

Metres; Blender +Z up and -Y front exports to glTF +Y up and +Z front. The root
is at the floor centre of the 6 m footprint; lower entry is +Z. Nominal clear
tread width is 1 m; outside casing width is 1.32 m. Lower/upper deck ribs are
approximately 0.103/3.703 m above the datum, a 3.6 m difference. Eighteen rigid
steps rise 0.2 m each over a 5.1 m flight. Actual exported measurements and hashes
are in `reports/assets.json` and metadata. This compact configuration uses short
landings and an approximately 35.2 degree incline.

`STEPS_FutureMotion` contains `STEP_001` through `STEP_018`, each a separate mesh
with a pivot at the tread centre. Fixed meshes batch the chassis, handrails,
16 glass panels, landing plates, two toothed comb plates and one blank signpost.
The signpost has steel and graphite primitives. All geometry shares three
materials. Glass is alpha blended, without screen-space transmission. Static
rest geometry has no return-step chain, animation, collider or passenger logic.
Future circulation must author the hidden return route and landing transitions.

Build from this directory:

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python generate.py
node validate.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python inspect_sources.py
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
