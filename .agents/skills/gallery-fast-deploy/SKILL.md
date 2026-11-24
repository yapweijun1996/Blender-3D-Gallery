---
name: gallery-fast-deploy
description: Maintain or diagnose Blender-3D-Gallery's minimal GitHub Pages checkout and exact-input build cache. Use when deployment downloads, cache invalidation or Pages publication need work.
---

# Fast gallery deployment

The workflow and selector are owned by `.github/workflows/deploy.yml` and `scripts/deployment-inputs.mjs`. Read [the deployment contract](../../../docs/deployment.md) for the implemented flow and measured evidence.

1. Inspect current main, remote and user changes. Use an isolated checkout when work overlaps. Existing user publication authorization governs pushing.
2. Start from the small application checkout plus `models/catalog.json`. Run the selector with Node 24 from the repository root. It uses the current Git index to identify model files, literal runtime dependencies and Vite model globs.
3. Stage intended file changes before measuring a cache key. The key uses indexed Git blob IDs. It represents committed inputs and does not fingerprint arbitrary unstaged content.
4. Require the verification job to pass before publishing. It runs the full-checkout `npm test`, `npm run test:world` and `npm run validate:assets` unless an exact green-based, single static model append passes the focused gate. Manual and ambiguous pushes always use the full gate. The deployment job restores only the exact site cache key. On a miss, apply the generated non-cone sparse patterns, install locked dependencies and run `npm run build:deploy`. The manual `validate_assets` input forces a fresh build.
5. Verify a sparse build against the normal build after dependency-selection changes. Compare every emitted file hash, including PWA build-info and the service worker. For cache changes, observe a successful cold run and a hit that skips the deployment job's model downloads, installation and build.
6. Verify the remote commit, Actions result and live build identifier. Keep deploy cancellation separate from a build failure. A new main push may intentionally replace a running deployment.
7. On a missing artifact after a successful upload, inspect both upload finalization and deploy metadata lookup. One observed run failed at that lookup. Establish the actual failure before changing source, cache or workflow behavior.

Only call a deployment complete when the intended run succeeds and the public build matches. Document physical-device, visual and runtime coverage separately from workflow success.
