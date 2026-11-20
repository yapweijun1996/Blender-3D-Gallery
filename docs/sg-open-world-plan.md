# Singapore open world: rebuild plan (2026-11-20)

Owner feedback on the first drive demo: poor overall detail, too few vehicle types, no real physics (wants crashes and flips),
poor building quality, a route that feels fake with no junctions, no real Singapore or Johor Bahru map. Owner decisions:
real OpenStreetMap road network, first as a corridor (about 1 km wide, Marina Bay to Johor Bahru), then wider; a real physics engine
(Rapier) with crashes and flips; traffic on the network with traffic lights at junctions and several vehicle types; everything
as realistic as the web budget allows. Next after the cars: the MRT (stations and trains), also realistic.

## Findings (feasibility, measured today)

- Overpass returns real data for a 1.7 km by 2 km box at Marina Bay: 2,841 ways, including primary, secondary, tertiary and
  residential roads, service roads, footways and cycleways, 293 buildings (216 with a height or level count) and 26 water polygons;
  raw JSON 2.2 MB. The corridor needs filtering and compact tiles.
- Rapier (`@dimforge/rapier3d-compat` 0.21.0, WASM embedded) runs in Node and the browser and has a vehicle controller
  (`createVehicleController`); a headless run settled a box on a ground plane at the expected height. Added as a dependency.

## Architecture

1. Data pipeline (`scripts/osm-corridor.mjs`): fetch the corridor in tiles from Overpass with a generic client name, keep only
   drivable roads (motorway to residential and service), crossings and traffic signals, building footprints with height, water, parks and
   rail; simplify to 1 m, write compact binary tiles (500 m) to `models/world/tiles/`, plus an index. Licence note: OpenStreetMap
   contributors (ODbL), credit shown in the app.
2. Road network: a graph (nodes at junctions, edges with lane count, speed, one-way, class), lane geometry, junction patches,
   traffic-light plans per signalised junction, road markings and kerbs generated per edge.
3. Streaming: tiles within 600 m of the player are built and physics colliders created; far tiles are dropped.
4. Physics (Rapier): vehicle controller per vehicle (suspension, steering, brakes), building and kerb colliders, crash response
   (impulse, deformation by a damage factor, flips allowed), pedestrians as kinematic capsules.
5. Traffic AI: vehicles follow lane paths on the graph, obey signals, keep distance, turn at junctions, yield to the player.
6. Buildings: extruded footprints with real height and a facade shader (window grid, floor lines, colour by use) plus the existing
   game-ready models for landmarks and shophouses; roofs and podiums where tagged.
7. Vehicles: more types (taxi, SBS bus, double bus, lorry, van, ambulance, school bus, police, motorbikes) from the existing gallery
   models converted to game-ready form.
8. MRT (next): stations (entrances, concourse, platforms with screen doors) and trains, from the existing MRT models.

## Milestones

M1 data and network: corridor tiles for the first 3 km, graph builder with tests, a top-down debug view. Gate: network has no
disconnected components along the route, junction count and lane counts plausible, tiles under 150 KB each.
M2 physics vehicle on the real roads with kerb and building colliders. Gate: headless Rapier tests (settle, drive, crash, flip), real-browser drive.
M3 traffic and signals on the graph. Gate: no vehicle overlap over 5 minutes of simulation, signal cycles respected.
M4 buildings with facades and landmarks; Johor Bahru side. Gate: draw-call and triangle budget on a phone profile.
M5 vehicle variety and MRT.
Each milestone ends with tests, an independent look at screenshots and a push to main.

## Detail-first approach (owner, 2026-11-20 evening)

Do not build the whole map in detail at once. Start with the area around the start (Marina Bay Sands), first about 100 m, then 500 m, and
make it as close to the real Singapore as possible (real road layout, lanes, junctions, pavements, trees, street furniture, signs), then grow.
Real data: `output/osm/marina_bay.json` (OpenStreetMap, ODbL, 9,004 elements: 1,566 buildings, 551 mapped trees, 144 traffic signals, 586
crossings, 96 bus stops, 88 subway entrances, artworks). Hand-modelled landmarks around Marina Bay: Marina Bay Sands, ArtScience Museum, the
Merlion, Esplanade (the durian), Helix Bridge, Supertree Grove, Bayfront and Promenade MRT, The Float. Work is split into about ten parallel
Codex jobs that must not touch each other's folders: models go to `output/world-models/<name>` (mbs, merlion, esplanade, artscience, streetkit,
vegetation), vehicles to `output/drive-models/gameC`, MRT to `output/mrt-models/kit`, code to `src/world/network` + `scripts/world` and
`src/world/physics`. The manager verifies each result with its own checks, copies it into `models/world/...`, wires it in, tests and pushes.

## Status (2026-11-21)

Verified in Chrome (software GL), an iPhone 15 WebKit emulation and Node; nothing here was measured on a real phone. Commands: `npm test` (783 tests),
`npm run test:world` (road-network tiles, needs the untracked `output/osm/marina_bay.json`), `npm run test:openworld`, `npm run test:mrt`.

| Milestone | State | Evidence |
| --- | --- | --- |
| M1 data and network | Done for the Marina Bay extract (4.5 km by 4 km, 184 tiles of 250 m, 4 MB in `models/world/tiles/`). Not yet the corridor to Johor Bahru. | `scripts/world/build-tiles.mjs`, `src/world/network/*`, 8 tests |
| M2 physics vehicle | Done: Rapier vehicle (`src/world/physics/*`) with crash damage, flip detection, righting and reverse; building colliders from the mapped outlines; traffic and nearby vehicles are kinematic boxes. | `tests/world-physics.test.mjs` (7) |
| M3 traffic and signals | Done at arcade level: `src/world/traffic.js` (graph stitched from tile fragments, left-lane driving, car following with look-ahead, random turns, two-phase signals, 8 vehicle types), `src/world/signals.js` draws the lights. Missing: yielding at unsignalised junctions, cars do not react to pedestrians. | `tests/world-traffic.test.mjs` (4), `tests/world-signals.test.mjs` (2) |
| M4 buildings and landmarks | Partly: buildings are extruded outlines with a flat colour. Marina Bay Sands and the Esplanade are fitted onto their mapped outlines (`scripts/world/fit-landmark.mjs`), ArtScience Museum, Merlion Park and Helix Bridge are placed by coordinates (`src/world/landmarks.js`). Missing: facade detail on ordinary buildings, Supertrees (no mapped coordinates), The Float, Johor Bahru, bridges and tunnels (the world is flat). | `tests/world-landmarks.test.mjs`, screenshots |
| M5 vehicles and MRT | Vehicles done (6 new game-ready types). MRT: a generic station page `?page=sg-mrt` (three-carriage train, platform screen doors, three views). Missing: passengers, entrance from the world, the real Bayfront and Promenade layouts. | `tests/mrt-schedule.test.mjs` (3), `scripts/test-mrt-browser.mjs` |

Pages: `?page=sg-world` (Singapore Open World) and `?page=sg-mrt` (Singapore MRT Station). Street furniture (lamps, bus shelters and flags) comes from
`src/world/furniture.js`, zebra bars from the mapped crossings (`src/world/tile-mesh.js`), pedestrians (the dress-up chibis) from `src/world/pedestrians.js`.
All 64 models made for it are in the gallery collection "Singapore Open World" (`models/sg-*`, registered with `scripts/register-gallery-model.mjs`,
Khronos validator 0 errors and 0 warnings). Phones load a 3 by 3 ring of tiles with shorter fog.

Known gaps: the player car tops out near 180 km/h; no real-device frame rate; WebKit logs style-src refusals on every demo page (not specific to this work);
`wasm-unsafe-eval` was added to the page's script policy for Rapier.
