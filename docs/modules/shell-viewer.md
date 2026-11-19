# Shell and viewer modules

Scope: the page shell (routing, library browsing, menus, language and palette, topbar), the GLB viewer, the build-time registries and the deploy workflow. Every statement below was read from the code at the time of writing; file paths and function names are given so it can be re-verified. Data is static: there is no backend, and `models/catalog.json` plus `data/demos.json` are the only registries.

## 1. Overview and data flow

```
models/catalog.json + models/*.glb/.json   data/demos.json
        |  scripts/catalog.mjs loadCatalog()      |  scripts/demo-registry.mjs loadDemos()
        v                                          v
   vite.config.js plugin "gallery-registries" (virtual:gallery-catalog / virtual:gallery-demos)
        v
   src/main.js  (state owner: route, filters, active viewer/page)
     |-- library/browse.js (DOM helpers, matches, setupFilters)
     |-- i18n/*, design/*  (language, palette)       |-- navigation.js, smart-topbar.js, scroll-to-top.js
     |-- openViewer() --dynamic import--> viewer.js --> model-viewer-renderer.js, viewer-framing.js
     '-- syncRoute()  --dynamic import--> game/ solar/ chibi-motion/ chibi-dressup/ shelf-inspector/ product-studio/ pages
```

`src/main.js` is the only entry point and the single owner of runtime state. Everything else is either a stateless helper or a `setup*()` function called once at startup.

## 2. `src/main.js` (shell controller, 809 lines)

**Responsibility.** Render the model library and demo index, own URL-driven routing, open/close the viewer dialog, mount/unmount demo pages, wire PWA state into the UI. It exports nothing.

**State it owns (module-level `let`).**
- Viewer: `viewerController` (AbortController), `activeViewer` (`{reset, dispose, setView}`), `activeAsset`, `opener` (focus return), `modelReturnUrl`.
- Routing: `mountedRoute`, `routeRun` (monotonic token against stale async mounts), `pageController` (AbortController for the mounting demo), `lastRouteUrl` (restore URL when the game vetoes leaving), page handles `gamePage`, `solarPage`, `productStudioPage`, `shelfInspectorPage`, `motionPage`, `dressupPage`.
- `pwaState` (last `pwa-state-change` detail).
- Constant lookups built from the catalog: `assets` (flat), `assetById` (keyed by both `id` and `slug`), `demoPages`, `motionDemos` (two chibi-motion variants keyed `chibi-motion`/`tripo-motion`).

**Routing (`route()`, `syncRoute()`, `navigate()`).**
- `route()` maps `?page=` to one of `demoPages` + `demos` + `about`, `#about` legacy hash, otherwise `gallery` (`?page=models` is also `gallery`; unknown values fall back to gallery and `syncRoute` shows `shell.missingRoute` + an update offer).
- `isSearchMode()` = `page=models`, or no `page` with any of `q/theme/category/collection/feature`; it toggles `.search-mode` and which heading/intro is shown in `renderModels()`.
- `syncRoute()` order: refresh scroll-to-top; if leaving the game, call `gamePage.beforeLeave()` and on veto `history.replaceState` back to `lastRouteUrl`; toggle `setSmartTopbar(!isDemo)`; show/hide `#<name>-page` sections, footer (hidden on game), `body.game-page`, `aria-current` on nav links; `refreshTitle`; early return if the same route is already mounted; otherwise abort `pageController`, dispose every old page, bump `routeRun`, then for demos lazy-`import()` the page module and call `mountGame / mountMotion / mountShelfInspector / mountProductStudio / mountDressup / mountSolar`. After the await it re-checks `run !== routeRun` and `signal.aborted`; an aborted late result is disposed. Failure renders `shell.experienceFailed` with retry (re-runs `syncRoute`) and `offerUpdate`. Successful mount dispatches a `<page>-mounted` window event (used by browser tests). For non-demo routes it closes the viewer if the page is not gallery, and calls `syncModelUrl()` on gallery. Focus moves to the new page's `h1` when the route or library mode changed.
- `navigate(page, alreadyConfirmed, hash, home)` pushes a URL (deleting `model`/`page`; `home` also clears the five filter params), closes the mobile menu without focus restore, scrolls to top, calls `syncRoute`. A single delegated document `click` handler converts `a[data-asset-id]` (opens viewer), `a[data-page]` and `.brand` into SPA navigation, ignoring modified clicks. `popstate` and `hashchange` both call `syncRoute`.

**Library rendering (`renderModels`, `createCard`, `renderDemos`).** Filters are read straight from the form controls (`#model-search`, `-category`, `-theme`, `-collection`, `-feature`), results grouped by `browseCategory`, rebuilt with `replaceChildren` each time. The feature filter (`animated` = `animations > 0`, `interactive` = `hasInteractiveControls`) is evaluated here, not in `browse.matches`. `hasInteractiveControls` is a hard-coded id/collection list (`interactive-shopping-cart`, `gjh-mall-visitor-v2`, `gjh-visitor-v3`, `singapore-fish`) that mirrors, but is independent of, the dispatch in `viewer.js`. `preserveLibraryMode()` keeps `?page=models|gallery` coherent when the user types/clears filters. Legacy category URLs are kept via hidden `<option data-previous-category>` entries.

**Viewer dialog (`openViewer`, `closeViewer`, `syncModelUrl`).**
1. `openViewer` aborts the previous controller and disposes the previous viewer, fills title, metadata `<dl>` (`metadata()`), description plus attribution links (only `https://` URLs, `rel="noopener noreferrer"`), download link (hidden when `downloadable === false`), poster, up to three related links from the same collection, `showModal()`, pushes `?model=<slug>` (remembering `modelReturnUrl` the first time).
2. It dynamic-imports `./viewer.js` and calls `createViewer(viewport, asset.file, status, signal, asset)`; if the signal aborted meanwhile the viewer is disposed, otherwise `activeViewer` is stored, poster hidden, Reset enabled. On error: `viewer.unavailable`, Retry button shown, `pwaRuntime.checkForUpdate(true)`.
3. `closeViewer` aborts, disposes, closes the dialog, strips `model` from the URL (`replaceState` to `modelReturnUrl` if set) and refocuses `opener` (or the card, or `.brand`). Esc (`cancel` event) and backdrop click route here. Fullscreen button toggles `viewport.requestFullscreen`.
4. `syncModelUrl` makes `?model=` deep links, back/forward and unknown ids work (`viewer.missingModel` notice).

**Language/PWA wiring.** `refreshLanguage()` is subscribed with `onLanguageChange` and re-renders the current library/demo list, viewer metadata, title, version chip and update buttons. `refreshDemoOfflineStatus`, `refreshUpdateActions`, `offerUpdate` read `pwaState` from `setupPwa(() => gamePage)` (`src/pwa/register.js`, documented elsewhere). At the end it removes `data-i18n-pending` from `<html>`.

**Lifecycle.** Startup is a straight-line script (no init function): localizeTree, language sync, picker, menu, topbar, palette, scroll-to-top, filter setup, `syncRoute()`. There is no teardown; listeners live for the page's life.

**Tests.** No unit test imports `main.js` (it needs the DOM and virtual modules). Coverage is `scripts/test-library-browser.mjs` (Playwright against a build): static index counts and no GLB/WebGL on index, search/filters/clear and URL state, category grouping, mobile filters, demo filters, mobile footer/back-to-top, legacy `?model=` deep link/refresh/history, failed load + retry, unknown model/no WebGL, mobile menu keyboard/focus, demo launch/return/canvas release, reduced motion and 200% reflow. `scripts/test-pwa-browser.mjs` covers update/offline UI.

**Known gaps.** `let motionPage/dressupPage/shelfInspectorPage` are declared above the imports while the other page handles are declared lower (style inconsistency; works). `demoPages` is duplicated in three places (`main.js`, `scripts/demo-registry.mjs` `routes`, and `scripts/i18n-build.mjs` derives from `data/demos.json`); adding a demo needs edits in all of them plus a lazy-import branch in `syncRoute`. The `syncRoute` import chain is an if/else ladder with the product-studio page as the implicit default. `openViewer` references `pwaRuntime`, a `const` declared later in the file (safe only because it is called after startup). No unit test on route/state logic.

## 3. `src/viewer.js` (`createViewer`, default export)

**Responsibility.** Build one Three.js scene for one GLB inside the dialog viewport and return `{ reset, dispose, setView }`. Called only from `main.js openViewer` (dynamic import, so Three.js loads only when a model is opened).

**Flow.** Acquire the shared renderer lease; set tone mapping/clear colour per asset (defaults; `marina-bay-sands-loop`, vehicle `proton-saga-1985`, `family === "solar-system"` override); create scene, camera (FOV 35), `OrbitControls` (damping), keyboard handler (arrows orbit 10 deg, `+/-/PageUp/PageDown` zoom); lights from `asset.details.display.previewLighting` with defaults. Then `fetch(url, {signal})` -> `arrayBuffer()` -> `GLTFLoader.parseAsync` (deliberately not `FileLoader`; see `docs/gallery-loading.md`), aborting at every await if `disposed`/`signal.aborted`. Metadata `display` fields apply: `previewRotationY`, `previewCameraDirection`, `studioEnvironment`/`environmentIntensity`, `textureAnisotropy`.

**Per-asset add-on dispatch (by asset id/collection, dynamic imports each guarded by an abort check).** `singapore-fish` collection -> `fish-motion.js`; `interactive-shopping-cart` -> `shopping-cart/demo.js`; `gjh-mall-visitor-v2`/`gjh-visitor-v3` -> `visitor-v2|v3/demo.js`; `tripo-chibi-rig` -> `chibi-rig-controls.js`; `tripo-convert-1c818c0d`/`-405dc0a0` -> `tripo-animation-preview.js`; `marina-bay-sands-loop` -> `building-loop.js`; `proton-saga-1985` -> inline vehicle toolbar (front/rear/left/right presets, four door hinges only when all `Door_{FL,FR,RL,RR}_Hinge` nodes exist, shadowed studio floor, fog).

**Rendering model.** On-demand: `invalidate()` schedules one `requestAnimationFrame` only if visible; `draw()` updates add-ons, `controls.update()`, renders, and re-invalidates only while something is animating or the camera is moving. `visibilitychange` cancels the frame and suspends fish motion. A `ResizeObserver` + window `resize` call `syncViewerSize` and refit via `frameForResize`. `reset()` clears add-on state/doors and calls `frameObject` (fit + near/far + min/max distance, inertia cleared by temporarily disabling damping).

**State ownership.** All state is closure-local: renderer lease, scene, camera, controls, `model`, `studio` group, add-on handles, `frame`, `disposed`. The only shared state is the renderer (section 5).

**Disposal.** `dispose()` is idempotent and is also registered on `signal`'s `abort`. It cancels the frame, disconnects observers, removes listeners, disposes controls, every add-on, geometries/materials/textures of `model` and `studio`, clears `scene.environment`, disposes the shadow map, removes the vehicle toolbar and releases the renderer lease. Any exception during load runs `dispose()` then rethrows (so `main.js` shows retry). A `webglcontextlost` listener prevents default and shows `viewer.interrupted`.

**Dependencies.** `three` (0.187.0), `OrbitControls`, `GLTFLoader`, `i18n/index.js` (`localize`, `t`), `model-viewer-renderer.js`, `viewer-framing.js`, plus the lazily loaded add-ons above.

**Tests.** `tests/viewer-framing.test.mjs` (framing only), `tests/preview-config.test.mjs` (the metadata `display` contract the viewer consumes, via `validateMetadata`), `scripts/test-viewer-context-cleanup.mjs` (Playwright: counts WebGL contexts and GPU buffer/texture/program leaks across repeated open/close), `scripts/test-library-browser.mjs` (open/retry/fullscreen/deep link). Add-ons have their own tests (e.g. `tests/interactive-shopping-cart.test.mjs`, `tests/gjh-visitor-v2.test.mjs`).

**Known gaps.** `createViewer` is a ~430-line closure with asset-id string checks; no unit test constructs it (needs WebGL). Add-on selection duplicates `hasInteractiveControls` in `main.js`. Disposal of add-on-owned GPU resources is trusted to each add-on. `onKeyDown` references `invalidate` before its `const` declaration (safe since the handler runs later).

## 4. `src/viewer-framing.js`

**Responsibility.** Pure camera/renderer sizing math. **Exports:** `syncViewerSize(container, renderer, camera, pixelRatio)` returns `{sizeChanged, aspectChanged, pixelRatioChanged}` (no-op if the container has zero size; throws `RangeError` on a bad pixel ratio; calls `renderer.setSize(w, h, false)`); `fitViewerBounds(box, camera, direction, options)` (8 box corners); `fitViewerObject(object, camera, direction, options)` (uses transformed, finite vertices of visible meshes, including `InstancedMesh` instances and skinned meshes via `skeleton.update()`, falling back to box corners). Both delegate to the private `fitViewerPoints`, which validates (non-empty bounds, perspective camera, `heightFill`/`widthFill` in (0,1), non-zero direction; degenerate up vector uses a fallback up) and returns `{target, direction, distance, radius, minDistance, maxDistance}` (`minDistance = max(0.05 r, 0.18 d)`, `maxDistance = max(12 d, 12 r)`). Defaults: height fill 0.75, width fill 0.9. No state, no disposal. Depends only on `three`.
**Tests:** `tests/viewer-framing.test.mjs` (aspect ratios desktop/mobile, resize + refit, invalid input, vertex-based fit). **Gap:** `fitViewerObject` walks every vertex twice (bounds pass, then point pass), O(vertices) per reset/resize on heavy models.

## 5. `src/model-viewer-renderer.js`

**Responsibility.** Share one `WebGLRenderer` across all viewer openings (WebKit counts lost contexts until GC). **Export:** `acquireModelViewerRenderer()` returns a lease `{ renderer, getStudioEnvironment(), release() }`. Module state: `shared` renderer, `studioTarget` (PMREM of `RoomEnvironment`, built lazily), `owner` token, `lifecycleInstalled`.
- Acquiring while a lease is active throws (`main.js` always disposes the previous viewer first). A lost context destroys the shared instance and a new one is created.
- `release()` (token-checked, idempotent) removes the canvas, resets render lists/state/target, shrinks to 1x1 and clears; if the context is lost it fully destroys. `getStudioEnvironment()` throws once the lease is stale.
- A `pagehide` listener (non-persisted) calls `destroy()` (dispose, `forceContextLoss`, remove canvas, dispose PMREM target).
**Tests:** only indirectly via `scripts/test-viewer-context-cleanup.mjs`. **Gap:** no unit test of lease semantics (stale lease, double acquire, lost context).

## 6. `src/navigation.js`

`setupMenu()` wires `#mobile-menu` (a `<dialog>`) to `#menu-trigger`/`#close-menu`: opens with `showModal`, locks `body.style.overflow` and restores the previous value on close, `aria-expanded`, focuses the first nav link, backdrop-click close (rect hit test), auto-close when `(min-width: 901px)` matches. Returns `close(restoreFocus = true)`; `main.js` keeps it as `closeMenu` and passes `false` from `navigate()` so focus goes to the page heading instead of the trigger. State: two closure vars (`previousOverflow`, `restoreFocus`). No teardown. Covered only by the mobile-menu case in `scripts/test-library-browser.mjs`.

## 7. `src/library/browse.js`

Pure DOM/filter helpers, no module state. Exports: `normalized`, `matches(item, query, category, collection, theme, translated)` (every whitespace-separated query word must appear in a haystack of title/name/description/category/browseCategory/collectionName/tags plus translated labels; `category` also matches `previousCategory`), `element`, `poster(url, title, live)` (lazy 400x400 `<img>`; on error hides it and adds a localized fallback; `live` makes alt text re-localizable), `categoryKey` (`category.<slug>` i18n key), `options(select, values, keyFn)` (sorted unique localized `<option>`s), `emptyState`, `setupFilters(form, fields, onChange)` (mirrors field values into the query string with `history.replaceState`, returns a `sync()` that restores fields from the URL), `formatBytes`. Depends on `i18n/index.js`. Tested by `scripts/test-library-browser.mjs` and the key coverage in `scripts/check-i18n.mjs` (imports `categoryKey`); no unit tests for `matches`. **Gap:** `matches` for demos passes `category` as the second argument while models pass theme/collection, a positional-parameter contract that is easy to misuse.

## 8. `src/i18n/*`

- `preferences.js`: `DEFAULT_LANGUAGE = "en"`, `LANGUAGE_STORAGE_KEY = "b3g:language:v1"`, `languages` (`en`, `zh-Hans`, `ms` with label/short), `readSavedLanguage(key, ids, fallback)` (try/catch around localStorage). Also serialised into the build-time head script, so it must stay self-contained.
- `index.js`: `messages` (tables from `messages/{en,zh-Hans,ms}.js`), `t(key, params, locale)` (falls back locale -> `en` -> the key; `{name}` interpolation), `number`, `plural(key, count, params)` (`Intl.PluralRules`, tries `key.<category>`, `key.other`, then English), `localize(node, key, params, attr)` (writes `data-i18n[-attr]`, stores params, which may be a function, in a `WeakMap`, sets text/attribute), `localizeTree(root)`, `mountMarkup`, `onLanguageChange(cb, signal)` (window event `gallery-language-change`), `setLanguage(id)` (updates `<html lang>`, re-localizes tree, dispatches event, persists), `syncLanguageAcrossTabs()` (`storage` event). Module state: current `language`, initialised from `<html lang>`.
- `picker.js` `setupLanguagePicker()`: builds radio list in `#language-picker`, updates trigger labels on change, focus management, closes when the mobile menu closes.
- `picker.css`: dialog styling.
**Build integration.** `scripts/i18n-build.mjs` (`i18nBuildPlugin`) injects a CSP-hashed bootstrap script that sets `<html lang>` and a localized `<title>` before app JS, and pre-fills `data-i18n*` text/attributes in the HTML in English.
**Tests.** `scripts/check-i18n.mjs` (run by `npm test`): same language set in picker and tables, every locale has exactly English's keys, non-empty strings, matching placeholders, no duplicate keys, referenced keys exist (catalog categories, palette names, etc.). **Gap:** no runtime unit tests of `t`/`plural`/`localize`; no check that a `data-i18n` key used in code strings outside the scanned sources exists.

## 9. `src/design/*`

- `tokens.js`: `DEFAULT_PALETTE = "editorial-moss"`, `PALETTE_STORAGE_KEY = "b3g:palette:v1"`, `palettes` (role -> colour per palette incl. `colorScheme`), `paletteThemes` (`id -> [background, scheme]`), `supportingRoles`, `resolvePalette(id)`.
- `palette.js`: `readSavedPalette(key)`, `applyPalette(requested, themes, fallback)` (validates id, sets `<html data-palette>`, `theme-color` and `color-scheme` metas). Both are serialised into the build-time head script, so they must be dependency-free.
- `palette-picker.js` `setupPalettePicker()`: radio cards in `#palette-picker`, `select()` applies and checks, change persists to localStorage (failure keeps live choice), cross-tab `storage` listener, desktop and mobile-menu triggers, focus return rules. `palette-picker.css`: styling.
**Build integration.** `scripts/palette-build.mjs`: virtual `virtual:gallery-palette-colors.css` (one `[data-palette]` rule per palette; default also on `:root:not([data-palette])`) and a CSP-hashed head script that applies the saved palette before first paint.
**Tests.** `scripts/check-palette-contrast.mjs` and `scripts/check-color-tokens.mjs` (both in `npm test`), `scripts/check-i18n.mjs` (palette name keys). Picker interaction has no dedicated test. Owner of state: `<html data-palette>` plus localStorage; no in-memory store.

## 10. `src/smart-topbar.js` and `src/scroll-to-top.js`

- `setupSmartTopbar()` returns `setEnabled(bool)`. It toggles `data-smart` on `.topbar`; when enabled, scrolling down past 80 px by more than 8 px sets `data-scroll-hidden`, scrolling up, `focusin`, `:focus-within`, being within 80 px of the top, or any `dialog[open]` (detected by a `MutationObserver` on the `open` attribute) reveals it. `main.js` disables it on demo pages (`setSmartTopbar(!isDemo)`).
- `setupScrollToTop(getPage)` creates `#scroll-to-top` before `.footer`, returns `refresh()`. Visible only on `gallery/demos/about`, pages taller than 1.5 viewports, after scrolling 320 px or 0.8 viewport, and no open dialog/PWA notice. Updates are coalesced with `queueMicrotask` (deliberately no `requestAnimationFrame`, to keep demos' frame budget). Click scrolls to top (instant under reduced motion) and focuses the visible `h1`. Also exports `getPageHeading(main)`, used by `main.js` for focus management. Listeners and observer are never removed.
**Tests.** Only the back-to-top case in `scripts/test-library-browser.mjs`; topbar behaviour has no automated test. **Gap:** hard-coded thresholds; `getPage` is passed `route` before `route` is defined in source order (function declaration hoisting makes it work).

## 11. Build-time registries

**`vite.config.js`.** Plugins in order: `pwaBuildPlugin`, `paletteBuildPlugin`, `i18nBuildPlugin`, a dev-only plugin that strips the production CSP `<meta data-production-csp>` (so Vite HMR works), and `gallery-registries`. The latter resolves `virtual:gallery-catalog` and `virtual:gallery-demos`; `load()` runs `loadCatalog()` (so every build/dev load validates all GLBs), rewrites each `file`/`thumbnail` (and demo `thumbnail`) into a Vite `?url` import so assets get hashed URLs, and emits `export default <json>`. `base: "./"`, `assetsInlineLimit: 0`, `__APP_VERSION__` from `package.json`. **Gap:** `loadCatalog()` is called once per virtual module (twice per build) and reads/parses every GLB each time; no caching and no HMR invalidation when `models/catalog.json` changes in dev.

**`scripts/catalog.mjs`.** Exports `textField`, `tagsField`, `validateCatalog(input)`, `validateMetadata(input, expectedId)`, `loadCatalog(root)`. `validateCatalog` clones and normalises: unique slug-pattern ids/slugs (slug defaults to id, a slug may not equal another asset's id), required names/category, `browseCategory` defaulting to `category`, `previousCategory`, tags, default description, safe paths (`models/` prefix, no `..`, `\ ? # %`, extension allow-list: `.glb`; `.webp/.png/.jpg/.jpeg`; `.json`), `downloadable` boolean default true, `format = "GLB"`. `validateMetadata` checks the `display` object consumed by the viewer (preview rotation, camera direction not vertical, lighting ranges, anisotropy 1-16, environment intensity 0-3), accuracy notes, attribution, rights, scientific properties. `loadCatalog` additionally resolves files via `realpath` inside `models/` (no symlink escape), parses each GLB header/JSON chunk, rejects external image/buffer URIs, checks the scene root against `asset.root` (including the skinned multi-root case), counts triangles (only mode 4) and unique vertices, materials, animations, bytes, and derives `license`.

**`scripts/demo-registry.mjs`.** `validateDemos(input, catalog)` and `loadDemos(root, catalog)`: array of unique slug-pattern `id`/`slug`, text fields, tags/technologies, `status` in `available|unavailable`, `route` must be one of seven hard-coded `?page=` routes and unique, `thumbnailAssetId` must exist in the catalog and supplies `thumbnail`.

**`scripts/deployment-inputs.mjs`.** Reads `git ls-files --stage` (rejects symlinks), selects tracked `src|scripts|public|data/`, root config files and `models/catalog.json`, adds every `file/thumbnail/metadata` of every catalog asset, then iteratively scans selected JS/CSS/HTML for string literals that resolve under `models/` (including globs and `/models/` absolute paths, and follows model-owned JS imports). Outputs sparse-checkout patterns to `/tmp/gallery-deployment-patterns` and `cache_key=pages-v1-<sha256 of path+blob hash>` to `GITHUB_OUTPUT`. Template-literal paths (`${`) are skipped, so a dynamically built model path is not detected; the doc comment says the production build is the completeness check.

**`.github/workflows/deploy.yml`.** Triggers: push to `main`, manual `workflow_dispatch` (input `validate_assets`). Single job (20 min, concurrency group `pages`, cancel in progress) with pinned action SHAs: sparse checkout without `models/`, `docs/`, `output/`, `tests/`, then Node 24, `deployment-inputs.mjs`, restore `dist` from cache keyed by the digest (skipped when validating), sparse-checkout of the selected model files, `npm ci`, optional full `git sparse-checkout disable` + `npm run validate:assets`, `npm run build:deploy` (= `vite build`, no asset validation), upload and deploy to GitHub Pages. An identical-input cache hit skips the build. **Gaps:** `npm test` and the browser tests do not run in CI; the normal push path builds without `validate:assets` (only the manual dispatch validates); the workflow does not run `check-i18n`/palette checks. Details of rollout: `docs/deployment.md`.

**Tests for registries.** `tests/registry.test.mjs` (catalog enrichment/categories, duplicates, malformed values, path traversal/schemes, defaults, symlink refusal, demo registry poster resolution and schema failures, legacy id aliases, metadata validation), `tests/catalog.test.mjs` (GLB external URI rejection, embedded data URIs, billiards fixtures), `tests/preview-config.test.mjs`. `scripts/deployment-inputs.mjs` and `vite.config.js` have no automated tests.

## 12. Summary of cross-cutting gaps

1. No unit tests for the shell state machine (`main.js`), `navigation.js`, topbar/scroll-to-top, `browse.matches`, i18n runtime, or the renderer lease; coverage depends on Playwright scripts that need a build and are not in CI.
2. Demo/route lists and interactive-asset lists are duplicated by hand across `main.js`, `demo-registry.mjs`, `viewer.js` and `data/demos.json`.
3. Registry loading re-validates all GLBs per virtual module and has no dev HMR invalidation.
4. CI deploy skips unit and asset validation on the push path.
