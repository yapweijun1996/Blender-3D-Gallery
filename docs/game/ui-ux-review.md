# Game UI and UX review

The existing restrained gallery style and table-first composition were retained. A visual review of actual desktop and mobile screenshots found no major regression; the randomly ordered rack and differing device-pixel ratios prevent pixel-identical comparison.

## Changes supported by evidence

- The table and range controls have visible keyboard focus. Game-changing shortcuts require table focus; clicking or touching the canvas focuses the table. A keyboard regression checks the asynchronous save boundary, not merely the immediately visible phase.
- Mobile aiming includes “Drag to aim; press Shoot to strike.” Secondary buttons have larger touch targets. Player cards expose a compact count while Chromium's accessibility tree includes the actual remaining ball numbers or the eight-ball instruction.
- A storage failure remains visible during mobile play. Failed initial GLB/WebGL loading offers Retry loading and Back to Gallery. Losing WebGL closes obstructing dialogs and exposes a focused recovery action.
- App options offers real Standard and Performance rendering-quality choices. Standard preserves the original pixel-ratio cap; Performance lowers the cap to 1 until the player leaves Game. It does not alter the models or game state.

Compare [mobile baseline](../../output/playwright/game-audit/baseline/aiming-390x844.png) and [mobile after](../../output/playwright/game-audit/after/aiming-390x844.png), or [desktop baseline](../../output/playwright/game-audit/baseline/aiming-1440x900.png) and [desktop after](../../output/playwright/game-audit/after/aiming-1440x900.png). The [mobile Options dialog](../../output/playwright/game-audit/after/390-options-open.png) shows the quality control. Full browser observations are in [results.json](../../output/playwright/game-audit/after/results.json).

## Accessibility evidence and limits

Chromium browser tests exercised keyboard focus and shooting, visible failure feedback, native dialog recovery, 320/390px accessibility-tree text for numbered remaining balls, touch-target dimensions for key actions, and reduced-motion CSS while a real game remained playable. Sample calculated text/background contrast ratios ranged from 5.46:1 to 11.92:1 for four inspected color pairs; this is not an exhaustive contrast audit or a WCAG conformance claim.

At widths up to 900px the visible player-card summary still shows a count rather than each remaining number; the complete numbered list appears in Chromium's accessibility tree. Sighted low-vision usability of the small balls and the need for a visible numbered detail remain P2 research/design work. VoiceOver, TalkBack, real-user comprehension, physical-device focus and full screen-reader announcement behavior were not tested.
