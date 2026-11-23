# Singapore MRT game kit

Eleven self-contained, texture-free binary glTF 2.0 assets derived from the gallery exports. [models.json](models.json) records measured sizes, triangle and primitive counts, file bytes, used materials, validator results and hashes. The city kit already contains the station entrance.

| GLB | Original gallery asset | Six-view Cycles comparison |
| --- | --- | --- |
| [mrt_carriage.glb](mrt_carriage.glb) | [MRT Train Carriage](../../../models/mrt-train-carriage/README.md) | [PNG](comparisons/mrt_carriage.png) |
| [mrt_platform.glb](mrt_platform.glb) | [MRT Platform](../../../models/mrt-platform/README.md) | [PNG](comparisons/mrt_platform.png) |
| [platform_screen_door.glb](platform_screen_door.glb) | [MRT Platform Screen Door](../../../models/mrt-platform-screen-door/README.md) | [PNG](comparisons/platform_screen_door.png) |
| [fare_gate.glb](fare_gate.glb) | [Train Ticket Gate](../../../models/train-ticket-gate/README.md) | [PNG](comparisons/fare_gate.png) |
| [station_sign.glb](station_sign.glb) | [MRT Station Signage](../../../models/mrt-station-signage/README.md) | [PNG](comparisons/station_sign.png) |
| [route_map.glb](route_map.glb) | [MRT Route Map Panel](../../../models/mrt-route-map-panel/README.md) | [PNG](comparisons/route_map.png) |
| [train_seat.glb](train_seat.glb) | [MRT Train Seat](../../../models/mrt-train-seat/README.md) | [PNG](comparisons/train_seat.png) |
| [train_door.glb](train_door.glb) | [MRT Train Door](../../../models/mrt-train-door/README.md) | [PNG](comparisons/train_door.png) |
| [grab_handle.glb](grab_handle.glb) | [MRT Ceiling Grab Handle](../../../models/mrt-ceiling-grab-handle/README.md) | [PNG](comparisons/grab_handle.png) |
| [card_reader.glb](card_reader.glb) | [Access Card Reader](../../../models/access-card-reader/README.md) | [PNG](comparisons/card_reader.png) |
| [arrival_display.glb](arrival_display.glb) | [Bus Arrival Display](../../../models/bus-arrival-display/README.md) | [PNG](comparisons/arrival_display.png) |

## Placement and movement

Use metres, +Y up and +Z forward. The placement origin is the horizontal footprint centre at ground level. The platform runs along X with its track edge towards +Z. It repeats the original 20 m construction across 120 m. The deck and roof are continuous. The raised tactile ribs and yellow edge line follow the track side. Deck height is 1.15 m. The carriage floor and sills are 1.20 m above wheel contact.

- `body` contains the fixed geometry. `door_L1`, `door_L2`, `door_R1` and `door_R2` each carry one carriage doorway's two original panels as a single sliding assembly. Doorway 1 is towards +Z and doorway 2 towards –Z. Their opening strokes are –1.46 m and +1.46 m along Z, respectively.
- `wheel_FL` and `wheel_FR` are the leading axle, followed by `wheel_FL2` and `wheel_FR2`, `wheel_RL2` and `wheel_RR2`, then `wheel_RL` and `wheel_RR`. Each pivots around local X at its axle centre.
- The 3 m screen door retains the four glazed panels. `leaf_1` opens towards –X and `leaf_2` towards +X. The gate slides `flap_L` and `flap_R` open towards –X and +X. Each moving node records its closed-to-open displacement in glTF metres under `extras.openTranslationMeters`. Drive these transforms from the game.
- Change the `paint` material's base color factor for tinting. Other surfaces use flat PBR shading with vertex colors where needed. The carriage's door glazing and opaque panels share a single blend primitive per door to fit the draw budget. The carriage stripe uses the gallery's muted teal palette, and station equipment retains the gallery's transit blue.

## Verification and rebuild

Rows 1 and 3 in each PNG show the original. Rows 2 and 4 show the actual delivered GLB. The first row pair shows front, three-quarter and side. The second pair shows rear, elevated and detail. Carriage detail looks down the passenger aisle. Platform front and detail frame the same local section. The remaining platform views fit the full respective lengths. The screen-door framing adapts to the respective widths. Per-sheet JSON records the exact source, final GLB, capture and Cycles settings. [qa.json](qa.json) records both visual reviews and the verified geometry coverage.

The geometry checks intersect rays with final GLB triangles. They cover open and closed passages, floor and sill elevations, aisle clearance, platform deck continuity, wheel pivots, node names and budgets. Game controller integration and engine-specific transparency sorting remain engine-side checks.

Run these commands from this folder with FFmpeg, the repository's installed glTF Validator, and the supplied launcher. Run Blender stages sequentially.

```sh
zsh run-blender.sh build.py
zsh run-blender.sh render.py
node validate.mjs --with-renders
```

The build and render scripts accept individual gallery folder IDs. Scratch captures and build metadata are written under `.work/`.
