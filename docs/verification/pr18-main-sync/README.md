# PR18 main synchronization verification

2026-11-13 UTC. Merged main 5ca54d373e564cd0e10cdf3d07e3d7767fa20a88 into feature branch feat/sgmy-asset-batch-07 (previous head 825dd5ea30c04d70aadc739d886f3d01ffcadd56). This does not merge PR18 into main or deploy it.

The only conflict was models/catalog.json. Resolution retains both complete parent catalogs with 140 unique assets and unchanged shared entries. Every non-catalog tracked file from both parents is byte-identical to its parent version. Sources, exports, historic reports, application code, workflows and tests were not edited. See preservation.json.

## Fixed-run results

Commands and exit codes are in status.tsv; raw logs and browser results accompany this report.
- Unit tests: PASS, 250/250, zero failures or skips.
- Build and catalog/GLB validation: PASS.
- Ten batch07 assets: PASS, 30/30 strict Chromium viewport cases.
- Loader lifecycle: PASS, 4/4.
- Library integration: PASS, 9/9 in this single run.
- Legacy preview cases: PASS, 14/14. All 70 standard state PNGs byte-identical to the prior batch07 candidate evidence.

No failed test was filtered, changed or retried to green. This passing library run does not explain or erase historic failures in other branches. This catalog-only integration does not claim a new visual quality review; previous rendered preview inspection remains documented in the unchanged batch07 report.

Physical Android/iOS and Safari/WebKit remain NOT TESTED. Overall per-asset status remains NEEDS REVIEW for those platform limits. No production deployment or main merge is authorized by this report.
