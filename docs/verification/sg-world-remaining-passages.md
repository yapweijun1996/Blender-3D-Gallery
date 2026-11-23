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

Seven ways in this inventory have verified through routes on the ordinary map. Fort Canning Link accounts for two, Raffles Boulevard for three and Temasek Boulevard for two. The remaining 964 ways include 450 with explicit private, destination or permit access, 236 other service roads and 278 other roads. Access tags and road class alone do not establish a driveable passage.

## Raffles Boulevard

The ordinary map includes the one-way Raffles Boulevard passage `479745478` in tile `-1_-4`. Its connected chain is `649944021:0` → `479745478:0` → `479745478:1` → `479745479:0`. The two covered edges span 22.97 m in plan and have five lanes, represented as a 17 m game carriageway. The corridor intersects structure `393090492` along both edges, with the sampled road footprint extending beyond the structure at the portal corners. The raw structure has `layer=1`, `min_height=4.5` and `height=6`. The road has `maxheight=4.5`.

The game uses a level road and footway at Y=0. The source supplies no surveyed portal floor elevations. All three tiles intersecting structure `393090492` use the same 4.5–6 m span. The two north-side footway edges follow one covered walk. Its centerline stays at least 9.09 m from the road center, while the 2.2 m drawn ribbon grazes the edge of the 17 m carriageway. The continuous asphalt surface takes precedence on the shared strip. The connected stairs record levels 0 and 1 with no endpoint elevations. A pedestrian capsule on the first 7.8 m of footway `749001558:4` overlaps the existing Millenia Walk building collider. For this edge, outdoor walkers start at the next mapped vertex, 9.32 m along the line. The original mapped geometry remains in the tile. Small convex panels support both outdoor walkways at Y=0 while retaining the ordinary world ground.

On the default map, the previous build stopped the sedan at the east portal. The corrected road passed a keyboard-driven sedan through both portals. In the physics tests, a bus and four sedans crossed together. Across the five lanes, 1,375 covered samples measured 4.50 m between actual support and soffit within 2 mm. The visible double-decker bus is 4.40 m tall. Two capsules traversed the outdoor paths for 43.88 m and 33.25 m. The closest simulated bus-to-capsule margin was 0.75 m. [Previous east portal](raffles-boulevard/east-portal-before.webp) · [Open east portal](raffles-boulevard/east-portal-open.webp).

Service road `429052425:0` joins between the two covered through edges and leads to a destination-access drive. It stays outside the simulated through route. The mapped left bus lane carries the condition `Mo-Sa 07:30-23:00`. The game conservatively reserves it for simulated buses at all hours. The local extract does not contain turn-restriction relations for establishing legal access.

## Marina Square

Raffles Boulevard ways `545362402` and `545362403` form a 47.39 m, five-lane through route in tile `-2_-4`. Both carry `tunnel=building_passage` and `maxheight=4.5`. They have no measured road elevations, physical clearance or grade in the pinned extract. The Marina Square building `303311927` has `height=0` and no usable height or level count. Its existing retail roof height in the game is 9.6 m.

The simulation uses a level road at Y=0 and a soffit at Y=4.5. The building mesh cuts a 17 m carriageway with a 0.30 m margin on each side. Only its intersection with the mall footprint gets a ceiling and interior walls. The bulk of the mall keeps its existing shell. Customer corridor `474174793` crosses the road 21.71 m from the western tagged portal. Its source specifies level 1 and gives no metric elevation. Both mapped corridor segments share a simulated floor at Y=4.8, 0.30 m above the soffit. A Rapier walker crosses above moving traffic on this floor. Street pedestrians continue to use the outdoor path network.

At the two garage mouths, `1314801325:0` leaves the main road and `1314801304:0` rejoins it. Both are one-way destination-access drives with unknown ramp profiles. Their map records remain available and the simulated through route bypasses both garages. Three connecting edges of 1.57 m, 3.48 m and 2.17 m use their original nodes to carry traffic through the portals. The usual 4 m minimum still applies to other short edges. Six underground garage kerbs project into the through lanes on plan. The renderer suppresses these kerbs where their source and tile records agree on the lower level. As beside Millenia Walk, the game reserves the left lane for buses throughout the day.

At the entrance and exit junctions, three surface side roads meet the carriageway. Their kerbs end at the edge of the through lanes. One bus and four sedans passed together with zero damage. All 1,749 covered probes matched the visible pavement and the collision soffit across the road width. An indoor pedestrian capsule passed over a moving vehicle during the same physics run. The previous build stopped the sedan against the east wall. [Previous east portal](marina-square/previous-east-portal.webp) · [Open west portal](marina-square/west-portal.webp) · [Open east portal](marina-square/east-portal.webp).

## Temasek Boulevard at Suntec City

The northeast and southwest carriageways under Suntec City span 39.81 m and 39.72 m. Each is a two-lane, 6.8 m one-way road. The pinned extract places both inside the same building footprint, `393210509`, with `min_height=5` and `height=20`. The game puts the asphalt at Y=0. The extract supplies no surveyed road elevation and flags the northeast alignment as estimated. The previous game build stopped the sedan against the wall at both entrances.

| Travel direction | Approach → passage → exit | Mapped lane turns |
| --- | --- | --- |
| Northeast | `21702431:4` → `395443687:0` → `750875319:0` | `left;through\|through` |
| Southwest | `21701084:0` → `395443688:0` → `750875316:0` | `left\|left` |

The simulated through traffic stays in its lane to each mapped exit. The service driveway at the northeast exit remains in the map. Its kerbs and those of two adjoining roads stop at the through lanes. The southwest approach retains its mapped toll flag. The game has no toll collection here.

The two outside walks use a 0.55 m outward shift that tapers to zero over the first and last 8 m. The shift clears the modeled buses while preserving the end connections. A character capsule traversed 89.72 m on the northeast side and 95.36 m on the southwest side. Minimum modeled bus clearance was 0.270 m and 0.261 m respectively. The upper customer corridor `460300678:6` crosses both roads. Its source says `indoor=yes`, `level=1` and `layer=-1`. Only the 45.91 m segment supported inside this footprint gets a simulated walking floor, at Y=5.30, using an assumed 0.30 m slab above the mapped soffit.

Across both carriageways, 1,988 sampled positions matched the visible asphalt, physical road support and 5 m soffit. Two buses and two sedans passed in opposite directions with zero damage. All four vehicles had four wheels supported under the roof simultaneously for 276 simulation frames. Keyboard controls and emulated phone touch controls each cleared both exits with zero damage. Browser observations followed individual ambient vehicles from the passages onto their expected exits without changing lanes. [Previous northeast entrance](temasek-boulevard/previous-northeast-entry.webp) · [Open northeast entrance](temasek-boulevard/northeast-entry.webp) · [Open southwest entrance](temasek-boulevard/southwest-entry.webp).

## Ambient traffic access

Ordinary simulated vehicles use roads whose effective motor access is unspecified, `yes`, `designated` or `permissive`. They apply the same rule when spawning and choosing a turn, including reverse travel on a two-way road. A tile reload also invalidates a cached turn when the destination becomes restricted. Mapped geometry still supplies the player’s road surface, minimap, signals, street furniture and mission distance calculations. This simulation uses the access value stored on each road. It does not interpret conditional schedules or grant real-world travel permission.

Across all 830 tiles, the shared road graph contains 11,662 edges. The ambient rule excludes 958 of them, including 57 that otherwise meet the spawn length and road class requirements. Of the 450 passage ways with private, destination or permit access, 24 have segments in the shared graph (27 edges). All 27 previously allowed ambient traffic. All 27 are now excluded from ambient route selection. A deterministic game test also checks an approach with both a public exit and a destination-access driveway, where the old vehicle turned into the driveway.

| Effective access outside the ambient policy | Edges in the shared graph | Otherwise meet the spawn criteria |
| --- | ---: | ---: |
| Private | 855 | 47 |
| Destination | 82 | 2 |
| Permit | 19 | 7 |
| Customers | 1 | 0 |
| Restricted | 1 | 1 |

## Next assessments

Raffles Link `532351088:0` is a 6.46 m one-way building passage in tile `-3_-4`. Its exit connects to a 2.41 m section of the same street. Building `620812487` has no mapped height or soffit. Indoor pedestrian bridge `460302684:0` crosses above the road on mapped level 1, also without a metric elevation. The ordinary map still has a solid wall. In a local prototype, a 4.0 m wide opening and an assumed 4.5 m soffit let a sedan, bus and lorry pass without damage. Keeping the sides solid and supporting the upper pedestrian bridge remain acceptance criteria for a release.

Kirk Terrace `1343676204:0` straddles two tiles and connects to a mapped private road at one end. These two cases need separate geometry and access decisions.

Defer Kheam Hock Road `659688751:0`. Its two-way 40.32 m tunnel links `97408974:0` and `659688752:0` in tile `-19_-21`, and its source also carries `maxheight=4.5`. The current game meshes for the two Pan-Island Expressway crossings, `159090940:0` and `627656467:0`, put the rendered underside at about Y = −0.90 m at both centerline intersections. Their two-vertex profiles sample the bridge ramps at the ends of the 26.60 m and 27.13 m edges. A verified or explicitly simulated pair of upper-deck and lower-road profiles is needed before using this corridor.

## Reproduce the count

Run from the repository root when the original local extract is present.

```sh
node --input-type=module - output/osm/combined.json <<'NODE'
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { buildTileFiles } from './scripts/world/build-tiles.mjs';
import { allowsAmbientTraffic, buildTrafficGraph } from './src/world/traffic.js';

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
const tiles = index.tiles.map(({ file }) => JSON.parse(files.get(file)));
const edgeWays = new Map();
for (const tile of tiles) {
  for (const road of tile.roads) edgeWays.set(road.id, road.wayId);
  for (const road of tile.roads) ways.set(road.wayId, road);
}
assert.equal(ways.size, 9762);
const counts = new Map();
const verified = new Set([719635729, 159677768, 479745478, 545362402, 545362403, 395443687, 395443688]);
const restricted = new Set();
let service = 0, other = 0;
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
  if (verified.has(id)) continue;
  if (['private', 'destination', 'permit'].includes(access)) restricted.add(id);
  else if (road.class === 'service') service++;
  else other++;
}
console.table(Object.fromEntries(counts));
const graph = buildTrafficGraph(tiles);
const allEdges = [...graph.edges.values()];
const passageEdges = allEdges.filter(edge => restricted.has(edgeWays.get(edge.id)));
const excluded = allEdges.filter(edge => !allowsAmbientTraffic(edge));
const spawnClassAndLength = edge => edge.length > 25 && edge.class !== 'service' && edge.class !== 'footway';
const wayCount = list => new Set(list.map(edge => edgeWays.get(edge.id))).size;
console.log({ restricted: restricted.size, service, other, sharedEdges: allEdges.length,
  excluded: excluded.length, otherwiseSpawnEligible: excluded.filter(spawnClassAndLength).length,
  restrictedPassageWaysInGraph: wayCount(passageEdges), restrictedPassageEdgesInGraph: passageEdges.length,
  ambientEligibleRestrictedPassageEdges: passageEdges.filter(allowsAmbientTraffic).length });
NODE
```
