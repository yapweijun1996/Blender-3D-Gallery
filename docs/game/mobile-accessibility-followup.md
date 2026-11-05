# Mobile and accessibility follow-up

## Current fix validation: 2026-11-05

The final isolated branch `codex/game-loading-reliability-latest` uses main snapshot `2581395a7d8c4d475eb558f431f211745fb4617a`, preserving concurrent Gallery and viewport work. The matrix ran on the identical production-format app from snapshot31e5475; the subsequent main update changed only two test-count fixtures, and rebuilding retained the same build identity. Build identity `042c99b1e32521a0` passed the primary agent's independent final browser run: **20/20**, exit 0, no collected unexpected console or page errors. An earlier intermediate integration also passed 20/20 at build `df37c64681102b95`; its evidence is retained separately.

The original Pause-label failure was reproduced on this newer baseline before editing. A Game-scoped rule at <=260px wraps header/caption controls and stacks shot/placement and Pause rows, retaining >=44px targets. The expanded checks measure visual-viewport bounds, label clipping, control/text overlap, center hit testing and actual touch interaction. Main intentionally places each range label inside its corresponding 44px target: the test permits only the two correctly associated, pointer-transparent labels within the reserved 16px padding area. Every viewport also touches both real ranges and verifies their values change; no generic overlap exception was added. They cover 195x422, 195x800, 260/261px breakpoint sides, 320x450, 320x568, 360x800, 390x844, 768x1024, 1440x900, 844x390 and 568x320. Error retry, keyboard modal paths and AX names/status/progress are included. The primary agent inspected new 195px, 390px and desktop aiming screenshots. Controls may require scrolling; simultaneous first-viewport visibility is not claimed.

Retained [final JSON](../../output/playwright/game-loading-fix/mobile-latest-results.json), [test log](../../output/playwright/game-loading-fix/mobile-latest.log), [new-baseline failure JSON](../../output/playwright/game-loading-fix/mobile-baseline-results.json), [baseline screenshot](../../output/playwright/game-loading-fix/mobile-baseline-195x422.png), [fixed narrow screenshot](../../output/playwright/game-loading-fix/latest-actions-195x422-aiming.png), [phone screenshot](../../output/playwright/game-loading-fix/latest-actions-390x844-aiming.png) and [desktop screenshot](../../output/playwright/game-loading-fix/latest-actions-1440x900-aiming.png).

These are Chromium touch emulation and AX-tree checks. Physical phones/tablets, actual browser zoom, VoiceOver/TalkBack, hardware safe areas and sustained mobile performance remain unverified. The original narrow P2 is resolved in the tested candidate; it is not a full WCAG conformance determination. Gallery, About, assets and download behavior are not changed by the CSS repair.

## Historical review before the fix

The following sections record the earlier revision and findings; their remaining-failure and no-code-change statements describe that historical review.

## Confirmed finding

**P2 — very narrow stress viewport:** In a Chromium touch-emulated context configured to 195×422, the screenshot shows the `Pause / menu` text wrapping beyond its fixed-height button; Aim and Power text also becomes crowded. The actual reported layout viewport was 199×431 CSS pixels. This is below the 320 CSS-pixel reflow probe and is not evidence of an actual 200% browser zoom failure or a WCAG conformance determination. See `reflow-195x422.png` in the local evidence directory below. No application code was changed in this review.

## Scope and environment

- Source: `d19606eb65962b66a0fc07be5b5f3c06ec6ef745`, branch `codex/pr1-review-followup`.
- Frozen `dist/` build identity: `7c832c4d674222d3`; `dist/index.html` SHA-256: `cdfd0e61b1f9ea041a4e2e4c32b678d0548deb18185c7bfb42cfedb8c4dc8737`.
- 2026-11-05; macOS arm64, Node 24.21.0, Playwright Chromium 156.0.8078.4 with SwiftShader WebGL and loopback HTTP. Touch is browser emulation, not a physical device.
- Executed: `/opt/homebrew/opt/node@24/bin/node scripts/test-game-review-followup.mjs`. Raw results and screenshots: `/tmp/game-pr1-followup/mobile-a11y/run-JNDvv1/`. These local files are not tracked and may be removed by the operating system; the script creates a fresh run directory on each execution.

## Observed results

| Check | Result | Evidence and limits |
| --- | --- | --- |
| 360×800 touch, DPR 2 | Pass | Touchscreen taps started a match, confirmed placement, changed aim on the real canvas, paused, resumed, restarted and exited to Gallery. Five measured game buttons were at least 44×44 CSS pixels; document `scrollWidth` was 360. |
| 390×844 touch, DPR 3 | Pass | The same journey passed, with `scrollWidth` 390. Screenshots include aiming and the pause dialog. |
| 768×1024 touch, DPR 2 | Pass | The same journey passed using an emulated touch-enabled tablet viewport, with `scrollWidth` 768. This is not a physical tablet. |
| Keyboard modal paths | Pass for background-control exclusion and focus restoration; full focus trap unverified | Rules, Options and nested Pause/Restart opened by keyboard; Tab did not focus another application control; Escape closed the appropriate dialog and restored focus to its trigger. Chromium reported `BODY` as active between dialog controls; this may represent a browser-chrome focus cycle, but it was not independently verified. This is not evidence of a strict continuous in-dialog focus loop or a screen-reader test. |
| Chromium accessibility tree, 390×844 | Pass, with qualification | Actual AX nodes included named Aim and Power sliders, Shoot and Pause buttons, a `status` role, and one each of `solids cleared; 8 ball next.` and the actual seven stripe ball numbers. The visual `7 left` summary was not duplicated as AX text. This does not establish what a particular screen reader announces. |
| 320×450 viewport reflow | Pass for measured bounds | `innerWidth` and document `scrollWidth` were both 320; Shoot and Pause were 128×44 CSS pixels. They were below the initial viewport and this probe did not click them after scrolling. This viewport is only a reflow approximation, not an actual browser zoom test. |
| 195×422 viewport stress | P2 visual issue; automated assertion invalid | Actual `innerWidth` and `scrollWidth` were both 199. The original test incorrectly compared `scrollWidth` with the requested width of 195 and therefore reported an invalid horizontal-overflow failure; the screenshot independently shows the button-label issue above. The original run did not collect `visualViewport.width` or `scale`. |

No uncaught page errors or console errors were recorded in the seven scenarios. The original run returned **6/7 automated checks passed**; its seventh failure was the incorrect configured-width comparison described above, not proof of horizontal overflow. After that run, the script was corrected to compare measured layout widths, record `visualViewport` dimensions and scale, and check button text bounds. The review agent syntax-checked the correction; the primary agent subsequently reran it in Chromium, as recorded below.

## Coverage not established

- **0 physical phones, 0 physical tablets, 0 real screen-reader sessions** and no VoiceOver or TalkBack session were available. Browser touch emulation and Chromium AX-tree inspection do not replace those checks.
- Actual browser 200% zoom, mobile visual-viewport behavior and scale, system font scaling, nonzero device safe areas, physical orientation changes, OS interruption and real touch cancellation remain unverified. Two resized CSS viewports are approximations only.
- Only Chromium was run in this follow-up. No cross-browser accessibility certification, user study, full WCAG audit or sustained mobile performance measurement is claimed.

## Independent corrected-script rerun

The primary agent executed the corrected script on the same revision. It returned 6/7 checks passed, exit 1. The remaining failure is now a genuine text-bounds assertion for Pause / menu at the sub-320px stress viewport, not the former configured-width comparison. Its measured layout width was 199px, visualViewport width 195px and scale 1; this remains an artificial narrow viewport, not browser zoom. The 320px probe measured visualViewport width 320 and scale 1. The three touch journeys, modal paths and AX checks passed again. Raw results: [retained JSON](../../output/playwright/pr1-followup/mobile-accessibility.json); [stress screenshot](../../output/playwright/pr1-followup/reflow-195x422.png). No full passing result or real zoom/device certification is claimed.
