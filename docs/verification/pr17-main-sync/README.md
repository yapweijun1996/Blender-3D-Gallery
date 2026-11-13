# PR17 main synchronization verification

2026-11-13 UTC. Merged main 85ceaa99165762f1f1d5a0e6dcb5bc2ee5a5be1a into feature branch feat/sgmy-asset-batch-06 (previous head 45b5a44455c3e5aa4cedee06dec43e753977eaa1). This does not merge PR17 into main or deploy it.

The only conflict was models/catalog.json. Resolution retains both complete parent catalogs with 130 unique assets and unchanged shared entries. Every non-catalog tracked file from both parents is byte-identical to its parent version. Sources, exports, historic reports, application code, workflows and tests were not edited. See preservation.json.

## Fixed-run results

Commands and exit codes are in status.tsv; raw logs and browser results accompany this report.
- Unit tests: PASS, 245/245, zero failures or skips.
- Build and catalog/GLB validation: PASS.
- Ten batch06 assets: PASS, 30/30 strict Chromium viewport cases.
- Loader lifecycle: PASS, 4/4.
- Library integration: PASS, 9/9 in this single run.
- Legacy preview cases: PASS, 14/14. All 70 standard state PNGs byte-identical to the prior batch06 candidate evidence.

No failed test was filtered, changed or retried to green. This passing library run does not explain or erase historic Back-readiness failures in other branches. This catalog-only integration does not claim a new visual quality review; previous rendered preview inspection remains documented in the unchanged batch06 report.

Physical Android/iOS and Safari/WebKit remain NOT TESTED. Overall per-asset status remains NEEDS REVIEW for those platform limits. No production deployment or main merge is authorized by this report.
