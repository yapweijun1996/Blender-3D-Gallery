# Product Studio first release candidate

Base: 5fd5401c910a7784c2691e8e0693046f4c007e52.

PASS: one original fictional DEMO tin, source .blend, 186,016-byte GLB, original artwork/font license, independently editable parts, authored open/exploded clips, preview inspection and source-edit evidence.
PASS: 504 unit tests; Product Studio 15 browser scenarios; Game 12-viewport responsive journey; five touch negative/lifecycle checks; full existing Game/PWA/Solar/library/reviewed/GJH regression. See evidence/canvas-fix-final/status.txt.
PASS: preserves 431 previous catalog entries and existing assets. Adds one model and one demo route. No brand-specific packaging or third-party label rights claimed.

Game touch fix: canvas-only nonpassive touchstart cancellation prevents a native fling from consuming the next button tap. Original rapid UX test is unchanged. Before trace recorded 6 FilterTapSuppression events, fixed trace 0; inspection pinch/orbit, noncanvas scrolling, keyboard, cancel and disposal negative checks pass. Previous failures remain in evidence.

CI/PAGES: pending actual remote run. Workflow now places the unit and browser gates before Pages artifact upload/deployment. Local PASS is not remote CI PASS. Failed CI leaves the previous Pages release live. Allow up to 90 minutes for CI; local full regression took about 25 minutes.

Rollback: preserve base SHA above. If live verification fails, revert this release commit and run the same deployment gates; do not force-push history. Existing model and demo routes remain available.

NOT TESTED: physical Android/iOS and shipping Safari, screen reader hardware. This is a first slice only, not completion of the full packaging platform or 500-model backlog. No label editor, product backend, uploads or manufacturing simulation.
