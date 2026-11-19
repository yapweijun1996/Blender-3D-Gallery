# Eight-Ball Shooting Interaction — Task & Acceptance Tracker (v1.1 Left-side Pull & Release)

> **Status:** `Remote Verified Complete — Acceptance 16/16` — the full CI build/deploy succeeded and the matching production build passed a cold offline touch-shot check. The application release and subsequent runner mirror-configuration follow-up are verified; see sections 10–11. See the final release record below; prior failure notes are preserved.
> **Core flow:** `Aim → Hold Left Power Handle → Drag Down → Cue Pulls Back → Release → Cue Strikes → Balls Move`
> **Spec:** [docs/game/gameplay-contract.md](docs/game/gameplay-contract.md) — "Left-side Pull & Release Shooting Specification v1.1" (supersedes v1.0 §4.3/§5/§6 on-table cue grab)
> **Branch / worktree:** `feat/eight-ball-left-pull-release`, isolated from the original dirty checkout; baseline `39615f7`; full feature acceptance build `66837cb8b2817ced`; initial Saga-integrated build `7a61e8ae1a814835`; current corrective application build `0473d7f6bfac8301`.

---

## 1. Implementation Phases

| Phase | Deliverable | Key modules (verified paths) | Gate | Status |
| --- | --- | --- | --- | --- |
| 1 | Left power handle, pointer capture, `pullRatio` from pointer-down origin, clamping, cancellation | `src/game/page.js`, `src/game/style.css`, new pure helper module + unit tests | Input unit tests | `[x]` |
| 2 | Cue backward offset from `pullRatio`, locked aim, deterministic forward strike, single contact event | `src/game/scene.js`, `src/game/page.js` | Animation/contact tests | `[x]` |
| 3 | Idempotent `ShotIntent` → existing `createShot` (strength = `pullRatio^1.5`), no shot while moving/paused | `src/game/page.js`, `src/game/physics.js` (reuse, no rewrite) | Shot unit + integration | `[x]` |
| 4 | Remove Shoot button & power slider; update browser tests to real mouse/touch pull; responsive/landscape QA | `src/game/page.js`, `src/game/style.css`, `scripts/test-game-*.mjs`, `scripts/browser-test-utils.mjs` | Full Playwright regression | `[x]` |

## 2. Mandatory Behavior Checklist

- [x] Drag-only aim: dragging the felt aims at the pointer, the cue shaft can be grabbed and dragged; hover and tap never change aim (supersedes the earlier hover-aim behaviour)
- [x] Pointer down on the **left handle** (only) starts `CHARGING`; aim locked
- [x] Dragging down moves handle, fills meter, pulls visible cue back along its axis (same `pullRatio`)
- [x] Release ≥ 5% → forward strike → exactly one impulse at cue contact
- [x] Release < 5% / tap without drag → cancel, no shot
- [x] `pointercancel`, `lostpointercapture`, blur, Escape → cancel uncommitted charge
- [x] Second pointer ignored; duplicate `pointerup` never shoots twice
- [x] Release outside controller still shoots when capture is active
- [x] Controller disabled during placement, motion, resolution, pause, inspection, context loss, game over
- [x] Handle resets after commit; cue hidden while balls move
- [x] Rules, physics, checkpoint schema (`aiming`/`placing`/`finished`) and save behaviour preserved
- [x] Keyboard secondary path: focusable handle, Arrow keys charge, Space/Enter release

## 3. Prohibited

- [x] No Shoot button · No power slider as primary control · No click-to-shoot · No shot on pointer down · No shooting by dragging anywhere on the table · No track-click shot

## 4. Acceptance Tests (16/16 — locally verified)

- [x] 1. Mouse drag on handle charges and releases a shot
- [x] 2. Touch drag on handle charges and releases a shot
- [x] 3. Short drag (<5%) cancels
- [x] 4. Long drag clamps at 100%
- [x] 5. Reverse (upward) drag yields 0% and cannot shoot
- [x] 6. Pointer cancel / lost capture never shoots
- [x] 7. Duplicate release → one impulse
- [x] 8. Cue offset ∝ `pullRatio` and aligned with aim
- [x] 9. Impulse applied at contact, not at release
- [x] 10. ~80% pull gives higher initial cue-ball speed than ~30%
- [x] 11. No shooting while balls move
- [x] 12. No shooting while paused; pause during strike cancels without double-fire
- [x] 13. Save/reload never replays committed shot
- [x] 14. Turn resolution after all balls settle
- [x] 15. Mobile landscape: table + controller visible, no page scroll during drag
- [x] 16. Existing Game/PWA/library/reviewed browser suites pass after test migration

## 5. Rack & Break Setup (unchanged)

- [x] 15-ball tight triangle · [x] 8-ball center of row 3 · [x] apex on Foot Spot · [x] solid/stripe rear corners
- [x] Break placement behind head string enforced (`legalPlacement`) · [ ] head-string visual guide (v1.0 P0-2, deferred)

## 6. Preserved Historical Workspace Notes

The original design recorded untracked v1.0 prototype files (`src/game/interaction.js`, `tests/game-interaction.test.mjs`) and an empty `feat/eight-ball-gameplay-interaction-v1` branch. Those notes describe that earlier workspace, not the current implementation branch. No cleanup or deletion of those prototypes was authorized or performed.

The original checkout remains on `codex/game-experience` with unrelated tracked and untracked work. This delivery uses an isolated worktree and does not overwrite that work. The earlier note that the main checkout was on `main` is historical, not current Git evidence.

## 7. Local Verification Record

- Saga-integrated application build: `7a61e8ae1a814835` at merge `4b54607`; current released application build: `0473d7f6bfac8301` (see final release record below). Full feature acceptance was executed on build `66837cb8b2817ced`; implementation baseline: `39615f7`. See the integration record below for the exact final-tree checks.
- Environment: macOS arm64, Node 24.21.0, pinned Playwright 1.64.1; Chromium/SwiftShader and WebKit where recorded. Mobile touch, viewport and safe-area checks are emulated, not physical-device certification.
- `npm test`: 85 passed. Production build passed; the existing shared Three.js chunk-size advisory remains.
- The full Game browser regression passed 45 groups and UX passed 7 groups on `c111bb7a831289f9`. Subsequent runtime changes were confined to narrow-screen framing, spacing and placement-button text; existing physics, input and storage logic remained the same. The affected final-build checks below were rerun separately.
- On final build `66837cb8b2817ced`, all 30 left-pull acceptance groups passed, including exact-threshold/repeated-release input, fixed-step burst equivalence, direct placement, Reset, pending-save cancellation and keyboard controls. All 16 PWA groups passed, including the new charged-handle update/late-release scenario.
- Independent manager checks also passed: PWA standard 9, reviewed regressions 8, loading 6, library 9 in isolation and Solar assets 17. The library timeout under concurrent browser load was compared with the baseline; both baseline and candidate passed in isolation without a library code change.
- Final build responsive checks passed 20 placement/aiming cases over 10 viewport sizes. Mobile/accessibility follow-up passed all 20 cases, including narrow Reset/Place text fitting.
- Independent final geometry checks parsed the actual table GLB (2.540000066 × 1.399999976 meters in the table plane). At 568 × 320 the measured camera span gives a 4.944047 px ball diameter; the full cabinet and all six pocket circles fit. The 44 px handle, table and Pause remain inside injected 24/18/28/14 px safe insets, with zero horizontal overflow and 153 px bounded scrolling.
- Independent actual-GLB contact checks measured approximately 0.072 m retraction at 60% charge and a contact gap below 1e-7 m before the single impulse. A pointer-owned charge ignores keyboard release. Valid/invalid white-ball drag recovery and a real Reset/Place commit were also exercised.
- The unchanged `develop-web-game` client reached a real `moving` state with one committed shot on the final application build; screenshots were inspected. The client was copied unchanged to resolve the repository's pinned Playwright dependency.
- Initial failures were retained and investigated: active-handle disabling, deferred contact commit, narrow safe-area clipping, projected ball size, obsolete input shortcuts, random-rack comparison, range-input quantization and stale ResizeObserver screenshots. Correctness fixes and assertion migrations retain real pointer/touch input and strict impulse, geometry, target-size and recovery checks.

Local logs and artifacts: `/tmp/left-pull-manager-final-unit.log`, `/tmp/left-pull-manager-final-build.log`, `/tmp/left-pull-main-c111-final.log`, `/tmp/left-pull-ux-c111-final.log`, `/tmp/left-pull-acceptance-668.log`, `/tmp/left-pull-pwa-668.log`, `/tmp/left-pull-responsive-668.log`, `/tmp/left-pull-followup-668.log`, `/tmp/left-pull-review-geometry-final.json`, `/tmp/left-pull-test-summary.md`, and `/tmp/left-pull-66837-stock/`. These local files are execution evidence, not a claim of remote publication.

## 8. Remaining Limits

- The head-string visual guide remains explicitly deferred, as recorded above; the existing legal head-string placement rule remains active.
- Physical iOS/Android, actual installed-PWA/browser-chrome behavior, VoiceOver/TalkBack and sustained device GPU/thermal performance remain unverified.
- Existing asset-redistribution decisions remain owner-deferred. This task changes neither licensing nor asset/download policy.
- Local regression acceptance is complete. These local results alone did not establish a production release; the later final release record supplies the remote workflow and matching live evidence.

## 9. Post-Commit Main Integration

Feature commit `17e7639` was merged with the newly fetched `origin/main` revision `d3055c5` in isolated merge `4b54607`. The upstream change contains only 15 Proton Saga asset/source/preview files. All Game source, Game model bytes, shared application source, dependency manifests and the migrated test sources are unchanged from the accepted feature commit; no Saga work was overwritten.

The primary manager independently executed these checks on that merged tree with Node 24.21.0:

| Check | Observed result | Local evidence |
| --- | --- | --- |
| `npm test` | 85 passed, zero failed | `/tmp/left-pull-merged-unit.log` |
| `npm run build` | Passed; final build `7a61e8ae1a814835` | `/tmp/left-pull-merged-build.log` |
| `npm run test:library` | All 9 groups passed in isolation, including the updated catalog assets | `/tmp/left-pull-merged-library.log` |

The full Game/PWA/pull-acceptance evidence above remains pinned to the feature builds and unchanged Game sources; it is not a claim that every Game suite was executed again after the Saga-only merge. Publication and live build identity are recorded in the later final release record.

## CI follow-up — historical failure and locally verified repair

All pending, under-review and incomplete-verification statements in this chronological section describe their recorded checkpoint, not the current release status. The final release record supersedes those gate states while preserving the failures and their evidence.

- GitHub Actions run `42196409550` failed the strict mobile layout assertion: the Pause button bottom was `807.984px` at a viewport height of `800px`. This is a confirmed platform-dependent layout regression, despite the earlier local acceptance evidence. No successful publication or live verification is claimed.
- The repair increases the tall-portrait viewport height reserve by 30px, preserving its aspect ratio, control sizes and existing ball-size/framing guards. Regression coverage includes 360×800 first-fold checks with multiple font families and a 360×651 safe-area boundary case. A 142px viewport-width floor preserves ball visibility at that boundary. Independent macOS Chromium repair checks passed on build `e6f5639e278e005c`: at 360×800 the Pause bottom is `767.984px` (32.016px spare), with zero scrolling/overflow under Arial, Verdana and system-ui controls; 44px targets and full cabinet/pocket visibility remain intact. Actual projected balls measure `8.29254px` at 360×800 and `4.944047px` at 568×320, retaining the strict 4.9px guard. Raw evidence: `/tmp/left-pull-ci-review.json`; the 360px screenshot was inspected. These local checks do not establish Linux success: the successful remote CI rerun remains pending.

- Final corrective application build `e641654ce031dfd9`: full responsive 12 journeys/24 placement and aiming states passed with no recorded errors; minimum projected ball `4.944047px`. At 360×651 with simulated safe areas, the 142×247.172px viewport yields `5.005691px` balls; bounded scrolling of 11px/20px keeps the controls inside safe bounds. Three font-family first-fold checks, the WebKit check and 20 mobile/accessibility follow-up cases passed. Logs: `/tmp/left-pull-ci-layout-651-final.log`, `/tmp/left-pull-ci-layout-fonts-final.log`, `/tmp/left-pull-ci-layout-responsive-final.log`, `/tmp/left-pull-ci-layout-followup-final.log`.
- Independent final-build checks reconfirmed 360×800 first-fold controls with 32.016px bottom margin and 360×651 actual frustum/cabinet/pocket visibility, retaining 44px targets and the 4.9px ball guard. The final 651px screenshot was inspected. Raw evidence: `/tmp/left-pull-ci-review-final.json`. These are local corrective checks; a successful Linux CI rerun and live build identity are not claimed here.

- The manager independently reran all 85 unit tests (0 failures) and the production build on the final corrective source; the application build identity remains `e641654ce031dfd9`. Execution logs: `/tmp/left-pull-ci-manager-unit.log`, `/tmp/left-pull-ci-manager-build.log`.

- A second remote run, `42200366667` for `b174850`, passed the earlier CI checks but failed the final responsive 568×320 aiming case: required scroll was `165px`, exceeding the unchanged `160px` guard. The Linux landscape layout needs a further focused repair; remote CI and publication remain unverified. The prior local results above remain scoped to their recorded builds.

- Second CI correction uses CSS only: hide the duplicate sidebar turn label in narrow landscape after placement, retaining the active player/turn in the HUD. Runtime JavaScript, model bytes and table framing are unchanged. Build `0473d7f6bfac8301` passed 12 responsive journeys/24 states plus 12 font-stress cases, four main-layout cases plus WebKit, UX 7 and manager unit 85. Logs: `/tmp/left-pull-ci568-build-final.log`, `/tmp/left-pull-ci568-responsive-final.log`, `/tmp/left-pull-ci568-main-layout-final.log`, `/tmp/left-pull-ci568-ux-final.log`, `/tmp/left-pull-ci568-manager-unit.log`.
- Independent final-build 568×320 and 640×360 probes with Arial/Verdana/system-ui and simulated safe areas preserve full cabinet/pocket framing, 44px targets and zero horizontal overflow. At 568px, required scroll is 131px/143px (Verdana), below the strict 160px limit; projected ball size remains 4.944047px. At 640px, scroll is 91px and ball size 5.566766px. The active HUD turn label remains visible; the Verdana screenshot was inspected. Raw evidence: `/tmp/left-pull-ci568-review.json`. Remote CI rerun and live verification remain pending.

- Final second-correction mobile/accessibility follow-up also passed all 20 cases on build `0473d7f6bfac8301`; log: `/tmp/left-pull-ci568-followup-final.log`. All selected local corrective gates are complete. Remote CI success and live publication remain separate pending evidence.

- Third remote run `42204003399` (`8bb183b`) passed Game, pull acceptance and PWA checks, then failed the library legacy-demo refresh case at `scripts/test-library-browser.mjs:203`: `page.reload()` exceeded its default 30s browser-load wait on Solar. This resembles the previously observed isolated baseline/library flake; the cause and a bounded harness correction are being checked. No runtime cause or successful publication is asserted, and remote/live gates remain pending.

- Library harness correction is limited to the legacy-demo lifecycle test: navigation waits for `DOMContentLoaded`, then the existing single 60s readiness budget requires the correct demo canvas, actual application readiness and real WebGL draws. Refresh additionally proves a new `performance.timeOrigin` and exactly one canvas; return-to-index, stopped draws and back navigation remain checked. No timeout increase, runtime, asset or dependency change is included.
- A controlled held noncritical image reproduced the waiting mechanism: `DOMContentLoaded` at 165ms, Solar ready with 168 draws/one canvas at 6442ms while the browser `load` event remained pending; releasing the image allowed `load` to complete. This proves that browser-load waiting can block a usable renderer, but does not identify the exact resource responsible for the CI timeout. Evidence: `/tmp/left-pull-library-load-proof.log`.

- Independent final-source full-library execution subsequently reproduced a refresh timeout while waiting for `DOMContentLoaded` itself, after the first seven groups passed (`/tmp/left-pull-library-review-final.log`). This occurred under two concurrent software-WebGL browser runs; it shows that the held-resource mechanism alone does not explain every failure and that the proposed wait-state change is not yet sufficient evidence of resolution. The failure is retained, and isolated rerun/diagnosis is required before closing this local gate.

- Isolated diagnostic execution of all nine library groups passed (`/tmp/left-pull-library-solo-diag.log`), retaining the original 1440×900 lifecycle viewport and all readiness/navigation/disposal limits. This run included temporary navigation logging, removed from the final harness; no fresh non-diagnostic full run is claimed here. It does not erase the preceding parallel-run failure.
- The diagnostic observed active Solar query latency of 13.716s and approximately 10.060s between the reload request and `DOMContentLoaded`, despite the preceding document having already completed `load` and rendered real frames. This supports software-WebGL/main-thread backpressure as a risk, beyond the separately proven held-resource mechanism. The exact remote CI blocker remains unidentified; no Solar performance fix or general timeout resolution is claimed. Final changes remain test-only, with the original 30s navigation/60s readiness budgets and viewport unchanged. Remote CI and live verification remain pending.

- CI run `42207787440` did not reach application/browser checks in its first attempt: Azure Ubuntu APT dependency downloads (43 packages) were unusually slow for approximately 16 minutes before cancellation. Its second attempt on runner/job `127865876182` again remained in dependency installation after approximately 12 minutes. These are runner package-delivery delays, not application test failures. A narrowly scoped mirror correction is being reviewed; no checks are removed and remote/live gates remain pending.

- Infrastructure correction adds a single pre-Playwright workflow step that rewrites only the exact Azure Ubuntu archive HTTP URL to `https://archive.ubuntu.com/ubuntu` in existing Ubuntu `.list`/deb822 source files. Suites, components, signing-key configuration, security URLs, dependency commands and every test remain unchanged. Fixture checks preserve neighboring/nonmatching URLs and source metadata; Bash syntax validation passed; four Noble `InRelease` URLs returned HTTP 200. Evidence: `/tmp/left-pull-apt-mirror-proof.log`. These checks establish syntax and endpoint reachability, not verified runner download speed or successful APT installation; the next CI run must establish those outcomes.

## 10. Final Release Verification — 2026-11-06 UTC

- **Remote commit:** `d0289febcded6b868a20b9580a7cfab0832f6da5`; application build **`0473d7f6bfac8301`**. [GitHub Actions run 42211833153](https://github.com/yapweijun1996/Blender-3D-Gallery/actions/runs/42211833153) completed the full build and GitHub Pages deployment successfully; run updated at `2026-11-06T11:54:25Z`. Deployment success is recorded in `/tmp/left-pull-ci-release-final.log`.
- **CI gates:** unit 85; Game/browser 76 (46 main plus 30 pull acceptance); PWA 16; library 9; standard 9; reviewed 8; UX 7; responsive 12 viewport journeys with the underlying font assertions; Solar asset 17 and scene checks at four viewports. All workflow checks passed with their existing limits.
- **Runner dependencies — corrected attribution:** dependency installation completed in this run (12.9 MB fetched in 1s and 114 MB in 8s), but the actual source was still Azure HTTP via `file:/etc/apt/apt-mirrors.txt`. The two-file rewrite did not reach that runner configuration and was a no-op. The recovered downloads cannot be attributed to the proposed mirror change. The application build/deployment and live evidence remain valid; the mirror-configuration follow-up is not yet verified.
- **Production verification:** the manager ran `/tmp/left-pull-live-check.mjs` against [the live site](https://yapweijun1996.github.io/Blender-3D-Gallery/) with expected build `0473d7f6bfac8301`; exit status was zero. In a fresh 320×568 touch context, the prepared Game pack was loaded, the browser switched offline, the page was closed, and a new page cold-started offline. A real CDP touch pull measured `0.6000000635782877`; holding caused no impulse or gesture scroll, release committed exactly once at measured GLB contact gap `1.734723475976807e-17m`, and the game settled to `aiming`, revision `2`, with `errors: []`. No horizontal overflow or obsolete Shoot/`#shot-power` control was found. Raw result: `/tmp/left-pull-live-final.log`; the manager inspected `/tmp/left-pull-live-charging.png`.
- **Limits preserved:** this is emulated Chromium touch/offline evidence, not physical iOS/Android installation or screen-reader certification. The head-string visual guide remains deferred; no prototype cleanup or licensing change was authorized. Active Solar software-WebGL backpressure remains an observed unresolved performance risk; the passing CI does not establish that its root cause is fixed.

## 11. Runner Mirror Configuration Follow-up — Verified 2026-11-06 UTC

The earlier CI log exposed a previously missed source file, `/etc/apt/apt-mirrors.txt`; the correction added that file to the exact URL rewrite while preserving signing configuration, package suites and all checks. The earlier no-op and corrected attribution remain recorded above.

- **Verified remote revision:** `41f41217766806683f3d75ecff8be664c6e6e2f5`. [CI run 42214110333](https://github.com/yapweijun1996/Blender-3D-Gallery/actions/runs/42214110333) completed every unchanged build/test gate and Pages deployment successfully, updated `2026-11-06T12:14:29Z`. Raw log: `/tmp/left-pull-ci-mirrorlist-final.log`.
- **Actual mirror use:** that log records the official HTTPS archive for Noble and its updates/backports/security metadata, plus actual package downloads (for example `Get:43 https://archive.ubuntu.com/ubuntu ... libavcodec60`). This closes the effective-configuration gate. Transfers were 12.9 MB in 2s and 114 MB in 35s, followed by successful installation. This is a healthy installation, not a speed improvement claim: the earlier recovered Azure run transferred 114 MB in 8s.
- **Repeated production proof:** the manager reran the fresh 320×568 cold-offline touch-shot probe after this deployment; exit status was zero and build `0473d7f6bfac8301` matched. The actual pull ratio was `0.6000000635782877`, exactly one commit occurred at contact gap `1.734723475976807e-17m`, and the game returned to `aiming`/revision `2` with `errors: []`. Raw evidence: `/tmp/left-pull-live-mirrorlist-final.log`.
- **Later upstream scope:** the manager fetched `5346e1f`, containing only Saga model/output work (29 files), with no changes to application source, scripts, tests, workflow or dependencies. That later asset work is preserved separately. The Game/CI evidence above remains pinned to tested revision `41f4121`; no fresh whole-site build or model validation after `5346e1f` is claimed.

This closes the mirror follow-up without changing application/runtime behavior. Physical-device/screen-reader limits, deferred head-string/prototype/licensing decisions and the unresolved active Solar software-WebGL backpressure risk in section 10 remain applicable.

---

# Premium 3D Asset Library Redesign — 2026-11-15

## T01 — Repository audit and execution plan (complete)

- Checkout: `main`, starting revision `1f9656346107bb49bdacc2b651c4f7e9ce869ac8`; remote `origin` is the requested GitHub repository. The checkout had extensive tracked and untracked changes before this request; preserve them. The first landing/search prototype was started before the expanded T01-first instruction and remains uncommitted. Baseline commands therefore describe the working tree, not an untouched revision.
- Stack: Vite 8, native JavaScript/CSS and Three.js; no framework migration is justified. `models/catalog.json` currently contains 554 assets in 428 collections. `scripts/catalog.mjs` validates registry paths and derives GLB metrics. The screenshot's statistics and model imagery are illustrative, not authoritative.
- Routing: query-based static-host routes and `history` support, with lazy model viewer dialog and independent demo lifecycles. Search already covers name, description, category, collection and tags; category, type and collection are URL-backed. Model downloads are controlled by the catalog's `downloadable` flag. Viewer has orbit, zoom, reset, fullscreen, loading/error handling, cleanup and special controls for selected models.
- UI: existing dark green tokens and focus/reduced-motion rules, responsive menu, static thumbnails and lazy WebGL. Before this redesign, the landing hero and full catalog shared a long page; no category shortcut cards, list/sort, theme selector or filter drawer. The viewer exposes measured material/animation counts, but general editing/playback is not available for all models.
- Deployment: Vite `base: "./"` supports GitHub Pages project paths. `.github/workflows/deploy.yml` runs on pushes to `main` and manual dispatch, installs Node 24 dependencies, validates/builds, runs unit and browser suites, then deploys `dist`. No deployment is authorized by this request; do not push to main without explicit authorization.
- Baseline: `npm run build` passed (with Vite’s large-chunk warning), and `npm test` passed 592 tests, on the already-dirty working tree after the initial prototype; these are not a clean pre-change baseline. No lint or typecheck scripts are defined in `package.json`; do not report those as passed. Existing historical test records above apply only to their recorded revisions.
- Routed instruction files `instruction-modules/investigation.md` and `instruction-modules/verification.md` are absent in this checkout; apply the core instructions and record verification directly.

## Sequential backlog and gates

T01 audit and baseline → T02 tokens/components → T03 navigation → T04 hero → T05 categories/counts → T06 search/history → T07 cards/grid → T08 viewer validation → T09 detail/download → T10 build/deployment compatibility → T11 filters → T12 grid/list → T13 sorting → T14 themes → T15 localization readiness → T16 states → T17 keyboard → T18 responsive/touch → T19 performance → T20 visual regression. Each task requires applicable tests, responsive/accessibility review and focused commit before proceeding. Changes already started must be reconciled with this sequence, not mistaken for accepted tasks. Existing user edits in shared files must not enter commits unintentionally.

Acceptance coverage E001–E100 must be tracked against deterministic assertions, with absent or out-of-scope features explicitly marked not applicable rather than counted as passes. Physical-device, assistive-technology and deployment verification must be distinguished from emulation/local checks. Optional P2 features require their own supported data and privacy decisions.

---

# Singapore and Malaysia Festival Models — 2026-11-15

**Status:** F01–F05 implemented and locally verified; later items remain planned.
Work through one model at a time. See the [festival model
brief](docs/festival-models/README.md) for concept images, existing inventory,
design ideas and per-model acceptance criteria. Recheck the catalog before
starting each item. Preserve the historical task records above.

## Initial sequential queue

- [x] **F01 — Christmas tree:** editable Blender source, standalone GLB,
  preview and catalog entry created; local validation and browser checks passed.
  See [model notes](models/christmas-tree/README.md) for evidence and limits.
- [x] **F02 — Christmas gift boxes:** four editable presents, standalone GLB,
  preview and catalog entry created; local validation and browser checks passed.
  See [model notes](models/christmas-gift-boxes/README.md) for evidence and limits.
- [x] **F03 — Gregorian New Year countdown clock:** year-independent static
  display, editable Blender source, GLB, preview and catalog entry created;
  local validation and browser checks passed. See
  [model notes](models/new-year-countdown-clock/README.md) for evidence and limits.
- [x] **F04 — Chinese New Year lion dance head:** original stylized editable
  source, GLB, preview and catalog entry created; local validation and browser
  checks passed. See [model notes](models/chinese-new-year-lion-dance-head/README.md)
  for references, evidence and limits.
- [x] **F05 — Chinese New Year kumquat tree:** original editable potted tree,
  GLB, preview and catalog entry created; local validation and browser checks
  passed. See [model notes](models/chinese-new-year-kumquat-tree/README.md) for
  evidence and limits.
- [ ] **F06 — Mid-Autumn rabbit lantern:** distinguish it from the existing
  lantern display and complete the acceptance gate after F05.

Additional Hari Raya, Deepavali, national celebration, Sabah Kaamatan and
Sarawak Gawai ideas are listed in the brief; decide their order after the initial
queue. Research Kaamatan and Gawai separately before creating culturally
specific designs. Existing assets require their own evidence review; their
presence in the catalog is not a completed quality assessment.

## Gate for each queue item

- [ ] Define the design and references; check catalog overlap and applicable rights.
- [ ] Save editable Blender source, reproducibility/provenance notes and actual GLB.
- [ ] Add a preview, metadata and catalog entry following the existing asset contract.
- [ ] Validate the GLB and run the applicable asset/build checks.
- [ ] Inspect the model and verify the real gallery/viewer workflow, controls,
  loading and fallbacks; record results and any unverified limits.

This gate is a reusable checklist for **each** item; consult its individual
evidence before marking it complete. No deployment, commit or push is implied by this planning entry.

---

# Chibi Character Standard and Mall Guide v5 — 2026-11-15

**Status:** Planning and documentation only. No v5 Blender model, GLB or catalog entry exists; nothing below is implemented or verified. See the [chibi standard](docs/chibi-character-standard.md) and the [v5 plan](docs/chibi-mall-guide-v5/plan.md).

- [x] Concept turnaround B generated and locked as the v5 reference (AI concept image; rights not cleared, internal reference only).
- [x] Owner decisions recorded: 40,000 triangle / 20 draw-call budget; mandatory rig (20 bones or fewer) with three shape keys driving brows and cheeks; fresh-agent review then owner check; animations idle+blink, two walk styles, wave, hold-and-point, put-sign-down; swappable sign icons; boy look kept.
- [x] Decided: extra low-detail GLB for distant NPCs (about 8,000 triangles, proposed); dialog avatar as pre-rendered stills, one per expression; festive uniform variant; expression and pose reference images generated, with a corrected put-down pose (`docs/chibi-mall-guide-v5/mockup/`).
- [x] Blink prototype done (`models/chibi-mall-guide-v5/prototype/blink/`): eyes-sink method adopted, key `blink` on a separate `Eyes` mesh; the eye opening still needs a designed shape.
- [ ] Open: owner approval of the standard; which festivals the festive uniform covers.
- [ ] S1 reference pack fixed and provenance note kept.
- [ ] S2 proportion blockout (about 2.5 heads, eyes in the lower third).
- [ ] S3 parts, head with brow/eye/mouth/cheek edge loops, thick-lock hair fitted under the cap.
- [ ] S4 materials and sign-icon atlas within budget.
- [ ] S5 armature, shape keys and animation clips.
- [ ] S6 GLB export and QA gate run 001 (G1 to G6) with a fresh-agent review.
- [ ] S7 catalog registration only after the gate passes.

Chibi Visitor v4 predates the standard (no rig, 113,428 triangles) and is in REWORK status; see its README.

Framework proposal (no code yet): [docs/chibi-framework-design.md](docs/chibi-framework-design.md). Open: location and name, Python-only or Node validation too, how many older characters to migrate, owner of versioning and reviews.

---

# Shopping Mall Modules and 400-Model Backlog — 2026-11-15

- [x] Preserve the user-supplied 400-model v1.0 plan in [the shopping mall documentation](docs/shopping-mall/production-backlog-v1.md); it is a plan, not an assertion that all models exist. Registry count: 400 unique IDs (172 P0 / 194 P1 / 34 P2).
- [x] Document existing-asset candidates, 1.2 m versus proposed 2 m grid differences, inconsistent provisional dimensions and interaction/QA gaps in [the reconciliation notes](docs/shopping-mall/README.md). Preserve the earlier 50-item list's differing IDs and priorities pending explicit mapping.
- [x] Record the expanded [shopping mall modular checklist](docs/shopping-mall/complete-modular-checklist.md), covering reusable assets, shops, public spaces, toilets, parking, decoration and interactions. Its entries are planning items and may overlap the 400-item backlog or existing assets; unchecked is not a claim that an asset does not exist.
- [x] Implement the local five-module preview and cutaway corridor from existing GLBs; desktop and emulated mobile browsing, module selection, orbit/reset, keyboard selection and load-error retry were checked. See [preview notes](mall-modules-preview/README.md) for evidence limits; the preview is not in the production Gallery build.
- [x] Enrich the local corridor with existing shopfronts, ceiling fixtures and furniture, plus fictional storefront labels; keep the five individual module views. Placement remains a visual study awaiting fit and navigation checks.
- [ ] Review the local [nine-module corridor preview](mall-modules-preview/) and confirm style and intended production scope. The current version includes the solid wall, the corner modules and existing glass partitions; the ceiling is cut away. This preview does not establish 400-item completion or a production-ready assembly.
- [ ] Map each selected backlog ID to current catalog assets and verify source, rights, dimensions, connectors and QA evidence before classifying it as reuse, adaptation or new work.
- [ ] Decide the structural grid and compatible transitions; measure a representative assembly before accepting fit. Confirm behavior-specific interaction and animation tests where requested.
- [ ] Deliver model batches only with individual source, GLB, provenance and applicable validation. PRs, commits and publication are separate actions and are not implied by this record.
- [ ] Produce the planned slices in dependency order: shell and corridor; public facilities; five representative shop types; vertical circulation; restrooms and family facilities; parking and outdoor access; merchandise, characters, seasonal assets and requested interactions. Record per-item evidence before acceptance.
- [x] Building-shell first module: created and locally registered [1.2 m solid wall](models/mall-solid-wall/README.md) with editable Blender source, GLB, preview and validation. Three straight copies meet at the nominal 1.2 m pitch; actual Gallery and corridor-preview loading was exercised locally.
- [x] Reused the existing floor GLB for a bounded L-shaped five-tile layout and checked its four internal joins and one floor/wall alignment: [results](models/mall-solid-wall/reports/floor-wall-assembly.json). This is a bounding-box check; it does not supply a finished corner edge.
- [x] Building-shell second module: created and locally registered [1.2 m straight floor edge trim](models/mall-floor-edge-trim/README.md), with editable Blender source, GLB, preview and local validation. Existing floor-to-trim top and edge alignment were checked with actual GLB bounds; the corridor preview uses repeated segments.
- [x] On the working tree containing both modules, `npm run validate:assets`, `node --test tests/catalog.test.mjs` (6 tests) and the Vite production build in a separate temporary output directory passed. The standalone corridor preview remains outside the production Gallery build.
- [x] Building-shell corner slice: created and locally registered the [floor outside corner cap](models/mall-floor-corner-trim/README.md) and [90° wall corner](models/mall-wall-corner/README.md), retained editable sources and GLBs, checked one joint configuration, and added both to the local corridor preview.
- [x] On the working tree with both corner models, asset validation and a separate-output Vite production build passed, as did 6 catalog tests. Local Chromium checked the new Gallery GLB hashes and the seven-module preview; device and fit limits remain in the asset READMEs.
- [x] Building-shell floor corner slice: created a [1.2 m corner tile](models/mall-floor-corner-tile/README.md) and [45° mitred outside trim pair](models/mall-floor-mitred-trim/README.md), registered both, checked a specific 90° assembly and added both to the local corridor preview.
- [x] For this floor-corner slice, Blender source/reimport bounds, Khronos validation, one actual-GLB assembly sample, the 6 catalog tests, asset validation and a temporary-output Vite build passed. Local Chromium rendered both exact GLB hashes and all nine preview views at desktop and emulated mobile sizes. See the asset READMEs for limits; the standalone preview is not in the production build.
- [x] Rechecked this mall slice on GitHub main baseline `17a0ed6f`: asset validation, 6 catalog tests, standard `npm run build`, four shell GLB/assembly validators and Chromium desktop/emulated-mobile preview and Gallery flows passed. On this baseline, an alternative custom-output build failed because the PWA build hook still reads `dist`; the standard build passed. The standalone preview is not in the production build.
- [ ] Check full mesh fit, other corner configurations and provisional 2 m planning dimensions before accepting the broader floor-corner/edge and wall-corner families.
- [ ] Compare the solid wall with `MALL-STR-010`'s provisional 2 m specification and validate a representative complete assembly, corner/transition interfaces and target-device performance before accepting the checklist item. Unreconciled P0 shell work still includes other corner configurations and edge transitions.

## 12. Documentation refresh and verified gap backlog — 2026-11-19

Documentation added: [FEATURES_MAP.md](FEATURES_MAP.md) (refreshed to `fb9d5070`) and per-module logic docs [shell and viewer](docs/modules/shell-viewer.md), [demos, game and PWA](docs/modules/demos-game-pwa.md), [chibi and animation](docs/modules/chibi-animation.md). They were produced by reading source; no tests or builds were run for them. The gaps below were each re-read against the code on this date and are open unless ticked.

- [x] `scripts/sync-chibi-dressup-modules.mjs` now preserves hand-authored `bodyIds` and `family` across syncs (verified by injecting `family` and re-running the sync; manifest then restored; `tests/chibi-dressup-config.test.mjs` 5/5 pass).
- [x] `models/chibi-dressup/README.md` no longer says "four" modules.
- [ ] `status` (`verified`/`pending`) is schema-checked in `config.js` but never changes runtime behavior, so a `pending` module is shown to visitors.
- [ ] (deferred: the workflow's sparse checkout excludes `tests/` and `models/`, so adding `npm test` needs a CI design change) `.github/workflows/deploy.yml` push path runs only `npm run build:deploy`: no `npm test`, no `validate:assets` (manual dispatch with the input can run it).
- [x] Added `npm run test:dressup` for `scripts/test-chibi-dressup-browser.mjs` (script entry only; the browser test itself was not run here and it needs a production build).
- [ ] `scripts/pwa-build.mjs:63` hard-codes the Game version string and `src/pwa/sw-template.js:57` hard-codes 18 pack files.
- [ ] Demo route and interactive-asset lists are duplicated by hand across `src/main.js`, `scripts/demo-registry.mjs`, `src/viewer.js` and `data/demos.json`.
- [ ] `src/visitor-v2/demo.js` and `src/visitor-v3/demo.js` share a scaffold; untested. `src/fish-motion.js` is the only viewer add-on imported statically.
- Superseded: the manifest now has two bodies (`neutral`, `female`) and seven `female-*` modules carrying `bodyIds` and `family`; the sync script candidates define those fields directly and fall back to the previous manifest values. No `hat` module is listed. Default prop sockets still come from untracked `output/modular-chibi-parts/*/attachment.json` (not re-verified).
- [ ] `npm run test:dressup` result on 2026-11-19 (not a pass): at commit `be28ea15` the committed test loops over every manifest module, including `female-*` ones that the default neutral body does not render, so it fails at `[data-module="female-hair-bob"]` (after a 20 s timeout on the first click under software rendering, which passes with a 90 s timeout). With another session's uncommitted edits to the test, `src/chibi-dressup/props.js` and `config.js` it advances and times out at `[data-clip="take_item"]`. Re-run once those edits are committed.
- Corrected during review: `game-mounted` is dispatched by `src/main.js` (`${page}-mounted`); the earlier doc claim that nothing dispatches it was wrong and was fixed.

