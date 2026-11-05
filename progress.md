Original prompt: based on the .md, please finish the game task, and commit and merge push to main github

# Delivery progress

- Baseline: 6f983e2, existing individual GLB gallery. Original Documents checkout is unreadable by shell; working in an isolated clone of the same remote and preserving the original uncommitted plan.
- Contract: Casual Eight-Ball v1, local two-player, real GLB assets, mobile controls, stable checkpoints, guarded PWA/offline updates, gallery regression, authorized main push/deploy.
- Current: implementing and validating core rules/physics before the 3D interface.

- Implemented the lazy Game route, Casual Eight-Ball rules, fixed-step disk solver, individual-GLB rendering, compact touch controls and stable checkpoints.
- Updated actual Blender table cushion openings/jaws and regenerated source, table/full GLBs and previews. Source audit: 21 roots, 141 meshes, valid mesh data, UVs and materials. All 22 GLBs pass Khronos with zero warnings/errors.
- Five-persona review found event-order, corrupted-save, storage ownership, save-failure, WebGL recovery, mobile layout and offline-pack issues. Fixed and reran affected browser journeys.
- Unit/geometry tests: 23 pass. Game browser suite: 12 Chromium scenarios plus WebKit shot smoke pass. PWA lifecycle suite: 9 pass, including failure injection and explicit N-to-N+1 recovery.
- Release procedure: final checks/diff, focused feature commit, fast-forward merge/push main, verify Actions and live Game; remote results are reported in the final delivery. The remaining hardware follow-up is physical iOS/Android installation and sustained performance.

- User challenged the release quality. Live first-entry review reproduced an empty table, mobile start action below the fold and desktop clipping. Added a real rack preview, compact desktop framing and mobile start controls before the table; testing entry separately from active play.

- Follow-up requested: improve the mobile PWA pool-game experience, usability and verified ball-physics issues under Auto Manager. Baseline `f2daf41`: production build and 35 unit tests passed; scope preserves existing rules, save compatibility, model assets and offline/update behavior. An early two-contact fixture exposes incorrect first-contact order; a 320×568 baseline shows an undersized playable table. Physical-device validation remains outstanding.
- Follow-up implemented: short-screen table and 44px aim controls, inspection and pause usability fixes, and ordered swept ball/pocket contacts with bounded approximations for subsequent dense contacts. On the integrated production build: 52 unit tests; 45 Game, 16 PWA, 9 PWA-standard, 9 library, 8 reviewed-bug, 7 usability and 10 responsive browser checks passed. A simulated 320×568 touch browser also cold-started the prepared Game pack offline and completed a shot. The 250 seeded break sample settled without invalid states or deep final overlaps. Physical phone installation, actual safe areas and sustained mobile performance remain unverified.

- Rolling follow-up: reproduced a cushion-contact path and rotation error against a 200-times-finer timestep. Resolve unobstructed cushion impacts at contact time and rotate along both path segments; keep bounded fallback handling for dense and repeated contacts. Added free-roll, straight/glancing rebound, both rail directions and rounded-jaw regression cases. A 250-seed break sample settled without invalid states or final overlap. Actual physical-device play and full spin physics remain unverified.
