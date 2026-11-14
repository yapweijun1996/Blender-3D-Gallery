# Contract

- Root: `ASSET_DemoBeverageCan`
- Geometry is metric, approximately 0.0665 m diameter by 0.115 m tall at rest (including rim bead).
- Separate editable `MOVABLE_Tab` and `MOVABLE_ScoreFlap` nodes.
- `TOP_AperturePlate` is an annulus over a real inner wall/opening; `BODY_HollowShell` is open at the top and has a hollow interior.
- Clips: `OpenClose` and `Exploded`, each 3 seconds, with rest at 0/3 s and the open state at 1.5 s. `OpenClose` keeps the top attached; `Exploded` may lift the top assembly.
- Fixed budgets: 18,000 triangles, 18 mesh primitives, 1,000,000 GLB bytes, label texture <=2048x1024.
- Fictional, unbranded, original citrus mark only; no copied packaging art.
