# Product Studio slice 03 — runtime beverage label concepts

Status: host verification PASS. 515 unit tests, build and all 23 Product Studio browser scenarios passed; original 22 scenarios retained. Evidence: `ui-review/`.

This slice adds three clearly fictional, original label concepts to the existing Demo Beverage Can:

- Citrus Grid
- Berry Night
- Mint Signal

The artwork is generated at runtime with a 1024×512 CanvasTexture. It targets only the authored `LABEL_OriginalCitrusBand` material, keeps the baked source map untouched, uses `THREE.SRGBColorSpace`, and sets `flipY = false` to match the GLTFLoader path and the authored cylindrical 0..1 UV seam. The original map is restored by `Reset product & camera`, by model navigation, and by disposal. At most one generated texture/material pair is live per mounted can; each replaced pair is disposed.

Label selection does not change geometry or authored animation clips. Model navigation remains latest-selection-wins; the label controller is disposed before the replaced model is released. The controls are a keyboard/touch-sized fieldset and are disabled for the food tin and while loading.

Limitations are intentional: these are runtime label variants only. They are not baked into the checked-in GLB or Blender source, there is no user upload, and the app does not export a modified GLB. Physical mobile Safari and an actual host Node 22 browser run were not available in this contained context.

## Verification

Passed in the contained Node 18 environment:

```sh
node --test tests/product-studio-labels.test.mjs tests/product-studio-switch.test.mjs tests/product-studio-pose.test.mjs tests/product-studio-beverage-asset.test.mjs
npm run validate:assets
```

The build/browser command is runnable on the required host Node 22:

```sh
TEST_ARTIFACT_DIR=docs/product-studio/evidence/slice03/browser node scripts/test-product-studio-browser.mjs
```

That existing Product Studio suite retains its original scenarios and now includes `beverage-runtime-label-presets-render-uv-reset-bound`, which captures original/preset front and rear renders, checks the actual label mesh UV range and texture color/flip settings, exercises reset and rapid label/model switching, and asserts a live texture bound.

The sandbox build attempt was not counted as a pass: `npm run build` reaches asset validation, then Vite fails under Node v18.19.1 because Rolldown imports `node:util.styleText`, which requires Node 22.

## Final review

Three real front/rear rendered preset previews inspected: upright readable DEMO artwork, distinct original colours and no apparent seam. Pattern repeats evenly with matching seam margins. 390px page controls inspected without clipping. Thirty direct label changes and twelve model switches returned to exact warmed GPU baselines (8 textures with a runtime label, 7 authored). Actual Three controller tests verify original map ownership, exactly-once generated resource disposal, repeat/reset/dispose behavior and canvas failure. Physical mobile devices remain untested; label-specific browser flow ran desktop Chromium. Existing CI is unchanged.
