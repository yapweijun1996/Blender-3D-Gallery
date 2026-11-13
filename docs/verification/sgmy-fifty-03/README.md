# SG/MY library: third 50-asset batch

**Full integration: FAIL. This is a review-only draft, not a release-ready claim.** All 50 new assets passed their local source/GLB/visual checks and all 150 fresh asset-view cases. An existing library demo-reload regression remains unresolved below.

Adds exactly 50 independent types: 023–028, 031–033, 035–036, 040, 142, 145, 148, 155–157, 190 and 470–500. Tested base `7621956d834a468504f481871ec4d6802d21cbb6`; existing244 registrations preserved, final294. Registrations are not completed master-backlog-type counts.

## Publication base boundary
Before publication main advanced to `9604912f6eded65d01424e6ff229f15fd739077d`, changing only58 GJH can files. No shared runtime, catalog or package change and no intersection with this batch’s changed paths. This PR changes no GJH files and does not replace those main updates. Tests remain explicitly on762; the newer GJH content was not retested here. See `main-advance-check.json`. No branch merge or history rewrite performed.

## Confirmed regression failure
`integration/library.log`: first seven library cases PASS. Case8, “legacy demos launch, refresh, return to index and release canvas”, fails at unchanged `scripts/test-library-browser.mjs:211`: `page.reload` exceeds30000ms waiting for `domcontentloaded`. The ninth reduced-motion/reflow case is NOT RUN. The script aborts before recording the failed case in results.json, so its seven PASS records are **not** a whole-suite PASS.

The inspected failure screenshot shows “Loading the experience…” but does not identify which iteration of `['game','solar']` failed. No Solar-specific cause is claimed. No application source, existing test, timeout or assertion was changed; no retry-to-green substituted for this failed run. One fixed diagnostic baseline control on exact762 with no new50 passed9/9, including both game and solar reloads; logging-only instrumentation changed no assertions/timeouts/app source. This does not identify the original failing iteration, prove causality or resolve the failed integration. See `baseline-control/evidence/diagnosis.md`; the original FAIL remains authoritative. The raw library environment label says macOS, inherited from the existing script; this actual integration ran on Ubuntu desktop Chromium/SwiftShader. Physical mobile was not tested.

## Verified passing checks on the same assembled tree
-383/383 unit tests and build.
-4 loading/cancellation lifecycle cases and 14 legacy preview cases.
-150/150 new-asset Chromium viewports (1440,768,390 widths), actual consumed GLB hashes, orbit/zoom/reset/close/reopen checks.
-Four isolated animation-browser assets (tool cabinet, crate, gift box, market scale). All 10 animated types/18 clips also have raw endpoint/Mixer/clearance checks in their individual validators; office mechanisms have inspected Blender action poses, not separate browser-animation UI claims.
-183 final studio views actually inspected by producers (64office+68nature+51festivals), plus corrected/open-pose views. All150 producer browser initial views inspected. Fresh integration's150 initial screenshot files match those final inspected views byte-for-byte, with final GLB hashes: `pixel-comparison.json`.
-Pre/post preservation checks: all prior tracked non-catalog files match exact latest-base Git blobs; all prior catalog values and all imported files match source commit objects. Existing catalog text is preserved additively, including GJH rights/download restrictions and latest three-panel-wrap work.

50 assets total 197,312 triangles / 10,845,520 GLB bytes. Independent editable `.blend` sources, Blender Python generators, optimized GLBs, multiangle previews, metadata and evidence included. Saved-copy source proofs change a component and material, save/reopen, export without regeneration, and preserve canonical source hashes. Fixed budgets retained.

## Regional registration coverage
The independently reconciled user list301–500 maps200/200 to unique assets:169 on main762 and31 in this draft;116 have explicit matching metadata IDs and84 have catalog/metadata name evidence. All200 metadata hashes were rechecked against the assembled tree. See `regional-301-500-coverage.json`. This is registration coverage, not release readiness.

## Asset status
| ID | Asset | Triangles | GLB bytes | Local asset | Overall |
|---|---|---:|---:|---|---|
| 023 | Office Chair | 2,876 | 145,044 | PASS | NEEDS REVIEW |
| 024 | Work Desk | 1,244 | 68,756 | PASS | NEEDS REVIEW |
| 025 | Desktop Monitor | 1,004 | 51,836 | PASS | NEEDS REVIEW |
| 026 | Laptop | 5,668 | 309,588 | PASS | NEEDS REVIEW |
| 027 | Meeting Table | 920 | 50,516 | PASS | NEEDS REVIEW |
| 028 | Meeting Chair | 1,776 | 92,788 | PASS | NEEDS REVIEW |
| 031 | Printer | 1,944 | 108,552 | PASS | NEEDS REVIEW |
| 032 | Filing Cabinet | 2,672 | 147,180 | PASS | NEEDS REVIEW |
| 033 | Whiteboard | 2,232 | 114,164 | PASS | NEEDS REVIEW |
| 035 | Coffee Machine | 2,944 | 150,288 | PASS | NEEDS REVIEW |
| 036 | Server Rack | 9,504 | 492,752 | PASS | NEEDS REVIEW |
| 040 | Office Locker | 2,372 | 131,556 | PASS | NEEDS REVIEW |
| 142 | Wooden Pallet | 4,440 | 215,384 | PASS | NEEDS REVIEW |
| 145 | Pallet Jack | 2,796 | 146,724 | PASS | NEEDS REVIEW |
| 148 | Shipping Container | 9,852 | 505,028 | PASS | NEEDS REVIEW |
| 155 | Fire Extinguisher | 3,004 | 146,400 | PASS | NEEDS REVIEW |
| 156 | Tool Cabinet | 1,392 | 85,812 | PASS | NEEDS REVIEW |
| 157 | Storage Crate | 2,484 | 138,044 | PASS | NEEDS REVIEW |
| 190 | Science Lab Bench | 1,888 | 104,036 | PASS | NEEDS REVIEW |
| 470 | Hibiscus Plant | 5,264 | 312,008 | PASS | NEEDS REVIEW |
| 471 | Orchid Planter | 7,912 | 517,964 | PASS | NEEDS REVIEW |
| 472 | Pandan Plant | 1,100 | 76,548 | PASS | NEEDS REVIEW |
| 473 | Durian Tree | 8,240 | 586,852 | PASS | NEEDS REVIEW |
| 474 | Mangrove Tree | 7,412 | 448,772 | PASS | NEEDS REVIEW |
| 475 | Tropical Fern Cluster | 14,796 | 805,968 | PASS | NEEDS REVIEW |
| 476 | Tropical Grass Patch | 2,412 | 171,780 | PASS | NEEDS REVIEW |
| 477 | Roadside Tree Pit | 2,700 | 147,452 | PASS | NEEDS REVIEW |
| 478 | Rainwater Puddle | 940 | 42,876 | PASS | NEEDS REVIEW |
| 479 | Tropical Rock Cluster | 320 | 26,852 | PASS | NEEDS REVIEW |
| 480 | Drainage Canal Bank | 348 | 22,408 | PASS | NEEDS REVIEW |
| 481 | Chinese New Year Lantern Arch | 9,980 | 510,192 | PASS | NEEDS REVIEW |
| 482 | Chinese New Year Mandarin Orange Basket | 6,712 | 346,888 | PASS | NEEDS REVIEW |
| 483 | Chinese New Year Red Packet Display | 3,132 | 170,656 | PASS | NEEDS REVIEW |
| 484 | Hari Raya Ketupat Decoration | 5,736 | 314,208 | PASS | NEEDS REVIEW |
| 485 | Hari Raya Pelita Lamp | 316 | 18,096 | PASS | NEEDS REVIEW |
| 486 | Hari Raya Bazaar Stall | 2,494 | 116,060 | PASS | NEEDS REVIEW |
| 487 | Deepavali Oil Lamp | 460 | 24,764 | PASS | NEEDS REVIEW |
| 488 | Deepavali Kolam Floor Pattern | 10,248 | 515,540 | PASS | NEEDS REVIEW |
| 489 | Deepavali Festive Arch | 7,400 | 392,552 | PASS | NEEDS REVIEW |
| 490 | Mid Autumn Lantern Display | 10,572 | 539,584 | PASS | NEEDS REVIEW |
| 491 | Mooncake Gift Box | 4,608 | 234,600 | PASS | NEEDS REVIEW |
| 492 | National Day Flag Pole | 740 | 41,916 | PASS | NEEDS REVIEW |
| 493 | Singapore Flag Banner | 1,420 | 72,040 | PASS | NEEDS REVIEW |
| 494 | Malaysia Flag Banner | 1,432 | 75,192 | PASS | NEEDS REVIEW |
| 495 | Community Event Tent | 1,302 | 74,144 | PASS | NEEDS REVIEW |
| 496 | Neighbourhood Pasar Malam Light String | 5,496 | 287,580 | PASS | NEEDS REVIEW |
| 497 | Local Wet Market Weighing Scale | 1,824 | 100,556 | PASS | NEEDS REVIEW |
| 498 | Durian Display Basket | 5,276 | 346,436 | PASS | NEEDS REVIEW |
| 499 | Local Newspaper Stand | 5,040 | 260,696 | PASS | NEEDS REVIEW |
| 500 | Traditional Five Stones Game Set | 668 | 39,892 | PASS | NEEDS REVIEW |

Overall NEEDS REVIEW includes the unresolved suite regression, physical Android/iOS, shipping Safari and actual-device performance. Metadata remains draft. No Gallery clip-playback controls, deployment or main merge are claimed.

## Provenance and honest failure history
-Office/industrial16: `eda9cbe4be8bd899d7464d9640939ec955fe4227`, base496b1db. `../office023/README.md` documents seam/contact fixes and pallet support links. Initial contact sheets/logs retained; first five draft binaries were not fully archived, while pallet before-fix sources/exports were retained.
-Nature/facilities17: `b5183e37efd7bcee01cd74d6ab65e96e48276943`, base496b1db. `../fifty03-nature/handoff.json` records exact final hashes. Lantern budget overrun corrected without raising cap; actual attachments, flower lobes, closed-lid, canal and grate defects corrected with snapshots. Durian FruitStalk naming collision corrected while retaining independent fruit/stalk assertions.
-Festivals17: `38381f8a39778200a08aafd2fb2804a05e02dde0`, base496b1db. `../festivals03-local.md` records tessellation API failure, support/dimension fixes, preserved evidence and corrected full-motion QA framing. Flag geometry assertions use original construction geometry; not copied marketplace models.

Earlier producer “combined integration pending” labels remain historical. This report supersedes only that stage: current full integration is FAIL, not pending or PASS. Source whitespace checks exclude verbatim raw logs rather than altering historical output.

## Cross-engine boundary
A separate isolated macOS26.6.2/Playwright1.64.1 WebKit2370 (engine27.2) attempt tested the published previous batch on exact762. Three taxi-sign smoke viewports failed; remaining147+10animation checks were not run. An independent blank-page WebGL2 clear/readPixels diagnostic also immediately lost context (error37442/nullprecision/zero pixels), establishing an environment/runtime blocker, not an asset-geometry verdict. CSP style observations are separate. This is neither shippingSafari nor physicaliOS validation and does not certify these new50 for WebKit. No security settings or active user browser/server were changed.

## Reproduction
Use fresh output directories after `npm test` and `npm run build`:
```sh
TEST_ARTIFACT_DIR=/tmp/fifty03-library node scripts/test-library-browser.mjs
MALL_QA_DIR=/tmp/fifty03-office node scripts/test-office023-browser.mjs
MALL_QA_DIR=/tmp/fifty03-festivals node scripts/test-festivals03-browser.mjs
MALL_QA_DIR=/tmp/fifty03-festivals-animation node scripts/test-festivals03-animation-browser.mjs
MALL_QA_DIR=/tmp/fifty03-nature node scripts/test-fifty03-nature-browser.mjs
```
Keep source/report-writing validation in isolated fixtures to preserve shipped evidence. Existing public redistribution wording remains unchanged/unspecified; no medical, engineering, botanical, lifting, cooking or fire-safety certification.
