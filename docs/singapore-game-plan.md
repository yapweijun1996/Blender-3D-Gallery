# Singapore open-world game: plan v0.1 (2026-11-20)

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
