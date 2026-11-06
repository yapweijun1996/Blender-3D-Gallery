# Eight-Ball Shooting Interaction — Task & Acceptance Tracker (v1.1 Left-side Pull & Release)

> **Status:** `Verified Complete — Local Acceptance 16/16` — the subsequent CI layout defect has a locally verified repair. Successful remote CI and live publication verification remain separate pending release gates; the first failed run and corrective evidence are recorded below.
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

- [x] Mouse hover / one-finger table drag rotates aim (360°); cue stays behind cue ball
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

- Saga-integrated application build: `7a61e8ae1a814835` at merge `4b54607`; current corrective application build: `e641654ce031dfd9` (see CI follow-up below). Full feature acceptance was executed on build `66837cb8b2817ced`; implementation baseline: `39615f7`. See the integration record below for the exact final-tree checks.
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
- Local regression acceptance is complete. No production release is established by these local results; record the remote commit, workflow and matching live build separately.

## 9. Post-Commit Main Integration

Feature commit `17e7639` was merged with the newly fetched `origin/main` revision `d3055c5` in isolated merge `4b54607`. The upstream change contains only 15 Proton Saga asset/source/preview files. All Game source, Game model bytes, shared application source, dependency manifests and the migrated test sources are unchanged from the accepted feature commit; no Saga work was overwritten.

The primary manager independently executed these checks on that merged tree with Node 24.21.0:

| Check | Observed result | Local evidence |
| --- | --- | --- |
| `npm test` | 85 passed, zero failed | `/tmp/left-pull-merged-unit.log` |
| `npm run build` | Passed; final build `7a61e8ae1a814835` | `/tmp/left-pull-merged-build.log` |
| `npm run test:library` | All 9 groups passed in isolation, including the updated catalog assets | `/tmp/left-pull-merged-library.log` |

The full Game/PWA/pull-acceptance evidence above remains pinned to the feature builds and unchanged Game sources; it is not a claim that every Game suite was executed again after the Saga-only merge. Publication and live build identity are still recorded separately after remote verification.

## CI follow-up — historical failure and locally verified repair

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

- CI run `42207787440` did not reach application/browser checks in its first attempt: Azure Ubuntu APT dependency downloads (43 packages) stalled for approximately 16 minutes before cancellation. Its second attempt on runner/job `127865876182` again remained in dependency installation after approximately 12 minutes. These are runner package-delivery delays, not application test failures. A narrowly scoped mirror correction is being reviewed; no checks are removed and remote/live gates remain pending.

- Infrastructure correction adds a single pre-Playwright workflow step that rewrites only the exact Azure Ubuntu archive HTTP URL to `https://archive.ubuntu.com/ubuntu` in existing Ubuntu `.list`/deb822 source files. Suites, components, signing-key configuration, security URLs, dependency commands and every test remain unchanged. Fixture checks preserve neighboring/nonmatching URLs and source metadata; Bash syntax validation passed; four Noble `InRelease` URLs returned HTTP 200. Evidence: `/tmp/left-pull-apt-mirror-proof.log`. These checks establish syntax and endpoint reachability, not verified runner download speed or successful APT installation; the next CI run must establish those outcomes.
