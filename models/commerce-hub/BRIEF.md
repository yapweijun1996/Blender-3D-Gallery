# Commerce hub: style samples (centre bags and shop)

Build two modules of a seven-module isometric scene so the owner can approve the style.
The attached images are the visual anchors: the full scene, the bags module and the shop module.

## Rules

- Model with local `bpy` only, through the `blender` MCP server (`execute_blender_code`). No AI meshes,
  no downloaded assets, no RunPod, no network access.
- Check `get_blendfile_summary_path_info` before the first change; never overwrite someone's saved file.
- The script files are the source of truth. Run them inside Blender with
  `exec(compile(open(path).read(), path, "exec"))`; do not model by hand in the session.
- Do not commit, push, or edit anything outside `models/commerce-hub/`.

## Layout

```
models/commerce-hub/
  source/common.py        shared units, palette, materials, plinth, camera, lights, export, metrics
  source/build_bags.py    centre module
  source/build_shop.py    shop module
  blend/<module>.blend
  exports/<module>.glb
  renders/<module>.png    1536x1024, framed like the matching anchor
  reports/<module>.json   triangles, bytes, materials, primitives, bounding box, validator-relevant notes
```

## Contract

- 1 Blender unit = 1 m of the miniature scene. Both modules use the same plinth helper: rounded-square
  sage outer slab plus a thinner light-grey inner slab, so all seven modules can be composed later.
- Origin at the plinth base centre, +Z up, front of the module matching the anchor's camera.
- Stable, descriptive object names for animation (for example `Plinth_Outer`, `Plinth_Inner`,
  `GlowRing`, `Bag_Large`, `Bag_Medium`, `Bag_Small`, `Shop_Glass`, `Shop_Door`).
- Principled BSDF only, nothing that is lost in glTF export. Glow uses emission. Glass uses simple
  alpha blending or transmission that survives export. Avoid image textures; the "POMELO STORE" sign
  and orange-slice logo are geometry.
- Palette to start from: sage `#8DB67E`, inner grey `#E6DEDA`, bag cream-orange `#F9C46B`,
  bag inside `#F29A2E`, backdrop `#F8F0E7`. Correct them by eye against the anchors.
- Budgets (hard): bags <= 15,000 triangles and <= 500 KB GLB; shop <= 30,000 triangles and <= 1 MB GLB.
  Merge static meshes by material where it does not cost a named animation part; keep each module
  at or below 20 primitives (bags) and 40 primitives (shop).
- The GLB contains only the model: no camera, lights or backdrop.
- Render with EEVEE, a long-lens or orthographic isometric camera, soft key and fill light, soft
  contact shadow on a cream backdrop.

## Done

Both modules exported and rendered, reports written, budgets met. Compare each render with its anchor,
fix the largest differences (at most three rounds), then report remaining differences honestly.
