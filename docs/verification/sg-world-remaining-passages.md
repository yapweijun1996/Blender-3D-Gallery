# Singapore Open World road passages

The 830 tracked road tiles contain 9,762 distinct road ways. The local corridor extract `output/osm/combined.json` regenerated all 830 tiles and `index.json` byte for byte. Its SHA-256 is `67b10fcde8967394ceb29e30e89c7ae587848bf2e4c4f34329d9e92fd87953fe`. The extract carries the original `tunnel` and `covered` tags, which the tile format reduces to the `tunnel` flag or omits.

## Inventory

Each OSM `wayId` counts once across all edges and tiles. A true tile `tunnel` flag takes priority and its raw tag determines the row. The next row includes non-tunnel ways tagged `covered=yes`. The last row includes all remaining ways with a negative tile layer. The access column values come from the tile builder's `motorcar`, `motor_vehicle`, `vehicle`, then `access` precedence. An absent tag supplies no access determination.

| Type | Ways | Access absent | Destination | Designated | Private | Permit | Permissive | Yes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `tunnel=yes` | 498 | 83 | 348 | 2 | 60 | 4 | 1 | 0 |
| `tunnel=building_passage` | 309 | 119 | 1 | 176 | 9 | 4 | 0 | 0 |
| `tunnel=covered` | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| `covered=yes`, non-tunnel | 101 | 83 | 2 | 1 | 13 | 0 | 1 | 1 |
| Negative layer only | 60 | 51 | 0 | 0 | 9 | 0 | 0 | 0 |
| **Total** | **971** | **339** | **351** | **179** | **91** | **8** | **2** | **1** |

The `tunnel=yes` count includes the two tagged Fort Canning Link ways already integrated, `719635729` and `159677768`. The first inventory left 969 ways after Fort Canning Link. The Raffles Boulevard passage below accounts for one more, leaving 968 ways for assessment. These rows identify map records for review. Each road still needs its own access and geometry assessment.

## Raffles Boulevard

The ordinary map includes the one-way Raffles Boulevard passage `479745478` in tile `-1_-4`. Its connected chain is `649944021:0` → `479745478:0` → `479745478:1` → `479745479:0`. The two covered edges span 22.97 m in plan and have five lanes, represented as a 17 m game carriageway. The corridor intersects structure `393090492` along both edges, with the sampled road footprint extending beyond the structure at the portal corners. The raw structure has `layer=1`, `min_height=4.5` and `height=6`. The road has `maxheight=4.5`.

The game uses a level road and footway at Y=0. The source supplies no surveyed portal floor elevations. All three tiles intersecting structure `393090492` use the same 4.5–6 m span. The two north-side footway edges follow one covered walk. Its centerline stays at least 9.09 m from the road center, while the 2.2 m drawn ribbon grazes the edge of the 17 m carriageway. The continuous asphalt surface takes precedence on the shared strip. The connected stairs record levels 0 and 1 with no endpoint elevations. A pedestrian capsule on the first 7.8 m of footway `749001558:4` overlaps the existing Millenia Walk building collider. For this edge, outdoor walkers start at the next mapped vertex, 9.32 m along the line. The original mapped geometry remains in the tile. Small convex panels support both outdoor walkways at Y=0 while retaining the ordinary world ground.

On the default map, the previous build stopped the sedan at the east portal. The corrected road passed a keyboard-driven sedan through both portals. In the physics tests, a bus and four sedans crossed together. Across the five lanes, 1,375 covered samples measured 4.50 m between actual support and soffit within 2 mm. The visible double-decker bus is 4.40 m tall. Two capsules traversed the outdoor paths for 43.88 m and 33.25 m. The closest simulated bus-to-capsule margin was 0.75 m. [Previous east portal](raffles-boulevard/east-portal-before.webp) · [Open east portal](raffles-boulevard/east-portal-open.webp).

Service road `429052425:0` joins between the two covered through edges and leads to a destination-access drive. It stays outside the simulated through route. The mapped left bus lane carries the condition `Mo-Sa 07:30-23:00`. The game conservatively reserves it for simulated buses at all hours. The local extract does not contain turn-restriction relations for establishing legal access.

A separate Raffles Boulevard section `545362402` and `545362403` spans 47.39 m in plan, overlaps Marina Square `303311927`, and runs past destination-access driveways `1314801325:0` and `1314801304:0`. Its overlapping structure has no `min_height` tag.

Defer Kheam Hock Road `659688751:0`. Its two-way 40.32 m tunnel links `97408974:0` and `659688752:0` in tile `-19_-21`, and its source also carries `maxheight=4.5`. The current game meshes for the two Pan-Island Expressway crossings, `159090940:0` and `627656467:0`, put the rendered underside at about Y = −0.90 m at both centerline intersections. Their two-vertex profiles sample the bridge ramps at the ends of the 26.60 m and 27.13 m edges. A verified or explicitly simulated pair of upper-deck and lower-road profiles is needed before using this corridor.

## Reproduce the count

Run from the repository root when the original local extract is present.

```sh
node --input-type=module - output/osm/combined.json <<'NODE'
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { buildTileFiles } from './scripts/world/build-tiles.mjs';

const bytes = readFileSync(process.argv[2]);
assert.equal(createHash('sha256').update(bytes).digest('hex'),
  '67b10fcde8967394ceb29e30e89c7ae587848bf2e4c4f34329d9e92fd87953fe');
const source = JSON.parse(bytes);
const tags = new Map(source.elements.filter(element => element.type === 'way')
  .map(way => [way.id, way.tags]));
const { files, index } = buildTileFiles(source);
assert.equal(index.tiles.length, 830);
for (const [file, contents] of files) {
  assert.equal(contents, readFileSync(`models/world/tiles/${file}`, 'utf8'), file);
}

const ways = new Map();
for (const { file } of index.tiles) {
  const tile = JSON.parse(files.get(file));
  for (const road of tile.roads) ways.set(road.wayId, road);
}
assert.equal(ways.size, 9762);
const counts = new Map();
for (const [id, road] of ways) {
  const raw = tags.get(id);
  assert.ok(raw, `missing source tags for ${id}`);
  let type;
  if (road.tunnel) type = `tunnel=${raw.tunnel}`;
  else if (raw.covered === 'yes') type = 'covered=yes, non-tunnel';
  else if (road.layer < 0) type = 'negative layer only';
  else continue;
  const row = counts.get(type) ?? { ways: 0 };
  const access = road.access ?? 'absent';
  row.ways++;
  row[access] = (row[access] ?? 0) + 1;
  counts.set(type, row);
}
console.table(Object.fromEntries(counts));
NODE
```
