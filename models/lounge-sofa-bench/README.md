# Lounge Sofa, Bench and Slim Table

Original brand-neutral mall rest-area furniture in the existing **Mall Fixtures** category.
Rounded greige three-seat sofa, matching backless bench, slim warm-toned shared table,
upholstery welts and recessed graphite supports. No external assets or textures.

The open L arrangement occupies a measured 3 × 2.2 m furniture envelope. The sofa is
2 × .85 × .8 m, the bench 1.6 × .38 × .45 m, and the table .85 × .22 × .5 m
(local width × depth × height; the bench and table are rotated 90° in plan).
Advisor round 1 deliberately expands the original 3 × 1.5 m target by .7 m in depth:
keeping the full-size bench perpendicular opens the front of all three sofa seats.
Measured projected strips provide .6 m of legroom and an open forward exit for every
sofa seat, plus .5 m on the bench's inward use side. The table's long edge serves both
bench pads; its upper end is .388 m from the right sofa seat's front centre in plan.
The other sofa seats have open legroom, but do not each have a table within reach.
These are geometric design allowances, not occupied ergonomics or accessibility
certification. Mall circulation must be planned separately.

The full-height upholstered arms overlap a narrower base on their inner faces;
the outer sides no longer share coplanar base faces that formed a dark slit. The
graphite underframe is inset beneath the fabric. Front, side, both oblique directions
and top previews document the layout and continuous outer arm sides.

Blender +Z up, front -Y; exported glTF +Y up, front +Z. Origin is the combined floor
centre. Source contains separately editable sofa, bench and table parts. Export uses
three evaluated material batches, giving three opaque mesh primitives. Studio floor,
lights and camera are excluded. Static geometry only; no sitting logic or animation.
The card uses a lightweight 512 px WebP derived from the 900 px hero PNG; preview
conversion uses the verified `/usr/bin/python3` Pillow installation.

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/lounge-sofa-bench/generate.py
# Export saved source edits without procedural rebuilding:
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/lounge-sofa-bench/generate.py -- --export-source --skip-render
node models/lounge-sofa-bench/validate.mjs
python3 models/lounge-sofa-bench/check_rebuild.py
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/lounge-sofa-bench/inspect_sources.py
npm run validate:assets
npm test
npm run build
node models/lounge-sofa-bench/check-browser.mjs
```

`validate.mjs` adapts the self-checkout-machine quality gate for this static group,
checks Khronos format validation, budgets, finite nondegenerate geometry, three
materials/primitives, source features, dimensions and floor-centred bounds. Evaluated
source bounds also check each seat's legroom strip, forward sofa exits, inner table
placement and shared reach. `check_rebuild.py` compares an isolated rebuild byte for
byte and matches the evaluated source measurements.
`inspect_sources.py` reopens the native source and checks a saved edited copy independently.

Similar existing models: `gjh-lounge-bench` has a framed upholstered bench with arms
and back; `living-room-sofa` is a standalone sofa; `public-service-waiting-bench` has
linked seats/backrests. None includes this matching backless bench and shared table.
See `reports/duplicate-search.json` for the full pre-build search.

Measured export: 12,972 triangles, 6,962 vertices, 247,964 bytes, three opaque
meshes/primitives/materials, no textures or animations. Khronos validation has zero
errors and warnings; full command results are in `reports/checks.json`.

Local tests and screenshots establish only their recorded coverage. Full-mall draw
calls, collision/occupancy planning, physical mobile devices and WebKit are unverified.
No release or deployment is included.
