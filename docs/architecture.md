# Proposed architecture

Status: the broader architecture remains a v1.0 candidate. The initial implementation is a Vite and vanilla JavaScript gallery with a lazily loaded Three.js viewer, a data-driven collection of individual GLBs and an optional complete scene, and a GitHub Pages Actions workflow. The local model/demo discovery architecture and legacy URL compatibility are described in [Models and Interactive Demos](gallery-information-architecture.md). The implemented Game/PWA boundaries are described in [game implementation](game-implementation-plan.md). It does not implement the proposed React migration or all capabilities below. `models/catalog.json` owns asset identities and paths; the Vite catalog plugin reads sizes and triangle counts from each GLB at build time and resolves URLs through Vite.

## Boundaries and data flow

A trusted local author creates a model in Blender, retains its source and reproducibility details where practical, exports GLB and representative images, and validates geometry, materials and rights. Reviewed metadata and assets form a versioned catalog. A static website displays posters in the gallery and loads a selected GLB on demand. The public site does not execute Blender scripts or contain API secrets.

The proposed stack is React, strict TypeScript and Vite, with Three.js / React Three Fiber for the viewer and a build-time JSON catalog. Pin mutually compatible versions and verify them during implementation. No runtime database or backend is planned for the initial read-only gallery.

## Viewer and routing

- Use static posters for cards and instantiate WebGL only for the active viewer. Fit the camera to model bounds, cap pixel ratio, release resources on exit and handle context loss.
- Use a stable slug and a query or hash link that works on static hosting, for example `?model=work-slug`. Do not assume server-side SPA rewrites.
- Resolve asset URLs against the configured Vite base path. For a GitHub Pages project site, verify the actual repository base path and direct-link behavior before release.
- Load models and images lazily where appropriate. An optional PWA may cache the shell and selected posters; it must not imply that all models are available offline.

## Proposed content layout

```text
models/<slug>/metadata.json      # authoritative model metadata
models/<slug>/generate.py        # when procedural and safe to share
models/<slug>/scene.blend        # optional; consider size and rights
public/models/<slug>/model.glb   # validated publication artifact
public/posters/<slug>.webp
public/thumbnails/<slug>.webp
```

Keep publication artifacts and original sources under intentional ownership; avoid unnecessary duplicate binaries. Model sources may need separate approved storage as the collection grows. See [asset standards](assets.md).

## Hosting and evolution

GitHub Pages is the proposed static host. Check current hosting limits, total artifact size and bandwidth before release and as the catalog grows. Adopt external storage or a backend only when measured needs and an explicit decision justify it. License code and artwork separately; a repository code license does not automatically license models.

## Implemented Solar System collection

The `solar-system` catalog collection adds 17 independent GLBs under `models/solar-system/`. Per-asset metadata JSON owns physical facts, source attribution and approximation notes; the catalog loader reads it at build time. Sources, previews, generators and measured reports are retained alongside the exports. Existing billiards paths and Game asset identities remain unchanged.

`?page=solar` lazily mounts `src/solar/page.js`. It composes 14 NASA-sourced gallery models and three original fictional asteroids with display transforms, circular orbital motion, reference metadata tilts, time controls, focus navigation, an instanced belt and a dynamic tail. `src/solar/assets.js` maps scene identities to gallery assets while retaining the solar collection’s physical reference facts. Vesta, Eros and Tempel 1 use illustrative positions and scale, not their actual orbital elements; the belt and comet tail are illustrative. Saturn is scaled using its planet diameter rather than its outer rings. Selection displays source credits and links to the corresponding gallery model. Realistic mode uses one radius/distance conversion; Presentation mode uses separate configurable display scales. Neither is an ephemeris. The demo loads separate optimized GLBs from `models/solar-demo/`, whose textures are capped at 1K and whose geometry and materials match the gallery assets. A hash-bound manifest and validation test detect stale sources; `scripts/optimize-solar-demo.mjs` regenerates them on macOS with `sips`. Full-resolution gallery models and downloads are unchanged. Paused scenes render again only after camera, viewport or view changes. Its GLBs are online-only and are not added to the Game's prepared offline pack. Leaving the route aborts pending work and releases renderer resources. Each dynamic page uses an explicit import branch so its own CSS is preloaded correctly.

See [Solar delivery and verification](../models/solar-system/reports/REPORT.md). The existing Pages workflow validates the collection and demo before publishing a `main` push. Publication was authorized on 2026-11-04; verify the workflow and actual site for each release.
