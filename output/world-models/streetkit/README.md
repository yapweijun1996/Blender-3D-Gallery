# Singapore street furniture kit

Twenty standalone Blender 5.1.2 GLBs for a Singapore streetscape. The models combine published local details with estimated dimensions for unspecified parts. The shelter represents a roadside shelter served by SBS Transit, using a selection of actual Blk 502 services and stop code 28401. Its structure is a representative shelter type.

## Placement

- glTF uses metres, Y-up and +Z toward the main front. Lay road markings in the XZ plane with travel toward +Z. The left and right arrows are handed relative to that travel direction.
- The scene origin is at the ground plane, centred on the base for poles and on the placement footprint for modules. Named mesh nodes retain their own translations so the complete assembly can be instantiated as exported.
- The road-light pole and arm reach 10 m. Gantry uprights are 16 m centre to centre, with 5.7 m clearance below the sign. The kerb, railing, covered walkway and tactile strip measure 4 m, 3 m, 6 m and 4 m along X.
- The flat PBR material names are the game-facing categories. Colour variations within a category use glTF `COLOR_0`. To replace a finish entirely, an engine can override the vertex colours as well as the base colour factor.
- Each marking is an independent mesh with a centred pivot. Its node translation places it in the asset's preview layout. Reset that translation when placing the mesh alone and apply a small render offset in the game when layering it over a road.

## Modelled details

| GLB | Features |
| --- | --- |
| `road_light.glb` | Tapered galvanised shaft, access plate, swept arm and cast cobra-head luminaire with an underside lens. |
| `gantry_sign.glb` | Concrete plinths, paired truss chords, diagonal bracing, sign hangers and a text-free green sign with down arrows. |
| `direction_sign.glb` | Twin posts, divided green board, blue PIE inset, expressway pictogram, Jurong legend and directional arrows. |
| `speed_sign.glb` | Red-rimmed 50 km/h plate with geometric numerals and a galvanised post. |
| `keep_left.glb` | Blue circular plate with a white down-left arrow and white keyline. |
| `ped_signal.glb` | Visored red and green pedestrian aspects, separate countdown enclosure and yellow push-button unit. |
| `mast_signal.glb` | Service hatch, tapered cantilever arm and three independently named, visored vehicle signal heads. |
| `bus_shelter_sbs.glb` | Road-facing Jurong West Ave 1 / B07 address plate, curved metal canopy with cantilever ribs, glazed windbreak, slatted bench and SBS route panel. |
| `bus_stop_flag.glb` | Blue bus pictogram, two-tone green stop address and green service tiles on a galvanised pole. |
| `kerb_drain.glb` | Chamfered concrete kerb, visible joints, recessed inlet, lintel and cast bars. |
| `drain_grate.glb` | Cast frame, open slots and transverse crossbars. |
| `manhole.glb` | Round, bevel-edged cast cover with raised chequer treads. |
| `guard_rail_3m.glb` | Leaf-green roadside railing with two picket bays, anchor plates and an ID plate. |
| `bollard.glb` | Bevel-capped steel post with a yellow reflective collar. |
| `bins.glb` | Blue recycling bin with a recessed intake, paired with a hooded litter bin with an access door. |
| `hydrant.glb` | Red pillar, flared foot, bonnet, operating nut and two opposed capped outlets. |
| `covered_walkway.glb` | Double-row columns, curved roof, secondary ribs, knee braces, gutters and downpipes. |
| `kiosk_substation.glb` | Small electricity service cabinet with a rain hood, plinth, hinges, lock, louvres and electrical warning plate. |
| `tactile_strip.glb` | Seven 300 mm ochre tiles, four ribs per tile and 300 mm flush paving gaps. |
| `road_markings.glb` | White zebra, stop line and three arrows, plus a yellow box and a part-day bus lane with the yellow BUS stencil. |

## Rebuild and review

The Blender launcher uses the supplied guarded runtime. Set `STREETKIT_BLENDER_ROOT` to another directory with the same guarded Blender layout if the supplied runtime moves.

```sh
zsh run-blender.zsh --stage all
node validate.mjs
```

The [manifest](models.json) records exported triangles, byte lengths, X/Y/Z dimensions, material and part names, hashes and the repository validator result. Each [contact sheet](reviews/) renders the exported GLB again in Cycles CPU with two threads. Read the tiles in order from top left as front, right, rear, left, top and oblique.

## Singapore references

- Geometry and colour conventions for signs, crossings and signals. [Traffic Police Basic Theory of Driving](https://www.police.gov.sg/docs/spf/spf/knowledge-hub/traffic/bt-eng-24126.pdf), [Traffic Signs Rules](https://sso.agc.gov.sg/SL/RTA1961-R33)
- Gantry clearance, road fittings, directional panels and green railings. [LTA Civil Design Criteria](https://www.lta.gov.sg/content/dam/ltagov/industry_innovations/industry_matters/development_construction_resources/pdf/TransportInfrastructure/civil_standards/pdf/EGD09106A3-Overall.pdf), [LTA road-element specifications](https://www.lta.gov.sg/content/ltagov/en/industry_innovations/industry_matters/development_construction_specifications_resources/Transport_Infrastructure_Design_Criteria_and_Specifications.html), [LTA railing details](https://www.lta.gov.sg/content/dam/ltagov/upcoming_projects/SDRE/Revised/SDRE14-5-RAL_1-2-MAY_2019.pdf)
- Stop address panels, shelter features and the double-pole curved linkway type. [LTA Commuter Infrastructure annex](https://www.lta.gov.sg/content/dam/ltagov/industry_innovations/industry_matters/development_construction_resources/pdf/TransportInfrastructure/IDC_revA1_2023/IDC%20VOL%20C%20_AnxAtoF_2025.pdf), [LTA bus shelters](https://www.lta.gov.sg/content/ltagov/en/who_we_are/statistics_and_publications/Connect/bus-stop-shelters.html), [LTA covered-linkway typology](https://www.lta.gov.sg/content/dam/ltagov/industry_innovations/industry_matters/development_construction_resources/Street_Work_Proposals/Standards_and_Specifications/GIS_Data_Hub/gis_data_hub_data_collection_specification_v3.2.pdf)
- Blk 502 shelter ID B07 and selected route IDs. [LTA notice-board locations](https://www.lta.gov.sg/content/dam/ltagov/industry_innovations/industry_matters/regulations_licensing/pdf/cfmPDF/Location_of_Bus_Stops_with_Free_Notice_Boards_2024.pdf), [SBS Transit 99](https://www.sbstransit.com.sg/Service/BusService?ServiceNo=99&ServiceType=Basic), [SBS Transit 185](https://www.sbstransit.com.sg/service/sbs-transit-app?Direction=2&ServiceNo=185), [SBS Transit 198](https://www.sbstransit.com.sg/Service/BusService?Dir=2&ServiceNo=198&ServiceType=Basic)
- Bus-lane stencil, box line widths and pedestrian countdown colour. [LTA road marking drawings](https://www.lta.gov.sg/content/dam/ltagov/industry_innovations/industry_matters/development_construction_resources/Street_Work_Proposals/Standards_and_Specifications/SDRE/SDRE14-8_RMS_1-14_September_2025.pdf), [LTA traffic-signal typology](https://www.lta.gov.sg/content/dam/ltagov/industry_innovations/industry_matters/development_construction_resources/Street_Work_Proposals/Standards_and_Specifications/GIS_Data_Hub/gis_data_collection_specs_v3.1.pdf)
- Directional tile spacing and rib layout. [LTA tactile-tile update](https://www.lta.gov.sg/content/ltagov/en/newsroom/2024/8/media-replies/ongoing-improvements-to-tactile-tiles.html), [LTA CYC9](https://www.lta.gov.sg/content/dam/ltagov/industry_innovations/industry_matters/development_construction_resources/Street_Work_Proposals/Standards_and_Specifications/SDRE/SDRE17-21_CYC_1-12_September_2025.pdf)
