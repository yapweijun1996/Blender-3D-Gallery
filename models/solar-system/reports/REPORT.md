# Solar System Asset Factory — delivery report

Prepared 2026-11-04. Repository baseline: 7c92c86. Implementation branch: codex/solar-system-assets. This report records the pre-release asset and local browser verification. The owner authorized commit, push and Pages publication on 2026-11-04. Consult the Pages workflow for the corresponding `main` commit and live-site verification for release status.

## Result

17 independent, embedded-texture GLBs, 17 independent packed Blender sources, 17 metadata records, 17 Blender PNG/WebP previews, and front/reverse neutral Three.js screenshots. Total GLB bytes: 40,299,656 (40.30 MB). All are within the requested initial size targets; no size exception is required. The 39-card Gallery retains the 22 billiards entries. The optional online demo uses the independent GLBs at `?page=solar`.

## Measured asset inventory

Texture memory is an RGBA8 + full mip-chain estimate, not a device VRAM measurement. JPEG/PNG file size is not decoded texture memory. Multi-mesh double-sided rendering can issue more triangles than the logical geometry count.

| GLB | Source | Triangles | MB (decimal) | Embedded textures | Texture MiB estimate | Technical + visual |
| --- | --- | ---: | ---: | --- | ---: | --- |
| [sun](../exports/sun.glb) | [Blend](../sources/sun.blend) | 9,024 | 3.01 | 2048×1024 | 10.7 | PASS |
| [mercury](../exports/mercury.glb) | [Blend](../sources/mercury.blend) | 9,024 | 4.24 | 2048×1024, 2048×1024 | 21.3 | PASS |
| [venus](../exports/venus.glb) | [Blend](../sources/venus.blend) | 9,024 | 1.75 | 2048×1024 | 10.7 | PASS |
| [earth](../exports/earth.glb) | [Blend](../sources/earth.blend) | 22,016 | 3.71 | 1440×720, 2048×1024 | 15.9 | PASS |
| [mars](../exports/mars.glb) | [Blend](../sources/mars.blend) | 9,024 | 3.50 | 1440×720, 2048×1024 | 15.9 | PASS |
| [jupiter](../exports/jupiter.glb) | [Blend](../sources/jupiter.blend) | 9,024 | 1.67 | 2048×1024 | 10.7 | PASS |
| [saturn](../exports/saturn.glb) | [Blend](../sources/saturn.blend) | 10,560 | 1.28 | 2048×1024, 1024×4 | 10.7 | PASS |
| [uranus](../exports/uranus.glb) | [Blend](../sources/uranus.blend) | 9,024 | 0.92 | 2048×1024 | 10.7 | PASS |
| [neptune](../exports/neptune.glb) | [Blend](../sources/neptune.blend) | 9,024 | 0.62 | 2048×1024 | 10.7 | PASS |
| [moon](../exports/moon.glb) | [Blend](../sources/moon.blend) | 9,024 | 4.68 | 2048×1024, 2048×1024 | 21.3 | PASS |
| [pluto](../exports/pluto.glb) | [Blend](../sources/pluto.blend) | 9,024 | 4.27 | 2048×1024, 2048×1024 | 21.3 | PASS |
| [asteroid-01](../exports/asteroid-01.glb) | [Blend](../sources/asteroid-01.blend) | 3,968 | 1.73 | 1024×512, 1024×512 | 5.3 | PASS |
| [asteroid-02](../exports/asteroid-02.glb) | [Blend](../sources/asteroid-02.blend) | 3,968 | 1.65 | 1024×512, 1024×512 | 5.3 | PASS |
| [asteroid-03](../exports/asteroid-03.glb) | [Blend](../sources/asteroid-03.blend) | 872 | 1.71 | 1024×512, 1024×512 | 5.3 | PASS |
| [asteroid-04](../exports/asteroid-04.glb) | [Blend](../sources/asteroid-04.blend) | 9,728 | 1.95 | 1024×512, 1024×512 | 5.3 | PASS |
| [asteroid-05](../exports/asteroid-05.glb) | [Blend](../sources/asteroid-05.blend) | 3,968 | 1.81 | 1024×512, 1024×512 | 5.3 | PASS |
| [comet](../exports/comet.glb) | [Blend](../sources/comet.blend) | 3,968 | 1.78 | 1024×512, 1024×512 | 5.3 | PASS |

## Evidence and statuses

- **PASS**: Blender MCP interactive connection, Python execution, model creation, materials, rendering and GLB export. Initially Blender was not running; existing Blender and its already installed localhost bridge were started. Blender 5.1.2, Python 3.13.9, NumPy 2.3.4. No unknown extension was installed. Background MCP CLI helper was unavailable because its configured executable name was missing; creation used successful interactive MCP calls.
- **PASS, 17/17**: GLB header/version/length, Khronos glTF Validator (zero errors and warnings), embedded textures, independent GLTFLoader load, finite vertex positions/transforms/normals, unit normals, nonzero triangles, face/normal agreement, finite nonempty bounds, texture decode and color spaces. See [machine report](validation.json).
- **PASS, 17/17**: independent Blender source reopen with auto-execution disabled and no missing external image dependencies. See [source report](source-validation.json). Source inspection used the official installed Blender CLI; creation/export used MCP.
- **PASS, 17/17**: single-agent visual review of Blender and two Three.js angles. See [hash-bound visual records](visual-review.json), [Blender sheet](blender-contact-sheet.png), [Three.js sheet](three-contact-sheet.png), [reverse sheet](reverse-contact-sheet.png). This is a technical/art review, not scientific certification.
- **PASS**: 23 unit/physics/catalog tests, all 39 catalog GLBs validated, production Vite build, 14 original browser scenarios including every card preview/download and WebKit Game smoke, and 9 PWA offline/update failure scenarios.
- **PASS**: Solar scene browser scenarios at 1440, 768, 390 and 320 CSS pixels: direct subpath route, all 17 models, selection/focus, full Saturn fit, realistic ratio mode, speed/pause, changed animated pixels, overview, Gallery return, viewer reset/close, scroll/overflow, no browser errors and cancelled in-flight navigation. See [scene report](scene-validation.json).
- **NOT TESTED**: physical iPhone/Android/tablet rendering, thermal performance, actual GPU memory, solar models in Safari/WebKit, installed-device Solar demo behavior and production deployment. Existing PWA suite exercises prepared Game offline behavior; the Solar pack is explicitly online-only.

## Scientific provenance and limitations

Facts use the [NASA Planetary Fact Sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/) and [Sun fact sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/sunfact.html), with rounded reference dimensions/periods/tilts. Diameter is equatorial except the Sun's volumetric mean diameter. Sun rotation is the adopted 16° latitude value, not rigid-body rotation. The Moon's orbital period and semimajor axis refer to Earth. Asteroids and comet are fictional types, with unknown physical properties represented as null rather than invented measurements.

Earth uses the [JPL/Caltech/USGS topographic land/ocean map](https://space.jpl.nasa.gov/tmaps/earth.html), Mars uses the [Viking mosaic](https://space.jpl.nasa.gov/tmaps/mars.html), Moon uses the [NASA CGI Moon Kit](https://svs.gsfc.nasa.gov/4720/), and Pluto uses the [New Horizons MVIC color mosaic](https://science.nasa.gov/resource/pluto-global-color-map/). See exact source URLs, bytes and hashes in [provenance](../reference/provenance.json). NASA media/source usage terms apply to the referenced imagery; these procedural Blender works are not NASA-reviewed products. The owner authorized public repository/Gallery display on 2026-11-04; no separate redistribution license has been selected for original geometry. No NASA logos are included.

Earth's colors are topographic, not a natural-color photographic Blue Marble. Its synthetic cloud deck and thin tint are not physical atmospheric scattering. Mars color is enhanced; Olympus Mons is only a broad mapped albedo region and has no measured elevation reconstruction. Pluto's unmapped southern area is a neutral synthetic continuation; the mosaic is enhanced color. Mercury craters, all microrelief, solar granulation/sunspots, gas bands and the Great Red Spot are representative procedural artwork. Ring geometry preserves a real Cassini gap; its optical profile is illustrative. Asteroid clast intersections are intentional, not watertight engineering meshes. The comet GLB has no tail.

The demo uses circular coplanar paths, illustrative phases, configurable display transforms, rounded orbital periods and metadata tilts. Realistic mode shares one physical distance/radius scale; small bodies remain fictional. Presentation mode enlarges bodies and compresses distances. Point-source lighting has constant falloff for readability; it does not reproduce irradiance. Starfield, belt placement and comet trajectory/tail are illustrative; no ephemeris, N-body gravity, spin precession or relativistic model is claimed. The online demo loads about 40.3 MB of GLBs sequentially and caps demo GPU textures at 1K while keeping original downloads intact.

## Known issues and recommended improvements

1. Review on real phones and measure sustained frame time/thermal behavior before public release; physical mobile performance is unverified.
2. Consider optional KTX2 textures and lower-cost belt LOD after measuring target devices. The existing shared Three.js chunk remains above Vite's 500 kB advisory and is lazy.
3. For higher scientific fidelity, replace illustrative normals with calibrated elevation datasets and use a natural-color Earth map; keep source provenance and avoid baking lighting into albedo.
4. Chromium reported some `net::ERR_ABORTED` transport notifications during scene tests, while all 17 model loads and rendered interactions completed and no loader/console error occurred. The individual URLs are retained in the scene report; this is not presented as zero transport cancellations.
5. Choose separate artwork redistribution terms if broader reuse permissions are desired. Source attribution and NASA/source usage terms remain applicable. Deployment was explicitly authorized on 2026-11-04.

## Reproduce and verify

Use Node 24, Blender 5.1.2 and cwebp. Final scene checks and unit tests also passed under Node 24.21.0. The shared [generator](../scripts/generate.py) covers every asset with deterministic seeds. Reference images are already retained; [fetch-references.py](../scripts/fetch-references.py) downloads images only. The generator refuses to replace an existing GLB. Generate into an isolated copy with empty factory output directories; never remove unrelated assets.

`blender --background --factory-startup --disable-autoexec --python models/solar-system/scripts/generate.py -- sun earth saturn`

For MCP, execute that same local script into a namespace with its __file__ set and call build('asset-id'); successful MCP execution was used for all 17 assets. Packed sources also open without the generator.

Run `npm test`, `npm run test:solar`, `npm run build`, `npm run test:browser`, `npm run test:pwa` and `node scripts/test-solar-scene.mjs`. Neutral review page: `/scripts/solar-review.html` under the Vite development server. `npm run test:solar` invalidates visual review when GLB hashes change; it does not invent a visual pass.
