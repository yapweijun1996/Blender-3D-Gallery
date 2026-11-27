# Independent review

Author of the scripts: Codex CLI `gpt-6.2-sol`. Reviewer: Claude Code, comparing renders with the anchors.
Scripts were reviewed for file, network and process access, then run through the Blender MCP in Blender 5.1.2.
Khronos validator: both GLBs 0 errors, 0 warnings. Redo rounds used: 3 of 3. Style approval: pending.

## Open differences after round 3, largest first

Web view uses scratch lighting chosen by the reviewer; it is not the gallery viewer or a final demo.
Fixed since round 2: contact shadow, floor glow, ring line and shop interior warmth are now carried by the
GLB (unlit vertex-alpha helpers); even cream backdrop; stocked shelves behind the door.

1. Web view: the sage plinth reads lighter and mintier than the anchor (scene lighting to be set by the demo).
2. Ring halo and floor glow are weaker and narrower than in the anchor.
3. Paper and ceramics look flatter: no soft ambient occlusion between objects.
4. Bag side folds show hard triangular shading facets.
5. Blender render: shop glazing and interior read darker and greyer than the anchor.
6. Shop: the inner plinth tier reads pink-beige; the shop anchor shows neutral light grey while the bags
   anchor shows warm cream. One shared `plinth()` means one colour: owner decision.

Measured: bags 7,928 triangles / 180,984 bytes / 18 primitives; shop 23,205 triangles / 624,304 bytes /
39 primitives. Not verified: physical-device performance, alpha sorting in motion. Still
views at -40, -20, 20 and 40 degrees showed no visible seams in the helper meshes.
Draw calls in the scratch view: bags 21, shop 45; the full scene should merge static parts.

## All seven modules (2026-11-27)

Redo rounds: delivery and warehouse 1 of 3; payment, analytics and automation 0 of 3.
Ambient occlusion is ray-cast in Blender onto an unlit vertex-alpha layer over the inner plinth
(`Fx_AmbientOcclusion`; the interior floors and the analytics third tier receive none). Directional shadows
are real-time in the viewer. `build()` adds the bake allowance (3,200 triangles, 110 KB, 1 primitive) to every module's
limits. Against the budgets in BRIEF-modules3.md, payment is over (6,801 vs 5,000 triangles; 163 vs 150 KB)
and analytics is over (6,884 vs 4,500; 161 vs 140 KB); automation is slightly over on triangles
(6,133 vs 6,000). The seven-module total still fits the 100,000 triangle / 3 MB target.

| Module | Triangles | GLB bytes | Primitives |
| --- | --- | --- | --- |
| bags | 10,884 | 250,928 | 19 |
| shop | 26,049 | 690,420 | 40 |
| delivery | 19,099 | 470,488 | 31 |
| warehouse | 23,088 | 701,676 | 28 |
| payment | 6,801 | 163,108 | 15 |
| analytics | 6,884 | 161,244 | 13 |
| automation | 6,133 | 160,672 | 16 |
| total | 98,938 | 2.6 MB | 162 |

All GLBs: Khronos validator 0 errors, 0 warnings. Totals leave about 1,000 triangles for connecting lines,
so the composed scene should share one plinth and merge static parts.

Real-time shadows (PCF, 2048 map): one frame at 1536x1024 took 1.4-2.2 ms without and 2.1-4.1 ms with
them in headless Chromium on a Mac, per module alone. Draw calls with shadows sum to 323 across modules.
Shadows are a modest gain: mean colour error against the EEVEE render fell by 0.1-3.7 levels, and
the millisecond timings are close to noise. The harness now uses radius 14 and intensity 0.55; the automation
shadow still reads as a flat patch. Phone performance is NOT VERIFIED.

Open differences: payment cards are smaller than the anchor and sit closer together; shared plinth is
thicker than in the delivery, warehouse and small-module anchors; warehouse conveyors are shorter than the
anchor; paper and card surfaces have less soft gloss.

## Composed demo (2026-11-27)

Production build, CSP enforced: seven modules load at 1440, 768 and 375 px; three languages; label focus and
Escape; reduced motion still; WebGL context released on leave; failed module retry. Steady frame 130 draw
calls (323 for the unmerged modules with shadows). Headless Chromium on a Mac GPU at 390x844 held 16.7 ms
p50/p95 while animating and orbiting at 1x, 4x and 6x CPU throttle; models ready 5.3 s after the demo code on
a 4 Mbps link. Physical phones are NOT VERIFIED.

## Composed-scene anchor and code review (2026-11-27)

The owner supplied a new composed anchor: plinths thinned (0.82 to 0.51), layout re-measured, brighter links
with end nodes, labels with leader pins, brighter lighting. Codex `gpt-6.2-sol` reviewed the first demo
commit: 1 P1 and 10 P2, all addressed and covered by `npm test` (1117) and `npm run test:commerce`; the fixes
were not re-reviewed. Shadows of moving parts refresh every sixth frame.

Open against the new anchor: softer, brighter bloom; the delivery link is curved in the anchor; the shop roof
unit is round with a divided roof there; the card network mark intentionally stays an original citrus disc.
