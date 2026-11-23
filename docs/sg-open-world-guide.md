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

Default-world integration still needs the actual surface and overhead layouts at the approaches, including the projected crossing with Fort Canning Road, plus streaming, AI route choice and target-device measurement. The opt-in prototype has its own scene and vehicle and uses the main site's route disposal and retry.

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
