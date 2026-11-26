# Demo modules: Game, PWA, Solar, Product Studio, Shelf Inspector, Cart demo

Code-reading reference. Everything below was verified against the source on
`main` (paths are repo-relative). Routing: `src/main.js` lazily `import()`s a
demo page per `?page=` route, hands it an `AbortController.signal`, and calls
`dispose()` on the returned handle when the route changes or the signal aborts
(`src/main.js` around the `mountedRoute` block). The cart demo is instead
created by `src/viewer.js` when the opened asset id is `interactive-shopping-cart`.

Shared conventions: every `mount*` returns `{ dispose, ... }`; every module
guards async work with `disposed`/`signal.aborted` checks; GLBs are fetched and
parsed with `GLTFLoader.parseAsync` and released with a local `disposeObject`.
UI text is localized through `src/i18n/index.js` (`localize`, `t`, `mountMarkup`).

## 1. Game (`src/game/*`) - local two-player 8-ball

### 1.1 Layering

| File | Role | Pure / DOM |
| --- | --- | --- |
| `table.js` | Table constants (`TABLE`, version `billiards-2026-11-v1`), `POCKETS`, `RAILS` segments, `groupOf`, `legalPlacement`, `makeRack(seed)` | pure |
| `physics.js` | Fixed-step simulation: `createShot`, `stepPhysics` | pure |
| `rules.js` | `adjudicate`, `RULES_VERSION = "casual-8ball-v1"` | pure |
| `interaction.js` | Pull/aim math: `PULL`, `CUE`, `pullRatio`, `meetsPullThreshold`, `shotStrength`, `aimAngle`, `dragAngle`, `hitsCue`, `strikeOffset` | pure |
| `presentation.js` | `aimContact` (guide ray), `postContact`, `shotFeedback` (uses i18n) | pure + i18n |
| `copy.js` | `englishGameMessage`, `gameMessageKey`, `translateGameMessage` | i18n |
| `storage.js` | `validateMatch`, `openGameStore` (IndexedDB + ownership) | IndexedDB |
| `assets.js` | Ordered required GLB IDs shared by the scene and the offline pack build | pure |
| `scene.js` | `createGameScene` (Three.js view) | DOM/WebGL |
| `page.js` | `mountGame` (controller, UI, input, loop) | DOM |
| `style.css` | Styles (not analysed) | - |

Dependency direction: `page.js` -> {`scene`, `storage`, `rules`, `physics`,
`table`, `interaction`, `presentation`}; `rules`, `physics`, `storage`,
`presentation` -> `table`/`copy`; `table.js` and `interaction.js` depend on
nothing. The physics/rules/table layer has no DOM or Three.js dependency and is
unit-tested directly.

### 1.2 Exported API (verified)

- `table.js`: `TABLE` (frozen; radius 0.028575 m, `step` = 1/120 s, `maxSpeed` 2.8),
  `POCKETS` (6, ids `p0..p5`), `RAILS` (authored cushion + jaw segments),
  `groupOf(id)` -> `"solids"` (1-7) / `"stripes"` (9-15) / `null` (0, 8),
  `legalPlacement(balls, x, z, behindHead=false, ignoreId=0)`,
  `makeRack(seed=1)` (LCG-seeded; 8 in the centre; one solid and one stripe in the
  rear corners; returns 16 balls sorted by id with `q` quaternions, `vx=vz=0`).
- `physics.js`: `createShot(balls, {x,z}, power)` sets the cue ball velocity
  (`speed = 0.18 + power*maxSpeed`) and returns the shot record
  `{firstContact, pockets[], tick, elapsed, settledFor, done, invalid}`; throws
  `game.state.invalidShot` / `missingCue` for bad input.
  `stepPhysics(balls, shot, dt=TABLE.step)` mutates balls and the shot in place.
- `rules.js`: `adjudicate(before, balls, shot)` -> next match state (see 1.3).
- `storage.js`: `validateMatch(m)`; `openGameStore()` -> `{claim, renew, load,
  save(checkpoint, pending), release}`.
- `scene.js`: `createGameScene(container, assets, signal, progress)` -> view with
  `canvas, render, dispose, point(x,y), cueTipDistance, cameraSpan, setInspection,
  inspectKey, setQuality, update(state, angle, power, candidate, cuePullOffset)`.
- `page.js`: `mountGame(root, assets, signal, onLeave)` -> `{dispose,
  hasActiveMatch(), prepareUpdate(), beforeLeave()}`. It also publishes the test
  hooks `window.render_game_to_text` and `window.advanceTime(ms)` (deleted on dispose).

### 1.3 Control flow: shot -> physics -> adjudicate -> persist

1. Pointer/keyboard input in `page.js` builds a frozen intent
   `{id, angle, strength, ratio}` (strength = `shotStrength(ratio)`, ratio from
   `pullRatio`, threshold `meetsPullThreshold`). `shoot(frozen)` requires phase
   `aiming`, not busy/inspecting/context-lost, and `ownership`.
2. `store.renew()` re-checks the lease (a failed renew sets `ownership=false`;
   an exception only sets `saveFailed`). `before = stableCopy(state)`.
3. `persist(before, { id })` writes the pre-shot checkpoint with a `pending`
   marker so a reload mid-shot can roll back ("rolledBack" message in `resume`).
4. If `prefers-reduced-motion` is not set, a cue strike animation runs
   (`delivery`, `PULL.strikeSeconds` = 0.11 s, `animateDelivery`); then
   `commitIntent` calls `createShot(...)`, sets `shot.id`, phase -> `moving`.
5. `frameLoop` (rAF, dt clamped to 0.08 s) accumulates time and runs up to 12
   fixed `TABLE.step` iterations per frame, each calling `animateDelivery` then
   `simulate` -> `stepPhysics`. `window.advanceTime(ms)` runs the same steps
   manually and suppresses the rAF stepping for 1 s (`manualUntil`).
6. `stepPhysics`: adaptive substeps (min 2; > 16 required -> `shot.invalid =
   game.state.speed`), 16 when `hasCrowdedApproach`; swept circle/circle impulse
   contacts, rail-segment reflection (`RAILS`), pocket sensors that append
   `{id, tick, sub, time}` to `shot.pockets`, `firstContact` recorded on the first
   cue-ball collision, `invalid` set on `leftTable` or after 25 s (`noSettle`);
   `done` after balls are at rest for 0.3 s.
7. When `shot.done || shot.invalid`, `completeShot()` (guards with `busy`) sets
   phase `adjudicating` and calls `adjudicate(before, state.balls, shot)`:
   - throws `"Shot was already resolved"` for a finished match, a missing id or a
     repeated `lastShotId` (idempotency);
   - `shot.invalid` -> returns `{...before, phase: "recovery", message}` (pre-shot
     state; nothing is saved; user presses Restore);
   - foul = scratch (cue pocketed) or wrong first contact (none; open-table
     contact with the 8; other group; 8 when not yet eligible; skipped on the break);
   - 8-ball pocketed: on the break it is re-spotted on the foot string (search
     from `footSpot` toward the head in steps of `radius/3`, else `noSpot` ->
     recovery); otherwise the match finishes (shooter wins only if eligible and
     no foul);
   - groups are assigned only by a legal first object pot on an open table
     (pots sorted by `tick, sub, time, id`); turn continues only if a ball of the
     shooter's group (or any object ball on the break) is potted; foul ->
     `ballInHand`, cue pocketed, phase `placing`.
   - `next.revision++`, `lastShotId` set.
8. `completeShot` then `persist(next)`, sets `state = next`, `stable` copy, and
   shows `shotFeedback(before, next, shot)` (via `lastResult`). If WebGL context
   was lost meanwhile, phase becomes `recovery` ("interrupted").
9. Ball-in-hand placement: pointer/keys move `candidate`; legal when
   `legalPlacement(..., behindHead = state.break)`.

Phases observed in code: `placing`, `aiming`, `moving`, `adjudicating`,
`paused`, `recovery`, `finished`. Only `aiming|placing|finished` are valid in a
persisted checkpoint (`validateMatch`).

### 1.4 State and storage ownership

- Authoritative match state lives in `page.js` closure variables `state`
  (live, includes transient phases) and `stable` (last persisted-quality copy,
  used by `prepareUpdate` and the heartbeat conflict check).
- Persistence: IndexedDB database `blender-gallery-game-v1`, store `records`,
  keys `owner`, `match` (`{checkpoint, pending, savedAt}`), `previous` (the prior
  `match` record, written on every save).
- `validateMatch` is the schema gate on both `save` and `load`: schema 1,
  `rulesVersion`, `tableVersion`, id/revision/player/groups/phase/winner
  consistency, 16 balls with ids 0-15 in order, finite coordinates within a
  1.21 x 0.66 box, zero velocities, unit quaternions, no overlaps beyond a
  0.0015 m tolerance, `finished` iff ball 8 pocketed, `placing` iff cue
  pocketed. A corrupt `match` record loads as `{corrupt: true}` and is treated
  as "incompatible" (page discards it).
- Single-writer ownership: Web Locks (`blender-gallery-game-owner`,
  `ifAvailable`) when available plus a 20 s lease record `{id, until}` renewed
  by `renew()`. `page.js` runs a 5 s heartbeat (`setInterval`) that renews or
  re-claims; on regaining ownership it keeps input locked, reloads the shared
  checkpoint, and if a local unsaved turn would be lost it drops the store and
  shows a conflict message with a "discard" action.
- No localStorage; the PWA module does not read game state except through the
  `prepareUpdate/hasActiveMatch` handle (section 2).

### 1.5 Scene (`scene.js`) lifecycle

Creates an `OrthographicCamera` top-down view (portrait rotates the camera up
vector), `OrbitControls` (disabled except in inspection mode), hemisphere +
directional light, DPR capped at 1.5. Loads 18 GLBs (`pool-table`,
`cue-stick-01`, `cue-ball`, `ball-01..15`) by id from the `assets` list passed by
`main.js`, with 4 parallel `fetch` + `parseAsync` workers; progress is
"completed models", not bytes. `ResizeObserver` drives `resize`. Teardown:
`dispose()` aborts the fetch controller and `LoadingManager`, disposes
controls, geometries/materials/textures and the renderer; also bound to
`signal` abort. A failed or aborted load disposes everything and rethrows.

### 1.6 Page lifecycle (`page.js`)

`mountGame`: `openGameStore()` -> `claim()` -> `load()` -> `createGameScene()`;
a store failure degrades to a "this tab only" mode (no persistence), not a hard
failure. All DOM/window listeners use `{signal}`. `dispose()` cancels rAF and the
heartbeat, disposes the view, `store.release()` (deletes own lease, closes db,
releases the Web Lock), removes the `window` test hooks, closes dialogs, and
clears `root`. Pause is entered on tab hide, ownership loss and menu; WebGL
context loss sets `contextLost` and forces `recovery`.

### 1.7 Dependencies

`three`, `three/addons` (GLTFLoader, OrbitControls), `src/i18n`, IndexedDB,
Web Locks, `crypto.randomUUID`/`getRandomValues`.

### 1.8 Tests

- Unit (`node --test tests/*.test.mjs`): `tests/game.test.mjs` (rack, placement,
  adjudication cases, duplicate-shot rejection, invalid-physics recovery,
  `validateMatch` corruption cases, fixed-step break determinism, six pocket
  approaches, cushion/no-tunnelling), `tests/game-presentation.test.mjs`
  (guide ray, feedback text), `tests/pool-table.test.mjs` (table GLB sight/support
  geometry).
- Browser (Playwright, not in `npm test`): `scripts/test-game-browser.mjs`,
  `test-game-experience.mjs` (`npm run test:browser`), `test-game-ux.mjs`,
  `test-game-responsive.mjs`, `test-game-loading.mjs`,
  `test-game-power-touch-scope.mjs`, `test-game-touch-cancellation.mjs`,
  `test-game-review-followup.mjs`, `test-pool-table-qa-browser.mjs`. Extra
  `scripts/audit-game-*.mjs` are performance/loading audits, not assertions.

### 1.9 Known gaps (as read)

- `page.js` (1090 lines) has no unit tests; the controller, heartbeat and
  ownership transitions are covered only by browser scripts.
- `storage.js` is exercised by tests only through `validateMatch`; `openGameStore`
  (locks, lease, `previous` backup) has no direct test, and nothing reads the
  `previous` record.
- A `recovery` caused by `shot.invalid` is never saved; reload returns to the
  `pending` pre-shot checkpoint via rolled-back resume.
- Physics is a 2D impulse model without spin or throw; `postContact` is
  documented in code as a frictionless estimate only.

## 2. PWA (`src/pwa/*`, `scripts/pwa-build.mjs`, `public/manifest.webmanifest`)

### 2.1 Responsibility and files

Offline shell + offline Game pack + coordinated, consent-based updates.

- `scripts/pwa-build.mjs` - `pwaBuildPlugin(version)`, a Vite `closeBundle`
  plugin (build only; registered first in `vite.config.js`).
- `src/pwa/sw-template.js` - service-worker source with `__BUILD__`, `__SHELL__`,
  `__PACK__` placeholders.
- `src/pwa/register.js` - `setupPwa(getGame)` page-side controller.
- `src/pwa/update-ui.js` - `createUpdateUi()` native modal for update progress.
- `src/pwa/update-state.js` - `classifyUpdate({waiting, pageVersion, latestVersion})`.
- `src/pwa/copy.js` - `pwaCopy`, `workerErrorKey`, `copyError` (maps legacy English
  worker errors to i18n keys).
- `public/manifest.webmanifest` - id `./`, scope `./`, `start_url ./?page=game`,
  standalone, two PNG icons (192, 512 maskable).

### 2.2 Build data flow (`pwaBuildPlugin`)

1. Walk `dist/`, hash every file (SHA-256, bytes), excluding `sw.js`,
   `build-info.json`, `game-pack.json`.
2. Resolve the required Game GLB IDs from `src/game/assets.js` through
   `loadCatalog()` and match source GLBs to emitted files by hash. The build
   fails for an empty pack, missing asset or missing emitted GLB.
3. Compute the build ID from the emitted file list, the Game pack contents
   and version, the worker template and the optional `B3G_TEST_BUILD` value.
4. Shell = `index.html` plus all `.js/.css/.webmanifest/.png/.svg` files.
5. Write `build-info.json` `{build, version}`, `game-pack.json`, and `sw.js`
   (placeholders replaced with JSON). The pack version joins `RULES_VERSION`
   and `TABLE.version` with a slash. App version still comes from `package.json`.

### 2.3 Service worker behaviour (`sw-template.js`)

- Build caches use `b3g-<scope>-shell-<BUILD>` and `b3g-<scope>-game-<BUILD>`.
  The durable card-awareness marker lives in `b3g-<scope>-state`.
- On install, the worker fetches `build-info.json?v=BUILD` (must match), then fetches each
  shell entry with `cache: "reload"` and verifies byte length + SHA-256 (+ `glTF`
  magic for GLBs) before `cache.put`. A failure deletes the shell cache and
  fails the install. After verification, the installer calls `skipWaiting()`
  when a gallery worker is active and the card-awareness marker is absent.
  This one-time migration runs regardless of open tabs. A fresh registration
  activates normally.
- The first card-aware worker writes the marker on activation and reopens
  card windows controlled by the gallery registration. Open gallery documents
  keep running with their current Game state and can still load assets from
  older caches. Later upgrades use the usual update approval flow.
- Fetch handling covers same-origin, in-scope GET requests. Gallery navigations
  map to `index.html`. Card navigations pass through, with a one-time redirect
  to remove the recovery query parameter while keeping the fragment. Shell
  entries come from cache or are re-fetched and verified. Hashed `assets/` can
  be served from the current or any older complete shell/pack cache of this
  scope (so old tabs keep working); otherwise network. Failed critical assets
  (`.glb/.js/.css`) return 503 and post `RESOURCE_LOAD_FAILED` to the client.
- Messages (via `MessageChannel` port): `BUILD_INFO`, `PACK_STATUS`,
  `CACHE_GAME` (3 parallel verified fetches into a temporary candidate cache,
  marker `__game-pack-ready__`, then copied to the pack cache; candidate always
  deleted; progress events `{progress,total}`), `ACTIVATE_UPDATE`
  (broadcasts `CAN_UPDATE` to all window clients, waits 1.2 s for
  `UPDATE_READY_REPLY` protocol 2, aborts if a new tab appeared / a tab is not
  ready / expiry (<= 15 s) / `CANCEL_UPDATE`; only then `skipWaiting()`;
  finally sends `UPDATE_DECISION`).
- Pack readiness requires a manifest for this build with at least one file,
  the completion marker and a cached entry for every required file.
- Old caches are intentionally never deleted (comment in `sw-template.js`).

### 2.4 Page-side flow (`register.js`)

- `supported = import.meta.env.PROD && "serviceWorker" in navigator`; dev builds
  never register.
- State object (frozen, republished through the `pwa-state-change` window event):
  `connectivity, offlinePack (unknown|checking|ready|missing|preparing|error),
  update (idle|preparing|checking-tabs|activating|reloading|available...),
  updateReady, updateVersion, supported, build, error`. `main.js` reads it via
  `pwaRuntime.getState()` and listens for the event.
- `ensureActiveWorker()` registers `sw.js` (`updateViaCache: "none"`, scope from
  `BASE_URL`) once and waits for activation (timeout).
- Offline pack: events `prepare-game-offline`, `online`, `offline` (and `game-mounted`, dispatched by `src/main.js` as `${page}-mounted` after a route mounts)
  drive `checkOffline()` / `CACHE_GAME`. Cross-tab invalidation uses
  `BroadcastChannel("b3g-pack:<path>")`, falling back to a `localStorage` write
  of the same key (only a signal, no data).
- Update: `checkForUpdate` (throttled 30 s in recovery mode, uses
  `registration.update()`), `reconcileUpdate` via `classifyUpdate` + `build-info.json`,
  `beginUpdate`: shows modal -> `getGame().prepareUpdate()` (refuses while a shot
  is moving; saves `stable`) -> `ACTIVATE_UPDATE` -> `controllerchange` -> one
  `location.reload()`. Other tabs answer `CAN_UPDATE` with
  `ready = !game.hasActiveMatch()` (or already in flow), locking themselves with
  a timed `remoteLocks` entry.
- `update-ui.js`: a `<dialog>` that blocks Escape while busy and swallows
  keydowns in the capture phase so Game shortcuts cannot stack a second modal.
- `install-app` event: uses the stored `beforeinstallprompt` or an install-help dialog.

### 2.5 Storage ownership

Cache Storage (`b3g-*`) is owned by the worker; `localStorage` is used only as
the pack-change fallback signal; no IndexedDB. Game checkpoints are untouched
by PWA code (only `prepareUpdate`).

### 2.6 Tests

`tests/pwa-update-state.test.mjs` (`classifyUpdate`), `tests/pwa-worker.test.mjs`
(worker template: stale navigation, evicted shell repair, install rejects bad
build/bytes); browser: `scripts/test-pwa-browser.mjs` (`npm run test:pwa`),
`scripts/test-pwa-standard.mjs` (`npm run test:standard`, builds artifacts,
checks demo/asset counts and offline behaviour), and `test-game-loading.mjs`
references the pack.

### 2.7 Known gaps

- `pwa-build.mjs` has no direct test; it is only exercised through built-output
  browser tests.
- Only Game assets are in the offline pack; other demos (Solar, Shelf, Product
  Studio) have no explicit offline pack and rely on whatever the shell/fetch
  path serves.
- `register.js` (604 lines) has no unit tests.
- Cache cleanup of older builds is deliberately absent (storage grows per build).

## 3. Solar (`src/solar/*`)

- Responsibility: 3D atlas of the solar system with presentation vs realistic
  scale, time speed, per-body focus and info panel.
- Exports: `assets.js` `solarSceneAssets(catalogAssets)` - filters
  `family === "solar-system"`, replaces each base body with its NASA catalog
  asset (map `replacements`: e.g. `sun -> nasa-sun`, `asteroid-01 -> nasa-vesta`),
  keeping the base `scientific_properties` and setting Saturn `modelScale`;
  throws if a replacement lacks `details`. `frame-gate.js`
  `createFrameGate(gl)` -> `{ready, submitted, dispose}` (WebGL2 fence sync, at
  most one frame in the GPU queue, non-blocking `clientWaitSync(sync,0,0)`,
  silently degrades when unsupported or on error). `page.js` re-exports a
  `solarSceneAssets` that maps each asset id to a bundled URL
  (`import.meta.glob('/models/solar-demo/*.glb', {query:'?url'})`; missing file throws)
  and `mountSolar(root, assets, signal)` -> `{dispose, getState()}`.
- Flow: build DOM, try `new WebGLRenderer` (failure -> "noWebGL" message and a
  dispose that only clears root); load GLBs sequentially, downsampling textures
  wider than 1024 px with `createImageBitmap`; wrap each model in `orbit`/`tilt`
  groups (axial tilt from `scientific_properties`); register selector options.
  Render loop (rAF): `days += dt*speed` (speed 0 when hidden), `updatePositions()`
  uses `orbital_period_days` (fallbacks 1900 comet / 1600 others) with a circular
  phase offset per body index; selection keeps the camera following the body;
  rendering happens only when `needsRender` (input, advance, camera change) and
  `frameGate.ready()`. `scales()` switches `presentation` vs `realistic` sizes
  and distances (`mode`).
- State: all in-closure (`days`, `selected`, `mode`, `bodies`, `loaded`);
  no storage. `getState()` exposes it to tests.
- Disposal: sets `disposed`, disposes frame gate, `OrbitControls`, all loaded
  models, helper disposables, `ImageBitmap`s (`unreleasedImages`), renderer;
  load loops check `disposed` after every await and dispose partially loaded models.
- Dependencies: `three`, `GLTFLoader`, `OrbitControls`, `src/i18n`, `models/solar-demo/*.glb`.
- Tests: `tests/solar-frame-gate.test.mjs`, `tests/solar-nasa.test.mjs`
  (scene asset mapping keeps physics facts), `tests/solar-demo-assets.test.mjs`
  (optimized GLBs vs sources), `tests/nasa-solar.test.mjs` (catalog attribution);
  browser/asset: `scripts/test-solar-scene.mjs`, `scripts/test-solar-assets.mjs`
  (`npm run test:solar`), plus `benchmark-solar-load.mjs`, `optimize-solar-demo.mjs`.
- Gaps: orbits are circular phase animations, not ephemerides (the UI note says
  presentation scale); `page.js` has no unit tests; GLBs load strictly
  sequentially.

## 4. Product Studio (`src/product-studio/*`)

- Responsibility: inspect packaging assets (food tin, beverage can) with
  authored open/exploded animation clips, camera presets and runtime-only label
  variants (can).
- Exports: `camera.js` `VIEW_DIRECTIONS`, `fitProductDistance(radius, aspect, fov)`,
  `setProductView(camera, controls, center, distance, name)`. `pose.js`
  `POSES` (`closed|open|exploded` -> clips `null|OpenClose|Exploded`),
  `REQUIRED_NODES`, `createPoseController(gltf, contract)` -> `{apply(mode, amount), dispose}`:
  validates required nodes per root (`ASSET_DemoFoodTin` or `ASSET_DemoBeverageCan`)
  and that both clips last 3 s (+/-1e-4), have tracks and start at 0, snapshots the
  rest pose and applies a paused `LoopOnce` action at `amount*1.5` s (no
  synthetic offsets). `load.js` `createLatestLoader({prepare, commit, release,
  start, fail})` (latest-selection-wins with `AbortController`; obsolete parsed
  values go to `release`; commit failure releases and calls `fail`) and
  `disposeProduct(object)`. `labels.js` `LABEL_PRESETS` (3), `createLabelController(model)`
  (canvas texture on a cloned material of `LABEL_OriginalCitrusBand`; `apply`,
  `reset`, `dispose` restore the authored material/map). `page.js`
  `mountProductStudio(root, asset, signal, alternatives)` -> `{dispose}`.
- Flow: `main.js` passes `demo-food-tin` plus `[demo-beverage-can]`. `select`
  -> `start` (reset UI) -> `prepare` (fetch + `parseAsync`) -> `commit`
  (build pose controller, pre-pose through all three states to compute union
  bounds, fit camera, create label controller for the can, show ready) or
  `fail` (error panel). Buttons animate pose changes in the rAF `render`
  (render-on-demand via `dirty`/`invalidate`).
- State: closure only (`mode`, `amount`, `current`, `labelsController`); labels are
  runtime textures, never written back to the GLB. No storage.
- Disposal: `loader.dispose()`, local abort, cancel rAF, observer, controls,
  `disposeModel()` (labels, poses, geometry/materials/textures), environment,
  renderer. `webglcontextlost` disposes the page and shows an error.
- Tests: `tests/product-studio-pose.test.mjs`, `-labels.test.mjs`, `-switch.test.mjs`
  (loader races, disposal), `-real-asset.test.mjs`, `-beverage-asset.test.mjs`;
  browser: `scripts/test-product-studio-browser.mjs`.
- Gaps: `page.js` (single 136-line dense file) has no unit tests; `fail` shows a
  generic error with no retry control; label presets are English-only canvas text.

## 5. Shelf Inspector (`src/shelf-inspector/*`)

- Responsibility: inspect seven GJH wall-shelf fixtures (M056-M062) at four LODs
  with row highlight, LED toggle and a runtime header title.
- Exports: `models.js` `SHELF_MODELS` (id, `support-manifest.json`, four LOD
  GLB URLs via `?url` imports, default camera direction). `parts.js`
  `cleanHeader(value)` (strips control chars, trim, max 32), `shelfRowIds(manifest)`
  (`['all','lower','middle','upper']` for three shelves or `['all','lower','upper']`
  for two; throws otherwise), `shelfRowLabels`, `createShelfParts(model, makeCanvas,
  manifest)` -> `{select(row), light(on), title(text), dispose}`. `page.js`
  `mountShelfInspector(root, signal)` -> `{dispose}`.
- Flow: validates manifests (`model_id` match, 4 LODs) before mounting; reuses
  `createLatestLoader`, `disposeProduct`, `setProductView` from Product Studio;
  select model/LOD -> fetch + parse -> `createShelfParts` (clones only local
  materials, resolves `runtime_nodes.shelves/leds`, header anchors from
  `runtime_header_surfaces`; non-M056 models without anchors are rejected) ->
  fit camera. Title text is drawn to a canvas, balanced over two lines on narrow
  plaques, and attached as overlay meshes at anchor local +Z.
- State: closure (`row`, `lit`, `title`, `current`); preserved across LOD or
  model switches (row resets to 0 if out of range). No storage.
- Disposal: loader, abort, rAF, observer, controls, parts (restores original
  materials), model, environment, renderer + `forceContextLoss`; context loss
  disposes the page.
- Tests: `tests/shelf-inspector.test.mjs` (14 cases: material ownership, title
  fitting, missing nodes, latest-request wins, per-model manifests), browser
  `scripts/test-shelf-inspector-browser.mjs`.
- Gaps: `page.js` is a very dense single-line style; it is not unit-tested (only
  `parts.js` and loader behaviour are); keyboard handling is hand-rolled on the canvas.

## 6. Shopping-cart demo (`src/shopping-cart/demo.js`)

- Responsibility: bounded interactive demonstration layered on the independent
  cart GLB: a shopper character pushes the cart, steers, adds/removes a basket
  item, and stops at a fixed obstacle.
- Export: default `createCartDemo({model, scene, container, signal, invalidate})`
  -> `{group, update(dt) -> boolean (needs another frame), reset, dispose}`.
  Created by `src/viewer.js` only for asset `interactive-shopping-cart`; the
  viewer calls `update` in its loop, `reset` on view reset and `dispose` on close.
- Flow: fetch + parse `models/mall-shopper/exports/mall-shopper.glb`; requires
  rig nodes `Wheel_*`, `Steer_*`, `BasketItem` (else throws) and shopper arm
  joints. Buttons (grab/push/left/straight/right/stop/release/add/remove/reset)
  mutate `grabbed, targetSpeed, angle, itemState`. `update` integrates speed
  (acceleration 0.8), a kinematic-bicycle yaw, `Box3` collision with the
  obstacle (collision restores the previous pose and stops), wheel spin, item
  lift tween (0.6 s smoothstep) and a 16-pass CCD solve placing both hands on
  the handle when grabbed. Debug values are written to `toolbar.dataset.*`.
- State: all local; `reset()` restores a clean Idle state. No storage.
- Disposal: stops animation, removes toolbar, disposes obstacle and the shopper
  geometry/materials (not the cart `model`, owned by viewer); on early abort the
  shopper is disposed and an `AbortError` thrown.
- Tests: `tests/interactive-shopping-cart.test.mjs` (GLB asset/rig contract),
  `tests/mall-retail-pop-up-cart.test.mjs` (a different asset), browser
  `scripts/test-shopping-cart-browser.mjs`.
- Gaps: `demo.js` logic (collision, steering, CCD) has no unit test and relies on
  the browser script; the obstacle is a fixed box at z=2.1, not a general
  physics system (stated in the file comment).

## 7. Verification commands

`npm test` (i18n/color checks + `node --test tests/*.test.mjs`) covers the unit
tests listed above. Browser suites need a built `dist/` and Playwright:
`npm run test:browser`, `test:pwa`, `test:standard`, `test:solar`,
`test:game-ux`, `test:game-experience`, `test:game-responsive`.
