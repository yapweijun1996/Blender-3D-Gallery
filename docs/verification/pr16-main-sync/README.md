# PR16 main synchronization verification

2026-11-13 UTC. Merged main c614411fd9073d34bee6f3a6fde5f5769f606841 into feature branch feat/sgmy-asset-batch-05 (previous head edcff51dab8e91785269be3d0772c5cfd6ace99b). This does not merge PR16 into main or deploy it.

The only conflict was models/catalog.json. Resolution retains both complete parent catalogs, with 120 unique assets and unchanged shared entries. Every non-catalog tracked file from both parents is byte-identical to its parent version. Sources, exports, historic reports, application code, workflows and tests were not edited. See preservation.json.

## Fixed-run results

All commands and exit codes are in status.tsv; raw logs and browser results accompany this report.
- Unit tests: PASS, 240/240, zero failures or skips.
- Build and catalog/GLB validation: PASS.
- Ten batch05 assets: PASS, 30/30 strict Chromium viewport cases.
- Loader lifecycle: PASS, 4/4.
- Library integration: PASS, 9/9 in this single run.
- Legacy preview cases: PASS, 14/14. All 70 standard state PNGs byte-identical to the prior batch05 candidate evidence.

No failed test was filtered, changed or retried to green. This passing library run does not explain or erase PR15's historic Back-readiness failure. This catalog-only integration does not claim a new visual quality review; previous rendered preview inspection remains documented in the unchanged batch05 report.

Physical Android/iOS and Safari/WebKit remain NOT TESTED. Overall per-asset status remains NEEDS REVIEW for those platform limits. No production deployment or main merge is authorized by this report.
