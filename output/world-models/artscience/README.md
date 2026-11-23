# Marina Bay landmarks — set 2

Six static Blender 5.1.2 game assets in binary glTF. Units are metres, +Y is up, and the main frontage faces +Z. The origin is the horizontal centre of each asset's footprint at its lowest structural point. Each named part is a separate mesh node. Materials use the requested PBR names and flat factors. The GLBs contain zero textures.

| Asset | Architectural features |
|---|---|
| ArtScience Museum | Ten individually lofted white FRP gallery fingers, roughly 21–60 m at the tips, with clipped glazed ends. The centre has a recessed rainwater dish, open oculus and raking diagrid supports. A sloped glass pavilion faces south over the reflecting lily pond and promenade. |
| Helix Bridge | The 280 m centreline follows a plan arc. The 6 m wide deck spans between tapered tripods and approach abutments. Six outer and five opposing inner stainless tubes form the cage. Four bay-side cantilever pods, glass railings and alternating glass and metal shades are individually represented. |
| Supertree Grove | The 50 m, 35 m and 25 m trees have concrete cores, vertical planting, branching steel crowns, cross ties and open dish silhouettes. The tallest has a glazed observatory and rooftop railing. |
| OCBC Skyway | A 20 m curved span with a dark deck, under-deck beams, amber handrails and steel cable infill. Place it at the required elevation when assembling a scene. |

Lengths measured along curves differ from the axis-aligned dimensions in `models.json`. The GLBs are low-poly reconstructions from public photographs and published dimensions. Fine cladding seams, lattice members, plants and handrail mesh are simplified within the triangle budgets. The pavilion, pond footprint, exact finger plan and tree variations use interpreted dimensions.

## Build and verification

Run the supplied guarded Blender 5.1.2 binary in background mode with `-noaudio -t 2 --python-exit-code 1 --python build_models.py`. It exports all six models and renders from the re-imported GLBs using Cycles CPU and two fixed threads. Pass asset names after `--` to rebuild specific models. `--export-only` and `--render-only` select a single stage.

Each contact sheet reads left to right. The top row is front, right and rear. The bottom row is front three-quarter, rear three-quarter and top. For the Helix Bridge the bottom centre is a close-up of a viewing pod and adjacent cage. The script records the exact view list and GLB and render hashes in `renders/evidence.json`.

Run `node validate_models.mjs` after rendering. It uses the repository's `gltf-validator`, checks exported geometry and budgets, and regenerates `models.json` from the delivered GLBs.

The six-view review checked the museum's ten clipped skylights and oculus, the bridge's paired helices and four pods, and the trees' lattice and concrete profiles. Revisions exposed the museum skylights and observatory glazing, varied the living wall geometry, and connected the Skyway posts to the deck. An independent reviewer checked the revised features against the reference photographs.

## Architectural references

- [Safdie Architects project photographs, section and geometry diagrams](https://www.safdiearchitects.com/projects/marina-bay-sands-artscience-museum) and [Marina Bay Sands factsheet](https://www.marinabaysands.com/content/dam/singapore/marinabaysands/master/main/home/company-information/media-centre/factsheets/artscience-museum.pdf)
- [COX Helix Bridge photographs](https://www.coxarchitecture.com.au/project/the-helix-bridge/?discipline=architecture) and [steel construction case study with Arup drawings](https://worldstainless.org/wp-content/uploads/2025/02/Helix_Pedestrian_Bridge.pdf)
- [Gardens by the Bay Supertree Grove and Observatory](https://www.gardensbythebay.com.sg/en/learn-with-us/explore-resources/articles/supertree-grove-and-supertree-observatory.html) and [OCBC Skyway reference photograph](https://cdn-imgix.headout.com/media/images/3fe5e31c1fed7ffafb6dbdd07aad0fca-OCBC%20skyway.jpg)
