# Provision Shop Pulley Tin Display

Original static Singapore heritage-inspired display, not a replica of a photographed shop or surviving artefact. Two plainly finished, empty repurposed tins hang at separate heights from a single continuous cord. Both lips are physically open, both wire bails are seated through external eyes, and the overhead grooved metal sheave has an actual through-axle on a short section of timber. The dark stand and base are fictional exhibition structure, not historical shop furniture. The model has no operation, brand, money, transactions, security or storage instructions.

- [National Heritage Board, Traditional Provision Shops](https://www.roots.gov.sg/-/media/Roots/Images/resources/e-books/nhb_ebook_traditional_provision_shops.pdf), introductory section and example image, for historical Singapore use of pulley tins in older provision shops.
- [National Library Board's BiblioAsia, My Childhood Memories: A Slice of Kampong Life](https://biblioasia.nlb.gov.sg/all-sections/places-and-buildings-2023-11-childhood-memories-kampong-wak-hassan/), first-hand account of two reused tins suspended from a simple pulley in a provision shop. Nothing here copies a named label or shop.

## Reproduce and verify

Use Blender 4.3.2. Blender is +Z up/-Y front; GLB is +Y up/+Z front. The static mesh has no external media.

```sh
blender -b --python-exit-code 4 --python generate.py -- --output ./generated
blender -b --python-exit-code 5 --python verify_blender.py -- ./generated
node verify.mjs ./generated/exports/provision-shop-pulley-tin-display.glb
```

Use `--skip-render` when you only need the editable source and GLB. The verification scripts check geometry, not the performance of a real fixture.
