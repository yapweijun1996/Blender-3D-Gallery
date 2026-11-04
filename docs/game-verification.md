# Game verification evidence

Verification date: 2026-11-04 (Asia/Singapore). Tested from a clean remote-baseline checkout, with the original working tree preserved. Commands below are reproducible; generated local screenshots and JSON are outside tracked source.

## Executed checks

| Check | Result | Coverage |
| --- | --- | --- |
| `npm test` | 23/23 pass | Existing catalog/root/number-mark geometry plus rack, placement, turn/group/foul/eight rules, event sorting, stable saves, fixed-step physics, all six pockets and cushions |
| `npm run build` | Pass | Production relative-path build; all 22 catalog GLBs validated |
| Khronos glTF Validator | 22/22; zero errors and warnings | Each standalone asset and optional assembled scene independently |
| Blender 5.1.2 source audit | Pass | Metric scale 1.0, 21 asset roots, Ball 00–15, 141 meshes; no mesh validation repairs, missing UV/materials, nonfinite vertices or degenerate faces |
| `npm run test:browser` | 14 scenario groups pass | Thirteen Chromium groups plus WebKit shot smoke; details below |
| `npm run test:pwa` | 9 lifecycle checks pass | Full pack, offline startup and update failure/recovery; details below |
| Development skill client | Run; screenshots/text inspected | Actual game canvas and keyboard input through the existing web-game action client |
| Five-persona review | Findings fixed and affected paths rerun | Rules, gameplay, mobile, assets, PWA/reliability |

The source audit checks structural mesh validity, not a universal closed-manifold guarantee: curved number patches are intentional surface geometry. Browser tests inspect actual GLBs rather than replacing them with screenshots.

## Browser journeys

1. New match, invalid placement rejection, cue confirmation, duplicate Shoot protection, moving-ball pause/resume and stable shot completion.
2. Reload during a moving shot and restore the exact previous turn.
3. Single leave confirmation and repeated Game-link clicks during route loading.
4. `320×568` touch layout: complete viewport and Shoot can be visible together, no horizontal overflow.
5. `390×844` touch layout: same checks.
6. `844×390` landscape touch layout: same checks.
7. Second tab cannot write; after the owner closes it automatically acquires the match.
8. Injected IndexedDB failure keeps Save & return in the match and reveals explicit unsaved discard.
9. A checkpoint with a null ball is rejected as incompatible without crashing.
10. A stable eligible-eight fixture is resumed; the real physics pots the eight and finishes once with Player 1 winning.
11. Actual `WEBGL_lose_context` before a match and during a match offers a reload path and a usable replacement canvas.
12. All 22 gallery cards open real independent previews, reset, close/dispose and download valid GLB bytes; legacy Ball 08/full-scene deep links still work. Gallery entry requests no GLB until a preview opens.
13. WebKit at a phone viewport starts, shoots and settles without recovery.

The review separately simulated a browser without Web Locks: reload waited for lease expiry, automatically reclaimed ownership and enabled Resume. This is a browser simulation, not a physical iOS result. The review also repeated offline preparation while disconnected and verified that the complete previous pack remained ready.

## PWA lifecycle checks

1. First installation validates the shell; preparing offline saves all eighteen expected GLBs.
2. Offline cold start loads Game and resumes the checkpoint. Repeated preparation stays ready. Unknown offline GLBs return HTTP 503 text, never HTML.
3. Missing required JavaScript makes the candidate worker redundant; the active build and pack remain usable.
4. A deliberately mismatched `build-info.json` rejects candidate installation.
5. A valid new build waits; the old HTML and active game continue.
6. A different tab's active game blocks Update now.
7. Explicit N→N+1 update saves the turn, activates, reloads and resumes identical ball state.
8. Failed new-pack download keeps the previous good pack, deletes staging caches and preserves a synthetic sibling application's cache.
9. The updated build subsequently prepares successfully and starts/resumes offline.

These are real service-worker tests against production-format builds on a loopback HTTP origin. The N→N+1 fixture alters build/HTML identity in isolated copies while keeping the same production application assets. It is not a real network rollout between two different gameplay releases.

## Artifacts

Tracked deliverables:

- `src/game/`: game rules, table, physics, rendering, storage, UI and responsive styles.
- `src/pwa/`, `scripts/pwa-build.mjs`, `public/manifest.webmanifest`, `public/icons/`: PWA sources.
- `models/eight-ball-billiards/scene.blend`: editable updated table source.
- `models/eight-ball-billiards/exports/table.glb`: individual table; 6,360 triangles, 417,656 bytes.
- `models/eight-ball-billiards/exports/billiards-scene.glb`: optional assembled scene; 98,100 triangles, 3,518,732 bytes.
- `models/eight-ball-billiards/preview.webp`, `thumbnails/table.webp`: updated scene/table previews.
- Existing ball, cue, rack and chalk GLBs remain available under the same catalog identities.

Generated locally:

- `/tmp/blender-gallery-game-qa/results.json`, desktop, winning-eight, mobile and WebKit screenshots.
- `/tmp/blender-gallery-pwa-qa/results.json`, offline updated-game screenshot.
- `/tmp/blender-game-source-audit.json`: Blender structural audit output.
- `dist/build-info.json`, `dist/game-pack.json`, `dist/sw.js`: emitted build identity and offline contract.

## Limits and release evidence

There was no attached physical iOS/Android device. Installation UI, real home-screen behavior, mobile GPU performance, memory pressure and browser storage eviction remain hardware checks. No claim of 30/60 fps on a particular phone, full accessibility certification, cross-browser bit-identical physics or tournament simulation is made.

The Pages workflow is gated by these suites. The exact deployed commit and workflow result should be checked in GitHub Actions and against `build-info.json`; the final delivery message records the verified remote release. Local checks alone are not a deployment claim.

## First-entry correction

A subsequent live review found that setup had an empty table and the phone start button below the fold; the earlier responsive checks covered active play only. Setup now renders real rack geometry and places phone start controls before the table. A separate first-entry viewport regression covers phone and desktop framing. This is a correction to the coverage gap, not a claim of a complete visual redesign.
