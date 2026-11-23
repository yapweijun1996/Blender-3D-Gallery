# Bayfront MRT game kit

Four standalone, metre-scale GLBs for Singapore's Bayfront interchange. The kit follows the requested footprints and takes its visual cues from Bayfront reference photographs. The real station has two stacked island levels, each serving both lines for cross-platform transfer. The two game modules use a single line identity apiece. The signs use the photographed CE1 / DT16 era and the route diagrams show nearby stops. The dimensions and internal arrangement are approximations based on the brief and public imagery.

| Module | Modelled features |
| --- | --- |
| Concourse | Tiled terrazzo and circular floor inlays, brushed-steel columns, stainless faregates with card readers and an accessible-width lane, glazed Passenger Service Centre, kiosks, twin escalator wells, lifts, wayfinding and green oculus with linear ceiling lighting |
| Circle Line platform | Full-length glazed platform screen doors on both edges, yellow-orange bands, tactile strips, boarding arrows, individual steel seats, route maps, lift, stair and escalator core |
| Downtown Line platform | Same island kit with Downtown Blue identity, route maps and screen-door bands |
| Exit B | Low pale canopy, steel mullions, glazed sides and rear, granite seating plinths, tiled street apron, paired descending escalators and the Bayfront / Marina Bay Sands signs |

## Game integration

The long axis is **X**, vertical is **+Y**, and passenger-facing front is **+Z**. The shared asset datum is `(0, 0, 0)` at the centre of the floor or street apron. Structural slabs and the descending escalator wells extend below the datum. Each visible part has a named mesh node and shares the asset datum, so related parts can be loaded or hidden independently.

The flat PBR materials use the requested names. Line and surface colours are baked as vertex colours. The signs and route diagrams use one embedded 1024 × 1024 JPEG per asset. Gates and screens are static scenery. Escalator banks and platforms can be positioned independently in the game. The contact sheets use studio lighting and selected roof or ceiling cutaways.

## Visual references

- [Exit B entrance photograph](https://commons.wikimedia.org/wiki/File:CE1_DT16_Bayfront_MRT_Exit_B_20201201_152238.jpg)
- [Concourse and faregate photograph](https://commons.wikimedia.org/wiki/File:CE1_DT16_Bayfront_MRT_Concourse_20201201_152103.jpg)
- [Cross-platform interchange and escalator photograph](https://commons.wikimedia.org/wiki/File:CE1_DT16_Bayfront_MRT_Platforms_A_and_B_20230108_171638.jpg)
- [Station layout, platforms and exit destinations](https://landtransportguru.net/bayfront-station/)
- [LTA wayfinding design reference](https://www.lta.gov.sg/content/dam/ltagov/who_we_are/statistics_and_publications/books/pdf/REthink_190918web.pdf)

## Rebuild and verify

Set `BLENDER_BIN` to the Blender 5.1.2 executable. On the guarded runner, also set `BLENDER_GUARD_DYLIB` to the supplied guard. Run `sh source/build.sh` from this folder to generate the four GLBs and six-view Cycles CPU sheets. The macOS atlas and sheet renderer requires Swift and AppKit. Run `node source/verify.cjs` with the repository's installed dependencies to validate the GLBs and regenerate `models.json`.
