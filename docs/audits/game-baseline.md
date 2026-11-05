# Game baseline audit

Audit date: 2026-11-05 (Asia/Singapore). This document records observations **before application changes**.

## Revision and environment

- Baseline commit: `38350b3933aa5d60bc7207d50b2e5577ae8781c3` (`main`). Isolated worktree branch: `codex/game-experience-improvements` at the same commit.
- The original working tree contained the untracked `docs/game-implementation-plan.local.md`; it was not copied, modified or removed. The isolated worktree was clean before the audit artifacts were created.
- macOS arm64, Chromium 156.0.8078.4. The first audit used Node 23.10.0 / npm 10.9.2. A separate clean archive of the same commit was subsequently installed, unit tested and built with the documented Node 24.21.0 / npm 11.19.0. npm warned that the optional `fsevents` install script was not approved; that clean archive's unit test and build still passed.
- Browser measurements used the existing Playwright Chromium launch flags for SwiftShader software WebGL, loopback HTTP, a production-format build and fresh browser contexts. This is not physical-device or hardware-GPU performance evidence.
- The routed `instruction-modules/investigation.md`, `verification.md` and `architecture.md` files were absent from the repository; the supplied core instructions, checked-in project guidance, skills and actual evidence were used instead.

## Actual implementation

`src/main.js` maps `?page=game` to a lazy import of `src/game/page.js`; leaving aborts and disposes the mounted page. Gallery, About and `?model=...` links remain in the same static Vite application. `src/game/page.js` owns interaction, match phases, dialogs, a requestAnimationFrame loop, visibility handling and route cleanup. `src/game/physics.js` performs the fixed 1/120-second planar simulation, `rules.js` adjudicates each shot, `table.js` defines dimensions and rack/placement, and `storage.js` owns validated IndexedDB checkpoints and cross-tab ownership. There is no third-party physics engine.

`src/game/scene.js` owns a Three.js orthographic camera, hemisphere and directional lights, OrbitControls for inspection, four-way concurrent GLB loading, resize observation and disposal. The game loads the table, cue and 16 individual ball GLBs, not the assembled scene. Render pixel ratio is capped at 1.5. `src/game/style.css` owns the game layout; `src/pwa/` and `scripts/pwa-build.mjs` own the offline/update contract. `.github/workflows/deploy.yml` runs the checks and deploys on `main`; this audit did not invoke it.

The project KB's architecture, asset, UX and quality records were read as proposed context. Its React/TypeScript and model-directory proposals do not describe this revision's actual vanilla JavaScript implementation. The existing original asset pack has source and reproducibility information, but redistribution terms remain unspecified. No asset was changed.

## Confirmed baseline behavior

- Local two-player casual eight-ball: new match, placement, aiming, power, shooting, physics, fouls, turn progression, win/loss, pause/resume and stable-turn saves. Existing tests exercise a physically potted winning eight, interrupted shots, multiple tabs and WebGL context-loss reload.
- Pointer aiming changed the aim at 360×800 and 390×844 with touch emulation and at 768×1024 and 1440×900 with mouse input. Pause/resume returned to aiming at each size. No document-level horizontal overflow was measured at those sizes.
- Missing and invalid GLBs and an unavailable WebGL context did not start a game; a text fallback was shown. Existing context-loss recovery passed its browser test.
- Setup, active-game and paused screenshots were captured. The four active-game screenshots are [360×800](../../output/playwright/game-audit/baseline/aiming-360x800.png), [390×844](../../output/playwright/game-audit/baseline/aiming-390x844.png), [768×1024](../../output/playwright/game-audit/baseline/aiming-768x1024.png), and [1440×900](../../output/playwright/game-audit/baseline/aiming-1440x900.png). Raw observations are in [results.json](../../output/playwright/game-audit/baseline/results.json).

## Findings and proposed sequence

No P0 was reproduced in this baseline. Severity reflects this task's user impact, not a claim that all defects were found.

| ID | Priority | Reproduction and impact | Evidence / intended correction |
| --- | --- | --- | --- |
| G-01 | P1 | Start a match, confirm placement, click the page heading so focus is on `BODY`, then press Space: the phase changes from `aiming` to `moving`. A player can accidentally strike while the table is not focused. | `keyboardOutsideTable` in results; `src/game/page.js` listens on `window` although the documented shortcut is table-focused. Scope gameplay shortcuts to the table while retaining normal semantic controls. |
| G-02 | P1 | At 390×844, inject an IndexedDB-open failure, start a match: `#save-status` contains “Autosave unavailable. Keep this tab open.” but is not visible; the game status gives no save warning. A player may believe progress is saved. | [Screenshot](../../output/playwright/game-audit/baseline/mobile-storage-failure.png); mobile `.is-playing .save-status` is hidden in `src/game/style.css`. Keep failures visible without crowding normal play. |
| G-03 | P2 | Abort a game GLB, serve invalid GLB bytes, or deny WebGL: the page displays a fallback but no direct retry action; a raw loader error appears as save status. | `faults` in results. Offer a clear, accessible recovery path without exposing raw errors as save state. |
| G-04 | P2 | At 360×800 and 390×844, Rules is 30px high and Inspect/Options are 36px; at 768 and 1440 the latter are 38px. | Measured button rectangles in results. Improve practical touch targets while preserving the compact scene and primary controls. |
| G-05 | P1 | Start a shot and background the page while its IndexedDB save/ownership check is still pending. Two independent Chromium probes delayed transaction completion and observed `moving` while hidden and after returning, without a pause dialog. | `pause()` returns while `busy`; `shoot()` can enter `moving` after the visibility event. Preserve the pending pause through asynchronous transitions and test the actual race. |
| G-06 | P2 | Resume a valid game with assigned groups on a 390px viewport: the real remaining-ball and “8 BALL” text is present in the DOM but hidden with `display: none`. | `.remaining` is hidden at widths up to 900px, including from assistive technology. Expose compact, real progress without inventing scores. |
| G-07 | P1 | Delay the first Web Lock request during Game initialization, return to Gallery before it resolves, then re-enter Game: the original session can retain the lock and the new page reports that another session owns the match. | Two independent Chromium probes delayed the lock request; the late acquisition can occur after disposal. Ensure a disposed store cannot retain a late lock, with a repeated-route regression. |
| G-08 | P2 | On a touch-emulated canvas, put down two fingers, release the first, then move the second: a `pointermove` is delivered but aiming no longer changes. | `pointerdown` replaces the active pointer, while every `pointerup`, `pointercancel` and `lostpointercapture` clears it regardless of pointer identity. Coordinate pointer ownership and cancellation. |
| G-09 | P2 | On the frozen baseline build, start a match, pause, lose WebGL context, then press Escape: the phase is `recovery` but the pause dialog remains open and obstructs the recovery action. | Reproduced in Chromium at 390×844 using `WEBGL_lose_context`; see [screenshot](../../output/playwright/game-audit/baseline/context-loss-paused.png). Close the obstructing dialog and focus recovery. |

First fix G-01/G-02/G-05/G-07 with regression tests; then G-03/G-04/G-06/G-08/G-09 with browser and visual checks. Preserve game mechanics, checkpoint format, PWA protocol, Gallery, About, downloads, deep links and all GLBs. Do not replace the existing state, physics or rendering architecture without an observed need.

## Executed checks

| Command / check | Baseline result |
| --- | --- |
| `npm ci` | Passed; 20 packages installed, npm reported 0 vulnerabilities. |
| `npm test` | 23 passed, 0 failed or skipped. |
| `npm run build` | Passed; glTF Validator reported 0 errors and 0 warnings for all 39 catalog GLBs. Vite reported its existing >500 kB lazy Three.js chunk advisory. |
| `npm run test:browser` | Passed: 13 Chromium scenario groups plus WebKit shot smoke, including all 39 gallery preview/download paths and context loss. |
| `npm run test:pwa` | Passed: 9 PWA/offline/update scenarios. |
| Node 24 clean archive: `npm ci`, `npm test`, `npm run build` | Passed; 23 unit tests passed. npm emitted the optional `fsevents` install-script warning noted above. |
| `node scripts/audit-game-observations.mjs baseline` | Equivalent audit harness ran against the baseline; four viewport journeys, pointer input, pause/resume, missing/invalid assets, no WebGL, keyboard-focus probe and three timing samples. The first harness attempt stopped on an ambiguous heading locator; it was corrected and rerun successfully. |
| Mobile save failure | Separate Chromium touch-emulated run injected an IndexedDB-open error; confirmed the warning text exists but is hidden after a match starts. |

The observation script now refuses to overwrite an existing evidence directory. For a repeat, use a new mode name or an empty `TEST_ARTIFACT_DIR` (for example, `node scripts/audit-game-observations.mjs baseline-repeat`).

## Repeatable local performance observations

With 1440×900, DPR 1, SwiftShader and an unthrottled loopback server, three fresh-context runs reached the game's `ready` signal in **214, 223 and 224 ms**. During a five-second requestAnimationFrame sample started by a real break and continuing into its settled state, p95 frame intervals were **50.1 ms** in each run and average intervals were **34.5, 31.6 and 34.5 ms**. These are browser frame-pacing observations for this software renderer, not isolated GPU timings, guaranteed gameplay FPS, network-load estimates or physical mobile results. The sample mixes motion and settled frames. No optimization is justified solely by these numbers.

The 18 game GLBs total **3,697,784 bytes** and contain no image or texture entries or external image/buffer URIs. A separate WebGL2 call counter in Chromium measured one forced render at 1440×900: setup **135 calls / 97,208 triangles**, aiming **140 / 97,500**, moving **135 / 97,208**. These are submitted draw counts, not GPU durations. A ten-cycle same-page navigation probe with immediate forced JS garbage collection recorded 61 listeners/739 nodes before Game and typically 90–95 listeners/748–942 nodes after returning to Gallery; heap values and node counts fluctuated. [Raw observations](../../output/playwright/game-audit/baseline/memory-immediate.json) do not by themselves prove or disprove a leak, especially for GPU resources.

## Unverified concerns

- Physical Android/iOS behavior, browser chrome and safe areas, real GPU frame times, texture memory, thermals and long-session memory leaks were not measured. Touch emulation and WebKit desktop are not device certification.
- The current suite does not establish every requested keyboard, touch cancellation, repeated-restart, missing/corrupt asset and reduced-motion path. Complete accessibility conformance, screen-reader usability and artwork redistribution rights are not established.
- No production deployment, remote PR, CI run, public release or KB write was performed by this audit.
