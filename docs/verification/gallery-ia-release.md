# Gallery IA release integration

## Authorization and preservation

On 2026-11-05 the owner explicitly authorized direct commit, merge and push to GitHub `main` after completion. This supersedes the original local-only delivery boundary for this release. The existing `main` push workflow automatically builds and publishes GitHub Pages; no new deployment mechanism or manual workflow trigger is introduced. KB writes remain unauthorized and were not performed.

The initial reviewed IA implementation was committed as `706beca`. Before release, fetching origin showed newer `main` at `7419def`, containing the independently developed Game reliability and mobile accessibility improvements from `e307bdb`. Integration is performed in the isolated IA worktree, retaining both histories. The local backup branch `backup/gallery-before-ia-20261105` points to `7419def`. A second local backup, `backup/gallery-last-live-20261105`, points to `38350b3`, the last successfully published revision. The intervening main run `41954973602` failed its mobile test before deployment; production still served build `75afc7500ec37f5b` during preflight. A normal Git revert can restore an authorized prior state without rewriting remote history.

Preserve the new upstream asynchronous save/context-loss safeguards, keyboard focus boundaries, IndexedDB ownership lifecycle, loading recovery, graphics-quality option, touch targets and remaining-ball feedback. Preserve the IA model/demo discovery, legacy URLs, safe metadata registries and absolute viewport button regressions. Merge conflicts in the catalog validator and Game layout must combine these requirements rather than select one side wholesale.

The original main worktree's unrelated untracked local plan remains outside the commit. Model sources, GLBs, attribution and rights are not changed by the IA release. Newly fetched upstream artifacts are retained as existing upstream work rather than rewritten or regenerated.

## Acceptance

Integrated acceptance used Node 24.21.0, Playwright 1.64.1 and the frozen production build `bf8ee8e9155e74aa`. Independent manager checks passed:

| Check | Result | Evidence |
| --- | --- | --- |
| Unit tests | 35 passed, zero failed | `/tmp/b3g-release-unit.log` |
| Production build | Asset validation and build passed | `/tmp/b3g-release-build.log` |
| Expanded Game/gallery browser suite | 45 passed; errors empty; includes WebKit smoke and every upstream reliability scenario | `/tmp/b3g-release-manager-game.log`, `/tmp/b3g-release-manager/game/results.json` |
| PWA suite | Nine passed | `/tmp/b3g-release-manager-pwa.log` |
| Solar scene | Four viewport cases passed | `/tmp/b3g-release-manager-solar-scene.log` |
| Solar assets | All 17 GLBs passed loader/geometry/validation checks | `/tmp/b3g-release-solar-assets.log` |
| Library independent QA | Nine passed on frozen build; all seven index viewports, zero initial GLBs/canvas/overflow | `/tmp/b3g-release-library-rerun.log` |
| Accessibility independent QA | Five 390 px routes, zero automated axe violations; incompletes retained | `/tmp/b3g-release-axe-final.log`, `/tmp/b3g-axe-results.json` |
| Registry preservation review | 16 catalog/registry tests passed; complete upstream URI checks retained | `/tmp/b3g-integration-registry-review.log` |

The observed upstream CI race was fixed in the test readiness boundary: `aiming` can be assigned before a pending save completes and its UI updates. Helpers now await a visible, enabled Shoot control, or a visible placement action, before measurements. Assertions are preserved; no fixed sleep substitutes for UI readiness. The compact 320×568 Game view retains all 44 px actions, player/remaining-ball information and instructions; its smaller 132 px table is an explicit small-screen tradeoff. Source Game page/scene/storage remain identical to upstream.

A library probe transiently showed the pool-table fallback while a production rebuild overlapped test execution. Its cause was not established as a product defect. Evidence was retained; isolated loads passed three of three, and the complete library suite passed on the frozen build. No additional rebuild ran during final acceptance.

Final diff review found no IA changes to original model binaries, the lockfile or deployment workflow. Initial IA-only checks remain separately recorded in `gallery-ia.md`; release acceptance is based on the integrated checks above. Local evidence paths identify session artifacts; public CI evidence is the Actions run associated with the exact pushed revision.

## Publication evidence

A successful push must be verified against `refs/heads/main` on GitHub. Match the Pages Actions run to the exact pushed revision, wait for its build and deployment outcome, then compare production `build-info.json` with the tested build and inspect the visible Models/Demos routes. A successful Git push alone is not a deployment claim. Final workflow and live-check results are reported with their exact identities after observation.

Real mobile GPU performance, physical iOS/Android installation, browser zoom and production Core Web Vitals remain outside the executed desktop browser evidence. Existing artwork terms remain pending; this release does not assign a new redistribution license.
