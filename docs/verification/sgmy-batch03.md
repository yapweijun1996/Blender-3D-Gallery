# SG/MY asset batch 03 verification

**10 new logical types / 10 GLBs. Every asset local PASS; overall NEEDS REVIEW because physical Android/iOS are NOT TESTED.** Desktop viewport emulation is not native mobile acceptance.

Fresh main base `762ca8e87a2037b5d0f60e903fbaa0cbaae2b8b2` includes externally merged PR13. All 90 old assets and existing collection prefix preserved; final catalog100. No application, workflow or existing test code edits. Only pre-existing tracked file changed is additive `models/catalog.json`. No main merge, deployment or remote action performed by this preparation.

Selected V2.1 priority scope: 440 Mall Retail Pop-Up Cart, then P1 IDs301–309. Prior completed assets and reused parts are not recounted. All models include independent Blender Python/source, GLB, multiple previews, metadata, rights and preserved validation history. No official HDB endorsement, surveyed-estate accuracy or construction/safety certification claimed. Owner-project reuse permitted; public redistribution unspecified, downloads remain disabled.

## Per-asset results

| Asset | Bytes | Triangles | Local | Overall |
|---|---:|---:|---|---|
| [Mall Retail Pop-Up Cart](../../models/mall-retail-pop-up-cart/verification.md) | 470,632 | 6,860 | PASS | NEEDS REVIEW |
| [HDB Corridor Gate](../../models/hdb-corridor-gate/verification.md) | 142,756 | 2,616 | PASS | NEEDS REVIEW |
| [HDB Utility Riser](../../models/hdb-utility-riser/verification.md) | 155,616 | 2,808 | PASS | NEEDS REVIEW |
| [HDB Clothes Drying Rack](../../models/hdb-clothes-drying-rack/verification.md) | 270,720 | 5,480 | PASS | NEEDS REVIEW |
| [HDB Aircon Compressor Ledge](../../models/hdb-aircon-compressor-ledge/verification.md) | 109,060 | 1,996 | PASS | NEEDS REVIEW |
| [HDB Bicycle Parking Shelter](../../models/hdb-bicycle-parking-shelter/verification.md) | 359,652 | 6,792 | PASS | NEEDS REVIEW |
| [HDB Staircase](../../models/hdb-staircase/verification.md) | 210,560 | 3,780 | PASS | NEEDS REVIEW |
| [HDB Lift Door](../../models/hdb-lift-door/verification.md) | 43,644 | 708 | PASS | NEEDS REVIEW |
| [HDB Lift Interior](../../models/hdb-lift-interior/verification.md) | 83,812 | 1,500 | PASS | NEEDS REVIEW |
| [HDB Corridor Window](../../models/hdb-corridor-window/verification.md) | 130,352 | 2,304 | PASS | NEEDS REVIEW |

Total new GLBs: **1,976,804 bytes**. Individual complexity budgets and exact SHA values are in asset reports and [summary](sgmy-batch03-final/summary.json).

## Fresh combined quality gate

- **230/230 unit tests**, production build and all catalog Khronos GLB validation PASS: [unit log](sgmy-batch03-final/unit.log), [build log](sgmy-batch03-final/build.log).
- **10/10 source/structural checks** rerun in disposable copies, so original historical reports remain unchanged. Reopened sources and real mesh/material edits re-exported; [results](sgmy-batch03-final/sources/results.json). Separately **10/10 independent source reopens**: [independent evidence](sgmy-batch03-final/independent/independent-review.json).
- **30/30 strict browser cases**, 1440/768/390px, desktop Chromium156.0.8078.4: exact consumed GLB byte/SHA, HTTP200, draw calls, orbit/zoom, exact reset, close/reopen and3 same-page cycles, restored focus, released render loops, no unexpected request/console/page errors filtered. [Results](sgmy-batch03-final/browser/results.json).
- **4/4 loader lifecycle**, including interruption/error recovery: [results](sgmy-batch03-final/lifecycle/results.json).
- **9/9 library suite in one fixed final run**: [results](sgmy-batch03-final/library/results.json). This does not erase the prior intermittent legacy-demo reload timeout. Untouched959fbc7 baseline reproduced7PASS then line211 reload timeout and final reflow case not run; [retained baseline](sgmy-batch03-final/baseline-library/library.log). Batch2 candidate had the same failure. No retry-to-green or test weakening was performed here, and the intermittent cause remains unresolved. Raw library JSON hardcodes macOS; actual runner is Ubuntu ARM64/SwiftShader.
- All10 studio preview sets and30 final initial browser screenshots independently inspected, plus coordinator review. Recognizable geometry, scale, visible materials and unclipped initial framing; lift interior lighting is subdued but visible. No unsupported runtime-interaction claim.

Source-level movable components are editable, not new runtime controls. Physical Android/iOS browsers, native install and production performance are NOT TESTED. Earlier producer reports describe their preparation stage; this combined report supersedes their pending aggregate status, not their historic failures. Initial cart headless-launch/bounds diagnostic, 307 freestanding draft/contact correction, and cabin noise/OIDN-unavailable evidence remain preserved.
