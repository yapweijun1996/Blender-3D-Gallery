# City kit A — buildings

The seven static GLBs use metres, glTF +Y up and +Z towards the street. Each mesh sits at an identity transform with its origin at the ground-level centre of the supporting footprint. The MRT footprint includes the approach steps. The two shop footprints include their rear floor extensions. Roof overhangs and projecting signs are included in the overall dimensions in [models.json](models.json).

| GLB | Gallery source | Six-view comparison |
| --- | --- | --- |
| [hdb_block.glb](hdb_block.glb) | [HDB Block](../../../models/hdb-block/README.md) | [PNG](comparisons/hdb_block.png) |
| [hdb_void_deck.glb](hdb_void_deck.glb) | [HDB Void Deck](../../../models/hdb-void-deck/README.md) | [PNG](comparisons/hdb_void_deck.png) |
| [hdb_coffee_shop.glb](hdb_coffee_shop.glb) | [HDB Coffee Shop Frontage](../../../models/hdb-coffee-shop-frontage/README.md) | [PNG](comparisons/hdb_coffee_shop.png) |
| [provision_shop.glb](provision_shop.glb) | [HDB Neighbourhood Shopfront](../../../models/hdb-neighbourhood-shopfront/README.md) | [PNG](comparisons/provision_shop.png) |
| [shoplot.glb](shoplot.glb) | [Shoplot Building](../../../models/shoplot-building/README.md) | [PNG](comparisons/shoplot.png) |
| [public_market.glb](public_market.glb) | [Public Market](../../../models/public-market/README.md) | [PNG](comparisons/public_market.png) |
| [mrt_entrance.glb](mrt_entrance.glb) | [MRT Station Entrance](../../../models/mrt-station-entrance/README.md) | [PNG](comparisons/mrt_entrance.png) |

Each sheet shows the original export in rows 1 and 3 and the final GLB in rows 2 and 4. The first row pair shows front, street oblique and right elevations. The second pair shows rear, left and elevated oblique views. Cycles CPU rendered both versions with matched framing and lighting.

The HDB block uses the gallery generator's original dimensions and scale. It consolidates walls through the intervening slab volumes and removes small bevels and concealed faces. The other buildings derive directly from their published GLBs. The reduction preserves the market lettering, roof profile and six stalls, the shopfront fascia and awnings, and the MRT steps and balustrades. Each distinct PBR material forms one primitive.

The void deck adds a wall-mounted notice board and eight mailbox doors. The coffee shop adds two tables and four stools behind the counter, leaving the right-hand entrance clear. The provision shop retains its original glass door in an open position, shifts the display-side jamb 0.34 m, and adds a counter behind the glazing. Both shop modules extend the sill into a small interior floor. The four walk-in assets have shallow 1:8 approach slopes within their floor footprints. The exposed support feet reach the revised floor grade.

## Verification

[qa.json](qa.json) records the reference and final export hashes, render settings, visual findings, and geometry checks. The walkthrough checks sweep measured clear rectangles against final GLB triangles from the frontage into the interior and test floor heights across the measured routes. The void deck has a tested 2.40 m through-route. The market has a 5.80 m main aisle and two tested 1.65 m cross-aisles. The coffee shop has a 1.70 m entry route, and the provision shop has 1.42 m. All tested routes have 1.55 m of vertical clearance. The approach begins on an assumed level surface at the asset's base elevation. An in-game controller and physics session were outside these checks.

## Rebuild

Run from this folder with the repository's installed Node packages, Python 3, and FFmpeg on PATH. The Blender launcher uses the Blender and guard paths supplied for the job. Finish each Blender command before starting the next.

```sh
zsh run-blender.sh build.py
node validate.mjs
python3 check_walkability.py
zsh run-blender.sh render.py
```

The build and capture scripts also accept individual gallery folder IDs. Intermediate captures and machine-readable render and walkability records are written under `.work/`.
