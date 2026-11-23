# Woodlands Checkpoint game kit

Three modular Blender 5.1.2 assets depict the Singapore side of the Johor–Singapore Causeway. The kit uses the supplied game dimensions and publicly visible architectural cues. It depicts a 60 m frontage and a six-lane bay. Roof depth, rear elevations, equipment details and the selected lane states are game-scale interpretations.

## Modelled features

- **Lane** — 9 m asphalt tile with a 3.3 m clear roadway, a raised chamfered concrete island, black-and-yellow bollards, drainage grilles, a flat-roof glazed booth with a service slider and counter, a standalone inspection kiosk, and a striped 3.2 m boom on a separate hinge housing.
- **Canopy** — 30 m by roughly 8 m shallow blue barrel roof with seams, purlins, four transverse steel trusses, perimeter columns, drainage pipes and soffit fixtures. Its gantry carries six pairs of numbered and arrow/cross signs and six three-aspect lights with two-sided faces. Lanes 3 and 6 are presented closed. Sign numerals and LEDs use geometry and vertex color.
- **Building** — 60 m low white frontage with a curved blue-green curtain wall, mullions, spandrel bands, glazed entrance doors, steps, terrace planting, curved projecting eave, a glazed upper hall, side wings, ribbon windows, and roof service housings.

## Placement and controls

All GLBs use metres, +Y up, +Z front and +Z along the road. The file origin is the center of the ground footprint. Each named node has its own mesh. All materials are flat PBR and use the requested naming palette. All three files are texture-free.

Place the six lane tiles at X = −12.0, −7.2, −2.4, 2.4, 7.2 and 12.0 m under the canopy. The 4.8 m pitch comprises the 3.3 m roadway and 1.5 m island allowance. The roadway center sits 0.75 m to the left of each lane tile origin, directly below its matching gantry station. Canopy supports clear the six tile footprints.

For the boom, rotate the `boom_arm` node about local +Z from 0° down to −90° raised. Its rest-pose pivot is at (0.86, 1.02, 2.65) m in the lane tile, with the arm extending toward −X. Keep `boom_housing` stationary. Individual canopy controls, three-aspect lights and number signs are separate mesh nodes. The `lamp_emissive` material provides common low-level emission and the signal geometry carries the red or green base tint.

## Rebuild and verification

`build_models.py` is the editable procedural source. Run it from the kit directory with the provided Blender 5.1.2 binary and `DYLD_INSERT_LIBRARIES` guard using `-b -noaudio -t 2 --python-exit-code 1 --python build_models.py -- all`. The script also accepts `build` or `render` instead of `all` and optional model stems for a targeted pass.

Run `node validate_models.mjs` to validate all three files against the repository's glTF Validator and regenerate `models.json`. The manifest records triangle counts, bounds, named meshes, materials, byte counts and checksums. Each six-view contact sheet was rendered by reimporting its exact GLB into Blender using Cycles CPU, two threads and 16 samples. Read the panels left to right, with front, right and rear across the top and front three-quarter, rear three-quarter and top across the bottom.

## Visual references

- Curved tinted entrance glazing, projecting fascia and terrace planting. [National Archives of Singapore, Woodlands Checkpoint photograph on page 10](https://www.nas.gov.sg/archivesonline/data/pdfdoc/20180622001/4_Singapore%20Defence%20Technology%20Summit%20Factsheet%20-%20Site%20Visit.pdf)
- Car-clearance context and booth evolution. [SG101, Woodlands Checkpoint](https://www.sg101.gov.sg/resources/archives/woodlands-checkpoint/)
- Contemporary car-counter and roadside scanner details. [CNA, Woodlands Checkpoint car clearance photo report](https://www.channelnewsasia.com/singapore/qr-code-woodlands-tuas-checkpoint-passport-customs-malaysia-clearance-ica-4511441)

## Visual review

Both the author and an independent reviewer inspected all 18 final panels. The review checked the booth and controls, the canopy silhouette and six lane indicators, and the low curved glazed frontage. The revisions closed the building's entrance and roof transitions and moved the canopy supports clear of the outer lanes. The full site includes taller volumes beyond this frontage module. [ICA Annual Report 2011](https://www.ica.gov.sg/docs/ica/ica/ica-annuals/ica_annual_2011.pdf)
