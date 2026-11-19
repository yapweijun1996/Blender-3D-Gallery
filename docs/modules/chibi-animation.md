# Chibi and Animation Modules

Code-level reference for the chibi dress-up demo, the motion studios and the small per-asset animation add-ons.
Everything below was read from the files named; nothing here is a plan. Paths are relative to the repository root.
Related prose docs: `docs/chibi-dressup-spec.md`, `docs/chibi-dressup-progress.md`, `models/chibi-dressup/README.md`.

## 1. Map

| Module | Mounted by | Surface |
| --- | --- | --- |
| `src/chibi-dressup/*` | `src/main.js` route `?page=chibi-dressup` (dynamic `import("./chibi-dressup/page.js")`) | Full-page demo |
| `src/chibi-motion/page.js` | `src/main.js` routes `?page=chibi-motion`, `?page=tripo-motion` (`motionDemos` options table) | Full-page demo |
| `src/visitor-v2/demo.js`, `src/visitor-v3/demo.js` | `src/viewer.js` for asset ids `gjh-mall-visitor-v2`, `gjh-visitor-v3` | Viewer add-on toolbar |
| `src/chibi-rig-controls.js` | `src/viewer.js`, asset id `tripo-chibi-rig` | Viewer add-on toolbar |
| `src/tripo-animation-preview.js` | `src/viewer.js`, ids `tripo-convert-1c818c0d` (run, sit) and `tripo-convert-405dc0a0` (walk) | Viewer add-on toolbar |
| `src/fish-motion.js` | `src/viewer.js`, any asset with `collectionId === "singapore-fish"` (static import) | Viewer add-on toolbar |
| `src/building-loop.js` + `src/sands-water.js` | `src/viewer.js`, asset id `marina-bay-sands-loop` | Viewer add-on toolbar + reflective water |

Viewer add-ons share one contract (see `src/viewer.js`, dispatch around lines 216-290 and 406): a factory receives
`{ model, clips, container, invalidate, ... }`, inserts its toolbar with `container.insertAdjacentElement("afterend", ...)`,
and returns `update(elapsedSeconds) -> boolean` (true = keep redrawing) plus `dispose()`. The viewer's `draw()` calls every
add-on's `update` and re-invalidates while any returns true; its `dispose()` calls each add-on's `dispose()`. Add-ons are
loaded with `await import(...)` and each dispatch re-checks `disposed || signal.aborted` before constructing.
The page-style demos (dress-up, motion) instead return `{ dispose }` from `mount*` and own their own renderer loop.

Shared conventions across all of them: UI strings go through `src/i18n/index.js` (`localize`, `mountMarkup`, `t`); motion
respects `prefers-reduced-motion` by starting paused; `AnimationMixer.stopAllAction()` + `uncacheRoot(model)` on teardown.

---

## 2. Modular dress-up (`src/chibi-dressup/`)

### 2.1 `config.js` - schema, validation, persisted state

Pure module (only imports `languages` from `src/i18n/preferences.js`); the only file here with a Node unit test.

Exports:
- Constants: `STORAGE_KEY = "b3g:chibi-dressup:v1"`, `MOTION_CLIPS` (idle, walk, run, wave, jump, nod, dance),
  `ACTION_CLIPS` (sit, hold, box, bag, take), `CLIPS` (both), `HANDS` (`L`,`R`), `EXPRESSIONS`
  (neutral, happy, surprised, sad), `GESTURES` (nine hand poses).
- `validateManifest(manifest)` - throws `Error("Invalid dress-up manifest|body|module|default")`, returns the manifest.
- `fitsBody(module, bodyId, manifest)` - module fits the bodies in `bodyIds`; with no list it belongs to the first body.
- `moduleFamily(module)` - `module.family ?? module.id`.
- `modulesForBody(modules, bodyId, manifest)` - maps the current choice per slot to the same `family` on another body, else `null`.
- `normalizeConfig(value, manifest)` - coerces any stored/unknown value to a valid config
  `{ body, modules:{slot:id|null}, animation, hands:{L,R}, expression }`; invalid ids fall back to the manifest default
  (only if that default fits the body), else `null`.
- `loadConfig(manifest, storage?)`, `saveConfig(config, manifest, storage?)` - `localStorage` (or injected storage);
  both swallow errors, so blocked storage leaves a usable in-memory default.

Manifest schema (`models/chibi-dressup/manifest.json`, `version: 1`) as enforced by `validateManifest`:
- `slots`: exactly `["hair","top","bottom","shoes","hat"]` in any order (length and membership checked).
- `bodies[]` (non-empty): `id` slug (unique), `label` with a non-blank string for every locale in `languages`,
  `body` / `gestures` GLB paths, `motion[]` (non-empty GLB paths), optional `sockets`. A model path must match
  `^(?:[a-z0-9_-]+/)*[a-z0-9_-]+\.glb$` (no `..`, no extension other than `.glb`). `sockets` keys allowed:
  `hold_item|hold_box|hold_bag|jar` = `{translation[3], rotation[4]}` and `chair` = `{translation[3], scale[3]}`, all finite.
- `modules[]`: unique slug `id`, unique `file` matching `^modules/<lowercase-with-dash-or-underscore>.glb$`, a `slot` from `slots`,
  full locale `label`, `status` in {`verified`,`pending`}, positive safe-integer `bytes`, 64-hex `sha256`; optional
  `excludesSlots` (known slots, never the module's own slot), `bodyIds` (non-empty, known ids), `family` (slug).
  The sync script also writes a `source` field; the validator ignores unknown keys.
- `defaults`: `body` must be a body id; other keys must be a slot whose value is `null` or an existing module id of that slot.

Current committed manifest: one body (`neutral`: `base_body.glb`, `hand_gestures.glb`, motion `motion-clips.glb` +
`actions.glb` + `hold_actions.glb`, no per-body `sockets`), 14 modules, all `verified`, defaults `{hair:"hair-bob", body:"neutral"}`.
No `hat` module exists yet. `top-dress` carries `excludesSlots:["bottom"]`.

### 2.2 `view.js` - loading, three.js stage, disposal

- `loadModels(urls, signal, scenes)` - `fetch` + `GLTFLoader.parseAsync` per URL via `Promise.allSettled`, adds each `gltf.scene`
  to the caller's `scenes` Set (so a failed batch can still be disposed), rethrows the first rejection. Results keep input order.
- `disposeModels(scenes)` - collects geometries, skeletons, materials, textures (and `ImageBitmap`s) into Sets and disposes once each.
- `createView(stage, model, bounds, advance)` - builds Scene + lights + PerspectiveCamera + `WebGLRenderer({alpha})` + `OrbitControls`
  (no pan, polar clamp). Fits the camera from `bounds` (headroom for Jump), `ResizeObserver` on the stage. Render loop is
  on-demand: renders only when `playing` (calls `advance(delta)`, delta clamped to 0.05 s) or `dirty` (set by `invalidate()` and
  orbit changes). Returns `{ canvas, setPlaying, invalidate, triangles, dispose }`; `dispose` disconnects the observer, disposes
  controls and renderer, `forceContextLoss()`, removes the canvas.
- `getBounds(model)` - `Box3.setFromObject(model, true)`.

### 2.3 `rig.js` - motion retargeting, hand overlay, module binding

- `bindModule(model, scene, bodySkeleton)` - attaches a wardrobe GLB onto the body skeleton: matches joints by **name** (must be the
  same count, no duplicates, else `Module joints do not match body`), rewrites each shared `skinIndex` attribute through the
  index mapping (once per attribute), `model.attach(mesh)` + `mesh.bind(bodySkeleton, bindMatrix)`, `frustumCulled=false`,
  `visible=false`, disposes the module's own skeletons. Returns the meshes; the caller toggles `visible`.
- `createRig(model, skeleton, sources, handClips)` returns `{ select, current, time, update, inspect, dispose }`.
  - Retargeting (`retargetMotion`): for every body bone it finds the same-named bone in the motion GLB, computes a
    source-to-target basis change and re-expresses every quaternion track in the target bone's local frame. Clips
    in `MOTION_CLIPS` are retargeted **in place** (rotations only; hips X/Z pinned, vertical bob kept). The `ACTION_SOURCE_CLIPS`
    (`sit_down`, `sit_idle`, `stand_up`, `hold_item`, `hold_box`, `hold_bag`, `take_item`) are retargeted **with** position
    and scale tracks offset by the bone rest delta. Missing bone/clip/tracks throw (e.g. `Missing motion clip X`).
    All 14 source clips must exist across the supplied `sources` or `createRig` throws.
  - Playback: one `AnimationMixer` on the model; `select(name)` expands the logical choice with `plan()`:
    `sit -> [sit_down, sit_idle]`, `hold/box/bag/take -> [hold_item|hold_box|hold_bag|take_item]`, leaving `sit` prepends `stand_up`.
    `sit_down`/`stand_up` are `LoopOnce` + clamp; the mixer `finished` event starts the next queued clip; 0.3 s cross-fade.
  - Hand gestures (`readGestures`): each of 9 gestures x 2 hands must be a clip named `hand_<gesture>_<L|R>` with exactly one
    quaternion keyframe per finger bone. `update(delta, hands)` first restores finger bones to the last mixer sample, runs the
    mixer, then overwrites the selected hand's fingers with the pose (saving a baseline) - so gestures overlay any clip without
    changing playback.
  - `inspect()` returns clip, playing clip, times and per-joint rest/current rotations (used by the browser test).
  - `dispose()` restores fingers, `stopAllAction`, `uncacheRoot(model)`.

### 2.4 `props.js` - held props, chair, shelf jar

`createProps({ root, hand, chair, cup, box, bag, shelf, fitted })` returns `{ detach, sync }`.
- Hand sockets (`HAND_SOCKETS`, `JAR`) are hardcoded defaults for the neutral body, measured from
  `output/modular-chibi-parts/actions-astra` / `actions-hold2` (`attachment.json`, not all committed). `fitted`
  (= `body.sockets` from the manifest) overrides them per body; `chair` placement (translation, scale) is per body.
- Props are shared GLB scenes loaded once by the page; `detach()` removes them from the current body (jar returns to the
  shelf) so the next body can reuse them. `sync(clip, time)` is called every frame: chair visible for `sit_down|sit_idle|stand_up`,
  cup/box/bag visible for matching `hold_*` clip, shelf visible for `take_item` and the jar is moved by frame
  (`floor(time*24) % 48`): lerp shelf stop -> pickup stop over frames 3-16, re-parented to the hand at frame 29.
- Throws `Shelf prop has no jar` if the shelf scene lacks `Jam_jar`/`Jam jar`.

### 2.5 `expression.js` - face morph + texture swap

`createExpressionController(root, urls, loader?)` finds the skinned mesh with `morphTargetDictionary` containing
`expr_happy|expr_surprised|expr_sad` and a base `material.map`, else throws `Body has no expression morph targets` (the page
catches it and hides the expression fieldset). It clones the material, keeps the neutral map embedded, and lazy-loads the other
three PNG maps (`models/chibi-dressup/expressions/*.png`) on first use, copying colour space/filters from the base map.
`set(name)` is async and last-call-wins (`requested`); `apply` sets exactly one morph influence to 1 and swaps `material.map`.
`dispose()` restores the base material and disposes loaded maps (late loads dispose themselves).

### 2.6 `page.js` - `mountDressup(root, thumbnail, signal)`

(Read as-is; uncommitted changes in the working tree were not touched. At scan time `git diff` for this file and for
`scripts/test-chibi-dressup-browser.mjs` was empty, so the content below is the committed behaviour.)

Control flow:
1. `validateManifest(manifestData)` (import of `models/chibi-dressup/manifest.json`), `loadConfig(manifest)` from localStorage.
2. `mountMarkup` builds the stage (poster + `role=status` loading text, `aria-busy`), the form with fieldsets
   (body, wardrobe, animation + play/pause, expressions, hands). Fieldsets start `disabled`.
3. Shared props (`props/chair|cup|box|bag|shelf_item.glb`) load once into `propScenes`.
4. Model URLs come from `import.meta.glob("../../models/chibi-dressup/**/*.glb", {eager, query:"?url"})`; `assetUrl(file)`
   throws `Unknown dress-up model file` for any manifest path not in the build.
5. `buildCharacter(bodyId)`: loads `[body, gestures, ...motion, ...worn modules]` in one `loadModels`; on failure disposes
   the partial `incoming` set; on success `teardownCharacter()` (old view/rig/face/props/scenes) then builds: skeleton
   (single skeleton enforced) -> `bindModule` for each worn module -> `createExpressionController` (optional) ->
   `createRig(body.scene, skeleton, motion, gestures.animations)` -> `createProps` on `mixamorigRightHand` ->
   `rig.select(config.animation)` -> `buildWardrobe()` -> `createView(...)` whose `advance` calls `rig.update(delta, config.hands)`
   then `props.sync(rig.current, rig.time)` -> `renderConfig()`.
6. **Lazy wardrobe**: only modules currently worn download with the character; `chooseModule` -> `ensureModule` downloads on
   first wear (dedupes in-flight loads via `character.pending`), `bindModule`s it, then `applyConfig()`. A failed download reverts the
   slot to its previous value; a change of body/slot during the download aborts the apply.
7. `renderConfig()` is the single view-sync: `excludesSlots` of worn modules hide/disable covered slots (dress hides bottoms),
   toggles mesh visibility and `aria-pressed` states, updates the play label, runs `rig.update(0, hands)` and `props.sync`.
   `applyConfig()` = `renderConfig()` + `saveConfig()`. Choosing the worn module again un-wears it (slot -> null).
8. `switchBody(bodyId)`: guarded by `switching`; disables fieldsets, `modulesForBody()` carries choices over by family, rebuilds;
   on failure restores the previous config and rebuilds the previous body, showing `dressup.bodyFailed`. Body buttons are
   hidden when the manifest has fewer than two bodies (true today).
9. Clips, expressions, hand `<select>`s each write to `config` then `applyConfig()`. Reduced-motion: starts paused, and a
   `change` listener pauses it. `stage.inspectDressup()` exposes `{...rig.inspect(), body, switching, triangles, expression, modules}` for tests.

State ownership: `config` (in-memory object in `mountDressup`) is the single source of truth; localStorage key
`b3g:chibi-dressup:v1` holds `{body, modules, animation, hands, expression}` (written on every change, normalised on read).
Language is `b3g:language:v1` (owned by `src/i18n`). No other storage.

Lifecycle/disposal: returns `{ dispose }`; `dispose()` deletes `inspectDressup`, `teardownCharacter()` and disposes shared prop scenes.
`main.js` also calls `result.dispose()` if the route was aborted during mount. `signal` aborts fetches (`signal.throwIfAborted()`).
`onLanguageChange(translateModules, signal)` and the reduced-motion listener are tied to the same signal.
A mount error runs `dispose()` and rethrows (route shows a retry button, exercised by the browser test).

Dependencies: three, `GLTFLoader`, `OrbitControls`, `src/i18n`, `style.css`.

### 2.7 Supporting scripts and data

- `models/chibi-dressup/manifest.json` - see 2.1. Sources: `base_body.glb`, `hand_gestures.glb`, `actions.glb`, `hold_actions.glb`,
  `motion-clips.glb`, `props/`, `modules/*.glb`, `expressions/*.png`, `review/` (screenshots written by the browser test).
- `scripts/sync-chibi-dressup-modules.mjs` - manual maintenance script (not wired into `package.json`). A hardcoded `candidates`
  list maps `id/slot/label/paths` to source GLBs under `output/modular-chibi-parts/` (first existing path wins; `ENOENT` falls
  through; missing required source throws before anything is written). Copies to `models/chibi-dressup/modules/<id>.glb`,
  recomputes `bytes` + `sha256`, keeps the previous `status` only when the hash is unchanged, otherwise sets `pending`; rewrites
  `manifest.json`. Modules not in `candidates` are preserved after the candidates.
- `scripts/strip-motion-glb.py` - `python3 strip-motion-glb.py <in.glb> <out.glb>`; rewrites a GLB keeping only nodes (no `mesh`/`skin`),
  animation samplers and the accessors/bufferViews they use; drops a trailing unparented mesh node. Used to produce a
  skeleton-and-animation-only motion file (referenced in `docs/chibi-dressup-progress.md`). A sibling, `models/chibi-dressup/extract-motion.mjs`,
  does the same for `models/tripo-chibi-motion/motion.glb`.
- `scripts/test-chibi-dressup-browser.mjs` - Playwright smoke test (see 2.8). Read only; not modified.

### 2.8 Tests

- `tests/chibi-dressup-config.test.mjs` (`node --test`, part of `npm test`): manifest validates; every module file exists, starts with
  `glTF`, matches `bytes` and `sha256`; all i18n keys used by the page exist in every locale; 15 mutations of the manifest must throw
  `Invalid dress-up*`; config round trip with injected storage; stale/blocked storage normalisation; multi-body `fitsBody`,
  `modulesForBody`, socket validation and body fallback.
- `scripts/test-chibi-dressup-browser.mjs` (Playwright + `serveBuild()` from `scripts/browser-test-utils.mjs`; set
  `CHIBI_DRESSUP_OFFLINE=1` to serve `dist/` statically; not in `package.json` scripts - run directly): no GLB requests on the demos
  list; loading state; exactly 10 + 1 GLB requests on mount (props 5 + body + gestures + 3 motion + worn hair); every module downloads once
  and changes the triangle count (baseline 9512 with nothing worn); hair slot exclusivity; dress hides/disables jeans; all `CLIPS`
  advance time and rotate real body joints; each gesture x hand changes only that hand's joints and clearing restores the pose;
  expression maps lazy (0 then 3 requests); localStorage restore after reload; reduced-motion pauses; 390 px no horizontal overflow;
  zh-Hans/ms labels; unmount leaves no canvas; corrupt body GLB then Retry recovers; no console errors. Writes
  `models/chibi-dressup/review/{desktop,mobile}.png` (hence the modified `desktop.png` in `git status`).

---

## 3. Motion studio (`src/chibi-motion/page.js`)

`mountMotion(root, asset, signal, options)` -> `{ dispose }`.
- Options (defaults for the GJH chibi): `titleKey`, `subtitleKey`, `clips` (default `["Idle","Wave","Nod","Walk"]`), `cameraPosition`,
  `cameraTarget`. `src/main.js` `motionDemos` supplies the Tripo variant (`tripo-chibi-motion`, clips idle/wave/nod/jump/dance/run/walk
  - note lowercase names there vs capitalised defaults; the clip lookup uses `AnimationClip.findByName` as given).
- Flow: `fetch(asset.file, {signal})` -> `GLTFLoader.parseAsync` -> one `AnimationMixer` on `gltf.scene`; builds a button per requested
  clip (throws `Missing animation X` if absent; first becomes active; label key `clip.<lowercase name>`), a play/pause button
  and a 0-1000 range slider. Selecting a clip stops the previous action, `reset().play()`, `mixer.update(0)`. The slider pauses playback and
  sets `action.time`. The render loop (`setAnimationLoop`) advances the mixer only when playing (delta clamped to 0.1 s) and always
  renders and syncs the slider/time readout.
- State: in-memory only (clip, playing). Reduced-motion starts paused.
- Disposal: `dispose()` handles partially-built state (observer, controls, mixer, geometry/skeleton/material/map disposal, renderer
  loop stop, `forceContextLoss`, canvas removal); if the signal is already aborted after the fetch it returns `{ dispose }` without
  creating a renderer. Errors during setup call `dispose()` then rethrow.
- Tests: none dedicated (no file under `tests/` or `scripts/` references `mountMotion`; it is only exercised indirectly through
  demo routing checks such as `scripts/demo-registry.mjs`). Gaps: loop renders every frame even when hidden/paused;
  `previous` time handling means the first frame after tab restore is clamped by 0.1 s only.

## 4. Viewer add-ons

### 4.1 `src/chibi-rig-controls.js` - `createChibiRigControls({ model, scene, container, invalidate })`
Toolbar with two toggles: "raise arm" (pre-multiplies `LeftArm` bone quaternion by a rotation about the parent-space Z axis, 0.32 pi,
restored from a cached rest quaternion) and "skeleton" (a `SkeletonHelper`, depth test off, in `scene`). Returns `{ reset, dispose }`;
`dispose` removes toolbar and helper and disposes skeletons of every skinned mesh. `model.getObjectByName("LeftArm")` is not null-checked
(throws on a different rig). No test. In-memory only.

### 4.2 `src/tripo-animation-preview.js` - `createAnimationPreview({ model, clips, previews, container, onPlay })`
Builds one button per `[clipName, labelKey]`; missing clip throws `Missing animation clip`. `play(clip)` stops all, plays `LoopOnce` with
clamp, and (cached per clip) samples the model at 9 times to build a `Box3` envelope of the clip's travel, then resets to t=0 and calls
`onPlay(bounds)` so the viewer re-frames the camera (`frameObject` in `viewer.js`). `update(elapsed)` advances while running (clamped
0.05 s) and returns whether still running. `reset()` and `dispose()` clear state / mixer / toolbar. No test.

### 4.3 `src/visitor-v2/demo.js` and `src/visitor-v3/demo.js` - `createVisitorDemo({ model, clips, container, invalidate })`
Near-identical files (v3 imports `../visitor-v2/style.css` and its own `customization.js`). Each builds a `<section class="visitor-v2-controls">`
with selects for appearance (via `createVisitorCustomization(model)` from `models/gjh-mall-visitor-v2/customization.js` or
`models/gjh-visitor-v3/customization.js`) and an animation select. v2 clips: idle, walk, sprint, sit, stand, pickup, place, push, elevator;
v3 clips: idle, walk, run, turn_left, turn_right, sit_down, stand_up, pick_up, carry, wave, point, push_cart. `play(name)` throws
`Visitor animation missing` for an absent clip; looping set (idle/walk/run|sprint/carry|push) is `LoopRepeat`, the rest `LoopOnce` + clamp;
`playing` is false under reduced motion (a single frame is shown via `mixer.update(0)`). `update(dt)` advances (clamped 0.05 s) and
turns off when the action pauses. `reset()` restores defaults and plays idle. `dispose()` stops mixer, `uncacheRoot`, restores materials via
`custom.dispose()`, removes the toolbar. Customization (`apply`) validates enums and throws `TypeError` for invalid values; it clones hair/brow/skin
materials per instance and toggles mesh visibility by `V3_` name prefix. The file header comment states these controls demonstrate authored clips and
cosmetics only, not mall item/cart/seat/elevator logic. Storage: none.
Known gap: the two demo files are ~95% duplicated; any fix must be applied twice. `demo.js` itself is untested.

### 4.4 `src/fish-motion.js` - `createFishMotion({ model, clips, container, invalidate })`
Plays `Swim_Loop` (or first clip; throws if none) as `LoopRepeat`. Owns a pause/play button (inline-styled, `data-fish-playback`) and a
reduced-motion `matchMedia` listener. `update()` self-times with `performance.now()` (delta clamped 0.05 s; `suspend()` zeroes the clock
after the tab is hidden); returns `playing`. `dispose()` removes listener, mixer, skeletons, toolbar. Imported statically by `viewer.js` (every
viewer pays for it), dispatched by `collectionId`. No dedicated test.

### 4.5 `src/building-loop.js` + `src/sands-water.js` - Marina Bay Sands loop
`createBuildingLoop({ model, clip, container, invalidate })`: requires `gltf.animations[0]` (the viewer passes it); builds
`createBayReflection(model)`, a looping `AnimationAction`, a play/pause button and a stage label span. Stage text comes from
`ASSET_MarinaBaySands.userData.constructionStages` (`[[startSeconds,key],...]`); `showStage(time)` mirrors the clip (forward time =
`min(t, duration - t)`) and picks the `return` label for the downward half when `0.54 <= forward < 9.2` (hardcoded constants), labels via i18n key
`sands.<key>`. Reduced motion pauses and shows the mid-clip stage. `update` runs only while the action is running, advancing the mixer, the water
phase (`reflection.sample(action.time / duration)`) and the label.
`createBayReflection(model)` (`sands-water.js`): replaces the `Bay_Surface` mesh with a `Reflector` (768x384, custom ripple shader whose `phase`
uniform is driven by the clip fraction), hides the original surface; `dispose()` removes/dispose the reflector and shows the surface again.
Both throw if the expected node names/userData are missing (`Bay_Surface`, `ASSET_MarinaBaySands`). No dedicated test; the asset is covered by
catalog validation only.

---

## 5. Cross-cutting notes

Data flow summary (dress-up): `manifest.json` -> `validateManifest` -> `loadConfig` (localStorage) -> `assetUrl` (Vite glob) -> `loadModels`
(fetch+GLTF parse) -> `bindModule` (skin remap onto body skeleton) + `createRig` (retarget Mixamo-named clips onto body bones) -> `AnimationMixer`
-> `createView` loop (`rig.update` then `props.sync`) -> `renderConfig` / `saveConfig` on every UI change.

Rig contract the bodies and modules must satisfy (enforced by thrown errors): Mixamo bone names (`mixamorigHips`, `mixamorigRightHand`,
`mixamorigLeftHand*` fingers); modules carry the same joint list as the body; the body has exactly one skeleton, expression morph targets
`expr_happy|sad|surprised`, and the 9x2 `hand_<gesture>_<side>` single-key clips; motion GLBs together carry all 14 clips.

## 6. Known gaps (from reading the code)

1. `rig.js`, `props.js`, `expression.js`, `view.js`, `page.js` have no Node unit tests; their behaviour is only covered by the Playwright script, which is not in
   `package.json` scripts or `npm test`, so it only runs when invoked by hand.
2. Module `status` (`verified`/`pending`) is validated but never read at runtime: a `pending` module would be shown to visitors (`page.js` filters by
   `fitsBody` only). Publication gating relies on process, not code.
3. `sync-chibi-dressup-modules.mjs` rebuilds each synced module object from `{id, slot, excludesSlots, label, file, status, source, bytes, sha256}`;
   it would drop `bodyIds`/`family` on a module that has them (none do today). Its `candidates` list is hardcoded and not in `package.json`;
   `models/chibi-dressup/README.md` still says "the four listed modules" while the script lists 14.
4. The manifest has no `hat` module and a single body; the multi-body code paths (`switchBody`, `modulesForBody`, per-body `sockets`) are unit-tested
   against synthetic manifests only, not against real GLBs. If the fallback `buildCharacter(previous.body)` inside `switchBody`'s catch also fails, the
   error propagates out of an event handler with no user message.
5. Default prop sockets and jar timings are constants copied from untracked `output/modular-chibi-parts/*/attachment.json` files.
6. `chibi-motion/page.js`, `chibi-rig-controls.js`, `tripo-animation-preview.js`, `fish-motion.js`, `building-loop.js`, `sands-water.js` and both visitor
   `demo.js` files have no tests; `tests/gjh-visitor-v2|v3.test.mjs` test only the exported GLB (validator, draw calls, triangles, bones, clip names,
   shoe-floor contact for locomotion clips, finite transforms) and `customization.js` (independent, reversible, rejects invalid values). `scripts/check-i18n.mjs` lists
   these files only for i18n key scanning.
7. Duplication: visitor v2/v3 demos; the three mixer-based add-ons each reimplement reduced-motion handling; `chibi-motion` and `chibi-dressup` each have their own
   renderer/dispose boilerplate.
8. `fish-motion.js` is statically imported into the main viewer bundle while every other add-on is a dynamic import.
