# Six further character roles with shopper gait pilot

## Results
Six local PASS assets: Male Office Worker261, Female Office Worker262, Mall Shopper263, Bus Driver268, Hawker270 and Student272. They accumulate toward a future 50-model batch, not a six-model PR.
416 unit tests, build, 18 exact-hash gallery cases, 12 isolated clip cases and 4 lifecycle cases pass. Seven studio and 12 browser frames per role were inspected (114 final frames). Exact hashes/budgets are in summary.json.

## Walk method
Shopper263 alone has a verified articulated in-place step gait. Its actual foot vertices are tested at 61 times, with explicit planted stance intervals and 0.12 m swing clearance, no root drift, bag grip, joint ranges, loop/reset and clip switching. It does not implement forward locomotion, navigation, a skin or runtime IK. Other five roles have stationary occupation actions and no walk claim.

## Preserved diagnostic
Hawker's initial travel assertion used the custom bowl mesh object's origin, not its transformed geometry centre. The initial failure and original validator are retained in initial/hawker. Corrected structural and browser tests measure the actual bowl bounding-box centre with the original 12 cm travel threshold. No geometry, budgets or threshold were changed to hide the failure. Corrected proof is in hawker-mesh-center and final/motion/hawker.

## Limits
Wholly fictional, rigid articulated characters; no autonomous NPC behavior or new app animation controls. Desktop Chromium is not physical Android/iOS or Safari verification. Release remains NEEDS REVIEW. No remote push, PR or deployment is included. Full library regression was not run; these results do not resolve any earlier separate regression failure.
