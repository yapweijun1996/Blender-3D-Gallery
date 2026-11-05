# Game release readiness

**Status: NEEDS REVIEW.** Local implementation and regression checks passed, but physical-device performance/accessibility, longer-term GPU memory behavior and the existing asset redistribution decision remain open. This branch has not been merged or deployed; owner approval is required before either action.

## Local evidence

Baseline: `38350b3933aa5d60bc7207d50b2e5577ae8781c3`; branch: `codex/game-experience-improvements`. Final checks used Node 24.21.0 on macOS arm64 and production-format local builds.

| Check | Result |
| --- | --- |
| `npm test` | 25 passed, 0 failed/skipped. |
| `npm run build` | Passed; 39 catalog GLBs validated with 0 errors/warnings. Existing 639 kB lazy Three.js chunk advisory remains. |
| `npm run test:browser` | 45 scenario groups passed, including Chromium real-browser journeys and WebKit shot smoke. No collected page errors. |
| `npm run test:pwa` | 9 offline, update, cache and recovery scenarios passed. |
| `npm run test:solar` | Passed for 17 Solar assets. Existing review fields and physical-device status in generated reports are not newly established by this run. |
| `node scripts/test-solar-scene.mjs` | Passed at 1440, 768, 390 and 320 CSS-pixel widths. |
| Four requested Game viewports | Captured and inspected at 360×800, 390×844, 768×1024 and 1440×900; [matrix and evidence](mobile-test-matrix.md). |

The Solar test scripts write generated reports/screenshots under `models/solar-system/reports` by default. In this clean isolated worktree their generated outputs were copied to temporary evidence and the previously clean tracked reports were restored. Use a disposable worktree or an explicit artifact directory where supported when repeating them.

Machine-readable [browser](../../output/playwright/game-audit/after/browser-tests.json) and [PWA](../../output/playwright/game-audit/after/pwa-tests.json) results and the [unit-test log](../../output/playwright/game-audit/after/unit-tests.log) are retained with the screenshots. [Solar asset](../../output/playwright/game-audit/after/solar-assets.log) and [scene](../../output/playwright/game-audit/after/solar-scene.log) output is retained separately.

## Findings and disposition

- No P0 remains confirmed by local checks. The baseline P1 keyboard, mobile save-warning, background-save and late-lock failures have targeted browser regressions.
- **P1 release decision:** the original billiards pack states that redistribution terms have not been selected. No model or license was changed. The owner must resolve any required rights/redistribution decision before an authorized release.
- **P2:** at ≤900px the visible HUD shows a remaining count rather than each numbered ball; the numbered list is exposed in the Chromium accessibility tree. Sighted low-vision usability and a visible detail alternative need real-user/device evaluation.
- **P2 validation gaps:** physical iOS/Android, actual OS backgrounding, VoiceOver/TalkBack, nonzero safe-area insets, long-duration GPU memory, network-throttled startup and real-GPU performance remain unverified. Proposed performance targets are not met in the measured SwiftShader environment and must not be presented as met on hardware.
- No deployment, production data change, remote CI result or KB update is implied by local testing. Review status and performance numbers are recorded separately in [13-persona review](13-persona-review.md) and [performance report](performance-report.md).

## Rollback

Before merge, abandon or close the feature branch/PR; the original `main` and the user's untracked local plan remain intact. If a future approved merge needs reversal, use a normal revert of the merge/feature commit, run the same checks and use the separately authorized Pages deployment workflow. Do not force-push or delete player saves. Check checkpoint compatibility before any rollback that changes save schemas; this change preserves the existing schema.
