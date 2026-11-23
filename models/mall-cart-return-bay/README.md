# Mall Cart Return Bay

A two-place return corral for the supermarket representative. The feet occupy 1.60 × 1.10 m, with the origin beneath the footprint centre. In glTF, +Y is up and the open mouths face +Z. The side rails rise to 0.820 m and the raised cart symbols reach 1.201 m. Six chamfered anchor plates sit directly on the finished floor. A lower centre rail separates the parking places and a rear stop limits insertion. The two entrances are flush with the floor.

Park the project's original shopping carts at local X = −0.37 and +0.37 m, Z = 0, turned 180° so the handles face the aisle. The two unscaled carts sit 160 mm apart. Either cart can translate 1.15 m toward the aisle and return while its neighbour stays parked. The shop displays the parked pose. Visitor controls inspect the bay and walk around it.

LOD0 retains rounded bends, sockets, bumpers, paired anchor heads, guide ferrules, raised trolley pictograms and rivets. LOD1 drops ferrules and rivets and reduces the sweep profiles. LOD2 preserves the footprints, rail silhouettes, clearance and signboards with simplified return markings. Export batches each fixed region separately so the rails retain their open space.

## Reproduction

Use Blender 5.1.2 with the repository dependencies. Run these commands from the repository root.

```sh
blender --background --python-exit-code 1 --python models/mall-cart-return-bay/generate.py -- --export-source --skip-render
blender --background models/mall-cart-return-bay/sources/mall-cart-return-bay.blend --python-exit-code 1 --python models/mall-cart-return-bay/inspect_source.py
node models/mall-cart-return-bay/verify.mjs
node --test tests/mall-supermarket-shop.test.mjs
```

Use `--rebuild` to recreate the native source from the generator. Omit `--skip-render` to render the JPEG studio view. The saved source contains a named collection for each level, editable rail profiles and individual fittings. The two export modes reproduce the same three GLBs. See [asset verification](reports/geometry.json), [reproducibility](reports/reproducibility.json) and [rights](LICENSE.md).
