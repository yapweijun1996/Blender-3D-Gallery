# Transit Two-Tier Bicycle Tray

An original Singapore transit-inspired parking exhibit with an empty fixed lower bay and a genuinely moving upper tray. In the Gallery, the upper tray first slides horizontally on two captured runners, then pitches down around a carried axle. Only an isolated illustrative animation is demonstrated. There is no bicycle, station replica, lock, assistance mechanism, authentic operational procedure, or capacity/safety claim.

The single `TWO_TIER_TRAY_SLIDE_TIP` clip has two native tracks: `BIKE_UPPER_CARRIAGE.position` and `BIKE_UPPER_TRAY_PIVOT.quaternion`. The runner frame is stationary; the rotating hardware stays on the translated hinge. The GLB uses +Y up and +Z toward the front; Blender uses +Z up and -Y toward the front.

## Context

- [Singapore Land Transport Authority, Walking and Cycling Design Guide](https://www.lta.gov.sg/content/dam/ltagov/industry_innovations/industry_matters/development_construction_resources/walking_cycling_plan/pdf/walking-and-cycling-design-guide.pdf), local double-tier cycle-parking fixture context.
- [Securabike, Double Height with Ramp 2 Bike Rack](https://www.securabike.sg/Shop/Bike-Racks/Double-Height-with-Ramp-2-Bike-Rack-%281%29), generic slide-and-pivot arrangement only; original design, no copied product, dimensions or brand.

## Reproduce and verify the model

Run from this directory with Blender 4.3.2:

```sh
blender -b --python-exit-code 4 --python generate.py -- --output ./generated
blender -b --python-exit-code 5 --python verify_blender.py -- ./generated
node verify.mjs ./generated/exports/transit-two-tier-bicycle-tray.glb
```

Use `--skip-render` if only the Blender source and GLB export are needed. All visible geometry and materials are original, with no external media.
