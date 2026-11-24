# Stair-Side Bicycle Wheeling Channel

An original Singapore-inspired **illustrative** stair section with a single narrow rounded U-shaped wheel channel. Its bed rises continuously between two flush cropped landings with shallow curves at both ends. Six cast stairs and their rails are separately editable; six stepped saddle supports hold the wheel channel. The small painted cycle symbol and plaque are original exhibit marks. There is no standalone bicycle, animation, real location, installation instruction, use or compatibility claim, or accessibility/engineering certification.

- [LTA Cycling](https://www.lta.gov.sg/content/ltagov/en/getting_around/active_mobility/walking_cycling_infrastructure/cycling.html) documents staircase-adjacent bicycle wheeling ramps at selected Singapore pedestrian overhead bridges.
- [LTA Walking and Cycling Design Guide, chapter 5](https://www.lta.gov.sg/content/dam/ltagov/industry_innovations/industry_matters/development_construction_resources/walking_cycling_plan/pdf/walking-and-cycling-design-guide.pdf) confirms the wheeling-channel fixture type and end-transition concept. This exhibit does not reproduce an authority diagram or use official measurements, markings or standard details.

## Source and verification

Blender 5.3.0. In this directory run `blender -b -t 5 --python-exit-code 1 --python generate.py`. Use `-- --review /path/to/stills` for optional evidence of the two joins and top section. Same-version repeated native export reproduced the reviewed GLB byte-for-byte. Illustrative units are metres; Blender +Z up and −Y outward; glTF +Y up and +Z outward. No studio geometry transfers into the export.

- `blender -b stair-side-bicycle-wheeling-channel.blend --python-exit-code 1 --python verify_blender.py` checks the source. Start an empty Blender session and append `-- --reimport` to verify the GLB in Blender independently.
- `node verify.mjs` runs Khronos validation and Three.js physical ray checks of the contact bed, rolled lips and flush handovers. These are geometry checks on the model only, not functional real-world checks.
