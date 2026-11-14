# Product Studio progress

## Slice 01 — shipped

PASS: first actual CI43564607799 deployment and GitHub Pages verification completed for the original fictional food tin. The historical first-slice evidence remains authoritative; its 432 existing parsed registrations are preserved.

Base: 5fd5401c910a7784c2691e8e0693046f4c007e52.

PASS: one original fictional DEMO tin, source .blend, 186,016-byte GLB, original artwork/font license, independently editable parts, authored open/exploded clips, preview inspection and source-edit evidence.
PASS: 504 unit tests; Product Studio 15 browser scenarios; Game 12-viewport responsive journey; five touch negative/lifecycle checks; full existing Game/PWA/Solar/library/reviewed/GJH regression. See evidence/canvas-fix-final/status.txt.
PASS: preserves 431 previous catalog entries and existing assets. Adds one model and one demo route. No brand-specific packaging or third-party label rights claimed.

Game touch fix: canvas-only nonpassive touchstart cancellation prevents a native fling from consuming the next button tap. Original rapid UX test is unchanged. Before trace recorded 6 FilterTapSuppression events, fixed trace 0; inspection pinch/orbit, noncanvas scrolling, keyboard, cancel and disposal negative checks pass. Previous failures remain in evidence.

CI/PAGES: first-release CI run `6da74ca7` / `43564607799` is recorded PASS. The second packaging-can run remains pending host regeneration and verification. Workflow places the unit and browser gates before Pages artifact upload/deployment; failed CI leaves the previous Pages release live.

Rollback: preserve base SHA above. If live verification fails, revert this release commit and run the same deployment gates; do not force-push history. Existing model and demo routes remain available.

NOT TESTED: physical Android/iOS and shipping Safari, screen reader hardware. This is a first slice only, not completion of the full packaging platform or 500-model backlog. No label editor, product backend, uploads or manufacturing simulation.

## Slice 02 — original beverage can and model switch

PASS: original Blender beverage can, 11,772 triangles, 231,400-byte GLB, independent editable source, UV label, five rendered angles, authored tab/score flap and exploded clips. Khronos validation zero errors/warnings. Prior 432 catalog entries unchanged; one new registration.

PASS: 510 unit tests, build, and 22 Product Studio browser scenarios. Original 15 scenarios retained with retry assertions adapted to a persistent shared renderer; seven added cases cover latest selection, late failure, real GLTF stale parsing disposal, 20 model switches with warmed GPU resource counts, five route exits, retry, touch, keyboard and dynamic reduced motion. Actual mobile-emulation canvas images inspected.

Local extra full regression was stopped at the owner's request to avoid duplicating CI. Its completed unit/build checks passed; interrupted Game run is not claimed as PASS. Existing CI remains unchanged and gates Pages publication. CI/deployment for this slice pending.

Rollback: revert this slice commit and allow unchanged CI to republish the previously verified release. No forced history or permission changes. Physical Android/iOS and shipping Safari remain NOT TESTED.
