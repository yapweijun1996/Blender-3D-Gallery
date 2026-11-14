# Seventh partial local assembly: 33 candidates

## Result

One fixed local integration pass **PASS**, based on `3c41bcfd660c69a41fe3bb7f5f56baed6f4b4e0b`. The catalog contains 344 preserved prior entries plus 33 candidates (377 total). This is **not a completed batch of 50**, a release, or a main-branch delivery.

- 457 unit tests PASS in an independent copied fixture; producer reports remained immutable.
- Build PASS; 9 library, 4 lifecycle and 14 legacy preview cases PASS.
- 99 Gallery viewport cases and 45 isolated motion cases PASS.
- All 99 final GLB consumption hashes and producer pixel hashes match exactly.
- Old tracked files remain unchanged except additive catalog registration. Intentional 004 replacement is separately archive/hash bound.
- All 33 final initial views and 25 representative motion frames were visually inspected via the five review sheets in `integration/`.

Earlier care-six and PR21 library reload failures are preserved. This pass did not reproduce them; **no root-cause fix is claimed**.

## Status and limitations

32 candidates have producer-local PASS. Escalator 004 remains **NEEDS REVIEW**, despite its illustrative sampled motion passing. Its exact final GLB is `f8f8bda8b28a4faaf1fb2b03ee2a832fe23b90621eee9ab0a24a26c1b2b89ada`.

The canonical static 004 was intentionally replaced by commit `07417f6c9595385370dca94845c11e8decd92429` to add circulation and flush landings. Static bytes, failed candidates and replaced batch evidence remain archived. The proof status is **PASS_CENTER_PLANE_NONINTERSECTION_ONLY**, not physical contact PASS. Continuous wheel contact and constant-pitch chain fidelity remain unproven. No engineering/safety certification is claimed.

Four packages are **DERIVED EXTRACTIONS, counting policy PENDING**: public-bicycle-rack, singapore-shophouse-facade, malaysia-shoplot-facade and chinese-lantern. They are self-contained and require no external parent files to generate or view. The lantern parent originates from unmerged PR21: this is provenance publication status, not a runtime dependency or a requirement to merge PR21 before local QA.

Characters have rigid articulation, not skinning, IK or autonomous NPC behavior. Walking is in-place stepping, not forward locomotion. Physical Android/iOS and shipping Safari remain untested. Overall release status is **NEEDS REVIEW**. No remote push, PR, merge or deployment occurred.

## Evidence and reproduction

- `summary.json`, `asset-ledger.json`: counts, exact provenance, statuses and limitations.
- `imports/*.json`, `intentional-replacements.json`: source-file hashes and precise replacement/archive mapping.
- `external-pr-dedup.json`: logical-ID and slug comparison against PR21/PR24.
- `integration/status.json`: sequential fixed-pass commands and exit codes.
- `integration/gallery-comparison.json`: final SHA/pixel comparison.
- `integration/review-*.jpg`: inspected fresh gallery/action contact sheets.
- `verify-preservation.py`: prior files, catalog prefix, imported and archived-byte verification.
- `run-combined.py`, `suites.json`, `unit-fixture.py`: reproducible isolated-output orchestration, refusing to overwrite this completed pass.

The old distinct-packet motion script is preserved. A new scoped harness runs its original two interaction assertions unchanged, while the newly animated escalator uses its dedicated final three-viewport motion harness. No test assertions or timeouts were weakened.

## Whitespace review

The source diff check has 24 reviewed nonfunctional warnings retained, not an unqualified clean result: seven imported script trailing blank lines at EOF and 17 raw-log whitespace warnings. Exact paths/lines and canonical/candidate/archive classifications are in `whitespace-review.json`. No code or assertions were changed to remove them.
