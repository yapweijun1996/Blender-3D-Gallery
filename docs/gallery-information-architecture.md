# Models and Interactive Demos

## Ownership and delivery

The implementation remains Vite and native JavaScript. `models/catalog.json` is the authoritative model registry; `data/demos.json` is the demo registry. No database, external registry service or new runtime framework is required. Per-asset Solar metadata remains authoritative for physical facts, attributions and rights. GLBs and Blender sources are not transformed by this change.

The primary navigation is **3D Models**, **Interactive Demos**, **About**, **GitHub**. Models are individual inspectable files; demos combine assets into experiences. The Demo Index is a static poster grid and does not mount its registered experiences. New demos do not add top-level navigation items.

The original dark editorial identity is preserved: near-black background, warm text, muted green, Georgia display headings, original brand, compact labels and thin dividers. Search, filters and the mobile menu reuse that visual language.

## Static-host route compatibility

All URLs below are relative to `/Blender-3D-Gallery/`. Query routes work on GitHub Pages without server rewrites. Independent model detail uses the existing shareable query-addressed dialog; it is not a new physical HTML file.

| URL | Current destination | Compatibility |
| --- | --- | --- |
| `./` | Models landing and library | Existing root retained |
| `?page=gallery` | Models landing | Existing route alias retained |
| `?page=models` | Models landing and library | New canonical model index route |
| `?page=about` | Dedicated About page | New canonical About route; old fragment remains valid |
| `#collection` | Model library section | Existing fragment retained |
| `#about` | About section | Existing fragment retained |
| `?model=<id>` | One model's metadata and independently loaded viewer | All 39 existing identities retained |
| `?page=demos` | Interactive Demo Index | New canonical demo discovery page |
| `?page=game` | Existing casual eight-ball | Existing launch, refresh, save and PWA links retained |
| `?page=solar` | Existing Solar System | Existing launch and direct links retained |

The runtime uses query navigation with history entries. Back/forward must restore the selected page and model view. Search and filter ownership belongs to each static index, independently of the active 3D renderer. Model filters use `q`, `category` and `collection`; Demo filters use `dq` and `dc`. URL parameters preserve each index state across viewers, navigation and refresh. Leaving a demo aborts pending loading and disposes its renderer through the existing lifecycle interface. The Game's existing leave/save confirmation remains authoritative; a navigation control cannot bypass it.

## Registry contract

The model registry requires unique collection and asset IDs/slugs, nonempty names/categories, and existing contained `models/` file references. Missing slugs default to IDs; missing tags default to an empty array. Optional malformed types reject validation. Category text normalizes surrounding/repeated whitespace. Real file paths are checked to reject references escaping the model directory, including symlinks. Existing asset identity and path order remain unchanged.

Build-time metadata reads actual GLBs: format, bytes, triangle count, stored vertex count, material count and embedded animation count. Stored vertices count each referenced POSITION accessor once, rather than multiplying instances. Zero embedded animations does not imply the web demo is static: orbital movement and gameplay belong to JavaScript. Missing license terms are disclosed; existing downloads remain available without granting new redistribution rights.

Demo entries have unique IDs/slugs, title, category, description, tags, technologies, availability status, a catalog thumbnail identity and an explicit allowlisted launch route. `virtual:gallery-demos` resolves posters through Vite, as the existing model virtual catalog does for asset URLs. JSON values are content, not executable modules. DOM text uses text nodes/textContent rather than interpreting registry HTML.

To add a model: retain source/provenance, add a catalog entry and standalone GLB/poster, validate rights and run tests/build. To add a demo: add registry content, implement an explicit lazy module branch and its lifecycle interface, extend the route allowlist, and test direct links plus disposal. Do not turn registry strings into arbitrary imports or evaluate code from JSON.

## Rendering and cache boundaries

- Static indexes load posters and metadata; no GLB downloads or WebGL contexts are needed for their cards.
- A selected model activates one lazy viewer. Game and Solar activate only on their routes.
- Existing output color space, Solar tone mapping, lights and material properties are retained; there is no speculative exposure adjustment or asset recompression.
- The viewer must dispose geometry, materials, textures, controls, observer and renderer when dismissed or replaced. Hidden/inactive render work is checked separately from visual correctness.
- PWA shell caching and the explicitly prepared 18-GLB Game pack retain their existing scope. The Solar demo is online-only. Installing the app does not imply every gallery model is offline.

## Verification and limits

See [baseline](gallery-ia-baseline.md) and [executed verification](verification/gallery-ia.md). Local browser software rendering is not a physical mobile GPU benchmark. Automated accessibility checks are evidence for the checked rules and states, not full WCAG certification. Production performance and real installed-device behavior require separate observation; this task does not publish a release.
