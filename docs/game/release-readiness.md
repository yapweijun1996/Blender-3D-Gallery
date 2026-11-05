# Game release readiness

## Owner-approved main integration — 2026-11-06

The owner has now explicitly requested commit, merge and push to main. The earlier review-only permission statements below are historical and are superseded for this integration. Fresh checks of current main `7dc9f06` plus PR #2 head `ad3e8c4` passed at build `cc6a1b733057e06d`; see [integration evidence and limits](main-integration-verification-20261106.md). Licensing remains pending and downloads are unchanged. Remote publication is verified separately after push.

## Historical review delivery

**Status: NEEDS REVIEW.** The requested local loader and narrow-layout repairs are verified. This is a review delivery, not approval to merge or deploy. Asset licensing remains pending; downloads and assets are unchanged by this patch.

## Final source and scope

- Branch: `codex/game-loading-reliability-latest`, based on main snapshot `2581395a7d8c4d475eb558f431f211745fb4617a`.
- Tested production-format build: `042c99b1e32521a0`; Node 24.21.0, macOS Apple M4. Test runtime details are retained with each diagnostic.
- Application changes: `src/game/scene.js` reads native responses and uses the same GLTF parser/URL base, with scene-owned request cancellation and stopped queues; `src/game/style.css` reflows Game controls only at <=260px.
- Preserved: concurrent main Gallery/viewer/model and viewport work, all GLBs, lighting/camera/materials, rules/physics, save schema, downloads, PWA cache/update policy, dependency pins and deployment workflow. The final diff contains no changes to those protected paths.
- Validation found two obsolete catalog counts of40 (`41 !== 40`). Main subsequently fixed these in `2581395`; the branch adopts those upstream fixtures rather than duplicating the patch. App/dependency sources did not change between main snapshots31e5475 and2581395, and rebuilding produced the identical tested build. The two affected suites were rerun after synchronization. Strict equality and per-model preview/download coverage remain; first failure logs are retained.

## Executed verification

All final commands below exited 0. The [verification manifest](../../output/playwright/game-loading-fix/verification-manifest.json) records the exact code/base identities and the fixture-only synchronization; retained build logs normalize trailing spaces only. No runner case was marked skipped. Browser probes are actual browser interaction, not static markup tests.

| Command or probe | Final result | Retained evidence |
| --- | --- | --- |
| `npm run build` | Pass; asset validation and Vite build. Existing 639kB lazy Three.js chunk advisory remains. | [build log](../../output/playwright/game-loading-fix/build-synced.log) |
| `npm test` | 77 passed, 0 failed/skipped | [unit log](../../output/playwright/game-loading-fix/unit-latest.log) |
| `npm run test:browser` | 45 groups passed, including WebKit shot smoke and every gallery asset preview/download | [JSON](../../output/playwright/game-loading-fix/game-browser-synced-results.json), [log](../../output/playwright/game-loading-fix/game-browser-synced.log) |
| `node scripts/test-game-loading.mjs` | 5 passed: interrupted/truncated recovery, valid extras, held-request route cleanup, partial-transfer network cancellation | [log and CDP cancellation bytes](../../output/playwright/game-loading-fix/loading-final.log) |
| `node scripts/test-game-review-followup.mjs` | 20 passed; primary independently reran the final latest-main adaptation | [JSON](../../output/playwright/game-loading-fix/mobile-latest-results.json), [mobile review](mobile-accessibility-followup.md) |
| `npm run test:game-responsive` | 20 groups passed | [JSON](../../output/playwright/game-loading-fix/responsive-latest-results.json) |
| `npm run test:game-experience` | 5 groups passed | [JSON](../../output/playwright/game-loading-fix/experience-latest-results.json) |
| `npm run test:pwa` | 16 passed, including offline Game and safe updates | [JSON](../../output/playwright/game-loading-fix/pwa-latest-results.json) |
| `npm run test:standard` | 9 passed | [JSON](../../output/playwright/game-loading-fix/standard-synced-results.json) |
| `npm run test:library` | 9 passed | [JSON](../../output/playwright/game-loading-fix/library-latest-results.json) |
| `npm run test:game-ux` | 7 passed | [stdout log](../../output/playwright/game-loading-fix/ux-final.log) |
| `npm run test:reviewed` | 8 passed | [stdout log](../../output/playwright/game-loading-fix/reviewed-final.log) |
| `develop-web-game` client | Two action iterations reached `moving`; actual canvas screenshots inspected. The unchanged skill client was copied to an isolated temporary runner to resolve the pinned Playwright. | [run manifest](../../output/playwright/game-loading-fix/web-game-client/run.json), [state](../../output/playwright/game-loading-fix/web-game-client/state-1.json), [screenshot](../../output/playwright/game-loading-fix/web-game-client/shot-1.png) |
| Actual download and navigation | Real download event; 417,656-byte table GLB SHA-256 matches source; Gallery/About/Demos/Game round trip and legacy deep link passed | [JSON](../../output/playwright/game-loading-fix/download-latest-results.json) |
| Independent six-control mechanism reproduction | Both native controls finished; manual wrappers/FileLoader/GLTFLoader emitted the reproduced abort; returned bytes matched the original hash | [JSON](../../output/playwright/game-loading-fix/mechanism-independent.json) |
| Independent latest-build native diagnostic | Observed and unobserved runs each had 18 finished, 0 failed; 18/18 consumed-byte hashes matched | [JSON](../../output/playwright/game-loading-fix/native-latest-diagnostics.json) |

Initial [Game count failure](../../output/playwright/game-loading-fix/game-browser-initial-failure.log) and [standard count failure](../../output/playwright/game-loading-fix/standard-initial-failure.log) were followed by the successful full reruns above. The UX suite records its seven scenarios in stdout; its actual log is retained.

The primary agent inspected final 195px, 390px and desktop gameplay screenshots. The [matrix](mobile-test-matrix.md) and [mobile report](mobile-accessibility-followup.md) distinguish necessary scrolling, simulated touch, associated slider labels, AX-tree checks and physical-device gaps. A separate static reviewer found no confirmed new P0/P1/P2 in this bounded patch; that review is not an extra execution of the suites.

## Performance and remaining findings

- No new P0 was confirmed by the bounded checks. The reproducible narrow Pause-label issue and uncanceled Game downloads are resolved in the tested build.
- **P1, owner-deferred:** existing asset redistribution/license decisions remain open. No license grant, attribution replacement or download-policy change was made. See [decision context](asset-license-decisions.md).
- **Performance gap:** frozen-build alternating 5+5 cold starts at 100ms / 4Mbps gave medians 9,587ms before and 9,547ms after; ranges overlapped, so no speedup is established. All asset bytes were unchanged. Diagnostic segmentation identified uncompressed local JS delivery before roughly 7.5s of GLB transfer; 3.70MB of GLBs alone has an ideal 7.4s floor at 4Mbps. These figures do not describe production compression or physical phones. [Exact methods, build pins and raw data](loading-root-cause.md).
- **P2/verification gaps:** physical iOS/Android, VoiceOver/TalkBack, real browser zoom, hardware safe areas, thermal behavior and sustained GPU-memory retention remain unverified. The underlying Chromium reason for stream-wrapper cancellation events is unknown; the Game path avoids the reproduced wrapper while genuine cancellation/errors remain tested.
- Full Solar-generator/Saga-specific suites were not rerun: the patch does not change their assets, generators or scene logic. The build validates catalog GLBs, all 41 gallery models were previewed/downloaded by the Game regression, and library/reviewed checks exercised preserved routes. This does not imply a fresh complete Solar or Saga certification.
- The previous 13-persona panel remains historical; this follow-up has engineering, UX/accessibility, product/static and primary QA evidence, not a fresh independent 13-persona panel.

## Review delivery and rollback

Prepare a draft PR from the isolated feature branch only. The checked-in workflow triggers deployment for main pushes or explicit dispatch; this task does neither. No main merge, deployment, release or KB content update is authorized by these results. PR #1 had already been merged before this follow-up; this is a separate reviewable repair.

Before an approved merge, close the draft PR or abandon/revert these feature changes; no deployed behavior or player save was changed by this task. Any later rollback of an authorized merge should use a normal revert and the relevant tests, followed by a separately authorized deployment. Do not force-push or remove player checkpoints.

<details>
<summary>Historical pre-fix and pre-merge assessments</summary>

## Current follow-up: 2026-11-05

**Status: NEEDS REVIEW.** PR #1 was already merged at 10:24:15 SGT before this follow-up. This review uses `d19606eb65962b66a0fc07be5b5f3c06ec6ef745` in isolated branch `codex/pr1-review-followup`; it performs no further merge, deployment or asset-license change. There are no GitHub PR review comments or submitted reviews on #1 as of this check.

Fresh build and 70 unit tests passed. Corrected additional browser checks passed 6/7: three emulated touch journeys, keyboard modal checks, AX-tree checks and 320px reflow passed; an artificial sub-320px stress viewport retains a P2 overflowing button label. Hardware desktop rendering was measured on Apple M4; mobile GPU results are desktop mobile emulation. A cold 100ms/4Mbps profile loaded in approximately 9.5 seconds, above the provisional startup targets; GLB aborted-request events conflict with Resource Timing and ready-state evidence and remain unresolved. No all-device performance or accessibility acceptance is claimed.

The existing **P1 asset redistribution decision** remains open. Physical mobile, screen-reader operation and long-duration GPU memory behavior remain unverified. See [follow-up status](pr1-followup-status.md), [mobile/accessibility evidence](mobile-accessibility-followup.md), [performance evidence](performance-followup.md) and [owner license decisions](asset-license-decisions.md).

Rollback for this review is to remove its documentation, evidence and audit-script changes or revert a future review commit. It changes no runtime behavior, asset, save schema or deployed site. Reverting the already-merged PR would be a separate owner-authorized action; none is performed here.

## Historical pre-merge assessment

The remainder records the original feature-branch evidence and pre-merge status. Its branch/merge statements and test counts are historical, not the current repository state.

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

</details>
