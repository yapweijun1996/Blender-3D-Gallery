# Commerce hub: payment, analytics and automation modules

Extends BRIEF.md; its rules, layout and contract apply (local `bpy` only, no image textures, same units,
shared `plinth()` and `Fx_*` helpers from `source/common.py`, neutral light-grey inner tier). Anchors:
`reference/anchor-{payment,analytics,automation}.webp`, 1536x1024. Match camera yaw, elevation and framing.
Scripts: `source/build_{payment,analytics,automation}.py`. Start after the delivery and warehouse scripts
are in place, so only one writer edits `common.py` at a time.

## Budgets (hard, including plinth and effects)

| Module | Triangles | GLB | Primitives |
| --- | --- | --- | --- |
| payment | 5,000 | 150 KB | 14 |
| analytics | 4,500 | 140 KB | 14 |
| automation | 6,000 | 180 KB | 16 |

These keep the seven modules under 100,000 triangles and 3 MB with room for the connecting lines.

## payment

Three floating rounded cards stacked with gaps: dark sage at the bottom, amber in the middle, sage on top.
Top card: gold chip with contact grooves, four short number bars, one longer name bar, contactless arcs, and
a network mark in the lower right. Lower cards: one pale bar each. Soft contact shadows between cards
(unlit vertex-alpha helpers). Separate objects for animation: `Card_Top`, `Card_Middle`, `Card_Bottom`.

Network mark: do not reproduce a real payment brand. Use an original mark (a small citrus-slice disc)
unless the owner decides otherwise.

## analytics

Extra sage third tier on the inner plinth. Three rounded bars of rising height: cream, light sage, amber.
Behind them a translucent frosted panel with a small four-bar icon, two text lines and a rising line with
three round nodes. Panel uses alpha blending; icon and line are thin geometry just in front of it.
Separate objects: `Bar_Low`, `Bar_Mid`, `Bar_High` (origin at base, for grow animation), `Chart_Line`,
`Panel_Glass`.

## automation

Rounded sage cube machine: amber indicator pill on top, amber framed output slot with warm inner glow, a
card sliding out with a green stripe, a decorative square code and five barcode bars, white gear icon and
the geometry text "Automation" on the right face, light-green swoosh below it. The square code is a
decorative pattern that must not encode data. Separate objects: `Machine_Body`, `Output_Card` (origin at
the slot, for slide animation), `Indicator`.

## Done

Same as BRIEF.md: GLB, EEVEE render and report per module, budgets met, validator clean, compared with the
anchor in the browser, at most three redo rounds, differences recorded in REVIEW.md.
