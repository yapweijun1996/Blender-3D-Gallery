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

Use Node.js 24, then run `npm ci`, `npm run dev`, or `npm run build`. Vite produces `dist/` with relative asset paths suitable for a GitHub Pages project site. The `Build and deploy gallery` workflow runs on every push to `main` and can also be started manually. It installs with `npm ci`, runs unit/asset/build checks and Chromium/WebKit game, PWA, model-library, PWA-standard, reviewed-bug, game usability and responsive regression tests, then deploys the `dist/` artifact to the `github-pages` environment. Check the Actions run and published URL before treating a release as successful. The gallery build includes the individual GLBs, full-scene GLB and thumbnail images; the editable `.blend` remains in the repository. Asset names and paths are maintained in `models/catalog.json`. Build-time metadata is calculated directly from the GLBs; `npm run validate:assets` validates each file using Khronos glTF Validator and checks its expected root. Add assets to the catalog with a matching standalone GLB and thumbnail.

To roll back, revert the problematic commit on `main` and let the same workflow deploy the restored build.

## Play and test

Open **Interactive Demos → Game** or `?page=game`, start a two-player match, place the cue ball, aim and press Shoot. See Rules & controls for the casual ruleset. App options contains installation help and Make available offline; install alone does not download the game pack.

After `npm run build`, run `npx playwright install --with-deps chromium webkit`, `npm run test:browser`, `npm run test:pwa`, `npm run test:library`, `npm run test:standard` and `npm run test:reviewed`. Run `npm run test:game-ux` for inspection, touch and keyboard interactions, and `npm run test:game-responsive` for viewport and safe-area layout coverage. Each game test independently serves the existing production build. Browser artifacts are written to `/tmp/` by default. Real-device installation and performance checks are recorded as limits in the verification document.

## Solar System collection

A second collection adds 17 independent Blender-generated Solar System assets and an optional `?page=solar` demonstration. Each asset retains a packed `.blend`, standalone `.glb`, preview, metadata and reproducible generator. The demo includes selection, time speed, orbit/spin animation, two scale modes and a Three.js comet tail. It requires online asset loading; the existing prepared offline pack continues to cover Game only.

See [asset inventory, validation and scientific limitations](models/solar-system/reports/REPORT.md). Run `npm run test:library` for discovery/navigation regressions and `npm run test:solar` for independent Khronos/Three.js checks and `node scripts/test-solar-scene.mjs` for production-subpath scene checks. Physical mobile testing and separate artwork redistribution terms remain pending. Solar System publication was authorized on 2026-11-04; use the successful Pages workflow for the corresponding `main` commit as deployment evidence.
