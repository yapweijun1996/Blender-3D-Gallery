# Gardens by the Bay conservatories

The GLBs are self-contained game meshes built with Blender 5.1.2. Coordinates are in metres. X follows the long axis, +Y is up, +Z faces the entrance, and the origin is at the centre of the base on the ground.

| Asset | Length × depth × height | Modelled features |
| --- | --- | --- |
| `flower_dome.glb` | 130 × 100 × 38 m | Low, asymmetrical oval shell, diagonal glazing lattice, pale external fan ribs and spine, low stone plinth, entrance glazing under a slim canopy, and simplified planting beds, flower rows, and trees. |
| `cloud_forest.glb` | 100 × 80 × 58 m | Steep, skewed oval shell, radial ribs, diagonal tinted glazing, low stone plinth, and an entrance canopy. The 35 m `Cloud Mountain` is independently loadable. It has a layered rock core and bands of planting, with separate meshes for the waterfall and pool, elevated walks, and foothills. |

The dimensions follow the supplied envelope targets. The shell curves, rib spacing, canopy details, and the interior landscaping are visual approximations. The exterior geometry follows the architect's gridshell and external rib system. The planting and raised walks follow the Gardens' visitor references. [WilkinsonEyre project and drawings](https://wilkinsoneyre.com/projects/cooled-conservatories-gardens-by-the-bay), [Arup façade description](https://arup.newsweaver.com/ClientUpdateflyer/w885f0o204d), [Gardens by the Bay visitor brochure](https://www.gardensbythebay.com.sg/content/dam/gbb-2021/documents/venues/eBrochure_16092025.pdf).

Each named part is a top-level mesh. Glass uses alpha-blended PBR and several vertex tints for visibility into the domes. Foliage and water use vertex tints as well. All materials use the supplied naming palette. There are zero textures.

## Review and rebuild

`models.json` records measured glTF bounds, material and part names, triangle and byte counts, validator results, and hashes linking the final GLBs to their contact sheets. Each sheet was rendered by re-importing the GLB in Blender 5.1.2 and using Cycles CPU with two threads. Read the panels left to right. The top row is front, right, and rear. The bottom row is front three-quarter, rear three-quarter, and top.

With the supplied Blender launcher and accompanying `DYLD_INSERT_LIBRARIES` setting, run the following from this directory. `build` and `render` can also be run individually in place of `all`.

```sh
"$BLENDER" -b -noaudio -t 2 --python-exit-code 1 --python build_models.py -- all
node validate_models.mjs
```
