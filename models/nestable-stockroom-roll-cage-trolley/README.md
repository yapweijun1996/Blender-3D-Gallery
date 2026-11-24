# Nestable Stockroom Roll-Cage Trolley

An original Singapore retail-stockroom-inspired display with two instances of the **same** empty cargo cage shown already nested. Tapered open bases partly share a footprint; the two sets of casters remain individually visible and supported. The real lattice, lower deck pivots, and upper connections holding each raised deck are separately editable. No actual loading, handling, claimed capacity, safety classification, named store, or product replica is depicted.

The Blender model uses linked mesh data for the nested repeat while keeping its complete hierarchy editable. The GLB likewise shares identical geometry between the two instances. Blender +Z is up; GLB +Y is up and +Z front. There is no animation or external media.

## Context

- [TUKU Singapore, Nestable Roll Cage](https://tuku-singapore.com/sku/products/nestable-roll-cage), for the regional retail-stockroom fixture type.
- [Verdex, Nesting Roll Cage Trolley](https://www.verdex.com.au/media/product-attachments/nesting-roll-cage-trolley-v1760.pdf), first-party documentation of the general nesting type and folded panels and deck concept. The model uses original proportions, hardware, and styling, and does not represent that product.
- [Logistica Paggiola, A-frame Nestable Roll Cage](https://www.paggiola.com/en/product/roll-compenetrabile-ad-a/), independent source for the tapered nesting concept only.

## Reproduce and verify

From this directory in Blender 4.3.2:

```sh
blender -b --python-exit-code 4 --python generate.py -- --output ./generated
blender -b --python-exit-code 5 --python verify_blender.py -- ./generated
node verify.mjs ./generated/exports/nestable-stockroom-roll-cage-trolley.glb
```

Use `--skip-render` for the editable Blender file and static GLB only.
