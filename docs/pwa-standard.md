# PWA Product Standard contract

## Source and scope

This contract applies KB `pwa:product-standard` to Blender 3D Gallery. The November 18 amendment applies the `IMMERSIVE_3D` profile in v1.1.0 and KB `pwa:sw-install-integrity` v0.2.0 for deployment recovery. The owner retained commit, merge and push authorization.

Retain Editorial Moss as the default, preserve gallery assets and original sources, query routes, Game rules, checkpoint schema and reliability guards.

## Product decisions

- The palette picker supports dark and light palettes. The saved choice sets the document color scheme and theme-color meta on startup and updates both on selection.
- English, 简体中文 and Bahasa Melayu localize the in-app shell and install, update and offline prompts. The gallery restores its saved language before first paint. See [Interface languages](i18n.md).
- Preserve manifest identity `./`, scope `./`, start URL `./?page=game`, relative to the manifest under `/Blender-3D-Gallery/`.
- Installation help distinguishes installation from explicit offline Game preparation.
- Gallery, the Interactive Demos index and About use a sticky topbar. Past 80 px it hides after 8 px of downward travel, and 8 px of upward travel reveals it. Focus inside the bar or an open dialog reveals it. Transform-only movement keeps its layout space reserved. The safe area stays clear, and reduced motion removes the transition. Long index pages also provide contextual scroll-to-top.
- Game and every interactive demo route, including Tripo Chibi Motion Studio, keep the topbar in normal flow so it cannot cover canvas controls. The gallery model viewer uses a native top-layer dialog and browser fullscreen for its canvas.
- Actual iOS/Android installation, system chrome, keyboard and GPU results remain UNVERIFIED without physical-device evidence. Headless WebKit and simulated safe areas do not certify those surfaces.

## Offline contract

| Content | Guaranteed scope |
| --- | --- |
| HTML/scripts/CSS/icons/registry metadata | Available after successful shell preparation; first-ever launch requires network |
| Game | Offline after explicit successful preparation of all required verified GLBs, currently 18. Compatible checkpoints can resume. |
| Gallery posters/arbitrary GLBs | Not guaranteed offline; absent resources show truthful fallback/recovery |
| Solar System | Online GLB loading; excluded from Game pack |
| Original Blender files | Not downloaded by installation or Game preparation |

A Game-cached model does not imply full-library offline availability. The runtime's verified pack state owns readiness; connectivity, pack status and update stage are separate facts. Tabs broadcast only a cache-change signal; each tab independently checks its own active build before reporting readiness. A failed initial worker installation can be retried from Game options without reloading.

## Updating and cache lifecycle

Only explicit Update may activate a waiting worker and reload. Discovery shows availability while preserving current work. Show immediate branded accessible loading feedback; validate/save a stable Game turn, confirm scoped tabs are ready, activate and reload once after controller change. Refuse active shots, busy transactions or failed saves. The user cannot start another shot after the saved update checkpoint while activation is pending.

The topbar and mobile Menu show the semantic version injected from `package.json`. A waiting worker enables the same explicit Update action in both locations and the bottom notice remains available. The target version is shown when a no-store `build-info.json` response matches the waiting worker's build ID. Narrow topbars use the compact visible “Update” label and the full accessible label; the mobile Menu shows the full label.

Prevent duplicate requests and handle native dialog top-layer/focus correctly. Denial, failure or timeout restores interaction and offers retry. Late callbacks cannot cause another reload or reopen dismissed UI. Clean up timers/message ports after settlement.

Preserve build identity, scoped versioned caches, byte/hash validation and candidate publication. Failed candidates preserve known-good resources. Cached navigation deliberately serves one complete HTML build while an update waits; do not independently replace that with network-first navigation.

When a shell entry is missing from CacheStorage, the worker verifies the replacement against its own manifest or returns 503. Gallery GLBs are fetched on demand by their immutable URLs. If a deployment removes an older URL, the owning tab checks for an update after a failed chunk or GLB request. Unknown query routes check too. Checks are throttled and share the same update UI. A verified waiting update adds an inline action on an unknown route or failed experience. With no verified update, the ordinary fallback and retry remain available.

Retain old tabs' dependencies and prior good packs. Complete scoped caches are deliberately retained, including after tabs close: this implementation has no durable proof that a suspended client or the last complete Game pack is unused. Automatic complete-build eviction is an explicit exception. Failed shell candidates and temporary pack candidates are deleted; other projects' caches remain untouched. Storage may grow across versions and browser quota is not guaranteed. Clearing site storage removes offline resources and local saved matches, so it is not an automatic recovery step. A future eviction policy needs durable build/client ownership and pack migration evidence.

### One-time legacy-client migration

The previously deployed client lacks the new update-lock/deadline protocol. A new worker must refuse unsafe legacy acknowledgments and provide a save/close/reopen instruction. Finish the shot, save a stable turn, close every gallery tab or installed window, then reopen online so the waiting worker can activate without live old clients. Compatible IndexedDB saves remain; do not clear site data. The immediate branded loader and locked multi-tab update contract applies once clients run this amendment.

## Layout, chrome and security

Shared four-edge safe-area properties have zero fallback. Each edge has an owning container to avoid duplicate padding. Cover shell, menu, viewer, installation/game/update dialogs, notices, fullscreen and floating navigation. Preserve supported short Game viewport bounds and44px primary targets. Mobile text-entry controls are at least16px; page zoom remains available.

The manifest keeps opaque Editorial Moss theme and launch colors. The document theme-color follows the selected palette when the browser honors it. Apple standalone mode still requests the opaque black status bar. Startup splash and system chrome for light and dark palettes remain UNVERIFIED on physical iOS and Android devices. Validate current icon dimensions/maskable crop before changing artwork.

Production uses HTTPS and a minimal tested resource policy. Permit actual same-origin scripts/workers/models and necessary embedded texture schemes; the Vite development server removes the tagged CSP meta only for injected development CSS/HMR; production builds and preview retain it. The style policy permits two exact SHA-256 hashes for the built-in browser annotation overlay and cursor styles, observed on 2026-11-14. The build adds separate exact SHA-256 script hashes for the palette and language bootstraps. See [the color system](design.md#persistence-and-first-paint) for its initialization and storage contract. All other inline script and style sources remain blocked. Browser updates may change those styles; if annotation stops working, reproduce on a production-policy page and update the hashes only after checking the new injected styles. Meta CSP does not provide every HTTP-header capability. Preserve registry/GLB URI checks and keep secrets/private content out of caches.

## Standard acceptance matrix

| Check | Baseline | Required evidence |
| --- | --- | --- |
| iOS/status bar | Default Apple mode; physical unverified | Intentional opaque setting; separate real-device status |
| Safe areas | Partial | Four-edge menu/dialog/viewport checks; device scope disclosed |
| Manifest/install | Configured | Stable identity/scope/start/icons; device installation separately reported |
| Offline contract | Prepared Game passes prior9 tests | Truthful UI, cold launch, recovery, no full-library promise |
| SW versions | Scoped/hash verified | N to N+1, retention/cleanup, project isolation |
| Update prompt | Explicit existing | Waiting worker, user action, no forced reload on discovery |
| Update loader | Text/disabled actions | Immediate loading surface, safe interaction, failure recovery, one reload |
| Responsive | Prior7 sizes pass | Preserve7 index sizes plus short Game/nonzero insets |
| Accessibility | Existing keyboard/axe/targets | New UI focus, announcements, targets, reduced motion |
| Smart topbar | Nonpersistent header | Sticky hide and reveal, focus and modal reveal, reduced motion, safe areas, version and update action. Static on immersive routes |
| Scroll-to-top | Missing | Contextual, safe-area/modal/route aware, keyboard usable |
| Theme chrome | Selectable light and dark palettes | Document metadata and first-paint restoration in browser; physical system chrome UNVERIFIED |
| Language | English default, two selectable locales | Localized document title and app UI, first-paint restoration, same-origin tab sync and responsive picker |
| Security/privacy | HTTPS/scoped cache; CSP absent | Production CSP positive/negative checks; preserved privacy boundaries |

## Completion

Actual evidence belongs in `pwa-verification.md`. Every applicable MUST needs execution evidence or a concrete exception. Use PASS, FAIL, N/A and UNVERIFIED. Code/browser completion with a physical-device checklist must not be described as physically verified iOS compliance. Record revision/build, command results, screenshot scope and verified remote/live identities.
