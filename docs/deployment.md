# Fast GitHub Pages deployment

The implemented pipeline is [deploy.yml](../.github/workflows/deploy.yml). It runs on main pushes and manual dispatch. New pushes cancel superseded runs. A required verification job installs locked dependencies and chooses the narrowly scoped static-model checks or the complete suite. The build job requires verification to pass, including on a site cache hit. A separate job publishes the uploaded build to Pages. Node.js 24 and the lockfile define its JavaScript toolchain.

## Inputs and cache

The initial checkout contains the app, scripts and catalog while excluding model trees, docs, tests and local output. [The selector](../scripts/deployment-inputs.mjs) reads the Git index and catalog, includes catalog GLBs/posters/metadata, and follows literal model references and Vite model globs. It writes non-cone checkout patterns to `/tmp/gallery-deployment-patterns`.

The selector's cache key hashes the selected paths and indexed Git blob IDs. It is a committed-input identity. Stage intended changes before local key checks. The selector rejects tracked symbolic links and references to missing catalog files. Its literal dependency scan is bounded. A production build remains the check for completeness when code starts using a new dependency pattern.

In the build job, an exact `dist/` cache hit skips model downloads, npm installation and Vite. A miss downloads selected model files, runs `npm ci --no-audit --no-fund`, then `npm run build:deploy`. The existing manual `validate_assets=true` input still forces a fresh deployment build. All manual runs use the full verification suite. Local `npm run build` retains full validation.

## Verification modes

The initial verification checkout is sparse. Fast verification is possible only for a non-forced main push whose exact single parent is proved green by the repository's public Actions run record. The record is read anonymously with a short timeout; a missing or inaccessible record, failure, cancellation, rate limit or ambiguous commit falls back to full verification. No token permissions are added.

The diff must be one append-only catalog collection with exactly one new static model, plus regular, non-executable files in its previously nonexistent folder. Existing catalog data and order must be unchanged. Interactive, animated, skinned, multi-model and shared code/workflow changes use the full path. The existing deployment input selector must see only the new catalog media/metadata from the new folder; authoring files are not executed.

Fast mode checks catalog/schema/category consistency, exact source/GLB/thumbnail hashes and byte counts, a static WebP container, metadata/path sanity, and the new GLB's resource containment and Khronos validation. It does not replace a focused visual/model check. Full mode expands the checkout and retains `npm test`, `npm run test:world`, and `npm run validate:assets`. In both modes Pages still requires successful verification and the unchanged exact-input building, upload and deployment steps.

## Observed evidence

The minimal input selection reduced the measured uncompressed tracked checkout from 3,956,414,739 to 592,142,848 bytes, about 85%. The sparse and prior checkout produced 1,375 identical output files, including service-worker and PWA build hashes. These are measurements of that repository snapshot.

- [Cold deployment 44116543957](https://github.com/yapweijun1996/Blender-3D-Gallery/actions/runs/44116543957) succeeded in approximately 2 minutes 17 seconds.
- [Identical-input deployment 44117134618](https://github.com/yapweijun1996/Blender-3D-Gallery/actions/runs/44117134618) succeeded in 35 seconds and skipped model downloads, npm installation and build.
- [Compression batch 02 deployment 44121744672](https://github.com/yapweijun1996/Blender-3D-Gallery/actions/runs/44121744672) succeeded and its public build and nine GLB hashes matched the tested artifacts.

These historical timings predate the required full-checkout verification job; they do not measure the current workflow. Timings vary with runner availability, payload and hosting. The later compression batches further reduced the selected model bytes.

## Diagnose and verify

Check the actual main SHA, Actions steps and `build-info.json`. For an asset change, compare public GLB hashes with the tested files. Site publication and asset validation are separate observations. Use the [project Skill](../.agents/skills/gallery-fast-deploy/SKILL.md) when modifying the selector or cache.

The build job names the upload with its run ID and attempt number. After the upload succeeds, the pinned Pages action uses the Actions artifact service to resolve that unique name within the workflow run. An earlier anonymous REST preflight received HTTP 403 on all twelve requests even though the upload succeeded in [run 45227371662](https://github.com/yapweijun1996/Blender-3D-Gallery/actions/runs/45227371662). A failed publication can be retried on the same upload. If the upload has expired after its one-day retention period, rerun the whole workflow to produce a fresh, separately named upload. In [run 45210822388](https://github.com/yapweijun1996/Blender-3D-Gallery/actions/runs/45210822388), the earlier single-job workflow found zero artifacts immediately after upload. Its retry found two artifacts with the same name.

An installed PWA can still show an older cached index after a release. In the observed check, an old asset URL returned 404. Using the visible Update now action loaded the new index and the hash-matched model. Use that update flow before judging the latest public artifact.
