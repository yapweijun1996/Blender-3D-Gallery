# Casual Eight-Ball gameplay contract

This is a concise description of the existing game, not a new ruleset. The detailed rules, geometry, checkpoint and PWA contracts remain in [game implementation and delivery](../game-implementation-plan.md).

## Player journey

Two people share one device. A new match starts with Player 1 placing the cue ball behind the head string. Players aim, set power and explicitly shoot. Groups remain open on the break; the first legal post-break pot assigns solids and stripes. A foul gives the opponent ball in hand. Once a player's group was cleared before the shot, a legal eight-ball pot wins; an early or fouled eight loses. There is no score, AI opponent, spin, called pocket or claim of tournament rules.

The UI exposes the active player, groups, remaining balls and current instruction. The aiming guide labels the first ball, authored cushion segment or pocket opening along the initial straight path; its ring marks the cue-ball center there, not a guaranteed pot or post-impact trajectory. The settled-shot message reports observed object-ball pots, the next player and the existing rule result. Remaining-ball information reflects the game state; it is not a synthetic score.

## State and ownership

`src/game/page.js` coordinates the existing phases: setup/loading, `placing`, `aiming`, `moving`, `adjudicating`, `paused`, `finished` and `recovery`. A pause remembers the prior playable phase; resuming a moving shot continues it. Restart requires confirmation and starts a fresh rack, Player 1, placement, default aim and power. A completed match can be played again. An invalid simulation restores a previous stable turn rather than inventing a result.

`src/game/physics.js` advances a 1/120-second fixed simulation step. `rules.js` owns shot adjudication; `scene.js` displays state and does not decide outcomes. A single page-owned animation loop is canceled on disposal. A 280 ms cue delivery is presentation only: balls remain still until the existing single impulse starts the shot. Reduced motion skips cue travel. Pausing or backgrounding during startup or delivery cancels that unstarted shot; resuming returns to aiming and requires another explicit Shoot. Navigating away disposes a pending delivery. Backgrounding requests a pause and clears accumulated wall time; an interrupted shot is not fast-forwarded on return.

`storage.js` validates stable checkpoints and uses Web Locks with an IndexedDB lease fallback to prevent concurrent writers. A pending-shot marker permits recovery of the last complete turn. When storage is unavailable, play can continue in memory with an explicit warning; leaving without saving requires a deliberate choice. Exiting Game releases its listeners, renderer and ownership. Existing checkpoints retain their original schema and rules/table version checks.

## Inputs and recovery

The table accepts pointer/touch aiming and cue-ball placement; releasing a pointer never shoots. Accessible range inputs and buttons provide alternatives. With the table focused, arrows adjust aim or placement, Shift makes finer adjustments, Enter confirms placement, Space shoots, and F toggles fullscreen. Escape opens the pause menu where applicable. Inspect mode is separate from aiming and cannot shoot.

App options offers Standard and Performance graphics quality. Standard keeps the original 1.5 pixel-ratio cap; Performance caps it at 1 until the player leaves Game. The selection changes render resolution, not the simulation, models or saved match.

The game loads its table, cue and sixteen balls from the existing catalog. A failed initial 3D load or unavailable WebGL must leave a clear recovery path. Leaving during initialization aborts Game-owned model downloads, stops queued loads and prevents late results from changing the next route; entering Game again creates a fresh scene. The four-worker limit and existing catalog GLBs are preserved. WebGL context loss during a match offers a save/reload path for the last stable turn. No external model code is executed.

## Acceptance evidence

The baseline and findings are recorded in [game baseline](../audits/game-baseline.md). The final executed checks and remaining device limitations are recorded in [release readiness](release-readiness.md); an unexecuted scenario is not a passing result.

## Proposed Next-Iteration Gameplay & UX Improvements (2026-11-06 Backlog)

The following improvements are proposed based on live review of `?page=game` and are tracked in [task.md](../../task.md). They represent the target interaction design and are not yet implemented in the current build:

### 1. Target 5-Step Tabletop Gameplay Flow
1. **Ball Placement:** The player drags the cue ball directly on the table within the legal placement zone. The table renders real-time boundary lines (such as the head string on break) and collision/overlap constraints.
2. **Aim:** Once placement is set, the cue stick appears behind the cue ball. The player adjusts aim direction via mouse or touch on the table, with the aiming line and ghost-ball contact indicator updating in real time.
3. **Pull Back:** Pulling back along the cue stick axis retracts the cue stick; shot power increases proportionally with pull-back distance and shows visual power feedback.
4. **Release to Shoot:** Releasing the mouse button or finger drives the cue stick forward to strike the cue ball, with impulse power determined by the pull-back distance.
5. **Ball Physics & Turn Resolution:** Balls collide, roll, and pocket. Rules adjudication (fouls, group assignment, next turn) resolves only after all balls come to a complete stop.

### 2. Prioritized Issue Backlog (P0 – P2)
- **P0 — Direct Drag-and-Drop Cue Ball Placement (Replace Slider-First Ball in Hand):**
  - *Current:* Right-panel `Along the table` and `Across the table` range sliders are presented as primary placement controls.
  - *Target Fix:* Make direct on-table drag-and-drop (`Drag Cue Ball`) the primary interaction, validating position on release. Sliders should at most serve as secondary fine-tuning or accessibility fallbacks.
- **P0 — Head String & Legal Placement Zone Visualization:**
  - *Current:* The sidebar instructs `Place behind the head string, then confirm.`, but the 3D table lacks a visible head-string line or legal zone overlay.
  - *Target Fix:* Render a semi-transparent legal placement zone and a dashed head-string boundary line during break placement, with immediate visual feedback when hovering/dragging over invalid regions.
- **P1 — Streamline Cue Placement Confirmation (`Confirm cue position`):**
  - *Current:* Adjusting sliders followed by clicking `Confirm cue position` adds extra friction before aiming.
  - *Target Fix:* Transition directly from dragging and releasing the cue ball in a legal spot into aiming (or provide a lightweight confirmation / `Undo Placement` action to adjust placement without blocking flow).
- **P1 — Direct Cue Pull-Back Shooting (`Drag Cue → Pull Back → Release to Shoot`):**
  - *Current:* Cue stick, aiming line, and power feedback are hidden during placement, and shooting relies on the sidebar power slider and `Shoot` button.
  - *Target Fix:* Hide the cue stick only while placing the cue ball, then immediately transition into `Drag Cue → Pull Back → Release to Shoot` on the table with visible Cue Stick, Aiming Line, and Power Feedback rather than relying on a `Shoot` button.
- **P1 — Simplify Right-Side Gameplay Panel:**
  - *Current:* Dual sliders, confirmation buttons, pause controls, and verbose text occupy excessive sidebar space.
  - *Target Fix:* Move core placement, aiming, and shooting interactions onto the table canvas. Keep the right sidebar minimal: current turn/phase status, brief context hint, and `Pause / menu`.
- **P2 — Enrich Player HUD Match Telemetry:**
  - *Current:* `Player 1 · Turn` and `Open table` lack explicit break status, current turn sub-phase, and visual remaining-ball indicators once groups are assigned.
  - *Target Fix:* Display `Player 1 · Breaking` on the opening breakshot; once groups are assigned, clearly display `Solids` / `Stripes` along with remaining ball counts/indicators in the player HUD.

### 3. Standard Rack & Break Setup Specification
- **15 Object Balls:** Arranged in a tight triangle rack.
- **8-Ball Position:** Placed at the center of the third row.
- **Apex Ball Position:** Front apex ball centered on the Foot Spot (`TABLE.footSpot`).
- **Rear Corner Balls:** The two rear corners must contain one solid ball and one stripe ball (`makeRack` constraint).
- **Break Cue Ball:** Must be placed inside the legal area behind the Head String (`x <= TABLE.headString`).

---

## Eight-ball Gameplay Interaction Specification v1.0 (Technical Design)

> **Specification Status:** Design Complete / Implementation Not Started. No runtime code, KB, or production environment has been modified for this specification yet.

### 1. Core Interaction Principles

| Feature | Primary Operation | Expected Behavior |
| --- | --- | --- |
| Cue Ball Placement | Drag White Ball | Directly drag the cue ball to place it |
| Head String | Visual Guide | Display the legal break placement zone |
| Aiming | Rotate Cue | Cue stick rotates following the pointer |
| Shot Power | Pull Back | Pull-back distance determines shot power |
| Shoot | Release Pointer | Release pointer to strike directly (no `Shoot` button) |
| Ball Motion | Physics Simulation | Lock controls while balls are rolling |
| Turn Change | Automatic Resolution | Adjudicate turn after all balls settle |

**Key Constraint:** Do not rely on a `Shoot` button. Every shot must originate from pulling back and releasing the cue stick.

### 2. Gameplay Coordinate System

All gameplay logic uses **Table-local Coordinates** (never raw browser pixel coordinates). In this repository's 3D world (`src/game/table.js`), the table plane lies on `(x, z)` at elevation `TABLE.bedHeight + TABLE.radius` (where `x` runs along the table length left-to-right and `z`—denoted `y` in 2D top-down notation—runs across the table width), with `TABLE` as the single source of truth (`halfLength = 1.10495`, `halfWidth = 0.52096`, `radius = 0.028575`, `headString = -0.552`, `footSpot = 0.552`). Screen coordinates are projected onto the table plane via Three.js `Raycaster` (`view.point(clientX, clientY)`).

### 3. Cue Ball Placement (`STATE: BALL_IN_HAND`)

1. Entering placement renders the dashed Head String line and legal placement zone overlay.
2. `pointerdown` on the cue ball enters dragging state.
3. `pointermove` updates the cue ball position on the table plane in real time.
4. Valid positions show the normal cue ball with subtle green feedback; invalid positions show a red ghost ball and cannot be committed.
5. `pointerup` commits the placement and transitions to `AIMING` if valid; if invalid, the cue ball returns to the last valid position and remains in `BALL_IN_HAND` (never silently snapping to an arbitrary spot).
6. Touch devices support dragging/long-press without page scroll or text selection (`touch-action: none`). Provide `Reset Cue Position` as a secondary helper and retain keyboard fine-tuning for accessibility.

### 4. Cue Aiming (`STATE: AIMING`)

- Given cue ball center $C$ and pointer table projection $P$, the shot direction unit vector is $D = \frac{C - P}{\|C - P\|}$ with angle $\theta = \operatorname{atan2}(D_z, D_x)$. The cue stick always stays behind the cue ball along $-D$.
- Display only:
  1. **Primary Aim Line:** From the cue ball along $D$ to the first target ball or cushion.
  2. **Contact Indicator:** Ghost-ball ring at the predicted first contact point.
- Separate interaction zones to prevent Aim vs. Pull Back conflicts:
  - Near the cue ball / open table area: rotates aim direction.
  - Cue stick body/tail hit zone (or dedicated Touch Aim Handle on mobile): initiates `PULLING_BACK` and freezes the aim angle $\theta$.

### 5. Pull Back Power (`STATE: PULLING_BACK`)

- Given pointer displacement $S$ from the pull-back start point on the table plane:
  - $d = \operatorname{clamp}(-S \cdot D, 0, d_{\max})$
  - $p = \frac{d}{d_{\max}}$
  - $v = v_{\min} + (v_{\max} - v_{\min}) p^\gamma$
- Initial tuning candidates (to be calibrated):
  - Maximum Pull Distance $d_{\max}$: $0.45 \times \text{table width}$
  - Minimum Shoot Threshold: $5\%$
  - Power Curve $\gamma$: $1.5$
  - Maximum Power: $100\%$
  - Cue Strike Animation: $80\text{–}140\text{ ms}$
- Pulling forward (negative $d$), releasing below the $5\%$ threshold, or canceling the gesture returns to `AIMING` without firing.

### 6. Release to Shoot (`STATE: STRIKING`)

Upon pointer release with $p \ge 0.05$:
1. Lock `aimDirection` and `power`.
2. Play the forward cue strike animation ($80\text{–}140\text{ ms}$).
3. Apply the physics impulse at the exact **Strike Contact Event** when the cue tip reaches the cue ball (never before contact).
4. Transition to `BALLS_MOVING`, locking out further aiming or duplicate shots.
5. Wait until all balls settle before running `TURN_RESOLUTION`.

### 7. Explicit Gameplay State Machine

| Current State | Event | Next State |
| --- | --- | --- |
| `MATCH_SETUP` | Start Match | `BALL_IN_HAND` |
| `BALL_IN_HAND` | Valid Placement | `AIMING` |
| `AIMING` | Aim Pointer Move | `AIMING` |
| `AIMING` | Cue Pull Start | `PULLING_BACK` |
| `PULLING_BACK` | Cancel / Weak Pull | `AIMING` |
| `PULLING_BACK` | Valid Release | `STRIKING` |
| `STRIKING` | Cue Contact | `BALLS_MOVING` |
| `BALLS_MOVING` | All Balls Settled | `TURN_RESOLUTION` |
| `TURN_RESOLUTION` | Continue Turn | `AIMING` |
| `TURN_RESOLUTION` | Ball in Hand Awarded | `BALL_IN_HAND` |
| `TURN_RESOLUTION` | Game Won / Lost | `GAME_OVER` |

`PAUSED` acts as an overlay preserving the prior state and freezing strike/physics timers when active.

### 8. Pointer Events & Physics Decoupling

- Track `activePointerId` on `pointerdown` and call `setPointerCapture(e.pointerId)` so pulling the cursor outside the canvas bounds continues tracking smoothly.
- Cancel uncommitted pulls safely on `pointercancel`, `lostpointercapture`, `Escape`, or window blur.
- Ensure idempotency (`shotCommitted` / `shotId`) so duplicate `pointerup` events never submit a shot twice.
- Keep `Input Controller`, `Gameplay State Machine`, `Physics Engine` (`1/120 s` fixed step), and `Rules Engine + Renderer` cleanly separated.

### 9. HUD, Desktop/Mobile Ergonomics, and Implementation Phases

- **HUD:** Table-first presentation (`BALL_IN_HAND` → `Place Cue Ball`; `AIMING` → `Player Turn`; `PULLING_BACK` → `Power %`; `STRIKING` → minimal UI; `BALLS_MOVING` → `Balls Moving`; `TURN_RESOLUTION` → `Turn / Foul Notification`; `GAME_OVER` → `Winner + Rematch`).
- **Mobile:** Provide a Touch Aim Handle near the cue ball to avoid finger occlusion while preserving the `Pull Back → Release` mechanic.
- **Phased Delivery:**
  - **Phase 1:** Coordinate Adapter + Ball Placement + Head String (`Placement E2E`)
  - **Phase 2:** Aim + Cue Stick + Pull Back (`Pointer E2E`)
  - **Phase 3:** Release + Strike + Physics Sync (`Shot Golden Tests`)
  - **Phase 4:** Turn Resolution + HUD + Mobile (`Full Gameplay Regression`)



---

## Left-side Pull & Release Shooting Specification v1.1 (Supersedes v1.0 §4.3, §5, §6)

> **Status:** Design Complete / Implementation Not Started. No runtime code has been changed for v1.1. v1.0 sections on cue-ball placement (§3), aiming geometry (§4.1–4.2), physics decoupling (§8) and rack setup remain valid. v1.1 replaces the "grab the cue stick on the table" pull model with a **vertical power handle on the left side of the table**. The player does not need to grab the cue stick directly.

### 1. Core Interaction

`Aim → Hold Left Power Handle → Drag Down → Cue Pulls Back → Release → Cue Strikes → Balls Move`

- **Aim:** Mouse movement over the table (hover) or a one-finger drag on the table rotates the cue around the cue ball (360°). The cue always stays behind the cue ball relative to the shot direction. An aiming line and contact ring show the initial path only.
- **Charge:** Pointer down on the left power handle starts charging. Dragging down moves the handle, fills the meter, and pulls the visible cue backward along its own axis. The aim angle is locked while charging.
- **Release:** Releasing the active pointer with power ≥ minimum starts the forward strike. Exactly one physics impulse is applied at the moment the cue reaches the cue ball. The handle resets after the shot is committed, and the cue is hidden while balls move.

**Prohibited:** a Shoot button, a power slider as the main shooting control, click-to-shoot, shooting on pointer down, shooting by dragging anywhere on the table, or shooting by clicking/tapping the track.

### 2. Left Power Controller States

| State | Appearance / Behavior |
| --- | --- |
| Ready | Handle at top, 0% |
| Charging | Handle follows downward drag; meter fills |
| Low / High Power | Fill proportional to pull |
| Max Power | Handle at lower limit (100%) |
| Striking | Handle resets; cue moves forward |
| Balls Moving / Paused / Placement / Game Over | Controller disabled |

- Placed directly beside the table's left edge without covering pockets or playable cloth. Uses the existing dark-green theme with a high-contrast handle.
- Touch target is at least 44 × 44 CSS px. It is a custom interaction surface, not an `<input type="range">`.
- Only a drag sequence that starts on the handle may commit a shot.

### 3. Single Source of Truth: `pullRatio ∈ [0, 1]`

One normalized value drives the handle position, meter fill, displayed %, cue backward offset (`cuePullOffset = pullRatio × maxCuePullDistance`), and shot strength.

```ts
const dragDistance = Math.max(0, currentPointerY - pointerDownY); // relative to pointer-down origin
const pullRatio    = Math.min(1, dragDistance / maxDragDistance);
const shotStrength = Math.pow(pullRatio, config.powerCurve);
// Initial tuning defaults (not verified physical constants):
const config = { minPower: 0.05, powerCurve: 1.5, maxPower: 1, strikeDurationMs: 110 };
```

`shotStrength` is passed to the existing `createShot(balls, direction, power)` in `src/game/physics.js` (speed = `0.18 + power × TABLE.maxSpeed`). The existing solver is not replaced.

### 4. Pointer Events Contract

- Uses `pointerdown` / `pointermove` / `pointerup` / `pointercancel` / `lostpointercapture` and `setPointerCapture` on the handle.
- Only the pointer that started the drag can update or commit the shot. A second pointer is ignored.
- Releasing outside the controller still shoots if capture is active and the charge is valid.
- **Cancel without shooting:** `pointercancel`, `lostpointercapture` before commit, window blur, `Escape` while charging, or a release below `minPower` (including a tap with no drag) → back to `AIMING`.
- Duplicate `pointerup` never creates a second shot (idempotent `shotId`). Cancelling after a shot is committed neither undoes nor repeats it.
- `touch-action: none` on the controller and table prevents page scrolling during gestures.

### 5. Strike Synchronization

- On a valid release, freeze direction and strength, then animate the cue forward from `cuePullOffset` to contact over a deterministic strike timeline (`strikeDurationMs`, advanced by the existing fixed-step loop rather than `setTimeout`).
- Apply the impulse once at contact, then allow a brief follow-through and enter `BALLS_MOVING`.
- Pause, backgrounding or navigation during the strike cancels the uncommitted impulse (consistent with the existing delivery-cancellation contract) and never fires twice after resume.

### 6. State Machine (v1.1 naming)

```text
BALL_IN_HAND → (valid placement) → AIMING
AIMING → (pointer down on power handle) → CHARGING
CHARGING → (cancel / weak pull) → AIMING
CHARGING → (valid release) → STRIKING → (cue contact) → BALLS_MOVING
BALLS_MOVING → (all balls settled) → TURN_RESOLUTION → AIMING | BALL_IN_HAND | GAME_OVER
```

The controller is enabled only in `AIMING`. It is never enabled in placement, motion, resolution, pause, inspection, WebGL loss, lost tab ownership, or game over. `CHARGING` and `STRIKING` map to the existing checkpoint phase `aiming`, so the storage schema is unchanged.

### 7. Layout

- **Desktop:** left vertical power controller + table as the main area; compact player HUD above; minimal right-side status (turn, short hint, Pause). No horizontal power slider and no Shoot button.
- **Mobile landscape:** full table visible; controller along the left edge; one-finger pull-and-release; no clipped pockets or controls; orientation changes cancel an uncommitted charge safely. Fullscreen is not required.
- **Keyboard accessibility (secondary path):** the handle is focusable with an accessible label and `aria-valuenow`. Arrow keys adjust the charge and Space/Enter releases it. This uses the same `pullRatio` path and threshold.

### 8. Acceptance (Definition of Done)

A player can aim, pull down the left handle, see the cue move backward, release, see the cue strike, and see the balls move through the real physics engine, with no Shoot button. In the browser, a pull of about 80% must give a higher initial cue-ball speed than about 30% under the same conditions. Cancelled, weak and duplicate releases must never shoot, and save/reload must never replay a committed shot.
