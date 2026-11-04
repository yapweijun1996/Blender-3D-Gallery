# Blender 3D Gallery

A planned public, interactive gallery for real 3D models made in Blender. Artists may create models manually or with any suitable tool, including coding agents. The gallery is tool-neutral and focuses on discovering and viewing artwork.

The repository contains an initial static gallery and one original billiards asset pack. A GitHub Actions workflow builds and deploys the site to GitHub Pages on pushes to `main`. The broader product specifications remain proposals.

## Proposed visitor experience

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
- [Agent guidance](AGENTS.md): repository-specific working rules.

## Status

The gallery presents 21 individual billiards assets and an optional complete scene, each with an interactive viewer and individual GLB download. The broader specifications are a v1.0 candidate; a full searchable catalog, PWA and additional collections are future work. The asset pack is original, and redistribution terms have not yet been specified.

## Develop and deploy

Use Node.js 24, then run `npm ci`, `npm run dev`, or `npm run build`. Vite produces `dist/` with relative asset paths suitable for a GitHub Pages project site. The `Build and deploy gallery` workflow runs on every push to `main` and can also be started manually. It builds with `npm ci` and deploys the `dist/` artifact to the `github-pages` environment. Check the Actions run and published URL before treating a release as successful. The gallery build includes the individual GLBs, full-scene GLB and thumbnail images; the editable `.blend` remains in the repository. Asset names and paths are maintained in `models/catalog.json`. Build-time metadata is calculated directly from the GLBs; `npm run validate:assets` validates each file using Khronos glTF Validator and checks its expected root. Add assets to the catalog with a matching standalone GLB and thumbnail.

To roll back, revert the problematic commit on `main` and let the same workflow deploy the restored build.
