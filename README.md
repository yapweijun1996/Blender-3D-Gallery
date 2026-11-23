# Blender 3D Gallery

A public, interactive gallery for real 3D models made in Blender, with a local two-player eight-ball game. Artists may create models manually or with any suitable tool, including coding agents. The gallery is tool-neutral and focuses on discovering and viewing artwork.

The repository contains an initial static gallery and one original billiards asset pack. A GitHub Actions workflow builds and deploys the site to GitHub Pages on pushes to `main`. The model library and Interactive Demo Index use local build-time registries with search and category filters.

## Visitor experience

- Browse a curated gallery, search and filter works, and open a shareable model page.
- Inspect a real 3D model with rotation, zoom and reset controls, with an accessible fallback when 3D is unavailable.
- See each work's description, attribution, license and measured asset information. Offer downloads only when the files and rights allow them.
- Use the gallery on desktop and mobile without an account, Blender installation or API key.

The gallery is not an online model editor, model-generation service, marketplace or admin dashboard.

## Project documentation

- [Product requirements](docs/product.md): scope, visitor journeys and acceptance criteria.
- [Architecture](docs/architecture.md): proposed stack, content flow and deployment boundaries.
- [Design and accessibility](docs/design.md): responsive layout and interaction requirements.
- [3D asset standard](docs/assets.md): model metadata, provenance and validation.
- [Blender engineering knowledge](docs/blender/README.md): source-backed authoring guidance, extension research, native calibration and the `blender` KB mirror.
- [P0 Blender extensions](docs/blender/p0-extensions.md): installed versions, verified Python calls, context requirements and reproducible evidence.
- [Shopping Mall geometry and texel-density QA](docs/model-qa/shopping-mall-2026-11-15/README.md): read-only source/export measurements, review findings and per-object CSV evidence.
- [Quality and release](docs/quality.md): test matrix, candidate budgets and release evidence.
- [Roadmap and decisions](docs/roadmap.md): milestones, open decisions and status.
- [Game implementation and delivery](docs/game-implementation-plan.md): game rules, architecture, controls, saved turns and offline/update contract.
- [PWA Product Standard](docs/pwa-standard.md) and [PWA verification](docs/pwa-verification.md): safe areas, explicit updates, offline scope, security policy and device limits.
- [Game verification](docs/game-verification.md): executed checks, artifact paths and hardware limits.
- [Models and demos architecture](docs/gallery-information-architecture.md): registries, query routes and legacy compatibility.
- [IA verification](docs/verification/gallery-ia.md): local baseline, browser evidence and limits.
- [Game audit](docs/audits/game-baseline.md) and [gameplay contract](docs/game/gameplay-contract.md): baseline findings, current interaction boundaries and links to this review's release evidence.
- [Agent guidance](AGENTS.md): repository-specific working rules.

## Status

The gallery presents 21 individual billiards assets and an optional complete scene, each with an interactive viewer and individual GLB download. The Game page adds Casual Eight-Ball for two people sharing one device, automatic stable-turn saves and an explicitly prepared offline PWA game pack. The model library groups all current collections and supports search, category and collection filters. Interactive Demos lists the Game and Solar System experiences behind one navigation destination. The asset pack is original, and redistribution terms have not yet been specified.

## Develop and deploy

Use Node.js 24, then run `npm ci`, `npm run dev`, or `npm run build`. Vite produces `dist/` with relative asset paths suitable for a GitHub Pages project site. The `Build and deploy gallery` workflow runs on every push to `main` and can also be started manually. It initially checks out the application, scripts and catalog, then selects the exact catalog resources and model files referenced by runtime imports and Vite globs. An exact cache key derived from the selected Git blob IDs restores `dist/` when the site inputs are unchanged. Cache misses download only selected models, install locked dependencies and run `npm run build:deploy` (Vite). A separate verification job checks out the full repository and runs `npm test`, `npm run test:world`, and `npm run validate:assets` before the build and Pages publication job, including on cache hits. The input selector is `scripts/deployment-inputs.mjs`; every new deployment is derived from the current catalog and imports. New pushes cancel superseded runs. The manual workflow input `validate_assets` forces a fresh site build; asset validation runs for every deployment. Local `npm run build` continues to include full asset validation. Browser regression tests (see the testing paragraph below) are not run in CI; run applicable checks locally before pushing to `main`. Check the Actions run and published URL before treating a release as successful. The gallery build includes the individual GLBs, full-scene GLB and thumbnail images; the editable `.blend` remains in the repository. Asset names and paths are maintained in `models/catalog.json`. Build-time metadata is calculated directly from the GLBs; `npm run validate:assets` validates each file using Khronos glTF Validator and checks its expected root. Add assets to the catalog with a matching standalone GLB and thumbnail.

To roll back, revert the problematic commit on `main` and let the same workflow deploy the restored build.

[Fast deployment contract](docs/deployment.md) · [Maintenance tool contracts](docs/tools.md) · [Work closeout, 2026-11-18](docs/2026-11-18-closeout.md)

## Play and test

Open **Interactive Demos → Game** or `?page=game`, start a two-player match, drag the cue ball to a legal position, aim, then pull the left handle down and release. The handle also supports keyboard charging with arrows and release with Space/Enter. See Rules & controls for the casual ruleset. App options contains installation help and Make available offline; install alone does not download the game pack.

After `npm run build`, run `npx playwright install --with-deps chromium webkit`, `npm run test:browser`, `npm run test:pwa`, `npm run test:library`, `npm run test:standard` and `npm run test:reviewed`. Run `npm run test:game-ux` for inspection, touch and keyboard interactions, and `npm run test:game-responsive` for viewport and safe-area layout coverage. Each game test independently serves the existing production build. Browser artifacts are written to `/tmp/` by default. Real-device installation and performance checks are recorded as limits in the verification document.

## Solar System collection

A second collection adds 17 independent Blender-generated Solar System assets and an optional `?page=solar` demonstration. Each original asset retains a packed `.blend`, standalone `.glb`, preview, metadata and reproducible generator. The demo uses 14 NASA-sourced models (including Vesta, Eros and Tempel 1) and three original fictional asteroid models. NASA model credits and limitations appear when each body is selected; the original models remain available in the gallery. The demo includes selection, time speed, illustrative orbit/spin animation, two scale modes and a Three.js comet tail. The demo loads approximately 12.8 MB of optimized GLBs online (down from 77 MB); the existing prepared offline pack continues to cover Game only.

See [asset inventory, validation and scientific limitations](models/solar-system/reports/REPORT.md). Run `npm run test:library` for discovery/navigation regressions and `npm run test:solar` for independent Khronos/Three.js checks and `node scripts/test-solar-scene.mjs` for production-subpath scene checks. Physical mobile testing and separate artwork redistribution terms remain pending. Solar System publication was authorized on 2026-11-04; use the successful Pages workflow for the corresponding `main` commit as deployment evidence.

## GJH Mall Furniture collection

Two original, metre-scale models add a lounge bench and an areca-inspired planter for reuse in the owner's GJH virtual mall. Each has an editable Blender source, deterministic generator, self-contained GLB, lightweight preview and measured provenance. The combined GLBs are 354,048 bytes; repeated placements can share their geometry and materials. See [authoring, reuse and rights](models/gjh-mall-furniture/README.md) and [verification](models/gjh-mall-furniture/verification.md). Run `node scripts/test-gjh-furniture.mjs` after building to exercise both actual models at desktop, tablet and mobile sizes. Public redistribution terms remain unspecified and gallery download buttons are disabled for this collection.

## Chibi character standard

The [chibi character standard](docs/chibi-character-standard.md) (draft) defines the shared style, budgets, rig and quality gate for chibi characters; the [Mall Guide v5 plan](docs/chibi-mall-guide-v5/plan.md) is its first application. Both are proposals: no v5 model exists yet.

## GJH mall visitor

The [GJH Mall Visitor collection](models/gjh-mall-visitor/README.md) adds an original reference-led rounded mascot with editable Blender source and self-contained idle/walk/sprint animation. The gallery viewer presents the model at rest; the consuming GJH V11 mall plays its animation clips. Actual geometry, animation/contact checks and provenance are recorded beside the source. Run `node models/gjh-mall-visitor/validate.mjs` and, after a build, `node scripts/test-gjh-visitor.mjs` for focused verification. Public artwork redistribution terms remain unspecified.
