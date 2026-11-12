# Event booth verification

Local source/export verification, 2026-11-12. Base: `e2039c0` (queue kit included). No merge or deployment performed by this task.

## Final asset

Blender 4.0.2 generated and reopened `sources/mall-event-booth.blend`. Source collections `PosterPanel` and `DisplayContent` each contain editable geometry/text, and the standalone GLB retains real mesh-bearing independent groups. Contract tests remove/replace each module while preserving the other and `BoothStructure`.

- GLB: 215,640 bytes, 4,632 triangles, 7,539 vertices, 7 materials, 14 primitives, no animations/textures/external buffers.
- SHA-256: `8fda1b51362eb3d11cd3525fb9ae1b3a220da22e745ed8b9af0eb6f0f8e87738`.
- Size: 2.72 × 2.73 × 1.18 metres in glTF XYZ; floor-centred origin.
- Thumbnail: 21,902-byte WebP.
- The preferred eight-primitive target is exceeded deliberately: structure/poster/display retain separate material slots for independent replacement. Byte and triangle budgets remain comfortably satisfied.
- Khronos validator: zero errors, zero warnings.

## Executed checks

- Blender generation and true source reopening: PASS.
- `node models/mall-event-booth/validate.mjs`: PASS.
- `npm test` on current main plus booth: 105/105 PASS. Subsequent strengthened module-replacement contract: 3/3 PASS.
- `npm run build`: PASS, including complete catalog validation; existing bundle-size warning remains.
- No UI, game, permission or download changes. Asset remains non-downloadable under the existing rights policy.

## Attempt history and browser scope

The initial isolated worker lacked the shared Blender toolchain; task-local copies resolved this. An early Node 18 attempt could not build Vite; Node 22.23.3 resolved the runtime mismatch. Offline worker browser attempts were not reached because localhost listen was unavailable. The supported networked profile first lacked the requested Chromium revision, then ran with the correct existing Chromium 1248.

An intermediate asset passed the general library suite and booth 1440×900, 768×1024 and 390×844 orbit/zoom/reset and consumed-byte checks. That intermediate booth script did not yet capture request-failure events, so those passes are not equivalent to final strict coverage. After final art placement and replay onto main, the script was strengthened to retain requestfailed/console/page errors, require response status 200, exact consumed GLB SHA/size and no horizontal overflow. Final coordinator verification on this exact final GLB passed all three viewports (1440×900, 768×1024, 390×844), including strict request-failure capture, response status, consumed bytes/SHA, orbit/zoom/reset and overflow. The general library suite passed all nine scenarios. Final full unit suite passed 105/105 and production build passed. All four final commands exited 0. Evidence is retained in the task workspace as `parent-final-unit.log`, `parent-final-build.log`, `parent-final-browser.log`, `parent-final-library.log` and matching `.exit` files; final captures are in `parent-final-qa/`. Close/reopen, focus and recovery are covered by the general library suite rather than claimed as booth-specific assertions. No physical-device/touch or GPU performance claim is made.
