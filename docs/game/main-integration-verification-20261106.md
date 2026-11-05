# Main integration verification — 2026-11-06

The owner explicitly requested “commit merge push to main” on 2026-11-06 (Asia/Singapore). This supersedes the earlier review-only merge restriction. It does not select an asset license or grant new redistribution rights; licensing stays pending and downloads remain unchanged.

## Candidate and preservation

The isolated worktree combines main `7dc9f06a067551d89c280e38ba2f52986ca7f848` with PR #2 head `ad3e8c469e233f9ada8ebb64533699dd7d1c661c`. Git reported no merge conflicts. An independent read-only reviewer confirmed that the application delta consists only of the Game loader and <=260px Game control reflow. The current main Saga/model/viewer changes, main/index/global styles, physics/rules, save schemas, PWA policy, dependencies and deployment workflow were not overwritten. The previous main is retained in local branch `codex/pre-game-main-20261106` and remains the first parent of the integration commit.

## Fresh local checks

Node 24.21.0; production-format build `cc6a1b733057e06d`. All listed commands exited 0 on the prepared integration, before its commit or main push:

| Command | Result | Evidence |
| --- | --- | --- |
| `npm ci` | Passed | Session install log retained locally |
| `npm test` | 77 passed, 0 failed/skipped | [log](../../output/playwright/main-integration-20261106/unit.log) |
| `npm run build` | Passed; existing large Three.js chunk advisory remains | [log](../../output/playwright/main-integration-20261106/build.log) |
| `npm run test:browser` | 45 passed, including WebKit and every gallery preview/download; collected errors empty | [JSON](../../output/playwright/main-integration-20261106/browser.json) |
| `npm run test:library` | 9 passed; collected errors empty | [JSON](../../output/playwright/main-integration-20261106/library.json) |
| `npm run test:pwa` | 16 passed; collected errors empty | [JSON](../../output/playwright/main-integration-20261106/pwa.json) |
| `node scripts/test-game-loading.mjs` | 5 passed, including partial-transfer cancellation and re-entry | [log](../../output/playwright/main-integration-20261106/loading.log) |
| `node scripts/test-game-review-followup.mjs` | 20 passed; all scenarios passed, no unexpected console/page errors | [JSON](../../output/playwright/main-integration-20261106/mobile.json) |

The primary agent inspected fresh [195px](../../output/playwright/main-integration-20261106/actions-195x422-aiming.png) and [390px](../../output/playwright/main-integration-20261106/actions-390x844-aiming.png) screenshots. JSON/PNG records are copied without modification; text-log trailing spaces are normalized, with original stdout retained under `/tmp/game-main-*.log`.

## Release and limits

The existing repository workflow runs on a main push and includes its own full validation followed by Pages deployment. No workflow dispatch, protection change, force-push or separate manual deployment is requested by this integration. Remote main, PR state, workflow result and live build must be observed after push before claiming publication. Those post-push facts are not asserted by these pre-push results.

Asset terms, physical iOS/Android, screen readers, actual zoom, sustained GPU-memory/thermal behavior and the previously documented restricted-network startup budget remain open. The owner approved this code merge with those disclosed limits; this is not a new accessibility/performance certification or license clearance.

For a later authorized rollback, revert the integration merge with its first parent as mainline, rerun relevant checks, and use the normal main workflow. Do not force-push or delete player checkpoints.
