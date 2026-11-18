# GJH v11 interior anchors

Use one GLB for the active tier at each entrance. Model units are metres. All files are self-contained.

Metres [x,y,z], bottom-centre at finished installation; datum is slot-centre at Y=0. Normalise source pivots/front axes at import. yaw_deg is right-handed about +Y. Facing +Z is toward concourse. Envelope [width,height,depth] before yaw. A fitted assembly includes supports and adapters required to attain the indicated top socket; preserve physical product proportions.

Create a slot parent with the world translation and yaw below. Attach the GLB at its slot-local translation and yaw with unit scale. Rotations follow the right-hand rule about +Y. Envelopes are design limits before rotation.

| Store | Anchor | Slot-local XYZ (m) | Local yaw (°) | Parent world XYZ (m) | Parent yaw (°) | Envelope WHD (m) |
|---|---|---|---:|---|---:|---|
| S01 New Moon | collector-triptych | [0, 2.47, -3.46] | 0 | [-10.0, 0, -6.0] | 0 | [3.95, 2.3, 0.7] |
| S02 MILI | hawker-stall-exhaust-hood | [0, 2.38, 0.5] | 0 | [0.0, 0, -6.0] | 0 | [2.65, 1.35, 1.4] |
| S03 GOGO | ice-cream-cart-potong | [-2.35, 0.025, 2.05] | 12 | [10.0, 0, -6.0] | 0 | [2.0, 2.6, 1.25] |
| S04 Borsch Med | patch-folio | [-0.48, 0.081, -0.63] | 7 | [20.0, 0, -6.0] | 0 | [2.38, 2.35, 1.12] |
| S05 Pien Tze Huang | specimen-drawers | [0, 0.081, -4.38] | 0 | [30.0, 0, -6.0] | 0 | [4.2, 2.98, 1.05] |
| S06 Flying Wheel | noodle-loom | [-0.65, 0.081, -0.83] | 3 | [-20.0, 0, 4.0] | 90 | [2.45, 2.96, 1.05] |
| S07 Gu Long | stacked-can-pyramid | [-0.55, 0.48, -0.85] | -8 | [-20.0, 0, 12.0] | 90 | [1.65, 2.45, 1.65] |
| S08 Skippy | peanut-butter-jar-stand | [-0.58, 0.58, -0.76] | 0 | [-20.0, 0, 20.0] | 90 | [1.65, 2.15, 1.05] |
| S09 SPAM | conveyor-belt | [-0.72, 0.081, -1.1] | 12 | [-20.0, 0, 28.0] | 90 | [2.65, 1.6, 1.02] |
| S10 California Mexico | nacre-cradle | [-0.45, 0.081, -1.4] | -7 | [-20.0, 0, 36.0] | 90 | [2.6, 2.62, 1.24] |
| S11 Hormel | packing-station | [-0.56, 0.081, -1.05] | 0 | [-20.0, 0, 44.0] | 90 | [2.62, 2.15, 1.12] |
| S12 Zeria | opal-index | [-0.52, 0.081, -1.2] | -5 | [40.0, 0, 4.0] | -90 | [2.55, 2.46, 1.05] |
| S13 Sony | headphone-display-stand | [-0.64, 0.43, -1.05] | 8 | [40.0, 0, 12.0] | -90 | [1.12, 2.6, 0.75] |
| S14 LG | tv-wall-mounted | [-0.62, 1.03, -3.99] | 0 | [40.0, 0, 20.0] | -90 | [3.65, 2.08, 0.3] |
| S15 Casio | grand-piano | [-1.05, 0.081, -1.02] | -22 | [40.0, 0, 28.0] | -90 | [1.95, 2.38, 2.75] |
| S16 GP | eyelet-rail | [-1.56, 0.081, -1.28] | 5 | [40.0, 0, 36.0] | -90 | [1.65, 2.55, 0.9] |
| S17 Gigaset | telephone-alcove | [-0.55, 0.081, -2.95] | -5 | [40.0, 0, 44.0] | -90 | [2.15, 2.86, 1.25] |

Rights and transformations accompany each file in [manifest.json](manifest.json).
