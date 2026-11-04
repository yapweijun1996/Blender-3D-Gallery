# Blender 3D Gallery

A planned public, interactive gallery for real 3D models made in Blender. Artists may create models manually or with any suitable tool, including coding agents. The gallery is tool-neutral and focuses on discovering and viewing artwork.

This repository currently contains project documentation only. The application, model catalog, assets, CI and deployment described below are proposals, not evidence of an existing implementation or release.

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

The specifications are a v1.0 candidate, not a claim of deployment or a substitute for implementation evidence. Decisions such as licensing, final visual direction, supported versions, performance budgets and release scope still require confirmation or measurement. There are no build or run instructions until an application exists.
