# Fast GitHub Pages deployment

The implemented pipeline is [deploy.yml](../.github/workflows/deploy.yml). It runs on main pushes and manual dispatch. New pushes cancel superseded runs. A verification job checks out the complete repository, installs the locked dependencies, and runs `npm test`, `npm run test:world`, and `npm run validate:assets`. The site build and publication job requires that job to pass, including on a site cache hit. Node.js 24 and the lockfile define its JavaScript toolchain.

## Inputs and cache

The initial checkout contains the app, scripts and catalog while excluding model trees, docs, tests and local output. [The selector](../scripts/deployment-inputs.mjs) reads the Git index and catalog, includes catalog GLBs/posters/metadata, and follows literal model references and Vite model globs. It writes non-cone checkout patterns to `/tmp/gallery-deployment-patterns`.

The selector's cache key hashes the selected paths and indexed Git blob IDs. It is a committed-input identity. Stage intended changes before local key checks. The selector rejects tracked symbolic links and references to missing catalog files. Its literal dependency scan is bounded. A production build remains the check for completeness when code starts using a new dependency pattern.

In the deployment job, an exact `dist/` cache hit skips model downloads, npm installation and Vite. A miss downloads selected model files, runs `npm ci --no-audit --no-fund`, then `npm run build:deploy`. The separate verification job always downloads the complete tracked repository and runs all three gates; this increases deployment time and transfer even when the site cache hits. The existing manual `validate_assets=true` input still forces a fresh deployment build, while asset validation now runs for every deployment. Local `npm run build` also retains full validation.

## Observed evidence

The minimal input selection reduced the measured uncompressed tracked checkout from 3,956,414,739 to 592,142,848 bytes, about 85%. The sparse and prior checkout produced 1,375 identical output files, including service-worker and PWA build hashes. These are measurements of that repository snapshot.

- [Cold deployment 44116543957](https://github.com/yapweijun1996/Blender-3D-Gallery/actions/runs/44116543957) succeeded in approximately 2 minutes 17 seconds.
- [Identical-input deployment 44117134618](https://github.com/yapweijun1996/Blender-3D-Gallery/actions/runs/44117134618) succeeded in 35 seconds and skipped model downloads, npm installation and build.
- [Compression batch 02 deployment 44121744672](https://github.com/yapweijun1996/Blender-3D-Gallery/actions/runs/44121744672) succeeded and its public build and nine GLB hashes matched the tested artifacts.

These historical timings predate the required full-checkout verification job; they do not measure the current workflow. Timings vary with runner availability, payload and hosting. The later compression batches further reduced the selected model bytes.

## Diagnose and verify

Check the actual main SHA, Actions steps and `build-info.json`. For an asset change, compare public GLB hashes with the tested files. Site publication and asset validation are separate observations. Use the [project Skill](../.agents/skills/gallery-fast-deploy/SKILL.md) when modifying the selector or cache.

One earlier run successfully finalized an uploaded Pages artifact, then the deployment metadata lookup returned zero artifacts. A later run succeeded. That observation does not establish a source-build defect. Inspect upload and deployment evidence before choosing a retry or a code change.

An installed PWA can still show an older cached index after a release. In the observed check, an old asset URL returned 404. Using the visible Update now action loaded the new index and the hash-matched model. Use that update flow before judging the latest public artifact.
