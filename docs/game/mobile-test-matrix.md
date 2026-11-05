# Game viewport and mobile test matrix

All results below are local browser automation on 2026-11-05. Touch, pixel density and viewport changes are emulated; no physical phone or tablet was attached.

| Viewport | Browser evidence | Result and qualification |
| --- | --- | --- |
| 360×800 | Chromium touch emulation; [baseline](../../output/playwright/game-audit/baseline/aiming-360x800.png), [after](../../output/playwright/game-audit/after/aiming-360x800.png) | Start, aim by touch, pause/resume; no document horizontal overflow. Key target dimensions checked. |
| 390×844 | Chromium touch emulation; [baseline](../../output/playwright/game-audit/baseline/aiming-390x844.png), [after](../../output/playwright/game-audit/after/aiming-390x844.png), [Options](../../output/playwright/game-audit/after/390-options-open.png) | Start, touch/pointer coordination, cancellation/handoff, pause/resume, restart, failure recovery, quality toggle and accessible group progress checked. WebKit separately completed a shot smoke test at this viewport. |
| 768×1024 | Chromium viewport and mouse input; [baseline](../../output/playwright/game-audit/baseline/aiming-768x1024.png), [after](../../output/playwright/game-audit/after/aiming-768x1024.png) | Layout, pointer aim and pause/resume checked with no horizontal overflow. Tablet touch was not independently emulated in this observation. |
| 1440×900 | Chromium desktop; [baseline](../../output/playwright/game-audit/baseline/aiming-1440x900.png), [after](../../output/playwright/game-audit/after/aiming-1440x900.png) | Layout, mouse aim, pause/resume and key control dimensions checked. |
| 320×568 and 844×390 | Chromium viewport/touch emulation in `npm run test:browser` | Short portrait and landscape layout checks passed; the same active game was also resized 390×844 → 844×390 → 390×844 with state, canvas and controls checked. |

The browser suite also exercises visibility-change injection during pending saves, multiple contacts and cancellation, a local save failure, retries, and leaving Game. Some cancellation is injected as a DOM `pointercancel`; a changed viewport is not a physical orientation event. Real iOS/Android browser chrome, nonzero safe-area insets, OS interruption, actual touch cancellation and hardware performance remain unverified.
