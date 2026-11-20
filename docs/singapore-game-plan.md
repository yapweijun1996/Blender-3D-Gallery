# Singapore open-world game: plan v0.2 (2026-11-20)

Status: planning draft from the owner's brief ("Singapore GTA-style game", reuse the modular chibi
characters, iPhone must not stutter). Nothing here is built yet. Decisions marked OPEN need the owner.

## 1. Pitch

A compact, stylised Singapore district you can walk, ride and drive through, with chibi characters
you dress up (the dress-up demo is the character creator). Open-world feel, short missions, no
real brands. Target: a web game (three.js) that holds 30 fps on an iPhone.

## 2. What we reuse

| Piece | Source | Notes |
| --- | --- | --- |
| Characters, wardrobe, clips, gestures | `models/chibi-dressup/` and `src/chibi-dressup/` | Three bodies, one 65-bone rig, manifest driven |
| Crowd of dressed NPCs | GJH v11 crowd (`assets/crowd.js`, NPC wardrobe limits) | 1.5 MiB per GLB, 6 MiB total, 20k triangles per outfit |
| Physics | Rapier (as in v11) | Character controller, vehicle raycast |
| Static props and Tripo props | `docs/tripo-settings-and-experience.md` | Redistribution confirmed by the owner (2026-11-20) |
| Process | `docs/chibi-modular-template.md` | Motion gate, independent render review, per-item verification |

## 3. Scope of the first playable (vertical slice)

- One district about 400 m by 400 m: HDB blocks with void decks, a hawker centre, a coffee shop,
  an MRT station entrance, a main road with a bus stop, a park connector. Original designs only.
- Movement: walk, run, jump, sit, enter and drive one car and one bicycle; MRT as a fast-travel
  gate (no simulation).
- 3 missions: food delivery by bicycle, taxi fares, a hawker-centre errand chain (carry actions
  already exist: cup, box, bag, shelf).
- Day/night cycle, simple traffic, 40 to 60 dressed pedestrians near the player.
- Dress-up: choose body and outfit at start and at a wardrobe shop.

OPEN: violence and police chase (GTA-like) or a non-violent "life in the city" game? Default in
this plan: non-violent, so it can be published publicly and played by anyone.

## 4. Technical plan

- World as streamed tiles (about 50 m) of instanced modules (blocks, shopfronts, trees, signs).
  Load only the tiles near the player; unload far ones; no per-frame allocation.
- Budgets for iPhone: at most 150 draw calls, 300k visible triangles, 40 MB of textures
  resident, 1024 px textures, one directional light with a baked light for the static world.
- Characters: skinned meshes only for the player and near NPCs (within about 25 m); farther
  pedestrians use a few cheap billboard or low-poly proxies. Pedestrians share clips through the
  existing retarget code.
- Vehicles: simple rigid-body cars with raycast wheels, low-poly shared body, 3 colour variants.
- Audio: small looped city ambience; sound effects lazily loaded.
- Save: local storage (outfit, money, mission progress). Loader with an infinity animation
  (as in v11), pause and reduced-motion respected.
- Repository: a separate repo or a `game/` route in this gallery. OPEN.

## 5. Phases (each ends with measured gates, a local commit and a verified push)

1. Prototype: one street, walk and run, camera, collision, dressed player, 60 fps on desktop,
   30 fps on an iPhone. Gate: frame-time and draw-call report on the phone.
2. District blocks: tile streaming, 10 module kinds, day/night. Gate: streaming has no hitch above 50 ms.
3. People and traffic: pedestrian crowd, cars, bicycle. Gate: 40 pedestrians and 8 cars stay at 30 fps.
4. Missions and economy: the three missions, wardrobe shop, save. Gate: end-to-end playthrough test.
5. Polish and release: loader, accessibility, language (English, Chinese, Malay as in the demos), PWA.

## 6. Content rules

- Original landmarks and signs; no real company logos or trademarks.
- Every Tripo or AI-generated asset gets a recorded source and licence; static props follow the
  strict loader rules (no embedded animations or skins on props).
- Each new character item goes through the motion gate and an independent render review.

## 7. Open decisions for the owner

1. Violence and police chase, or non-violent? (this plan assumes non-violent)
2. Which district first: heartland (HDB and hawker centre), Marina Bay, or Chinatown?
3. Where it lives: a route in Blender-3D-Gallery or a new repository?
4. Is Tripo credit spending allowed for the buildings and vehicles? (the budget approved so far is only for garments)
5. Minimum device: iPhone model and iOS version to hold 30 fps on.

## 8. First interaction demo: drive from Marina Bay to Johor Bahru (owner request, 2026-11-20)

The owner asked for an interaction demo that drives a car from Marina Bay Sands (Singapore) to
Johor Bahru (the owner's map shows Mid Valley Southkey), based on real map data. It doubles as
phase 0 of the game: a long, simple, recognisable road with one gameplay idea (the border).

Real route (research, 2026-11-20):

- Google Maps on the owner's phone: 38 km, 1 h 13 min to 1 h 16 min depending on the option, a traffic
  warning near Johor Bahru, and the note that the route crosses a country border. Google data and
  imagery are not used in the demo (terms of service); the owner's screenshot is only a reference.
- Open data check with the OSRM routing service on OpenStreetMap data: 31.2 km, 33 min in free-flow
  traffic, 718 route points (about 76 KB as GeoJSON), bounding box lon 103.7625 to 103.8615 and lat
  1.2823 to 1.4980. Road sequence: Sheares Avenue, East Coast Parkway, Rochor Road and Bukit Timah
  Road, Pan-Island Expressway, Bukit Timah Expressway, Woodlands Crossing, Woodlands Checkpoint (cars),
  Johor-Singapore Causeway, JB CIQ, Jalan Lingkaran Dalam, Jalan Tebrau, Persiaran Southkey Utama.
  The Causeway crosses near lon 103.7678, lat 1.4437.

Concept:

- A stylised 3D corridor built from the real route: road ribbon, lane count and speed limits from
  OpenStreetMap, simple landmark kits at the start (Marina Bay skyline), the expressways, the
  Woodlands checkpoint, the Causeway and Johor Bahru (Southkey towers). Everything between is
  low-poly instanced filler.
- The player drives a chibi driver in a small car (steer, accelerate, brake, horn) or lets the car
  follow the route in an auto mode; a minimap on a real-map-shaped line shows progress and the next
  road name. Day to night follows the clock of the trip.
- Interaction beats: toll or gantry beeps, lane changes in light traffic, the checkpoint queue and a
  passport and customs interaction at the booth (a mini-game, no real security procedure), then the
  Causeway view of the strait and arrival at Southkey. The chibi wardrobe and the carried props from the
  dress-up demo are reused for the driver and the booth officers.
- Mobile first: 30 fps on an iPhone, a streaming window of about 300 m of road, at most 150 draw calls.

Data and licence rules:

- Road geometry and names come from OpenStreetMap (ODbL): show "Contains OpenStreetMap data" credit in the
  app and keep a copy of the extracted route in the repository (`models/drive/route-mbs-jb.json`) so the demo works
  offline and never depends on a public routing server at run time. Fetch once with OSRM or an Overpass
  query, then commit the file.
- No Google Maps imagery, tiles or routes. No real brand logos. Public landmarks are drawn in an original style.
- The checkpoint is a game scene only: no depiction of real security procedures or personal documents.

Phases for this demo (each with measured gates):

1. Route data: extract and simplify the route (target under 120 KB), compute heading, length and lane data. Gate: the
   polyline matches the OSM route within a few metres and the Causeway crossing is at the right place.
2. Drive prototype: car on the road ribbon with simple physics, camera, minimap and speed. Gate: 60 fps on a desktop and 30 fps on an iPhone.
3. Landmarks and checkpoint: the six landmark kits, traffic, passport mini-game. Gate: end-to-end playthrough test.
4. Polish: day and night, sound, loader with the infinity animation, languages (English, Chinese, Malay), PWA.

Open questions for the owner: auto mode or manual driving first; whether the checkpoint mini-game should be
included; the exact start point and the end point; and whether Marina Bay Sands may be shown by name (it is a
real landmark; drawn in an original style it should be fine).

### Status of the drive demo (2026-11-20, evening)

Built and pushed: `?page=drive-jb`. Route data from OpenStreetMap (31.2 km, 718 points), real Blender-built model kit (22 models in
`models/drive/kit`, validated by `models/drive/validate.mjs`), streamed scenery, road kit (curbs, pavements, lane lines, zebra crossings,
guardrails, lamps, signs), two-way traffic of four vehicle types, dressed chibi pedestrians, chibi boy driver, Woodlands checkpoint with a
passport-stamp mini-game and lifting barriers, minimap, day to night clock, three languages, auto and manual driving, arrival panel.
Tests: `tests/drive-route.test.mjs` (route maths) and `npm run test:drive` (end to end in a normal browser). Not measured yet: iPhone
frame rate, because no phone capture has been received. Known gaps: the road is one carriageway (no lane changes), traffic does not react to
the player beyond slowing behind a car, no sound, the Johor side is generic low-rise.


## Update 2026-11-21: open world and MRT

The drive demo was rebuilt as an open-world study, `?page=sg-world`: the real OpenStreetMap road network and buildings around Marina Bay in streamed tiles, a car on Rapier
vehicle physics (crash, flip, right again), traffic with junction signals, hand-modelled landmarks at their real places, street furniture, zebra crossings and walking chibis.
`?page=sg-mrt` shows a train arriving at a platform. Status per milestone, tests and gaps: [sg-open-world-plan.md](sg-open-world-plan.md#status-2026-11-21).
The older pages `?page=drive-jb` (Marina Bay to Johor Bahru) and `?page=sg-heartland` (walkable HDB district) are unchanged and still pass their browser tests.
