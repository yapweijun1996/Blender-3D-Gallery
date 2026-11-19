# Modular chibi dress-up: progress log

Updated 2026-11-19 (auto manager). Spec: `docs/chibi-dressup-spec.md`. Gates: `docs/chibi-modular-game-checklist.md`.
Rule: push to main when the manager judges it fine; every module needs vertex and triangle motion checks at 0 (or masked, see below)
and an independent image review. Intermediate work lives under `output/modular-chibi-parts/` (not all of it is committed).

## Decisions from the owner (overnight)
- Expressions: face morph targets in Blender. Sit and hold-object: Studio animation presets retargeted, then fixed in Blender.
- Male and female bodies share hair and clothes as much as possible; every combination still needs the poke-through check.
- Garments that cannot avoid the body: hide the covered body regions at runtime (body-region masks), checked by masked checkers plus an exposed-pixel gate.

## Item status
| Item | Source | Status |
| --- | --- | --- |
| Body (neutral, hands repaired, 9 gestures) | CLI P2 + Astra | gesture round 2 review PASS WITH NOTES; in demo |
| Body female / male | Studio + Astra | hand repair and gestures in progress |
| Hair bob (female) | Tripo CLI + Astra v2 | checks 0, review PASS WITH NOTES; in demo |
| Hair spiky (male), side part (male), twin tails (female) | Studio + Astra | fitting in progress |
| Top T-shirt, jacket, dress | Studio + Sol | fitting in progress |
| Top hoodie | Tripo CLI + Sol | 3 rounds failed; to be retried with body masking |
| Bottom cargo pants, jeans | Studio + Sol | fitting in progress |
| Shoes sneakers (bpy), high-top, boots, sandals, slip-ons | bpy / Studio + Sol | sneakers round 3 and Studio shoes in progress |
| Body-region masks and masked checkers | Sol | in progress |
| Expressions (4) | Blender morphs | not started |
| Sit on chair, hold object | Studio presets + Blender | sit preset exported, not yet fixed |
| Demo page `?page=chibi-dressup` | Sol | framework committed locally, not pushed |

## Master task list (do not forget; owner request 2026-11-19)
Owner words: finish the full modular human body first, then apply it to GJH v11 (https://yapweijun1996.github.io/Webpage-Design-Gallery/demos/corporate/gjh/v11/),
design different outfitted characters (many NPC types), interior-design models via the Tripo Studio web skill, and push to main on GitHub for BOTH projects.

### Project A: Blender-3D-Gallery (this repo)
- [ ] Bodies: neutral (done), female, male (hands, gestures, textures at most 1024 px)
- [ ] Hair x4 (bob done; spiky, side part, twin tails in fitting)
- [ ] Tops x4 (T-shirt, jacket, dress, hoodie via body masking), bottoms x4 (cargo pants, jeans, plus two more), shoes x4 (sneakers, high-top, boots, sandals, slip-ons)
- [ ] Body-region masks and masked checkers; exposed-pixel gate
- [ ] Expressions x4 (face morphs); sit on chair and hold-object clips with chair and prop
- [ ] Dress-up demo `?page=chibi-dressup`: gender switch, hair, expression, top, bottom, shoes, actions (run, walk, jump, dance, wave, hold, sit)
- [ ] Docs, checklist, KB skills updated after each phase; push to main

### Project B: Webpage-Design-Gallery, demos/corporate/gjh/v11
- [ ] Audit v11 (render, layout, performance) and write docs/v11-npc-audit.md
- [ ] About 15 NPCs on screen with varied outfits, routes, idle behaviours; manifest driven; mobile safe
- [ ] Layout and interior redesign (owner allows layout changes)
- [ ] Interior models made with Tripo Studio web: public seating and planters, shop display racks and counters, lighting and decor, signage and service desks (12 reference images in progress)
- [ ] Tests (browser_gjh_demos.py etc.), PWA cache, README, version bump; push to main after the repo verification commands pass

### Cadence
Report in the session every 20 minutes; push each verified piece; record every decision in memory and docs.

### v11 decisions (owner, 2026-11-19)
- NPC types: shoppers and customers, shop staff and service staff (uniforms, counter, entrance), security guards and guides. No family or child bodies.
- Gender: half male, half female, all in the unified chibi style; roles are told apart by outfit and hair only.
- Interior style: oak wood, matte dark green, brushed brass (the 12 reference images follow it).
- Keep all real brand names, products and official links in v11 untouched; change only layout, furniture and NPCs.

## 2026-11-19 update: clothing and corrected clips shipped in the demo

- Body self-intersection fix (arms into hips, shins into thighs): `output/modular-chibi-parts/body-fix/motion_fixed.glb`; the demo clips file is its skeleton-and-animation extract (`scripts/strip-motion-glb.py`). Hair, sneakers rechecked: 0 vertices and 0 triangle pairs in all clips.
- Round 3 results against the corrected clips (own checkers + independent render review):
  - jeans: 0/0, min 0.7 mm, PASS WITH NOTES, in the demo.
  - T-shirt: 0 in rest, wave, jump, idle, nod; penetration up to 0.8 mm in walk and run and 0.3 mm in dance (small, accepted by the owner's "small flaws are fine"), PASS WITH NOTES, in the demo.
  - dress: 0/0 but minimum clearance 0.1 mm (limit 0.5 mm), PASS WITH NOTES; not in the demo yet because the demo has no slot-exclusion rule (dress would clip the jeans).
  - cargo pants: FAIL (run 2 vertices, 38 pairs; reviewer saw black slits). Bomber jacket: FAIL (walk 7 vertices, up to 12.7 mm). Both stay out; three rounds are used up.
- Budget note: the full set (body 9,512 + hair 2,972 + top 4,699 + bottom 4,704 + sneakers 3,492 = 25.4k triangles) exceeds the 20k whole-character target; fine for the single-character demo, too heavy for a crowd without LODs or decimation.
- Dress is now in the demo with a slot-exclusion rule (manifest `excludesSlots`; it hides and disables the bottoms).
- Hair round 3 (corrected clips, own checkers, independent render review): side-part 0/0 in all clips, PASS WITH NOTES (faint dark hairline, slightly faceted nape) → in the demo. Twin-tails 0/0 but review FAIL (near-black slits along the temples, faceted nape) after three rounds → not shipped; reason recorded, needs a different method (for example a fresh Studio generation) rather than a fourth redo.
- Expressions are in the demo: `models/chibi-dressup/base_body.glb` is now `output/modular-chibi-parts/expressions-astra/body_expressions.glb` (same 65 joints, 9,512 triangles, three morph targets); the three colour maps (about 0.8 MB each) load only when an expression is first chosen. The choice is saved in the local config. Not yet reviewed by an independent model beyond the Astra contact sheet; the screenshot check shows a clear surprised face and unchanged hair.
- Sit and hold-a-cup runtime (local, not pushed yet): `sit` plays sit_down, loops sit_idle on the chair, and plays stand_up when leaving; `hold` shows the cup in the right hand; all clip changes crossfade 0.3 s; the rig now retargets authored position and scale tracks (`actions.glb`, `props/chair.glb`, `props/cup.glb`). Hair and sneakers pass the four new clips (0 vertices, 0 triangle pairs). **T-shirt, jeans and dress fail them** (sit: 65 to 300 vertices, up to 16 mm; hold: 12 to 143 vertices, up to 12.8 mm), so Sol refits (`studio-modules/<name>/round4/`) are running; push after they pass the eleven-clip gate. Only one of the four required hold poses (small item, one hand) exists; big box, shopping bag and shelf pick-up are still to do.
- v11 reuse constraints measured from docs/gjh-v11-npcs.md: per GLB at most 1.5 MiB, 6 MiB for the whole manifest, textures at most 1024 px, outfit at most 20,000 triangles and 12 primitives. The demo's T-shirt and jeans (about 3.2 MB each) and the full set (25.4k triangles) do not fit, so a v11 "NPC LOD" set is needed: lighter body (about 4k), garments about 2k each, hair and shoes about 1.5k, textures 512 to 1024 px, rechecked with the motion gate. Planned after the eleven-clip garment refits (round 4) pass.
- 2026-11-19 interiors: all 12 reference props were generated and exported from Tripo Studio (GLB, 1k texture, quad retopology 1,500 polygons requested) to `output/v11-handoff/interiors/raw/`: bench, counter, wall art, service desk, pendant lamp, floor lamp, planter, clothes rack, ottoman, shelf, sign, display table. Khronos: 0 errors, 1 warning each (2 for the desk). Triangles 2.3k to 2.8k except the service desk (9,374, so its polygon field did not take 1500). Sizes 1.0 to 2.6 MiB except the desk (5.5 MiB). Still to do in Blender: decimate the desk, compress textures, fit scales and place in the v11 layout, then the v11 probes.
- 2026-11-19 actions: corrected sit/hold clips `output/modular-chibi-parts/actions-fix/actions_fixed.glb` (body overlap 24,046 to 3,116 pairs, about 15 residual neutral-body knee pairs); jeans refit v5 passes all eleven clips (0/0, min 1.03 mm), independent review PASS WITH NOTES. T-shirt and dress refits are still running.
