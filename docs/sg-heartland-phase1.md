# Singapore open city, phase 1: the Heartland block (design, 2026-11-20)

Goal (owner): continue towards the open Singapore city game. Phase 1 is a small, walkable and drivable heartland
district built from the gallery's EXISTING Singapore models (converted to game-ready form), reusing the drive demo's road
kit, Proton Saga, traffic, sound and the dress-up chibi characters. No new design: the gallery already has the models.

## Scope

- Route page `?page=sg-heartland` in this gallery. About 280 m by 280 m, one ring road with two crossings (zebra and traffic light).
- Player: the chibi from the dress-up demo (body and outfit chosen there are remembered), third-person camera, walk and run
  (WASD or touch joystick), jump not needed, sit on benches (existing clip), wave and dance as emotes.
- Enter the Proton Saga parked by the kerb (press E or tap), drive it round the ring road with the existing driving model, get out again.
- Places to visit and walk into: HDB void deck with a coffee shop, a hawker centre with stalls and tables, a provision shop, a bus stop,
  a playground, an MRT station entrance (a gate only, no train yet).
- Life: dressed chibi pedestrians, traffic, day and night clock, sounds (existing synthesiser plus footsteps and hawker chatter bed).
- Interactions: sit at a hawker table, order from a stall (tray appears using the existing hold-a-cup clip), buy from the provision shop
  (bag carry clip), wave to a pedestrian.

## Reused existing assets (gallery catalog ids)

Buildings: `hdb-block`, `hdb-void-deck`, `hdb-coffee-shop-frontage`, `hdb-neighbourhood-shopfront`, `shoplot-building`, `public-market`,
`hawker-stall`, `chicken-rice-stall`, `mrt-station-entrance`. Street: `bus-stop-shelter`, `singapore-traffic-signal-pole`,
`pedestrian-crossing`, `street-name-sign`, `heritage-street-lamp`, `public-service-waiting-bench`, `hdb-block-number-sign`.
Park: `playground-slide`, `playground-swing`, `rain-tree`, `angsana-tree`, `tembusu-tree`, `frangipani-tree`, `coconut-palm`.
Characters and animation: the dress-up bodies, clips (walk, run, wave, dance, sit, hold) and wardrobe.
Vehicles: the game-ready Saga and traffic vehicles in `models/drive/kit`.

## Technical rules

- Game-ready copies go to `models/city/kit/*.glb`: at most 16 primitives, flat PBR materials with the same names as the drive kit
  (paint, glass, tire, light, trim, wall, roof, window, leaf, trunk, metal, concrete, chrome, plate), no textures, no animations,
  budgets per model, validated by `models/city/validate.mjs`.
- Streaming and instancing as in the drive demo (window around the player). iPhone budget: 200k visible triangles, 130 draw calls.
- Interiors are simple walk-in volumes (void deck, coffee shop, hawker hall) loaded with the district, not separate scenes.
- Characters walk on a nav grid; collision with buildings through axis-aligned boxes from the model bounds.

## Steps

1. Game-ready kit (Codex, parallel): buildings set and street and park set. Gate: validator, triangles, six-view review.
2. Scene builder: district layout data file, instancing, ring road from the road kit, day and night.
3. Player controller: chibi rig with walk and run, camera, collision, touch joystick.
4. Car enter and exit using the driving model.
5. Places and interactions (hawker, coffee shop, provision shop, bench).
6. Crowd and traffic, sound, loader, three languages, end-to-end test (`npm run test:city`).
