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
