# Modular chibi: lessons learned (2026-11-18 to 2026-11-19)

Written after a long session building the Tripo/Blender/Codex modular chibi pipeline and a dress-up demo. Each lesson has the evidence that taught it.

## Verification
1. **A T-pose pass proves nothing about motion.** Three garments (T-shirt, hoodie, two Tripo variants) passed the T-pose check and then put 30 to 210 vertices inside the body under walk, run, wave and jump. Always run the vertex checker and the triangle-overlap checker over every frame of every clip.
2. **A vertex test is not enough.** The T-shirt v2 had 0 vertices inside the body and still 34 to 190 intersecting triangle pairs. Add a BVH triangle-overlap count.
3. **Independent image review finds what the author's numbers miss**: gaps behind the ears, a mirrored-lock seam, skin visible through a lifted sole, pinch fingertips that do not touch. Use a different model that sees only renders; send FAIL items back (maximum 3 rounds), accept PASS WITH NOTES.
4. **Look at the render.** A first test showed T-pose frames for every clip because the clip was applied wrongly (rotation_mode changed to Euler while the clips use quaternions; Blender 5 also needs `action_slot`). The numbers looked fine; the picture did not.
5. **Load every new asset in a real browser before committing.** Gesture library round 2 used local bone scale tracks that the demo's gesture layer did not support; the page showed "could not start" while build and unit tests passed. Bisect assets: restore the old file, reload, compare.

## Working with Codex
6. Give the worker the checker as a script and the exact failing numbers; "make it better" does not converge. Name the method (systematic worst-case offset baking over all frames, half-frame sampling, margin 2 mm) instead of hand tuning.
7. Workers report their own numbers; re-measure yourself. The sneaker, T-shirt and hoodie reports were each more optimistic than the independent measurement.
8. A garment that cannot fit after three rounds needs a different design, not a fourth round: use runtime hiding of covered body regions plus a masked checker and an exposed-pixel gate.
9. macOS shell: BSD `sed -i` needs a suffix argument; use Python for edits. Foreground `sleep` is blocked; use background `until` loops. Variable-length lists in zsh need arrays.

## Tripo
10. Studio and CLI are separate credit pools; the CLI key and Studio login are the same account. Details in `docs/tripo-settings-and-experience.md` and the KB skill `tripo:studio-web-computer-use`.
11. Retopology and segmentation do not repair hands; hands are repaired in Blender. Segment plus Fill Parts left open boundaries.
12. In a new Studio tab the retopology polygon field can stay at 10,000: zoom and check it before pressing the button (cost one extra 40-credit run).

## Multi-session and repositories
13. **Never run workers or edits in a shared checkout.** Another session ran `git checkout -- .` and discarded my tracked edits in the v11 repository while my job was still writing there. Use a `git worktree` for every job, back up untracked files, and tell the peer which paths are yours.
14. **Read the host project's existing systems before specifying a feature.** I asked for about 15 NPCs; v11 already has an NPC admission budget (200-call cap, mobile ceiling 1 to 3) and a hard "no lag on iPhone" rule. The feature has to plug into that budget, not add a second crowd.
15. The remote moves under you: `git fetch`, rebase onto origin/main, re-run tests, then push; another session had pushed 369 files meanwhile.
16. Ask the owner the few questions that change scope (style, counts, authority to push and spend) early and write the answers into memory and docs; they paid back repeatedly during unattended work.

## Process
17. Keep a master task list in the repo and in memory; report every 20 minutes; push each verified piece instead of one big push.
18. Record decisions with the reason; the reason is what lets a later session apply them to a new case.
