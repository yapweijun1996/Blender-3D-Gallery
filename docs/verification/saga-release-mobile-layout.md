# Saga release layout prerequisite

The Saga release commit `284a192` inherited the existing Game layout from `7f1f3f5`. GitHub deployment checks failed at 360×800 because the Shoot/Pause actions ended at 809.36 px, beyond the 800 px viewport. The same failure was recorded before Saga in run 42031807868 and after Saga in run 42032404964.

The owner authorized a minimal independent fix without using any original-worktree uncommitted Game changes. The CSS correction reserves 24 additional pixels in the tall-phone table size budget for wrapped guidance and the 44 px action row. The setup table receives the same reserve and safe-area subtraction. Desktop setup also caps the canvas height to the existing first-screen budget so its header and player cards cannot displace the table below the viewport. Fullscreen, shot rules, touch target sizes and short-phone minimum table dimensions are unchanged.

Local baseline testing also exposed setup-entry overflow at 1280×720 (board bottom 808.83 px) and 390×844 (857.98 px). The desktop correction brings its board bottom to 696.98 px. The 320×568 setup baseline remains within the viewport at 562 px. These checks are Chromium viewport/touch emulation, not physical-device validation.

Final verification commands: `npm run build`, `npm run test:browser`, and `npm run test:game-responsive`. No test assertions were relaxed. The parent release manager records final execution and deployment results.

The full Game browser run passed its layout and gameplay checks, then exposed one stale gallery assertion: it expected 39 assets. This release adds the Saga as asset 40, so the assertion is updated to 40. This changes the expected collection size only; no layout or game assertions were weakened.
