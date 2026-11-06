# Eight-Ball Shooting Interaction — Task & Acceptance Tracker (v1.1 Left-side Pull & Release)

> **Status:** `Design Complete / Implementation Not Started` (no runtime code modified)
> **Core flow:** `Aim → Hold Left Power Handle → Drag Down → Cue Pulls Back → Release → Cue Strikes → Balls Move`
> **Spec:** [docs/game/gameplay-contract.md](docs/game/gameplay-contract.md) — "Left-side Pull & Release Shooting Specification v1.1" (supersedes v1.0 §4.3/§5/§6 on-table cue grab)
> **Planned branch / worktree:** `feat/eight-ball-left-pull-release` in an isolated `git worktree` (not yet created)

---

## 1. Implementation Phases

| Phase | Deliverable | Key modules (verified paths) | Gate | Status |
| --- | --- | --- | --- | --- |
| 1 | Left power handle, pointer capture, `pullRatio` from pointer-down origin, clamping, cancellation | `src/game/page.js`, `src/game/style.css`, new pure helper module + unit tests | Input unit tests | `[ ]` |
| 2 | Cue backward offset from `pullRatio`, locked aim, deterministic forward strike, single contact event | `src/game/scene.js`, `src/game/page.js` | Animation/contact tests | `[ ]` |
| 3 | Idempotent `ShotIntent` → existing `createShot` (strength = `pullRatio^1.5`), no shot while moving/paused | `src/game/page.js`, `src/game/physics.js` (reuse, no rewrite) | Shot unit + integration | `[ ]` |
| 4 | Remove Shoot button & power slider; update browser tests to real mouse/touch pull; responsive/landscape QA | `src/game/page.js`, `src/game/style.css`, `scripts/test-game-*.mjs`, `scripts/browser-test-utils.mjs` | Full Playwright regression | `[ ]` |

## 2. Mandatory Behavior Checklist

- [ ] Mouse hover / one-finger table drag rotates aim (360°); cue stays behind cue ball
- [ ] Pointer down on the **left handle** (only) starts `CHARGING`; aim locked
- [ ] Dragging down moves handle, fills meter, pulls visible cue back along its axis (same `pullRatio`)
- [ ] Release ≥ 5% → forward strike → exactly one impulse at cue contact
- [ ] Release < 5% / tap without drag → cancel, no shot
- [ ] `pointercancel`, `lostpointercapture`, blur, Escape → cancel uncommitted charge
- [ ] Second pointer ignored; duplicate `pointerup` never shoots twice
- [ ] Release outside controller still shoots when capture is active
- [ ] Controller disabled during placement, motion, resolution, pause, inspection, context loss, game over
- [ ] Handle resets after commit; cue hidden while balls move
- [ ] Rules, physics, checkpoint schema (`aiming`/`placing`/`finished`) and save behaviour preserved
- [ ] Keyboard secondary path: focusable handle, Arrow keys charge, Space/Enter release

## 3. Prohibited

- [x] No Shoot button · No power slider as primary control · No click-to-shoot · No shot on pointer down · No shooting by dragging anywhere on the table · No track-click shot

## 4. Acceptance Tests (0/16 — not executed)

- [ ] 1. Mouse drag on handle charges and releases a shot
- [ ] 2. Touch drag on handle charges and releases a shot
- [ ] 3. Short drag (<5%) cancels
- [ ] 4. Long drag clamps at 100%
- [ ] 5. Reverse (upward) drag yields 0% and cannot shoot
- [ ] 6. Pointer cancel / lost capture never shoots
- [ ] 7. Duplicate release → one impulse
- [ ] 8. Cue offset ∝ `pullRatio` and aligned with aim
- [ ] 9. Impulse applied at contact, not at release
- [ ] 10. ~80% pull gives higher initial cue-ball speed than ~30%
- [ ] 11. No shooting while balls move
- [ ] 12. No shooting while paused; pause during strike cancels without double-fire
- [ ] 13. Save/reload never replays committed shot
- [ ] 14. Turn resolution after all balls settle
- [ ] 15. Mobile landscape: table + controller visible, no page scroll during drag
- [ ] 16. Existing Game/PWA/library/reviewed browser suites pass after test migration

## 5. Rack & Break Setup (unchanged)

- [x] 15-ball tight triangle · [x] 8-ball center of row 3 · [x] apex on Foot Spot · [x] solid/stripe rear corners
- [x] Break placement behind head string enforced (`legalPlacement`) · [ ] head-string visual guide (v1.0 P0-2, deferred)

## 6. Open Workspace Notes (require owner decision)

- Prior v1.0 prototype files remain **untracked** in the main checkout: `src/game/interaction.js`, `tests/game-interaction.test.mjs` (6 unit tests passed). Backups and a head-string scene patch are saved in the conversation scratch folder. Not deleted pending approval.
- Empty local branch `feat/eight-ball-gameplay-interaction-v1` (no commits) exists; main checkout is back on `main`.
