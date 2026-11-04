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
