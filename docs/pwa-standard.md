# PWA Product Standard contract

## Source and scope

This contract applies KB `pwa:product-standard` v1.0.0 to Blender 3D Gallery. Implementation base: `5c8474835656d4c5fdf704185db21f3784f06c75`, isolated in `feature/pwa-standard-v1`. The owner authorized this amendment and retained commit/merge/push authorization. KB remains read-only; the original untracked local plan is excluded.

Retain the dark editorial identity, all39 assets and original sources, query routes, Game rules, checkpoint schema and reliability guards. No application framework, runtime loader library, database or asset recompression is required.

## Product decisions

- Dark-only theme remains intentional; light-theme chrome is N/A.
- Preserve manifest identity `./`, scope `./`, start URL `./?page=game`, relative to the manifest under `/Blender-3D-Gallery/`.
- Installation help distinguishes installation from explicit offline Game preparation.
- The header is nonpersistent; smart hide/reveal topbar is N/A. Long static pages receive contextual scroll-to-top instead.
- Actual iOS/Android installation, system chrome, keyboard and GPU results remain UNVERIFIED without physical-device evidence. Headless WebKit and simulated safe areas do not certify those surfaces.

## Offline contract

| Content | Guaranteed scope |
| --- | --- |
| HTML/scripts/CSS/icons/registry metadata | Available after successful shell preparation; first-ever launch requires network |
| Game | Offline after explicit successful preparation of all18 verified GLBs; compatible checkpoints can resume |
| Gallery posters/arbitrary GLBs | Not guaranteed offline; absent resources show truthful fallback/recovery |
| Solar System | Online GLB loading; excluded from Game pack |
| Original Blender files | Not downloaded by installation or Game preparation |

A Game-cached model does not imply full-library offline availability. The runtime's verified pack state owns readiness; connectivity, pack status and update stage are separate facts.

## Updating and cache lifecycle

Only explicit Update may activate a waiting worker and reload. Discovery shows availability while preserving current work. Show immediate branded accessible loading feedback; validate/save a stable Game turn, confirm scoped tabs are ready, activate and reload once after controller change. Refuse active shots, busy transactions or failed saves. The user cannot start another shot after the saved update checkpoint while activation is pending.

Prevent duplicate requests and handle native dialog top-layer/focus correctly. Denial, failure or timeout restores interaction and offers retry. Late callbacks cannot cause another reload or reopen dismissed UI. Clean up timers/message ports after settlement.

Preserve build identity, scoped versioned caches, byte/hash validation and candidate publication. Failed candidates preserve known-good resources. Cached navigation deliberately serves one complete HTML build while an update waits; do not independently replace that with network-first navigation.

Retain old tabs' dependencies and prior good packs. Complete scoped caches are deliberately retained, including after tabs close: this implementation has no durable proof that a suspended client or the last complete Game pack is unused. Automatic complete-build eviction is an explicit exception. Failed shell candidates and temporary pack candidates are deleted; other projects' caches remain untouched. Storage may grow across versions and browser quota is not guaranteed. Clearing site storage removes offline resources and local saved matches, so it is not an automatic recovery step. A future eviction policy needs durable build/client ownership and pack migration evidence.

### One-time legacy-client migration

The previously deployed client lacks the new update-lock/deadline protocol. A new worker must refuse unsafe legacy acknowledgments and provide a save/close/reopen instruction. Finish the shot, save a stable turn, close every gallery tab or installed window, then reopen online so the waiting worker can activate without live old clients. Compatible IndexedDB saves remain; do not clear site data. The immediate branded loader and locked multi-tab update contract applies once clients run this amendment.

## Layout, chrome and security

Shared four-edge safe-area properties have zero fallback. Each edge has an owning container to avoid duplicate padding. Cover shell, menu, viewer, installation/game/update dialogs, notices, fullscreen and floating navigation. Preserve supported short Game viewport bounds and44px primary targets. Mobile text-entry controls are at least16px; page zoom remains available.

Configure intentional opaque dark chrome. Actual startup appearance remains device-specific and pending. Validate current icon dimensions/maskable crop before changing artwork.

Production uses HTTPS and a minimal tested resource policy. Permit actual same-origin scripts/workers/models and necessary embedded texture schemes; The Vite development server removes the tagged CSP meta only for injected development CSS/HMR; production builds and preview retain it. Document this development exception. Meta CSP does not provide every HTTP-header capability. Preserve registry/GLB URI checks and keep secrets/private content out of caches.

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
| Smart topbar | N/A | Nonpersistent header remains N/A |
| Scroll-to-top | Missing | Contextual, safe-area/modal/route aware, keyboard usable |
| Theme chrome | Dark only | Light N/A; dark configuration and honest device status |
| Security/privacy | HTTPS/scoped cache; CSP absent | Production CSP positive/negative checks; preserved privacy boundaries |

## Completion

Actual evidence belongs in `pwa-verification.md`. Every applicable MUST needs execution evidence or a concrete exception. Use PASS, FAIL, N/A and UNVERIFIED. Code/browser completion with a physical-device checklist must not be described as physically verified iOS compliance. Record revision/build, command results, screenshot scope and verified remote/live identities.
