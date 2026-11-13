# SG/MY asset batch 04 verification

**10 new logical types / 10 GLBs. Each asset local PASS; overall NEEDS REVIEW. Library regression gate FAIL; physical Android/iOS NOT TESTED. This is not deployment approval.**

Fresh base `2d8f7731fc7f9a01b77172780f3e31aa54228ad3` includes externally merged PR14. All 100 existing catalog assets and collection prefix remain identical; final catalog110. Only pre-existing tracked file changed: additive `models/catalog.json`. No application, workflow or existing test modifications. No merge, remote push, PR or deployment by this preparation.

Scope: exact selected V2.1 P1 IDs310–319, no variants/context pieces recounted. Independent Blender Python/.blend/GLB, multi-angle previews, metadata/rights and source validation retained. Generic HDB-inspired visual modules, not official models, surveyed estates or construction/safety certification. Owner-project reuse authorized; public redistribution unspecified, downloads disabled.

## Per-asset results

| Asset | GLB bytes | Triangles | Local | Overall |
|---|---:|---:|---|---|
| [HDB Playground Floor](../../models/hdb-playground-floor/verification.md) | 238,852 | 4,272 | PASS | NEEDS REVIEW |
| [HDB Fitness Corner](../../models/hdb-fitness-corner/verification.md) | 235,900 | 4,828 | PASS | NEEDS REVIEW |
| [HDB Community Notice Board](../../models/hdb-community-notice-board/verification.md) | 164,096 | 2,776 | PASS | NEEDS REVIEW |
| [HDB Block Number Sign](../../models/hdb-block-number-sign/verification.md) | 161,548 | 3,140 | PASS | NEEDS REVIEW |
| [HDB Rubbish Chute Hopper](../../models/hdb-rubbish-chute-hopper/verification.md) | 98,416 | 1,832 | PASS | NEEDS REVIEW |
| [HDB Bin Centre](../../models/hdb-bin-centre/verification.md) | 283,812 | 5,208 | PASS | NEEDS REVIEW |
| [HDB Multi-Purpose Hall](../../models/hdb-multi-purpose-hall/verification.md) | 109,848 | 1,944 | PASS | NEEDS REVIEW |
| [HDB Neighbourhood Shopfront](../../models/hdb-neighbourhood-shopfront/verification.md) | 107,760 | 1,872 | PASS | NEEDS REVIEW |
| [HDB Coffee Shop Frontage](../../models/hdb-coffee-shop-frontage/verification.md) | 104,440 | 1,872 | PASS | NEEDS REVIEW |
| [HDB Covered Linkway Column](../../models/hdb-covered-linkway-column/verification.md) | 31,396 | 540 | PASS | NEEDS REVIEW |

Total **1,536,068 bytes**. Exact SHA and per-type metrics in [summary](sgmy-batch04-final/summary.json).

## Combined gate, fixed run

- **235/235 unit tests**, production build and all catalog GLB validation PASS: [unit](sgmy-batch04-final/unit.log), [build](sgmy-batch04-final/build.log).
- **10/10 source/structural checks** rerun on isolated copies to preserve producer evidence; saved mesh/material source edits and re-export verified. [Results](sgmy-batch04-final/sources/results.json).
- **30/30 strict desktop Chromium156 browser cases** at1440/768/390px PASS: exact consumed GLB bytes/SHA, HTTP200, real rendering, orbit/zoom, exact reset/reopen,3 repeated same-page lifecycle cycles, restored focus, stopped render loops, no unexpected request/console/page errors filtered. [Results](sgmy-batch04-final/browser/results.json).
- **4/4 loader lifecycle** PASS: [results](sgmy-batch04-final/lifecycle/results.json).
- **Library FAIL**:7 cases PASS, then legacy demo readiness after browser Back timed out60s at `scripts/test-library-browser.mjs:223` (inside `demoReady` line44). Last reflow case NOT RUN. [Raw log](sgmy-batch04-final/library.log), [partial results](sgmy-batch04-final/library/results.json). No retry-to-green, test edits, filtering or suppression. Earlier main959fbc7 and batch2 showed a reload timeout at line211, while batch3's single final run passed9/9. This failure occurs at a different phase: do not call it a proven identical baseline failure or a proven new-model regression. One fixed unchanged full library run against pristine current main2d8f773 subsequently passed9/9. Candidate line223 failure was NOT reproduced on that baseline. Therefore this is not an established pre-existing failure; cause remains unestablished and candidate library gate remains FAIL. Baseline evidence is preserved under the independent review directory. Raw library JSON mislabels macOS; actual runner is Ubuntu ARM64/SwiftShader.

## Visual quality and presentation

All10 studio sets and30 final initial browser screenshots inspected. Geometry is recognizable and framed without clipping; simple static modules, not runtime gameplay. Some315–319 studio renders retain visible grain, not photorealistic/pristine presentation. Only314 uses the already-approved optional per-model lighting settings; no schema or global-default change. Independent baseline14/14 and candidate14/14 preview tests PASS; all70 initial/orbit/zoom/reset/reopen PNG hashes exactly match, including the ceiling. All10 independent source reopens PASS. See [independent review evidence](sgmy-batch04-final/independent/).

Physical Android/iOS browsers, native install and production performance remain NOT TESTED. Earlier producer reports retain their preparation chronology; this report supersedes pending aggregate status without erasing their evidence. Source-only editable moving parts do not imply runtime controls. Initial/alternate314 lighting and315–319 studio-light/camera corrections are retained.
