# Eight-ball Game — implementation and delivery

This document records the delivered implementation of the requested Game plan. It distinguishes implemented behavior, repeatable verification and device checks that still require hardware. The original detailed planning copy in the earlier working tree was preserved.

## Outcome and scope

The new **Game** navigation opens `?page=game`. Two people play Casual Eight-Ball on one device, using this repository's original, independently exported table, cue and sixteen ball GLBs. The gallery and its old `?model=...` links remain available. No account, backend, advertising service or external model download is required.

The delivered game includes a seeded valid rack, cue placement, aiming, shot power, collisions, cushions and pocket jaws, six pockets, alternating turns, group assignment, fouls, ball in hand, eight-ball win/loss, pause, restart, saved-turn resume and interrupted-shot recovery. App installation and an explicitly prepared offline game pack are included.

Online multiplayer, an AI opponent, competitive WPA rules, called pockets, spin, jump shots, photorealistic texture work and full rigid-body simulation are outside this version's contract.

## Delivery sequence and ownership

| Stage | Delivered result | Authoritative implementation |
| --- | --- | --- |
| Inspect | Existing catalog, GLBs, Blender source, gallery and Pages workflow inspected before edits | `models/catalog.json`, source `.blend`, project docs |
| Rules | Versioned Casual Eight-Ball contract and pure adjudication | `src/game/rules.js` |
| Geometry | Measured table and six pocket approaches, matching visual pocket jaws | `src/game/table.js`, `models/eight-ball-billiards/generate.py` |
| Simulation | Fixed-step planar ball motion and recovery boundaries | `src/game/physics.js` |
| Rendering | Reused individual GLBs, one game canvas, explicit inspect mode | `src/game/scene.js` |
| Interaction | Responsive local two-player interface, keyboard/touch controls and dialogs | `src/game/page.js`, `src/game/style.css` |
| Persistence | Validated stable checkpoints, pending-shot markers and one writable session | `src/game/storage.js` |
| PWA | Manifest/icons, verified offline resources and guarded updates | `src/pwa/`, `scripts/pwa-build.mjs` |
| QA | Unit, geometry, real browser and PWA lifecycle checks | `tests/`, `scripts/test-*-browser.mjs` |
| Release | CI gates and Pages deployment on `main` | `.github/workflows/deploy.yml` |

## Architecture

The existing Vite, vanilla JavaScript and Three.js stack is retained. Introducing React, a backend or a second asset catalog would add unnecessary migration risk for this scope.

```text
models/catalog.json ── build metadata / emitted URLs ── gallery
                                            └─────── lazy Game route
                                                     ├─ page: lifecycle + inputs
                                                     ├─ scene: Three.js presentation
                                                     ├─ physics: positions + events
                                                     ├─ rules: one final shot decision
                                                     └─ storage: stable checkpoints

production build ── shell identities + 18-file pack ── service worker
```

Physics and rules do not depend on Three.js or the DOM. Rendering consumes positions; it does not own match outcomes. `table.js` owns gameplay dimensions and the group mapping. `rules.js` owns turn decisions. Stored records carry both rules and table versions, and incompatible records do not silently migrate.

Gallery cards remain lightweight posters. Entering Game imports its code and creates one canvas. The game loads only eighteen individual model files, with four concurrent loads: Pool Table, Cue Stick 01, Cue Ball and Ball 01–15. It does not load the assembled scene and then overlay a second set of balls. Abort, route changes and disposal release the canvas, scene geometry/materials, controls, resize observation, event handlers and timers.

`render_game_to_text()` exposes bounded observable state for QA. `advanceTime(ms)` advances the same fixed-step simulation used by normal animation; it is not a separate rules engine or a winning-state cheat.

## Asset and coordinate contract

- Blender source units: metric, unit scale `1.0`.
- Export/world coordinates: Y up; gameplay X runs along the table, Z across it; distances are meters.
- Table outside dimensions are approximately `2.54 × 1.40 m`; ball diameter is `0.05715 m`; cue length is `1.47 m`.
- Felt elevation is `0.7785 m`; ball centers sit one radius above it.
- Cushion contact planes are X `±1.10495`, Z `±0.52096`.
- Pocket centers are X `-1.12`, `0`, `1.12` at Z `±0.56`.
- Long-rail ends, side openings and end-rail ends are modeled as explicit contact segments and jaws. The source's original corner openings blocked a ball, so the cushion lengths were shortened and twelve matching visual jaw pieces added.
- Standalone table, full scene, editable source, generator, table thumbnail and assembled WebP preview were regenerated together. Existing ball, rack, chalk and cue publication files remain independent.
- Materials retain the repository's glTF-compatible PBR values. Original curved number markings remain attached to their balls. No logos, branded artwork or third-party asset copies were added.

The asset pack remains a simplified untextured design. UV layers exist, but a newly authored texture atlas or baked texture set is not claimed. The project has not selected redistribution terms; adding gameplay does not change that licensing decision.

## Casual Eight-Ball v1

| Situation | Result |
| --- | --- |
| New match | Player 1 places the cue behind the head string and breaks |
| Rack | Fifteen object balls; eight in the middle; opposite rear corners from different groups |
| Break | Groups remain open; a legal object pot keeps the turn |
| Eight on break | Re-spot the eight; a simultaneous scratch gives the opponent ball in hand |
| Open table | First legal post-break object pot assigns solids/stripes |
| Mixed pots | Sort by simulation tick, substep and then ball ID; input array order cannot choose the group |
| Assigned group | First contact must be an active own-group ball, or the eight if the group was already cleared before the shot |
| Scratch, wrong contact, no contact | Opponent gets ball in hand; already pocketed object balls stay pocketed |
| Legal own pot | Same player continues |
| Miss or opponent-only pot | Turn passes |
| Legal eight | Win only when own group was cleared before the shot and the complete shot has no foul |
| Early eight, last own ball plus eight, eight with scratch/foul | Shooter loses |
| Open table with every group ball already gone | Either player may play the eight; this prevents an unwinnable edge case |
| Invalid simulation | Restore the pre-shot checkpoint; do not invent a foul, pot or winner |

There is no called-pocket rule, four-rail break requirement, post-contact rail requirement, spin or jump mechanic. These differences are shown in Rules & controls. The game does not claim tournament rules compliance.

A shot resolves once after every ball settles. The shot ID prevents duplicate adjudication. Eligibility for the eight is computed from the pre-shot snapshot, which prevents clearing the final group ball and the eight in one shot from becoming an accidental win.

## Simulation decision

A small analytical disk solver is used instead of adding a WASM rigid-body engine. Sixteen equal-radius balls on one fixed plane need circle contacts, cushion segments and pocket capture; a standalone solver keeps these boundaries inspectable and testable without coupling gameplay to rendering. This is a deliberate implementation change from the plan's physics-library exploration; no head-to-head Rapier performance benchmark is claimed.

- Fixed simulation step: `1/120 s`, independent of render rate.
- Adaptive substeps bound travel relative to ball radius. Repeated contact iterations resolve crowded racks and rail endpoints.
- Equal-mass impulses, ball/cushion restitution and rolling deceleration provide casual pool motion.
- Rolling quaternions follow displacement so the actual numbered ball meshes rotate.
- Each pocket capture is recorded once, with tick and substep identity.
- Low-speed settling requires a sustained quiet interval; adjudication does not run after a single quiet frame.
- Nonfinite positions, escape bounds or excessive shot duration trigger explicit recovery.
- Backgrounding pauses the match and clears accumulated wall time. Returning does not simulate a long hidden interval.

This model omits cloth-dependent spin, squirt, swerve, jump, airborne motion and scientific calibration against a real table. Repeatability is tested in the same JS engine; bit-identical replay across every browser is not promised.

## Interaction and responsive layout

Desktop uses a table plus controls sidebar. Portrait phones put the table above a compact aiming/power and Shoot/menu area. Short screens reduce heading and player-card height so the complete table and primary shot control can be visible together. No forced device orientation is required.

- Drag/tap on the table to aim or position the cue. Releasing the pointer sets the aim; it never shoots.
- Aim and power ranges provide precise alternatives to dragging. Desktop also offers one-degree buttons.
- When the table is focused, arrows change aim or placement, Shift makes finer changes, Enter confirms placement, Space shoots and F toggles fullscreen.
- Inspection explicitly enables orbit and zoom. Shooting is disabled until returning to Aim.
- Pause, restart confirmation, rules, app options and installation help use native dialogs.
- Touch handling uses pointer capture; cancellation stops dragging. The aim guide estimates initial contact only.
- WebGL loss hides shooting and offers save/reload; it never enables play on a lost canvas. This also works before a match exists.
- Idle aiming reuses a fixed line buffer and does not continuously redraw the canvas. Motion, input, camera changes and resize request actual renders.

Automated viewport checks cover `320×568`, `390×844` and `844×390`, including no horizontal overflow. Browser resizing and touch emulation do not establish real-device frame rate or installation behavior.

## Persistence and interruption recovery

IndexedDB stores a stable checkpoint and optional pending-shot marker in a single transaction. A checkpoint contains schema/rules/table versions, match and revision IDs, shooter, groups, break/placement/winner state, sixteen ordered ball identities, positions and orientations.

Validation rejects duplicate or shuffled identities, malformed/null entries, nonfinite data, motion in a stable checkpoint, invalid groups, incompatible versions, overlapping balls and contradictory cue/eight/phase/winner states.

Before a shot, the complete pre-shot checkpoint and pending ID are saved. Once the full shot settles and rules finish, one new stable checkpoint replaces it. Reloading during motion restores the previous complete turn and explains why the unfinished shot was discarded. It does not attempt to resume half a collision simulation.

Web Locks give one tab write ownership and automatically release on page termination. A twenty-second IndexedDB lease and periodic reacquisition cover browsers without that API; a reload in that fallback may wait for expiry. A second tab waits rather than overwriting the match. Ownership is checked again before shooting. After ownership is reacquired, interaction stays locked until the latest checkpoint is loaded. Conflicting unsaved local progress is retained and requires an explicit leave or reload rather than overwriting the shared checkpoint.

If storage is unavailable, in-memory play still works with a warning. Save & return remains in the match on failure and offers an explicit Leave without saving choice. Route navigation also warns before discarding an unfinished shot or unsaved progress. Browser storage eviction, clearing site data and different origins can remove or separate local saves; no cloud backup is implied.

## PWA and offline contract

The manifest supplies a stable app identity, standalone display, relative scope/start URL, opaque colors and original 192/512 icons. Install help covers browser installation and iPhone Add to Home Screen. Installation and offline preparation are separate actions.

The build emits `build-info.json`, `game-pack.json` and `sw.js`. The pack contains exactly eighteen GLBs, totaling **3,697,784 bytes** in this revision. The app shell additionally includes HTML, JavaScript, CSS, manifest and icons. Gallery thumbnails, every gallery download, editable Blender files and the assembled showcase are not promised offline.

1. Installation checks build identity and the byte length and SHA-256 of every required shell resource. A bad candidate fails closed.
2. **App options → Make available offline** verifies the game GLBs, stages a complete candidate cache and publishes readiness last. Repeating preparation on an already ready offline pack returns success without touching it.
3. Failed preparation never deletes an existing good pack. Partial candidate caches are not used by normal fetches.
4. Navigation serves one cached HTML build. Hashed resources remain versioned. Missing offline GLBs return a text error, not an HTML fallback.
5. A new worker waits. Update now first saves a stable match; an unfinished shot blocks activation.
6. Every scoped tab must acknowledge readiness. Another playing or unresponsive tab blocks activation.
7. Successful activation reloads the requesting page once. Saved stable checkpoints survive compatible releases.
8. Cache names include the project scope. Cleanup affects only this project's caches and conservatively retains usable versions while tabs exist. Complete scoped versions are retained even after tabs close; automatic eviction is deliberately deferred to protect suspended clients and previous complete packs. Browser quota is not guaranteed. See the authoritative [PWA amendment contract](pwa-standard.md) for retention and legacy-client migration exceptions.

The implementation follows the browser's [service-worker lifecycle](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers), [Web Locks coordination model](https://developer.mozilla.org/en-US/docs/Web/API/Web_Locks_API), and the relevant [Web Application Manifest fields](https://www.w3.org/TR/appmanifest/). These references describe APIs; they do not certify the application or replace device testing.

## Five-persona review and acceptance

| Persona | Main concern | Verified resolution |
| --- | --- | --- |
| Pool player / rules reviewer | Groups, foul timing, break eight, simultaneous events and winning paths | Pure rules tests, deterministic event sorting, whole-shot decision and browser winning-eight fixture |
| Gameplay engineer | Collision stability, pocket access and visual alignment | Six pocket fixtures, rail/low/high power checks, seeded breaks, matching Blender jaws |
| Mobile UX reviewer | Table and Shoot visible together; accidental camera/shot input | Three short/phone viewport checks, separate inspect mode and explicit Shoot |
| 3D asset reviewer | Correct ball identities, scale, independent models and retained gallery | Blender source audit, curved number tests, Khronos checks and all 22 gallery preview/download journeys |
| PWA / reliability reviewer | Bad updates, offline refresh, storage failures, multiple tabs and WebGL recovery | Failure injection, N→N+1 update tests, interrupted-shot resume and context-loss reload |

See [verification evidence](game-verification.md) for executed checks and their limits. A review finding is not treated as fixed until the affected scenario has been rerun.

## Develop, verify and release

Use Node.js 24 and Blender 5.1.2 for source regeneration.

```sh
npm ci
npm test
npm run build
npx playwright install --with-deps chromium webkit
npm run test:browser
npm run test:pwa
npm run dev
```

Browser scripts serve `dist/` on an ephemeral local port under `/Blender-3D-Gallery/`. They create their own contexts and write results/screenshots under `/tmp/blender-gallery-game-qa` and `/tmp/blender-gallery-pwa-qa`, or `TEST_ARTIFACT_DIR`. The PWA test generates isolated candidate builds; it does not replace production files.

The Actions workflow runs unit/asset/build and both browser suites before deploying `dist/` on a `main` push. The release procedure is a focused feature commit, fast-forward merge to current `main`, ordinary non-forced push, successful Pages workflow and direct checks of the published Game and gallery. Rollback is a normal revert followed by the same verified deployment, with compatible local-save versions retained where possible.

## Remaining validation limits

No physical iPhone, Android phone or tablet was attached for this delivery. Home-screen installation, safe areas with actual browser chrome, storage pressure and sustained thermal/frame-time behavior require those devices. WebKit headless is useful coverage but is not iOS certification. The renderer's shared Three.js chunk still exceeds Vite's 500 kB advisory threshold; it remains lazy and is not a per-card canvas. No unsupported mobile performance score or universal PWA certification is claimed.

## Subsequent game reliability and accessibility work

The 2026-11-05 review preserves the same rules, checkpoint schema and assets. It tightens keyboard and pointer ownership, preserves a pending background pause through asynchronous work, releases late Web Locks after route exit, and keeps recovery available after loading or WebGL failures. Mobile play shows a concise aiming hint and real progress, including numbered remaining balls for assistive technology. App options offers a session-only Performance quality setting that lowers the renderer's pixel-ratio cap; Standard retains the original cap. See the [baseline](audits/game-baseline.md), [gameplay contract](game/gameplay-contract.md) and [release readiness](game/release-readiness.md) for executed evidence and remaining limits.
