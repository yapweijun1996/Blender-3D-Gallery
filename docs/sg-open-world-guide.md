# Singapore open world: guide

Pages: `?page=sg-world` (drive from Marina Bay Sands to Johor Bahru on the real map) and `?page=sg-mrt` (a train arriving at a platform).
Plan and per-milestone status: [sg-open-world-plan.md](sg-open-world-plan.md). Open items: section 13 of [../task.md](../task.md).

## Playing

- Drive with the arrow keys or W A S D (down also reverses), Space for the handbrake, H for the horn, R to right the car; on a phone use the four buttons.
- Buttons under the view: Pause, Horn, Right the car, Vehicle (nine vehicles, remembered), Time (08:00, 13:00, 18:30, 22:00), Next mission, Sound.
- Missions: a gold beam marks the target, the top line shows the arrow, the distance and your best score; the score rewards beating the par time (shortest road path at 11 m/s) and costs damage.
  The Woodlands Checkpoint needs a full stop and the passport stamp game. The order: ArtScience Museum, Esplanade, Merlion, Bayfront MRT, Gardens by the Bay, Woodlands Checkpoint, Johor Bahru.
- Near an MRT entrance (red pillar with the station sign) a button or E goes down to the station page.
- Damage: smoke from 40 percent, the engine stalls at 95 percent until you right the car.

### Fort Canning Link tunnel prototype

Open [the Fort Canning Link tunnel prototype](https://yapweijun1996.github.io/Blender-3D-Gallery/?page=sg-world&tunnel=fort-canning) from Singapore Open World. Drive from the surface approach through the descent, covered tunnel and exit. Use the arrow keys or W A S D, or the four touch controls. Pause and Restart drive apply to this session. The Open World link returns to the normal map.

The prototype follows the 360.916 m three-lane, one-way OpenStreetMap way `159677768` and both connected surface ways from the [pinned Marina Bay snapshot](../scripts/world/fixtures/README.md). Road position is estimated in the source. The 5.5 m depth, 8% grade limit, level surface and 4.7 m covered clearance are simulation values. The profile spans three 250 m tiles with matching seam samples. The ramp opening, walls, ceiling and surrounding surface use the same geometry for rendering and Rapier collisions. The driven sedan uses the existing Blender car and vehicle physics.

Regenerate the prototype path without a network connection. The check compares the output with the tracked artifact and exercises a deterministic drive across both actual OSM endpoints, both covered portals and both tile seams.

```sh
node scripts/world/fort-canning-tunnel.mjs > scripts/world/fort-canning-tunnel.json
npm run test:world
node --test tests/world-tunnel-prototype.test.mjs
npm run build:deploy && npm run test:tunnel
```

### Default-world tunnel integration checks

On the [ordinary Singapore Open World map](https://yapweijun1996.github.io/Blender-3D-Gallery/?page=sg-world), approach Fort Canning Link from Victoria Street to drive under Fort Canning Road and join the five-lane Penang Road exit. The world starts loading the six required tiles within 800 m of the tunnel area. It keeps the original road in place until the tiles are verified, nearby vehicles and pedestrians are clear of the cut, and Rapier has indexed the new collision surfaces. If a tile fails to load, the surface remains drivable. The map retries once when the player leaves the protected patch or returns after leaving the preload area.

The 531.274 m simulation extends the descent and ascent along the connected Fort Canning Link ways in the pinned snapshot. It spans four tiles and keeps the mapped upstream footways and SMU Connexion above the roof. The accepted cut stays installed for the driving session, including trips away from Fort Canning and back.

Run the offline checks from the repository root.

```sh
node scripts/world/fort-canning-integration.mjs > scripts/world/fort-canning-integration.json
npm run test:world
node --test tests/world-fort-canning-crossings.test.mjs tests/world-tunnel-streaming.test.mjs tests/world-overhead-structures.test.mjs
npm run build:deploy && npm run test:streamed-tunnel
```

A Rapier sedan travels the extended approach, both portals and all three tile seams. At the parking aisle and Fort Canning Road, pairs of sedans drive across the same location at different heights in the same physics world. The chassis separation is 5.50 m and 5.45 m respectively at the closest points on plan.

The original centered profile reports four overlaps in the fixed map data.

- **Penang Road merge.** The full road width begins overlapping the exit 52.20 m after the last edge of the Fort Canning Road crossing. At the prototype's 8% grade limit this gives at most 4.18 m of depth against the model's 4.90 m roof clearance and thickness. Keeping the Penang Road merge at ground level requires an adjusted road profile or alignment. [LTA route map](https://onemotoring.lta.gov.sg/content/dam/onemotoring/Driving/Road_Closures/Temporary/FCT/FCTTT801TunnelClosureMapApr2025.pdf).
- **Innovation Bridge.** The mapped two-storey bridge intersects the entrance cut. The tile renderer and Rapier support a closed elevated footprint when an underside height is supplied. The accepted simulation height and clearance are recorded below. [SMU description](https://admissions.smu.edu.sg/our-community/news/smu-expands-city-campus-footprint-new-sustainable-development-named-tahir).
- **Two exit footways.** The `774912614:0` and `1552288080:0` footprints intersect the open ascent in plan. The adjusted alignment and walkable supports are described below.

The original streamed tiles ended where the three Fort Canning Link lanes and two Penang Road lanes merge. A separately pinned API sample verifies 168.71 m of five-lane, one-way Penang Road from the merge to a signal. The junction overlay adds the verified public-road movements to the streamed tiles. [OpenStreetMap merge continuation](https://api.openstreetmap.org/api/0.6/way/888048852/full.json), [middle segment](https://api.openstreetmap.org/api/0.6/way/74559749/full.json), [signal approach](https://api.openstreetmap.org/api/0.6/way/888048851/full.json).

The extended alignment, depth, roof and grade checks use game dimensions. The fixed inputs give plan geometry and layer tags.

#### Three-plus-two-lane merge candidate

The simulated exit keeps the three Fort Canning Link lanes and the two level Penang Road lanes separated until they meet at Y=0. All five lanes align with the pinned downstream road. The road triangles share the same vertices at the seam, and the two full-width mitered approaches have no positive-area overlap. The adjusted ascent peaks at 7.24%, within the 8% grade limit. Two Rapier sedans drove alongside each other through the seam without touching, with all four wheels supported on each car within four metres of it. Both drove at least 18 m into the mapped five-lane exit.

The roof covers the full Fort Canning Road and `774912614:0` footprints. The other footway, `1552288080:0`, clears the shifted cut. Over 9,100 independent surface probes verified both drawn ribbons. The initial Rapier capsule test dropped below the flat surface during sustained walking. The candidate now gives the exact pavement triangles 120 mm of convex support with their tops at the drawn pavement height. Both capsules walked the full mapped footways, about 113.46 m and 22.97 m.

The Innovation Bridge uses its mapped footprint with a 3.00 m simulated underside relative to the flat surface datum. Over the full crossing envelope the carriageway has at least 5.258 m of modeled clearance. The ray check hit the bridge underside and a Sedan drove through with wheel support.

```sh
npm run test:world
node --test tests/world-fort-canning-merge.test.mjs tests/world-fort-canning-clearance.test.mjs
```

At Dhoby Ghaut Green, the new road draws above the park fill. The six replacement tiles suppress the original road paint on the changed alignment and keep the upper crossing visible.

#### Penang Road junction source checks

The pinned junction data extend the five-lane Penang Road exit through the signal at node `408999681`. Penang Road continues straight and the two Penang Lane approaches join from opposite sides. The public-road overlay excludes the private service arm and verifies the mapped no-U-turn restriction. The next public fork has a verified left turn to Clemenceau Avenue and a through route on Penang Road. The source marks right turns on the incoming lanes at that fork, and those movements remain unassigned pending a mapped destination. [Signal incident ways](https://api.openstreetmap.org/api/0.6/node/408999681/ways.json), [OSM turn restriction](https://api.openstreetmap.org/api/0.6/relation/12351517.json), [first fork incident ways](https://api.openstreetmap.org/api/0.6/node/1275666711/ways.json).

The offline tile builder produces the public-road overlay across `-7_-7`, `-8_-7` and `-8_-8`. A route that spans two tiles requires both matching fragments. The terminal signal approach includes a mapped pedestrian crossing less than six metres before the junction. The simulated stop line is 15 m upstream of the junction, on the preceding graph edge. The traffic stop line and rendered signal use the same approach. A bus stops with its nose clear of the crossing on red and proceeds to the public exit on green.

The traffic engine can accept explicit forward lane assignments for a one-way merge. The Link lanes continue into downstream lanes 1–3 and the Penang feeder into lanes 4–5, numbered from the left. The same assignments control following distance and the lane taken at the merge. All five vehicles continued into the pinned Penang Road lanes in the offline traffic test. On the default map, the grade-aware traffic graph takes effect with the new road surface. At the first fork, traffic uses only movements with a verified public destination.

## Data pipeline (only needed when the map changes)

```sh
node scripts/world/fetch-corridor.mjs              # Overpass, 13 chunks along models/drive/route-mbs-jb.json, retries; needs output/osm/marina_bay.json
node scripts/world/build-tiles.mjs --input output/osm/combined.json   # writes models/world/tiles (830 tiles of 250 m, 12.8 MB)
node scripts/world/mission-distances.mjs           # road distances for the par times: src/world/mission-distances.js
node scripts/world/fit-landmark.mjs <model.glb> "<outline name regex>" [max ground height]   # pose of a landmark on its mapped outline
```

`output/osm/` is not tracked. The map data is © OpenStreetMap contributors (ODbL) and the credit is shown on the page.
Models are registered in the gallery with `node scripts/register-gallery-model.mjs` (collection "Singapore Open World").

## Code map

- `src/world/page.js`: the page (renderer, tiles streaming, physics world, HUD, missions, day cycle); `tile-mesh.js`: tile to geometry (roads, kerbs, footways, water, parks, building facades, bridge decks, zebra bars).
- `src/world/physics/`: Rapier vehicle (`vehicle.js`), crash damage (`crash.js`), world wrapper (`world.js`); `traffic.js`, `signals.js`: traffic on the road graph and the signal lights.
- `landmarks.js`, `groves.js`, `furniture.js`, `pedestrians.js` and `paths.js`, `bridges.js`, `missions.js`, `minimap.js`, `damage.js`, `stamp.js`: one concern each, pure logic where possible (tested in `tests/world-*.test.mjs`).
- `src/mrt/`: the station page (`schedule.js` the train cycle, `passengers.js`, `page.js`).

## Checks

```sh
npm test                    # all unit tests (800+)
npm run test:world          # road network tiles against the pinned OSM test fixture
npm run test:openworld      # real Chrome: loads, drives, missions, bridges' tiles, streaming, vehicles, checkpoint
npm run test:tunnel         # Chrome keyboard and emulated touch, both tunnel portals and route cleanup
npm run test:mrt
```

The browser tests use software rendering (about 1 fps), so they use hooks on the stage element (`teleport`, `simulate`, `setMission`, `hurt`, `stampHit`, `steerCheck`, `inspectWorld`).

## Known limits

The normal Open World map omits underground roads from road meshes and traffic. The Float is placed approximately, the Supertrees are scattered inside their mapped grove outline and ordinary buildings use textured extrusions. The world outside Marina Bay has mapped roads, buildings, water and parks. A [physical phone performance procedure](verification/sg-world-physical-performance.md) is ready. Real-device frame rate remains unmeasured.
