# Lounge Sofa, Bench and Slim Table

Original brand-neutral mall rest-area furniture in the existing **Mall Fixtures** category.
Rounded greige three-seat sofa, matching backless bench, slim warm-toned shared table,
upholstery welts and recessed graphite supports. No external assets or textures.

The compact staggered arrangement occupies a 3 × 1.5 m furniture envelope. The sofa is
2 × .85 × .8 m, the bench 1.6 × .38 × .45 m, and the table .85 × .22 × .5 m
(width × depth × height; measured export/source evidence is in `reports/`). The table
lies between the seating depth envelopes at their offset ends. Occupied legroom and
circulation extend outside this furniture envelope and require separate mall planning.

Blender +Z up, front -Y; exported glTF +Y up, front +Z. Origin is the combined floor
centre. Source contains separately editable sofa, bench and table parts. Export uses
three evaluated material batches, giving three opaque mesh primitives. Studio floor,
lights and camera are excluded. Static geometry only; no sitting logic or animation.
The card uses a lightweight 512 px WebP derived from the 900 px hero PNG; preview
conversion uses the available Python 3 Pillow installation.

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/lounge-sofa-bench/generate.py
# Export saved source edits without procedural rebuilding:
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/lounge-sofa-bench/generate.py -- --export-source --skip-render
node models/lounge-sofa-bench/validate.mjs
npm run validate:assets
npm test
npm run build
node models/lounge-sofa-bench/check-browser.mjs
```

`validate.mjs` adapts the self-checkout-machine quality gate for this static group,
checks Khronos format validation, budgets, finite nondegenerate geometry, three
materials/primitives, source features, dimensions, table gaps and floor-centred bounds.
`inspect_sources.py` reopens the native source and checks a saved edited copy independently.

Similar existing models: `gjh-lounge-bench` has a framed upholstered bench with arms
and back; `living-room-sofa` is a standalone sofa; `public-service-waiting-bench` has
linked seats/backrests. None includes this matching backless bench and shared table.
See `reports/duplicate-search.json` for the full pre-build search.

Local tests and screenshots establish only their recorded coverage. Full-mall draw
calls, collision/occupancy planning, physical mobile devices and WebKit are unverified.
No release or deployment is included.
