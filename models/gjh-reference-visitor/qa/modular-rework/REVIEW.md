# Modular character and hair QA

Status: **REWORK for reference fidelity and production animation**. The modular parts, hair reduction, and sampled structural checks are implemented; known visible and rigging limitations remain below. `final-v2/manifest.json` identifies the final source, character, hair, module manifest, reference and re-import captures by SHA-256. `final/validation-v3.json` identifies all 40 current GLBs by SHA-256.

## Visual review and repair

An independent reviewer inspected source turnarounds, the re-imported final GLB, head-turn and motion samples, and re-imported optional hat/jeans. The eyes, brows, mouth, hair and ears stay together in the sampled head turn; no major new holes or detached pieces appeared in the default views. The earlier crown had rectangular side profiles; it was rebuilt with tapered, rounded sections. The earlier jeans waistband visibly intersected the hoodie from behind; a narrower waist was re-exported and the independent reviewer confirmed the overlap was no longer visible in the sampled rest view.

Reference fidelity remains open: rear hair is more symmetric, layered and droplet-shaped than the reference, and the short crown tips are more upright. Hand and ear seams are visible at close range. Hiding an ear reveals a skin-coloured underlay with a noticeable bulge. Eyes, brows and mouth are textured surface patches, not independently shaped eyeballs or oral cavities. Hat and jeans are simple alternatives; they were inspected in rest pose only.

## Technical and rigging checks

- Khronos: 40 GLBs (complete character, rigid hair, 38 modules) report zero errors and zero warnings, with informational messages. See `final/validation-v3.json` for the file hashes and details.
- Hair: 8,876 triangles versus 62,860 previously. Full default character: 51,543 triangles and 24 materials. This exceeds both the reference sheet and the repository's draft full-character budget.
- `final/module-rig-v3.json`: 38 skinned slots rebound to the full character's named bones and compared across five sampled times per clip and a head turn. Optional Hat/Jeans were compared with a separately driven module skeleton because there is no default-character counterpart.
- `final/finger-rig-v2.json`: all ten fingers rotate and hide independently in a Three.js Node test.
- `final/hair-animation-v2.json`: rigid hair and full-character hair agree at rest, four head rotations and sampled clip times. A prior decimation-order mismatch was fixed and retested.
- `browser/final/report.json`: Chrome/WebGL2 static front and 32-degree captures of the exact character GLB, five clips present, no console errors or warnings, and no obvious opaque facial-patch artifacts. This is not a full browser animation or device test.
- `final-v2/pose-sit.png` still shows legs intersecting static shorts, and the sit pose lacks demonstrated seat/foot contact. A separate attempted hip/shorts-weight change reduced intersection but worsened foot contact. A further single-frame root-lowering experiment brought the feet near the ground but left obvious waist separation; neither candidate was merged or verified over a full transition. Walk/run full-cycle sliding and garment collision were not cleared. See `sit-investigation/`.

Three.js geometric tests stub texture decoding; browser rendering was checked only in two static views. The exact full animation cycles, all optional wardrobe/pose combinations, other renderers and physical devices are NOT_RUN. The hidden original head and hands and the pre-change artifact backup are retained for recovery.
