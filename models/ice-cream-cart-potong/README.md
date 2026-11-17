# Potong Ice-Cream Cart

Original brand-neutral three-wheel Singapore-style push cart for store S03.
The P1 envelope takes precedence: approximately 1.4 m wide × 0.8 m deep ×
1.8 m high, including the narrow oval umbrella. Closed insulated cabinet,
closed service flap, three open flavour tubs, handlebar, thumb bell, three
rounded ice bars with plain wood sticks and two layered wafer sandwiches.
No lettering, logos or external assets.

Original asset; reuse in the owner's projects is authorized.

Public redistribution terms have not been specified.

## Rebuild and saved-source export

From this directory:

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python generate.py
/opt/homebrew/bin/blender --background --python-exit-code 1 --python generate.py -- --export-source --skip-render
node validate.mjs
```

The lightweight gallery thumbnail is derived from the hero render with macOS:

```sh
sips -Z 512 -s format jpeg -s formatOptions 87 previews/hero.png --out previews/hero.jpg
```

From the repository root, run `npm run validate:assets`, `npm test`,
`npm run build`, then `node models/ice-cream-cart-potong/check-browser.mjs`.
Use `inspect_sources.py` with Blender and `node validate.mjs --source-edit`
to independently test a saved temporary edit without altering the delivered source.

Blender 5.2.3. Deterministic geometry and palette; no downloaded assets or textures.
Source objects remain named and editable; export evaluates and merges copies.
The second command preserves saved source edits. Metres; origin at floor centre;
Blender +Z up / -Y front becomes glTF +Y up / +Z front.

`FLAVOUR_ThreeTubs` is an independent visual node for downstream Inspect focus.
`SERVICE_Flap` has a lower-edge hinge origin; it is delivered closed and static.
There are no animation clips or new gallery controls. Two shared materials use
vertex colours. Five visible mesh nodes / six visual primitives fit the P1 draw
budget with the gallery's existing single-pass lighting.

`collider_box` has no material and is hidden in the Blender source. Since core
glTF has no visibility flag, its mesh is stored in the inactive second scene
`COLLISION_ONLY_NotVisible`; default scene loading never renders it. Consumers
can use the root's `collision_scene` extra to obtain the blocking box. The
collider covers the lower cart and handle; overhead canopy is not a floor blocker.

Similar existing assets: `cendol-dessert-cart` has a fixed roof, four wheels and
dessert bowls; `mall-retail-pop-up-cart` is a generic four-caster retail fixture.
Neither provides this object and feature set. Concept board: NOT FOUND at
`docs/references/gjh-mall-concept-board.png` on creation.

Measured export evidence: `reports/assets.json`; format: `reports/khronos.json`;
browser checks and source inspection are recorded under `reports/`.

## Advisor round 1

Replaced the stacked tub plates with continuous hollow containers: tapered
outer walls, rolled rims, inner walls and a floor. Each tub is 118 mm high;
the three coloured frozen surfaces sit 40 mm below the rim. The independent
`FLAVOUR_ThreeTubs` node is preserved. Tray bars are elongated and rounded,
with simple wood sticks; bars and sticks rest on the liner at 0.945 m without
the previous 2 mm gap. The adjacent wafer layers are preserved.

Measured GLB: 6,468 triangles (6,456 visible + 12 collider), 428,400 bytes,
10,560 visible vertices, two materials, no textures, five visible mesh nodes
and six visual primitives. Envelope remains 1.400 × 0.800 × 1.800 m (W/D/H).
Gallery vertex totals include the collider's additional 24 vertices.
`reports/reproducibility.json` records byte-identical GLB checks for a fresh
procedural rebuild and re-export from the saved Blender source.
