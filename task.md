# Eight-Ball Shooting Interaction — Task & Acceptance Tracker (v1.1 Left-side Pull & Release)

> **Status:** `Verified Complete — Local Acceptance 16/16` — implementation and local acceptance are complete. Publication is recorded separately after remote/live verification.
> **Core flow:** `Aim → Hold Left Power Handle → Drag Down → Cue Pulls Back → Release → Cue Strikes → Balls Move`
> **Spec:** [docs/game/gameplay-contract.md](docs/game/gameplay-contract.md) — "Left-side Pull & Release Shooting Specification v1.1" (supersedes v1.0 §4.3/§5/§6 on-table cue grab)
> **Branch / worktree:** `feat/eight-ball-left-pull-release`, isolated from the original dirty checkout; baseline `39615f7`; full feature acceptance build `66837cb8b2817ced`; final integrated build `7a61e8ae1a814835` after preserving the latest Saga assets.

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

- Final integrated application build: `7a61e8ae1a814835` at merge `4b54607`. Full feature acceptance was executed on build `66837cb8b2817ced`; implementation baseline: `39615f7`. See the integration record below for the exact final-tree checks.
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
