# PWA Standard verification

## Baseline

Revision `5c8474835656d4c5fdf704185db21f3784f06c75`, Node24.21.0, pinned Vite8.3.5/Three.js0.187.0/Playwright1.64.1. Clean dependency installation succeeded without lockfile changes. Fresh isolated `npm test` passed35 tests; `npm run build` passed asset validation and production build. Build identity `bf8ee8e9155e74aa`.

Fresh baseline screenshots at320x720,390x844,430x932,768x1024,1024x768,1440x900,1920x1080 observed39 cards, zero initial GLB requests/canvas, no document overflow/page errors. Evidence: `/tmp/b3g-pwa-baseline/`, `/tmp/b3g-pwa-baseline-unit.log`, `/tmp/b3g-pwa-baseline-build.log`. Manager inspected390px screenshot. Prior same-revision release evidence includes45 Game/gallery,9 PWA,9 library,17 Solar assets and4 scene viewport cases; that evidence does not establish new amendment acceptance.

## Amendment acceptance

Final candidate build: `220dd38e13c71fd9`. Environment: macOS27.0.1 arm64, Node24.21.0, Playwright1.64.1, Chromium156.0.8078.4 and WebKit27.2. Browser suites serve the real production subpath on localhost without network throttling; contexts are fresh unless a scenario explicitly prepares versioned caches. Chromium uses software SwiftShader. These are functional observations, not production timing or mobile hardware benchmarks.

| Check | Result | Execution evidence |
| --- | --- | --- |
| Unit tests | PASS,35 | `/tmp/b3g-pwa-accepted-unit.log` |
| Production build and catalog validation | PASS | `/tmp/b3g-pwa-final-build.log`; unchanged Three.js639kB advisory remains |
| Game/gallery regression | PASS,45, including WebKit shot smoke | `/tmp/b3g-pwa-accepted-game.log` |
| Model/demo library | PASS,9 | `/tmp/b3g-pwa-accepted-library.log` and `/tmp/b3g-pwa-accepted-library/` |
| PWA lifecycle/races/migration | PASS,17 on pre-UI-fix build385043054bbd21b1 | `/tmp/b3g-pwa-runtime-test.log`, `/tmp/blender-gallery-pwa-qa/`; runtime/SW sources unchanged in final build |
| PWA Standard UI | PASS,9 on final build | `/tmp/b3g-pwa-standard-final.log`, `/tmp/blender-gallery-pwa-standard/` |
| Axe-core4.14.0 | PASS,zero automated violations across6 states | `/tmp/b3g-pwa-axe-final.log`, `/tmp/b3g-pwa-axe-results.json`; incomplete human-review items remain |
| Solar assets | PASS,17 | `/tmp/b3g-pwa-final-solar-assets.log`, `/tmp/b3g-pwa-final-solar-reports/`; task-generated reports restored, assets unchanged |
| Solar scene | PASS,4 viewport cases | `/tmp/b3g-pwa-accepted-solar-scene.log` |
| Extreme Game safe areas | PASS,6 phase/viewport cases | `/tmp/b3g-pwa-accepted-insets.log`;320×568,390×844,844×390, placing and aiming |
| Source whitespace integrity | PASS | `git diff --check` |

The 17-case PWA command enables one historical-runtime migration fixture with `PWA_LEGACY_DIST=/tmp/b3g-pwa-baseline-dist npm run test:pwa`. A fresh clone without that optional historical build executes16 current-runtime cases. Candidate fixture changes remain confined to test servers/IndexedDB/worker responses. Normal application readiness comes from real UI preparation, not injected state.

The final standard suite checks all seven exact viewports with simulated top24/right18/bottom28/left14 insets,14 index screenshots,16px mobile entry, zero index GLBs/canvases, no overflow, scrolled menu/viewer close paths, actual fullscreen, focus return, reduced motion, contextual top action, manifest/PNG identity, actual Earth GLB textures under CSP, deliberately blocked external content, immutable runtime status, actual18-GLB preparation, offline Demo text, nested installation help and a real explicit A/B update loader. The dev check verifies actual CSS and Vite client delivery; it does not claim a source-edit HMR experiment.

Manager separately simulated top32/right16/bottom34/left16 on the three Game sizes and asserted all primary controls remain at least44px and inside usable bounds. On320×568 the canvas can shrink to66px to retain players, instructions and controls; physical-device usability remains pending. Manager visually inspected the390px Demo page, installation help, branded update loader and short Game screenshots. Central icon artwork fits the visible safe zone; actual platform masking remains unverified.

## Standard result matrix

| Standard check | Status and scope |
| --- | --- |
| iOS/status bar | Configuration PASS (`black`, opaque); actual installed iOS UNVERIFIED |
| Safe areas | PASS for simulated four-edge layouts/dialogs/fullscreen; physical device UNVERIFIED |
| Manifest/install | Identity/scope/start/icons PASS; actual installation UNVERIFIED |
| Offline contract | PASS for explicitly prepared Game and truthful online-only Solar/library scope |
| SW versions | PASS for verified candidates, scoped isolation and retained dependencies; automatic complete-cache eviction has a concrete exception in the contract |
| Update prompt | PASS for explicit consent and waiting-worker behavior; one-time legacy save/close/reopen migration tested |
| Update loader | PASS for safe-save refusal, retry, active-shot blocking, remote input locks, timeouts, late callbacks and one document reload |
| Responsive layout | PASS for7 index widths and short Game layouts; real browser zoom UNVERIFIED |
| Accessibility | PASS for executed keyboard/focus/contrast checks and6-state axe scan; full WCAG conformance not claimed |
| Smart topbar | N/A, header is nonpersistent |
| Scroll-to-top | PASS for contextual visibility, keyboard/reduced motion and no Game RAF contention |
| Theme chrome | Dark configuration PASS; light theme N/A; actual OS chrome UNVERIFIED |
| Security/privacy | Production CSP positive/negative checks PASS; dev-only CSS/HMR exception and meta/header limits documented |

## Findings resolved during acceptance

- Retry from an update error previously hid the focused Retry button. Busy transitions now focus the loader heading; real retry/focus assertions remain.
- Installation help inherited white text on its accent button, producing measured contrast1.4. An explicit dark foreground fixes it; the permanent contrast assertion failed on the retained old build and passed on the final candidate. Red evidence: `/tmp/b3g-pwa-standard-before-contrast-fix.log`.
- Hidden scroll-to-top checks added a second pending RAF alongside Game. The unchanged Game regression detected it; the helper now uses a coalesced microtask and immediately hides in demos. No test assertion was weakened.
- Old client code cannot provide the new input-lock protocol. Tested safe migration preserves the stable checkpoint and instructs close-all/reopen rather than accepting an unsafe activation.

## Release gate and retained limits

The existing main-push Pages workflow now additionally gates deployment on model-library and PWA-standard suites. Release acceptance requires the exact pushed SHA, a successful workflow and matching live build identity, followed by live navigation/CSP/3D checks. Those remote identities are reported in the delivery message after execution; local results alone do not establish deployment.

Complete caches are deliberately retained to protect suspended clients and the last good pack. Temporary candidates are cleaned, but automatic complete-version eviction is deferred; storage quota is not guaranteed. Production Core Web Vitals, actual browser zoom and sustained mobile GPU/memory behavior were not measured. No dependency, lockfile, model/source asset, Game rules or checkpoint schema change is introduced. KB remains read-only.

## Physical-device checklist

Record device, OS/browser version, browser versus installed mode, orientation, network/cache state, screenshot and outcome. All entries remain UNVERIFIED until executed.

- Install from Safari to iPhone Home Screen; check identity, icon and Game startup destination.
- Completely close/reopen; check startup background, opaque status-bar/icon contrast and safe areas under system light/dark settings.
- Check portrait/landscape notch/Dynamic Island/home indicator, menus, viewer, install/update dialogs and fullscreen.
- Focus search with actual keyboard, rotate, dismiss keyboard and check layout/page zoom.
- Prepare Game pack, disconnect, cold launch and resume a stable saved turn.
- Receive real new waiting version; observe prompt, click Update, see loader, activate/reload once and resume compatible state.
- Verify refused update during shot, other-tab play or save failure leaves useful recovery.
- For claimed Android installation support, repeat installation/offline/update on a recorded Android/Chrome device.

Headless WebKit is not an iPhone. Safe-area simulation is not actual system chrome. Half-width reflow is not real browser zoom. No production Core Web Vitals or physical GPU/memory claim follows from these checks.
