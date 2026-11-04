# Proposed architecture

Status: v1.0 candidate; no application or deployment is implied.

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
