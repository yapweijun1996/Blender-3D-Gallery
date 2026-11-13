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

- Materials: `Label <SKU>` (base-colour image, metallic 0.2, roughness 0.3: glossy lacquered print), `Gold lacquered rim` (0.9 / 0.28), `Silver tinplate` (0.9 / 0.34). No normal maps, so no tangents are needed.
- Textures: `textures/<slug>-label.jpg` (LOD0) and `textures/lod1/<slug>-label-lod1.jpg`, JPEG quality 88 embedded in the GLBs, sRGB, clamp-to-edge. Dimensions are not powers of two (fine for WebGL2 mipmaps).
- Nodes in each GLB: `GoldRim`, `SilverMetal`, `Label` under the asset root. Editable parts (`BottomSeam`, `TopSeam`, `Lid`, `OpeningScore`, `PullTabPlate`, `PullTabRivet`, `PullTabRing`, `Base`, `CanBody`, `Label`) are separate objects in `sources/gjh-abalone-cans.blend`.
- Evidence: `reports/qa/` (24-view and six-view sheets), `reports/screenshots/` (v2/v3 same-angle pairs, textures, mobile, cards, LOD), `reports/golden/` (regression goldens), `reports/build.json` (inputs, layout, costs), `reports/assets.json` (metrics).

## Follow-up: "the can looks fake, too flat like a rectangle" (user review)

Cause, confirmed in the viewer: (1) the baked cylinder shading had been divided out of the label, but the viewer's lights were too flat and too strong (hemisphere 0.45 plus directional 0.9 clipped the light-yellow label to near white), so the sides were as bright as the centre; (2) the label was matte, with no highlight band like a lacquered tin. The official marketing renders of the Mexico can (shown on the eShop page) confirm the real can is high-gloss with a vertical highlight and dark edges.

Changes: label metallic 0.2 and roughness 0.3; viewer lighting (metadata) hemisphere 0.15, directional 0.55 from the front left, studio environment intensity 1.0, which gives a soft highlight band and a natural falloff toward the edges. Three other lighting sets were tried and rejected (point-like hotspot, washed-out colour, still flat). Compare `reports/screenshots/v3-*` with `v4-*` (front, 40 degrees, zoom). This is a judgement of look from screenshots; it is not measured against a real can, and the highlight depends on the viewer's RoomEnvironment.

Also checked: the eShop page for the Mexico can has only front and back packshots; its five "Info" graphics are marketing composites of the front face, so they cannot fill the missing third face.

## Texture distortion investigation (Australia first, then all four SKUs)

Task: circular certification logos looked unnaturally proportioned when zoomed, label top and bottom needed checking, small print looked degraded. Findings in the order requested; evidence images are `reports/screenshots/v5-*`.

**1. Actual GLB inspection** (`gjh-can-australia-abalone.glb`). Embedded JPEG, 1280 x 624 (before 1280 x 634); sampler magFilter LINEAR, minFilter LINEAR_MIPMAP_LINEAR, clamp-to-edge; label material metallic 0.2, roughness 0.3. Label wall radius 0.03705 m, circumference 0.23279 m, label height 0.11359 m (v 0 to 1 spans seam to seam; the strips under the seams extrapolate to v -0.018 and 1.018). Texel density is identical on every wall triangle: 5498.5 px/m horizontal, 5493.4 px/m vertical.

**2. Circumference to height ratio.** C/H = 2.049 against a texture aspect of 2.051, so the mesh and UV ratio are consistent (before: 2.035 against 2.019, vertical density 0.8% higher). The real mismatch was in the artwork rows, see 6.

**3. Circular logos, source versus render.** Boxes measured on 4x enlarged official photos; the face-on aspect is what a camera facing the logo sees after unrolling.

| Logo (Australia) | Photo width/height | Printed circle would show | Face-on width/height after unrolling | Verdict |
| --- | ---: | ---: | ---: | --- |
| Halal circle | 0.65 | 0.62 | 1.04 | printed, correct |
| ASME seal | 0.63 | 0.63 | 1.00 | printed, correct |
| Wild Caught badge | 0.91 | 0.58 | **1.60** | pasted on flat in the packshot, too wide |

The same flat Wild Caught badge exists in New Zealand (1.41 before) and Mexico (1.74 before). The South Africa red seal measures about 0.59 in the photo against 0.63 expected for a printed one, so it is left unchanged. This explains the report: the mesh and UV are not the cause, the packshot's retouched badge is.

**4. UV checker.** A texture with physically sized 20 mm circles at eight angles (grid every 10 mm) was applied to the actual GLB and rendered with an orthographic camera: face-on width/height 0.99 at every angle including the wrap seam (1 px of 167 px quantisation), and with a fixed camera 0.697 at plus and minus 45 degrees against 0.699 expected from the cosine compression. Same result before and after the change (the 0.8% anisotropy is below this test's resolution). No stretching or seam error from the mesh or UVs.

**5. Filtering, mipmaps, compression, resolution.** Mipmaps present. **Anisotropy was 1** (the viewer default; this machine supports 16), which visibly softened small text on the curved sides at oblique angles (`v5-aniso-1-before.jpg` against `v5-aniso-8-after.jpg`). Fixed by an opt-in `display.textureAnisotropy` of 8 for these cans. JPEG quality 88 shows no blocks at close range. Resolution is capped by the source (see Sharpness above).

**6. Top and bottom label boundaries.** Measured on all 11 packshots: the printed label runs from row 313 to row 848. v3 cropped rows 301 to 835 (5% of the can bbox), so the top 13 rows were the pale gold seam and lid pixels (the pale band under the top rim) and the bottom 13 rows of label were missing, and the rows were stretched 2.3% vertically against the horizontal scale (`v5-label-top-before.jpg` against `v5-label-top-after.jpg`, and the bottom pair). Fixed: exact measured rows, the scale taken from the measured body silhouette, and the can height derived from the label rows (124.0 mm instead of 124.6 mm).

**7. Fixes applied (confirmed defects only).**
- Label rows and scale: described in 6.
- Flat Wild Caught badges (Australia, New Zealand, Mexico): columns inside the badge's rows are remapped so its arc width equals its height; the freed angle is absorbed in the plain background on its left and the front panel ends just after the badge. No pixel is redrawn. Face-on render, Australia: 1.50 (colour mask) to 0.99; New Zealand and Mexico round by pixel check (the colour mask is unreliable against their blue bands; `v5-badge-*` crops). This is a geometric correction of the source photograph, can be switched off with `OVERLAY_BADGES`, and slightly stretches the plain background beside the badge.
- Anisotropic filtering: opt-in, validated in `scripts/catalog.mjs`, tested.
- Not changed: source resolution, the highlight and shading baked into the photographs, panel order and spacing, the Mexico placeholder.

**8 and 9. Regression and all four variants.** `npm run test:cans` now records 12 golden views per can at 0, 40, 90, 180 and 270 degrees, each normal and zoomed, plus top and bottom, for all four cans (48 goldens). The viewer turns in 10 degree steps, so 40 degrees stands in for 45. Result: 48 of 48 views passed on two consecutive runs on an idle machine (mean channel difference at most 2.0, at most 1% of pixels differing by more than 40). The goldens are a local regression guard from headless Chromium software rendering, not a cross-GPU reference. Before/after evidence: `reports/screenshots/v5-*`; the earlier `v3-*`/`v4-*` sets are kept for history.

**10. Remaining limitations.** Only the three Wild Caught badges were found to be pasted on flat; the other circular graphics (for example the Trans Fat Free circle, the recycle mark and the Double Boiled seal on the other faces) were not individually measured. Fine print is capped by the 1000 px source. Face-on logo proportions on the flat-badge fix rely on the badge boxes measured by eye on enlarged photographs (about 2 px).

## Codex flat-label comparison set (AI-generated label, not official)

Requested as a comparison version: quality first, similar look is enough. Four cans with the same geometry as the photo set, labelled with flat artwork generated by the Codex CLI (`image_gen`) from the official packshots. Evidence: `reports/codex/compare/` (same-angle viewer sheets and flat-label sheets).

| Check | Result |
| --- | --- |
| glTF validator (`validate.mjs codex`) | 0 errors, 0 warnings on all four |
| Budgets | 4,888 triangles, 3 materials, 3 draw calls, 391 to 431 KiB (target 500 KiB) |
| Geometry parity with the photo set | same within 0.5 mm (tested) |
| Label texel density | isotropic (tested); texture 1536 px around the can |
| Disclosure | each metadata file has `label_source.status`, the hash of the flat label and the discrepancies found (tested) |
| Visual regression | `npm run test:cans:codex`, see result below |

What it improves over the photo set: sharper print, round logos by construction, no photo seams or baked highlights in the label, a complete 360 degrees for Mexico.

What it does not give: fidelity. After a second Codex pass that corrected the text errors found in review (checked by eye against the official information-face photos), the remaining differences are:
- Australia: the nutrition table now reads cholesterol 150 mg as official; seals are generic. The front still prints 425 g, matching the retailer listing used for the pack size.
- New Zealand: distributor and packer lines now match the official photo; seals are generic.
- South Africa: the invented crown and star seals were removed in a second pass; the remaining award marks are generic.
- Mexico: net weight 454 g, GJH logo and addresses now match the official photo; the third face is still invented.
- All four: QR codes and barcodes were redrawn and not scanned; the first Codex attempt (rejected) had invented certificate numbers and a year, so the prompt now forbids them.

Not verified: that the generated Chinese is correct in every place (spot-checked on the prominent strings only), scannability of the codes, mobile devices and other browsers. This set is for comparison; do not treat its text as product information. Visual regression: `npm run test:cans:codex` records 5 views per can (0, 90, 180 and 270 degrees plus a zoomed front, 20 goldens); 20 of 20 passed on two consecutive runs on an idle machine. These goldens are a local guard from headless Chromium software rendering.

## Not done or not possible here

- KTX2/Basis and Meshopt compression: the gallery viewer has no decoders. The GLBs are plain glTF with JPEG textures.
- Runtime LOD switching: LOD1 GLBs are exported and load in Three.js (`reports/screenshots/v3-lod0-vs-lod1.jpg`); the gallery has no switching mechanism, so E2E LOD behaviour is untested.
- Physical devices, iOS Safari, Android Chrome, Firefox and Safari proper.
- Official dimensions, die-line, the third Mexico face and the true panel order.
- The goldens are a local regression guard from software rendering, not a cross-GPU reference.
