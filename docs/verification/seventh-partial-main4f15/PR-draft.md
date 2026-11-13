## Scope: 33 deliverables, not 50 new model types
Adds the reviewed local packet: 19 original rigid-articulated character roles, 8 distinct mall/city assets (including illustrative escalator004), 2 additional designs (passenger lift and round dining table), and 4 derived extraction packages.

32 deliverables have producer-local PASS; escalator004 remains NEEDS REVIEW. Four derived packages have counting policy PENDING: public bicycle rack, Singapore shophouse facade, Malaysia shoplot facade and Chinese lantern. They are self-contained. Lantern parent provenance is from unmerged PR21; it is not a runtime/generation dependency.

## Integration evidence
Tested exact main `4f15c0b31fdceaa50297bf4ad28feae3049fdb22` in a fresh independent workspace.
- 398 existing catalog entries preserved, plus 33 = 431 registrations. This is not a claim that 431 of the planned 500 types are complete.
- 499 unit tests, build, 9 library, 4 lifecycle, 99 Gallery viewport, 45 isolated motion and 14 legacy cases PASS.
- 48 original GJH and 20 Codex comparison golden views PASS; no golden updates.
- All 99 final GLB consumption and pixel comparisons match exact producer evidence.
- Existing main files unchanged except additive catalog registration; original 4,572 imported paths/evidence preserved.
- Fresh representative Gallery and action images inspected. Full historical source/edit/preview evidence retained.

Current evidence: `docs/verification/seventh-partial-main4f15/`. Earlier integration evidence: `docs/verification/seventh-partial/`.

## Review limitations
Keep this PR Draft. Escalator004 has sampled illustrative circulation, not proven continuous wheel contact or constant-pitch chain engineering. Its wheel/rail result is CENTER_PLANE_NONINTERSECTION_ONLY; contact remains NEEDS REVIEW. Static source and failed candidates are archived.
Characters use rigid articulation, not skinning/IK or autonomous NPC systems. Walking is in-place stepping.
Physical Android/iOS and shipping Safari remain untested.
Earlier care-six/PR21 library reload failures remain preserved; this fixed run did not reproduce them and is not a root-cause fix.
Imported source/log whitespace warnings are reviewed and retained, not a clean diff-check claim.
No merge or deployment is included.
