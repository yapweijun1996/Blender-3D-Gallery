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

The game loads its table, cue and sixteen balls from the existing catalog. A failed initial 3D load or unavailable WebGL must leave a clear recovery path. WebGL context loss during a match offers a save/reload path for the last stable turn. No external model code is executed.

## Acceptance evidence

The baseline and findings are recorded in [game baseline](../audits/game-baseline.md). The final executed checks and remaining device limitations are recorded in [release readiness](release-readiness.md); an unexecuted scenario is not a passing result.
