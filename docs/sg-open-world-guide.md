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
npm run test:world          # road network tiles (needs output/osm/marina_bay.json)
npm run test:openworld      # real Chrome: loads, drives, missions, bridges' tiles, streaming, vehicles, checkpoint
npm run test:mrt
```

The browser tests use software rendering (about 1 fps), so they use hooks on the stage element (`teleport`, `simulate`, `setMission`, `hurt`, `stampHit`, `steerCheck`, `inspectWorld`).

## Known limits

Tunnels are not drawn; the Float is placed approximately; the Supertrees are scattered inside the mapped grove outline; ordinary buildings are extrusions with a texture;
the world outside Marina Bay has only mapped roads, buildings, water and parks; no real-device frame rate has been measured (Chrome software GL and an iPhone 15 WebKit emulation only).
