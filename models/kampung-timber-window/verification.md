# Kampung Timber Window verification

Overall: NEEDS REVIEW. Local gate: PASS. Physical Android/iOS and Safari/WebKit untested. No deployment.

- Editable Blender source, canonical SHA and copied-component +0.123m re-export: reports/source.json.
- Khronos0 errors/0 warnings; geometry,metre dimensions,origin,hierarchy,budgets: reports/assets.json.
- Actual exported-GLB rendered hero/front/rear pixels inspected with final hashes: reports/visual-review.json.
- Actual consumed GLB SHA,orbit,zoom,exactreset,close/reopen,no request/console/page errors at1440/768/390 desktop Chromium: reports/browser/results.json. Viewport emulation is not a physical device test.
- Explicit expected open/closed poses,fixed components,reset: reports/animation.json. Browser AnimationMixer pixel change/exactreset and inspected open pose: reports/animation-browser.json. Gallery has no component-control UI.

Initial static metrics/logs retained; final proofs bind current source/GLB hashes. See ../../docs/verification/batch325341-local.md for corrections and commands.
