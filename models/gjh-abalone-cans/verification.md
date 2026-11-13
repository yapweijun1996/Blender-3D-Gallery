# Verification: GJH Abalone Cans (refinement pass v3)

Run on 2026-11-13, Blender 5.2.3 LTS, macOS arm64, headless Chromium (Playwright, software rendering) against the real gallery viewer (`?model=<slug>`). v2 = commit `496b1db` (previous pass), v3 = this change. Before/after viewer shots use the same arrow-key camera script, so the angles are identical. Contact sheets and screenshots are in `reports/`.

## Root cause of the side-label problem (GJH-P0-01 / 02 / 03)

Inspected in the order given by the report: source artwork, layout, material, sampling, geometry, render.

1. **Source artwork.** The official eShop set has three different faces for New Zealand, Australia and South Africa (front, food-photo face, nutrition/information face) and two for Mexico (front, information face). v2 assumed one "back" exactly opposite the front, so the faces were in the wrong places and the information face was unused.
2. **Texture sampling.** v2 blended front and back across 80 to 100 degrees, which pulled in the packshots' limb zone (edge glare and background anti-aliasing). That is the pale grey vertical band at the sides. Compare `reports/screenshots/v2-*-side.jpg` with `v3-*-side.jpg` and `v2-texture-*.jpg` with `v3-texture-*.jpg`.
3. **UV and geometry** were not the cause: the label is one island (u around, v along the height) and the automated test confirms u covers exactly one wrap and v stays within the seams.

Fix: each packshot is treated as a cylinder panel (angle = asin of the normalised column), only the reliable centre (about 70 degrees each side) is used, and seams are placed where neighbouring faces match best in colour and artwork. Nothing is redrawn, generated or retouched; the artwork pixels come from the official packshots (SHA-256 in `reports/build.json` and the metadata).

**Known limits of that fix**
- Panel **order and spacing are estimates**. The total seam cost differs by only about 4% between the two possible orders, and Australia alone prefers the other order, so the order is not proven by evidence; one shared order is used for consistency across the three-panel SKUs. A physical can or a die-line is needed to confirm it.
- **Mexico has no official third face.** About 121 degrees are an unprinted placeholder (two flat base colours, no artwork). `label_layout` in the metadata records this.
- An attempt to infer the panel angles from the printed wave line failed (fit R-squared 0.05 to 0.35) and was not used.

## Gap register

| ID | Status | Evidence |
| --- | --- | --- |
| P0-01 side seam grey band | PASS | Cause found and fixed; v2 vs v3 side views; 24-view sheets. |
| P0-02 label fidelity | PARTIAL | All artwork from the official packshots with recorded hashes; panel order estimated; Mexico has a placeholder sector. |
| P0-03 360 degree texture integrity | PASS (NZ, AU, SA) / PARTIAL (MX) | `reports/qa/*-turntable-24.jpg` (every 15 degrees); no tears or cut text. Mexico shows its disclosed placeholder. |
| P1-01 pull tab | PASS | Separate ring, rivet, neck plate and opening score (parts in the .blend; merged per material in the GLB). Official lid type not verified (no lid photo exists). |
| P1-02 top lid | PASS | Recessed panel, two pressed rings, rolled seam; automated check of the profile levels. |
| P1-03 bottom | PASS | Standing ring, recessed base and central panel (`v3-*-bottom.jpg`, `reports/qa/*-six-views.jpg`). |
| P1-04 gold rim material | PASS | Metallic 0.9, roughness 0.28; reads as metal in the viewer with its studio environment. Not measured against a real can. |
| P1-05 back label softness | PARTIAL | Limited by the source: the official page tops out at 1000 x 1000 px, about 350 px for the can width. Texture is 1280 px for the full circumference (about 1.3x native detail); a 2048 x 1024 texture was not adopted because it would only enlarge the blur. |
| P1-06 label distortion | PASS (visual) | Exact cylinder projection; front, side, reverse, top and bottom reviewed. |
| P1-07 geometry and normals | PASS | glTF validator 0/0; automated check that label wall normals face outward; rounded seam profiles instead of bevel modifiers. |
| P1-08 real scale | UNVERIFIED | No official dimension found. A retailer listing gives 7.5 x 11 x 7.5 with no unit (possibly the box), about 14% shorter than the packshot-based 124.6 mm. Diameter and height are still estimates. |
| P1-09 runtime performance | PARTIAL | File size, triangles, draw calls and texture memory measured (below). FPS and device GPU memory not measured. |
| P1-10 cross-device | UNVERIFIED | See E2E-25 to 27. |
| P2-01 lighting | PARTIAL | Viewer uses its RoomEnvironment (opt-in) with tuned lights; no HDRI. |
| P2-02 roughness variation | NOT DONE | Roughness differs per material only. |
| P2-03 edge detail | PASS | Rounded seam and lid profiles. |
| P2-04 viewer background | NOT DONE | The viewer background is global; only thumbnails use the studio. |
| P2-05 camera presets | PARTIAL | Six standard views exist in the QA sheets and golden tests; no UI presets in the viewer. |
| P2-06 developer inspector | NOT DONE | |
| P2-07 shared QA pipeline | PASS | One generator, one validator and one test suite for all four SKUs. |
| P2-08 golden screenshots | PASS | `npm run test:cans`: 24 golden views, stable over repeated runs (local, headless Chromium). |

## Acceptance tests (30)

| ID | Result | Notes |
| --- | --- | --- |
| E2E-01 24 views every 15 degrees | PASS (NZ, AU, SA) / PARTIAL (MX) | Reviewed on the contact sheets. Mexico has the disclosed unprinted sector. |
| E2E-02 side grey band | PASS | Root cause fixed. |
| E2E-03 UV island boundary | PASS | Automated u/v range plus visual. |
| E2E-04 wrap continuity matches the real packaging | UNVERIFIED | Seam positions are estimates. |
| E2E-05 texture sampling | PASS (visual) | Clamp-to-edge, no sampling lines seen. |
| E2E-06 mipmap levels | UNVERIFIED | Not tested at several distances. |
| E2E-07 pull tab structure | PASS | Visual and geometry; official lid type unverified. |
| E2E-08 lid profile | PASS | Automated. |
| E2E-09 bottom recess | PASS | Automated and visual. |
| E2E-10 normals | PASS | Label automated; others visual. |
| E2E-11 geometry integrity | PASS (visual) | No automated intersection test; parts overlap by design under the seams. |
| E2E-12 physical dimensions | UNVERIFIED | See P1-08. |
| E2E-13 gold rim | PASS (visual) | |
| E2E-14 silver lid | PASS (visual) | |
| E2E-15 front label fidelity | PASS | Derived from the official front packshot. |
| E2E-16 back label fidelity | PARTIAL | Real faces, soft source, estimated placement. |
| E2E-17 country accuracy | PASS | Each can shows its own origin text and Chinese mark. |
| E2E-18 compression | PASS (visual) | JPEG quality 88, no blocks or broken text seen. |
| E2E-19 glTF validator | PASS | 0 errors, 0 warnings on all 8 GLBs. |
| E2E-20 GLB size | PASS | Largest 384 KiB (target 500). |
| E2E-21 triangles | PASS | 4,888 (target 5,000). |
| E2E-22 draw calls | PASS | 3 (target 3). Materials: 3. |
| E2E-23 desktop FPS | UNVERIFIED | Only software-rendered headless Chromium. |
| E2E-24 mobile FPS | UNVERIFIED | |
| E2E-25 iOS Safari | UNVERIFIED | |
| E2E-26 Android Chrome | UNVERIFIED | |
| E2E-27 desktop browsers | PARTIAL | Chromium only. Firefox is not installed here; Playwright WebKit did not show the canvas within 30 s (cause not investigated). |
| E2E-28 visual regression | PASS | `npm run test:cans`, 24/24 on two consecutive runs. |
| E2E-29 four-SKU consistency | PASS | Identical geometry budgets (automated); labels correct per SKU; Mexico partial. |
| E2E-30 delivery integrity | PASS | Validator, recorded SHA-256 and reload-stable rendering (2 reloads, no errors, 0 failed requests). |

## Measurements (`reports/assets.json`, regenerated by `validate.mjs`)

| Can | LOD0 tris | LOD0 draw calls | Materials | LOD0 GLB | LOD0 texture | LOD0 GPU texture* | LOD1 tris | LOD1 draw calls | LOD1 GLB | LOD1 texture | LOD1 GPU texture* |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |
| New Zealand | 4,888 | 3 | 3 | 384 KiB | 1280x632 | 4.31 MB | 3,044 | 3 | 155 KiB | 640x316 | 1.08 MB |
| Australia | 4,888 | 3 | 3 | 372 KiB | 1280x634 | 4.33 MB | 3,044 | 3 | 152 KiB | 640x317 | 1.08 MB |
| South Africa | 4,888 | 3 | 3 | 382 KiB | 1280x634 | 4.33 MB | 3,044 | 3 | 153 KiB | 640x317 | 1.08 MB |
| Mexico | 4,888 | 3 | 3 | 268 KiB | 1280x632 | 4.31 MB | 3,044 | 3 | 118 KiB | 640x316 | 1.08 MB |

\*Estimate: RGBA8 with a full mip chain (width x height x 4 x 4/3); not measured on a device. v2 for comparison: 3,802 triangles, 7 draw calls, 4 materials.

Load timing (localhost Vite dev server, headless Chromium, 3 runs): canvas visible in 0.54 to 1.9 s, GLB fetch 2 to 86 ms. Indicative only, not a network or device measurement.

## Inventory

- Materials: `Label <SKU>` (base-colour image, metallic 0.05, roughness 0.5), `Gold lacquered rim` (0.9 / 0.28), `Silver tinplate` (0.9 / 0.34). No normal maps, so no tangents are needed.
- Textures: `textures/<slug>-label.jpg` (LOD0) and `textures/lod1/<slug>-label-lod1.jpg`, JPEG quality 88 embedded in the GLBs, sRGB, clamp-to-edge. Dimensions are not powers of two (fine for WebGL2 mipmaps).
- Nodes in each GLB: `GoldRim`, `SilverMetal`, `Label` under the asset root. Editable parts (`BottomSeam`, `TopSeam`, `Lid`, `OpeningScore`, `PullTabPlate`, `PullTabRivet`, `PullTabRing`, `Base`, `CanBody`, `Label`) are separate objects in `sources/gjh-abalone-cans.blend`.
- Evidence: `reports/qa/` (24-view and six-view sheets), `reports/screenshots/` (v2/v3 same-angle pairs, textures, mobile, cards, LOD), `reports/golden/` (regression goldens), `reports/build.json` (inputs, layout, costs), `reports/assets.json` (metrics).

## Not done or not possible here

- KTX2/Basis and Meshopt compression: the gallery viewer has no decoders. The GLBs are plain glTF with JPEG textures.
- Runtime LOD switching: LOD1 GLBs are exported and load in Three.js (`reports/screenshots/v3-lod0-vs-lod1.jpg`); the gallery has no switching mechanism, so E2E LOD behaviour is untested.
- Physical devices, iOS Safari, Android Chrome, Firefox and Safari proper.
- Official dimensions, die-line, the third Mexico face and the true panel order.
- The goldens are a local regression guard from software rendering, not a cross-GPU reference.
