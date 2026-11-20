# Singapore world tiles

The offline builder uses Node.js and reads the Overpass `out geom` extract at
`output/osm/marina_bay.json`. OpenStreetMap contributors provide the source data
under the ODbL. The tile index carries the attribution for downstream display.

```sh
node --test scripts/world/world-network.test.mjs
node scripts/world/build-tiles.mjs --output /tmp/marina-bay-tiles
```

Omit `--output` to write to `models/world/tiles/`. Use `--input` to select
a different extract with the same shape. The builder checks all serialized tiles
against the 120,000-byte limit before writing. Read the tile list from
`index.json`, which the builder writes last.

## Road graph

`buildRoadGraph(osm)` returns vehicle `nodes`, `edges` and `junctions`, plus
`pedestrian.nodes`, `pedestrian.edges` and `pedestrian.crossings`. Shared OSM
node IDs and explicitly tagged crossings and signals determine edge breaks.
An intersection seen only in the flat projection does not create a connection.
Bridge, tunnel and layer information remains available on each road edge.
Private and designated access tags remain on the edge for routing policy.
Roads that explicitly forbid cars are excluded. The source extract contains
ways and nodes, with no turn-restriction or multipolygon relations.

Road geometry uses `[x, z]` in local metres, east and south respectively.
Each edge goes from `from` to `to`; reverse travel is allowed if `oneway` is
false. OSM `oneway=-1` reverses the edge geometry. The 0.5 m simplification
keeps graph endpoints. Lane paths run in travel order at 3.4 m spacing.
One-way carriageways use the full centred width. Two-way roads place opposing
traffic on the left side of their dividing line. Tagged centre lanes use
`direction: "both"`, and a single shared lane has coincident paths in each
direction. Lane paths describe the individual edge, so a route planner still
needs to choose turns between those paths.

## Tile format

Each tile spans 250 m on both axes. Multiply its signed `x` and `z` indices by
250 to recover the world-space origin. The arrays hold clipped line and
polygon fragments and point features. Add the origin to any local `geometry`
or `point` coordinate to recover its projected position. Coordinates are
stored in metres and rounded to centimetres. A point feature belongs to one
tile; a line or polygon can use the same feature ID across several tiles.

The `roads` array carries carriageway attributes, topology IDs and centreline
fragments. Lane centre-lines are available from the graph builder. `kerbs`
hold the outer edges of each carriageway. `junctions` include closed patch
rings, with the anchor point stored once in its owning tile. Both the patch
and its anchor carry the signal flag. Pedestrian ways and crossings are
separate arrays. Individual crossings can be point markers or walkable line
segments. Building heights use a positive tagged height, then tagged levels
at 3.2 m per level, then a class default. The street-lamp layer stays empty
where the extract contains no mapped lamps.
