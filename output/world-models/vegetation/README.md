# Singapore street vegetation kit

Fifteen game-scale assets for Singapore streets, verges and paved public spaces. Each plant represents a plausible specimen at the dimensions in `models.json`. The streetscape fixtures represent generic cast-concrete and cast-metal designs. The rain tree is 14 m high with an 18 m crown along glTF X. The hedge has a 2 m repeat length, and the flower bed has a 2 × 1 m footprint.

| File | Features modelled |
| --- | --- |
| `rain_tree.glb` | Low, wide umbrella of compound foliage, stiff spreading limbs above a stout fork, and a broad-rooted dark trunk. [NParks rain tree](https://www.nparks.gov.sg/florafaunaweb/flora/3/1/3106) |
| `angsana.glb` | Taller dome, outer foliage that droops from raised branches, plank-like buttresses and grey-brown bark. The specimen is in its green phase. [NParks angsana](https://www.nparks.gov.sg/florafaunaweb/flora/3/0/3093) |
| `tembusu.glb` | Irregular, tiered dark-green crown, flared root base and tall dark trunk with a lower lateral branch. [NParks tembusu](https://www.nparks.gov.sg/florafaunaweb/flora/2/8/2895) |
| `royal_palm.glb` | Upright smooth grey trunk with a subtle mid-trunk bulge, green crownshaft and fountain of bright pinnate fronds. [NParks royal palm](https://www.nparks.gov.sg/florafaunaweb/flora/2/6/2682) |
| `coconut_palm.glb` | Curved, ring-scarred trunk, longer and more pendulous fronds, and green fruit beneath the crown. [NParks coconut palm](https://www.nparks.gov.sg/florafaunaweb/flora/5/6/5618) |
| `bottle_palm.glb` | Swollen grey base, sharply narrowing neck, short green crownshaft and sparse rising fronds. [NParks bottle palm](https://www.nparks.gov.sg/florafaunaweb/flora/2/6/2631) |
| `frangipani.glb` | Open, thick-forked frame with long leaves at branch ends and white five-petalled flowers with yellow throats at LOD0. [NParks frangipani](https://www.nparks.gov.sg/florafaunaweb/flora/3/0/3074) |
| `bougainvillea.glb` | Mounded, arching shrub with clusters of three papery magenta bracts and small pale flower centres. [NParks bougainvillea](https://biodiversitysg.nparks.gov.sg/our-biodiversity/flowering-plants/shrubs-herbaceous-plants/bougainvillea-cultivars/) |
| `heliconia.glb` | Broad blades on leafy stems with upright, alternating orange and gold bracts based on ‘Alan Carle’. [NParks heliconia](https://www.nparks.gov.sg/florafaunaweb/flora/4/2/4275) |
| `ginger.glb` | Red ginger clump with upright leafy stems, lanceolate blades and red overlapping terminal bracts. [NParks red ginger](https://www.nparks.gov.sg/florafaunaweb/flora/1/6/1645) |
| `hedge_2m.glb` | Clipped hedge with eased shoulders and occasional bronze new growth based on brush cherry. [NParks brush cherry](https://www.nparks.gov.sg/florafaunaweb/flora/3/1/3157) |
| `grass_tuft.glb` | Radiating cluster of individually curved grass blades for verge edges. |
| `flower_bed.glb` | Mixed yellow, pink, coral and pale flowers, visible soil and jointed stone edging. |
| `planter_box.glb` | Tapered precast shell with a recessed plinth, chamfered corners, coping and recessed planting soil. Drain details face both long sides. |
| `tree_pit.glb` | Flush square cast-metal surround with an octagonal trunk opening, 32 radial grate bars with open slots at LOD0 and exposed soil. |

## Game integration

- The GLBs use metres and Y-up. +Z faces forward. Both LOD root pivots are at the planting or fixture centre on the ground. Tree canopies can overhang that pivot.
- Load the `lod0` or `lod1` node subtree and display one level at a time. A generic glTF viewer displays both unless the application selects a level. The roots carry a numeric `lod_level` extra. Named child meshes keep crowns, trunks and other useful parts separately addressable.
- The material slots use the kit’s exact names. Opaque glTF vertex colours (`COLOR_0`) carry bark, foliage and flower colour variation. The game can tint them through the material base colour. The GLBs contain no images, animation, skin, camera or light.

## Rebuild and review

`build.py` is the editable procedural source. Run it from the repository root with the supplied Blender 5.1.2 executable and guard. `all` builds and renders, `build` exports, and `render` imports the current GLBs and renders them. Append asset stems after the mode to select individual models.

```sh
DYLD_INSERT_LIBRARIES="$BLENDER_GUARD" "$BLENDER" -b -noaudio -t 2 \
  --python-exit-code 1 --python output/world-models/vegetation/build.py -- all
node output/world-models/vegetation/validate.cjs
```

The 15 PNGs in `review/` use Cycles CPU with two threads. Each cell shows LOD0 on the left and LOD1 on the right at equal scale. Read left to right across the first row for front, right and back, then across the second for left, top and front three-quarter. The four side elevations use a slight downward angle so the low modules show their front edges.

`models.json` records triangle counts, bounds, size, part names, used materials, file sizes, SHA-256 digests and the result from the repository’s Khronos glTF validator. The validator also independently checks geometry, opaque materials, both LOD trees, file size and the 20% triangle ratio.

The final six-view sheets were inspected by the builder and an independent reviewer. Revisions connected loose foliage and flowers, filled gaps in the rain tree and tembusu crowns, improved palm frond coverage in elevation and narrowed the grate slots. Close views show the geometric simplification used to meet the triangle budgets.
