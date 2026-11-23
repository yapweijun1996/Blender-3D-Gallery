# Independent QA advisor review

**Verdict — REWORK.** The classic outfit reads clearly as a chibi mall visitor. Sequential wardrobe assembly and locomotion have reproducible functional defects. Hair silhouette and hoodie color placement also differ from the reference.

Reviewed on 2026-11-17 by separate visual, motion, and module reviewers. The Blender 5.1.2 scene contains the Visitor Rig with 19 bones and 38 module slots. The full character GLB has SHA-256 `d95a4d7060361974f03c5f1e788c902f9a037b2a57208ba8f36ec799195fc026`. All 17 entries in the [capture manifest](final-v2/manifest.json), including source, reference, and images, matched their recorded hashes. All 46 archive entries matched their workspace counterparts. This review produced no changes to the source model, exports, or delivery ZIP.

## Functional findings

| Priority | Reproduction and observation | Repair acceptance |
| --- | --- | --- |
| P1 — sequential outfit assembly | When the entire [Three.js example](../../MODULES.md#assembly-in-threejs) runs once per equip, attaching Hat before Jeans introduces duplicate bone names into the next traversal. With Three.js r187, the hat referenced 19 of 19 original bones and the jeans referenced 0 of 19. Rotating the original left thigh by 0.8 radians moved no jeans vertex. Caching the original bone map before the first attachment restored a maximum displacement of about 175 mm. | Equip Hat then Jeans and Jeans then Hat, remove each, and repeat. Every bound joint must resolve to the original character bone by object identity. Animated vertex positions should match the same module equipped alone. |
| P1 — walk and run contact | The motion reviewer sampled every skinned shoe vertex at 121 evenly spaced times per clip in Three.js r187. Relative to the standing sole plane, the deepest walk penetration was 16.0 mm and the deepest run penetration was 20.2 mm. Both shoes penetrated by more than 5 mm at 98 walk samples and 66 run samples. Idle stayed level. | Check full cycles against a visible floor and replay at the intended movement speed. The planted sole should meet the floor without a visible sink or slide through the support phase. Horizontal sliding still needs a runtime speed contract. |
| P1 — sit and stand-up | Both soles finished the sit 47.7 mm above the standing floor and began stand-up at the same height. Both knees emerge through the front of the shorts in the [sit capture](final-v2/pose-sit.png). The shorts are bound only to Root. | Check the full transitions with a seat at the intended height. Verify thigh and shorts motion, waist continuity, seat contact and the intended foot placement with both wardrobe variants. |

## Visual findings

| Priority | Reference comparison | Repair acceptance |
| --- | --- | --- |
| P1 — hair silhouette | The [front](final-v2/front.png) shows several similarly long pointed bangs. The reference has a dominant broad diagonal lock. The [back](final-v2/back.png) has several similarly sized rounded tips in a row. The reference layers unequal locks over a compact darker nape. | Compare the same front, profile and back cameras. Keep both eyes clear, make the main diagonal sweep distinct, and recover the outward side tufts and uneven rear overlaps. Retain the current head-to-body proportions. |
| P2 — hoodie colors | The model has a pale front collar, thin purple cuffs, and a thick purple waistband. The classic reference puts the purple around the neck and across wide cuffs, with a pale hem. | Check all three color boundaries in a full-body front view. |

## Verified scope and budget

The 38 slots comprise 36 default slots and two optional wardrobe items. The [existing per-slot checks](final/module-rig-v3.json) cover single-module rebindings, and [finger checks](final/finger-rig-v2.json) cover all ten fingers independently. The [validator report](final/validation-v3.json) records zero errors and zero warnings for 40 matching GLBs. The [browser check](browser/final/report.json) covers two static views. Full animated outfit combinations and device performance remain unverified.

The default character has 51,543 triangles and 24 materials. The hoodie uses 13,448 triangles, the head 11,100, and the hair 8,876. The sheet suggests 1,500–3,000 triangles for the entire character. If a game asset in that range is required, a separate low-detail design must also address the head and clothing. The optional hat and jeans are excluded from these counts.
