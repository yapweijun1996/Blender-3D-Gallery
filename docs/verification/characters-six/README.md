# Six occupation characters

## Results
Six distinct roles, local PASS and release NEEDS REVIEW. This is local accumulation toward a future 50-model PR, not a six-model release. Cleaner266 remains separately committed and untouched.

Evidence includes 18 gallery viewport cases, 12 isolated motion cases, source/GLB proofs and 41 motion samples per clip. Exact final hashes and fixed budget results are in summary.json. All 416 repository unit tests, build and 4 gallery lifecycle cases pass; logs are under final/. Full library regression was not run in this tranche.

## Corrections preserved
- Cashier's initial scanner motion missed the declared 7 cm travel minimum. Increased actual shoulder sweep to 0.24 radians; did not lower minimum travel or budgets. Initial artifact/logs retained.
- Chef's initial pot looked like a ribbed ring. Replaced it with a real hollow wall; retained the original artifact.
- Teacher's initial pointer was behind the board despite a structurally passing but incorrectly directed plane check. Moved the board behind the pointer and corrected the explicit front-plane predicate. Initial geometry and validation source retained.
Final source edits and validations were rerun for the changed artifacts. No failed history was replaced.

## Review and limitations
Final studio multiangle/action frames and browser frames were actually inspected. Motion is rigid articulation, not skin, IK, walking or autonomous behavior. Desktop Chromium is not physical Android/iOS or Safari. No new application UI, deployment, public push or PR is included. No additional character roles are authorized by this local handoff.
