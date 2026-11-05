# Product requirements

Status: the searchable model library, query-addressed model detail and Interactive Demo Index are implemented in the local IA development branch. Existing Game/PWA and Solar experiences remain available. See [IA delivery](gallery-information-architecture.md) and [executed verification](verification/gallery-ia.md). Licensing and broader curated-publication requirements remain open; the initial local acceptance is distinct from the subsequent [authorized release integration](verification/gallery-ia-release.md).

## Goal and scope

Present a growing, curated collection of real Blender-created 3D works. The product is a gallery for discovery and inspection, not an online Blender editor, AI generation service or administrative system. Manual work and work made using different coding tools are equally eligible; creation method is attribution, not the product brand.

## Main journeys

1. Discover works through a responsive gallery with real covers, titles, categories, search, filtering, sorting, result count and a clear empty state.
2. Open a work in a real GLB viewer with loading and error states, rotate and zoom controls, camera reset and a fitted initial view. Support touch and provide a poster and explanation when WebGL or the asset is unavailable.
3. Read the work's description, creator and creation method, Blender version, measured size and geometry statistics, and license. Only offer source or download links when rights and files permit them.
4. Share a stable model link and return to the gallery. Preserve filters and scroll position where practical.

## MVP acceptance

- Search covers titles, descriptions, categories and tags; category, sorting and clear-filter controls work on mobile and desktop.
- Each published entry has a unique slug, validated metadata, a real validated model, a representative cover and confirmed rights. Counts are derived from the catalog.
- A direct model link works under the actual GitHub Pages base path. Unknown links, network failures and missing models show useful recovery paths.
- Non-canvas actions are keyboard accessible; touch targets and focus states are clear. A text description and poster provide an alternative to the 3D view.
- No login, API key or local Blender installation is required to view published works.

A launch collection of 12 validated works is a proposed target, not a completed count or a fixed commitment. Favorites, expanded discovery and additional collections remain possible later work. The delivered Game/PWA scope and its limits are documented separately.
