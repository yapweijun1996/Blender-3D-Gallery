# Restaurant Food Props

Original, unbranded procedural restaurant prop set for the GJH Virtual Mall.
Ten named service meshes plus a 1.0 x 0.6 metre tray: noodles with chopsticks,
rice plate, soup, three pleated dumplings in a basket, a plate of two triangular
sandwich halves, two cups with bent straws, salad, pastry and sauce ramekin.
The sandwich has sliced bread and vegetables; no burger or product packaging.

Metres; origin at tray underside centre; Blender +Z up / -Y front, exported
as glTF +Y up / +Z front. The tray is placed at floor datum for reuse on a
separate counter. Each dish has a floor-contact pivot, can be moved independently,
and contains intentionally intersecting food layers as disconnected closed solids.
One shared opaque material uses the `Color` corner attribute as vertex colour.
No textures, text, fonts, external resources, animations or runtime interaction code.

Rebuild from this directory with Blender 5.2.3 LTS:

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python generate.py
```

This deterministically replaces the source, GLB and four studio previews. Seed:
`73129`. Use `-- --skip-render` for geometry only. Preserve manual source edits
by appending `-- --export-source`, which opens the saved `.blend`, exports its
current geometry, and renders it without rebuilding.

Run the asset gates from the repository root:

```sh
node models/restaurant-food-props/validate.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/restaurant-food-props/inspect_sources.py
node models/restaurant-food-props/validate.mjs models/restaurant-food-props/reports/source-edit/edited.glb
npm run validate:assets
npm test
npm run build
node models/restaurant-food-props/browser-check.mjs
```

`reports/` records measured geometry, Khronos validation, source reopening and
actual saved mesh/material edit re-export, standalone rebuild byte identity,
duplicate search, visual review, and browser evidence. The page screenshot and
repository check logs are delivered to `~/Documents/MallQueue/reports/`.

Status remains draft for manager review. No restaurant mini-game behavior,
complete mall scene/frame-rate budget, physical Android/iOS, WebKit or deployment
is verified. Original asset; owner-project reuse is authorized. Public
redistribution terms are unspecified; see LICENSE.md.
