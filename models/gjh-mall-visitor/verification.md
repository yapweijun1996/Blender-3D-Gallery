# Visitor asset verification

The final locally exported model is the green-polo mascot selected by the user. The private reference remains outside the repository.

## Executed asset checks

- Blender 5.2.3 LTS generated the GLB, editable `.blend`, and front/side/back/portrait/walk/sprint renders.
- `inspect_sources.py` reopened the actual `.blend`: 12 editable articulated meshes, all expected joints, and idle/walk/sprint NLA tracks on every animated node.
- `validate.mjs` passed Khronos validation with zero errors and zero warnings. Actual export: 369,976 bytes, 10,356 triangles, 25 material primitives and eight materials.
- All three clips include 33 transform tracks, including constant pose resets. The validator samples actual mesh vertices and joint rotations rather than relying on action names alone.
- Maximum sampled sole-to-floor errors: idle below 0.000001 m, walk 0.00020 m, sprint 0.00127 m. Horizontal drift remains zero.
- GLB SHA-256: `43d08b67f4450b6aac478cfca4ca664044662cd79021ed15d55ef5612e312be2`.

Source and generator hashes are in `reports/sources.json`; measured bounds and animation details are in `reports/assets.json`.

## Visual review and corrections

Independent review of the initial renders found angular sleeve tops, an overly exposed neck, visible knee shading bands and airborne walking feet. The final source rounds the sleeve shoulders, lowers the head, uses appropriate cap normals and bakes floor contact from posed sneaker vertices. The export explicitly retains constant channels so each clip restores the entire pose; dropping constant torso tilt had caused the earlier exported contact discrepancy.

The revised front, side, back and gait renders were reviewed. Open thin frames preserve visible eyes; swept hair, smile, green polo, cream collar, cuffed jeans and white sneakers follow the selected concept. Minor close-up polygon faceting and simplified rigid joint seams remain intentional lightweight-model limitations. The model exceeds the reference's aspirational 2,000–5,000 triangles; the reviewed 15,000-triangle / 25-primitive budget is met.

## Browser and delivery boundary

Run `npm test`, `npm run build` and `node scripts/test-gjh-visitor.mjs` from the repository root for the source gallery's actual rendered-viewer checks. Those browser results and the consuming mall's playback/regression results are separate release evidence; the asset checks above do not claim either browser run or deployment has passed. The source gallery displays the rest model; the mall consumes its animation clips. Physical mobile GPU performance is not established by desktop browser emulation.


## Executed source-gallery release checks

- `npm test`: 90 tests passed.
- `npm run build`: all 57 registered GLBs validated with zero errors/warnings; production build passed. The existing shared Three.js/OrbitControls chunk-size advisory remains.
- `node scripts/test-gjh-visitor.mjs`: PASS at 1440, 768 and 390. Discovery loads no GLB, actual hashed production export matches the source SHA-256, keyboard orbit changes the rendered model, reset/Escape work, and no page errors or document overflow occurred.
- `npm run test:library`: all nine existing model-library journeys passed, including failure recovery and keyboard/mobile navigation.
- Structured browser receipts are in `reports/gallery-browser.json` and `reports/library-browser.json`. Tests use headless Chromium/SwiftShader on macOS, not physical phones. The consuming mall separately passed its full existing regression at 1440/768/390, with a maximum sampled 130 draw calls; its focused animation/release checks are still pending at the time of this source record.

The initial focused browser assertion incorrectly expected an unbundled model path; it was corrected to check the actual Vite content-hashed URL and exact response bytes. No model, geometry budget or browser assertion was relaxed.
