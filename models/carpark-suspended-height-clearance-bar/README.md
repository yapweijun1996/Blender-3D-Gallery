# Carpark Suspended Height-Clearance Bar

An original static exhibit of a suspended overhead warning bar in a short Singapore-inspired car park entrance. The short chain runs use real alternating closed links and separate steel eye and plate assemblies. Two square piers support the original concrete section; the unnumbered signage and floor cue are fictional. No real clearance, compliance, load, certified hardware or safe vehicle movement is represented. It is not a construction, installation, adjustment or driving guide.

## Context references

- [Singapore Land Transport Authority, Code of Practice on Vehicle Parking Provision](https://www.lta.gov.sg/content/dam/ltagov/industry_innovations/industry_matters/development_construction_resources/vehicle_parking/pdf/cop_on_vehicle_parking_provision_in_development_proposals_2019_edition.pdf): local documentation of the suspended bar fixture type at car park entrances; no dimensions or official visual design borrowed.
- [Post Guard, Height Guard](https://www.postguard.com/product/4-5-height-guard/): manufacturer documentation of chain suspension as a general subtype, not a Singapore product attribution or copied design.

Each link, eye, mounting stem, plate and structural panel is editable. Blender +Z is up; Gallery GLB +Y is up and +Z front. Geometry is original, and all materials are local vertex colours or values without external media.

## Reproduce and check

Run from this directory with Blender 4.3.2:

```sh
blender -b --python-exit-code 4 --python generate.py -- --output ./generated
blender -b --python-exit-code 5 --python verify_blender.py -- ./generated
node verify.mjs ./generated/exports/carpark-suspended-height-clearance-bar.glb
```

Use `--skip-render` to generate only the editable native file and static GLB.
