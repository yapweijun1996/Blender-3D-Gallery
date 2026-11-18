# Modular chibi dress-up: product spec (single source of truth)

Status: v0.1, 2026-11-18, from the owner's brief. This file is the reference for the dress-up
demo in the Blender 3D Gallery and for later reuse in the GJH Virtual Mall (version 11 web page)
and a planned Singapore GTA-style web game. Acceptance gates: `docs/chibi-modular-game-checklist.md`.
Tool knowledge: `docs/tripo-settings-and-experience.md`. Pipeline: `docs/gjh-modular-chibi-tripo-pipeline.md`.

## 1. What the visitor can change

| Slot | Count | Notes |
| --- | --- | --- |
| Gender / body | 2 | male and female bodies; separate body meshes are acceptable if the fit needs it. Same 65 `mixamorig:*` skeleton so clips are shared |
| Hair | 4 | 2 male styles, 2 female styles |
| Expression | 4 | for example neutral, happy, surprised, sad; face morph targets or swappable face textures |
| Top | 4 | per body if needed |
| Bottom | 4 | |
| Shoes | 4 | |
| Optional later | | hat, glasses, backpack, held items |

Choices are saved locally and restored on reload; the demo must also work without saved state.

## 2. Actions

Run, walk, jump, dance, wave (greeting), hold an object (carry a small prop in the hand, using a gesture such as grip small),
sit down on a chair (a chair prop is part of the demo; the character sits normally and can stand up again), plus idle.
Hand gestures from `hand_gestures.glb` layer on top of any action.

## 3. Rules that every asset must pass

- Same skeleton and bone names for every body and module; one mesh-only skinned GLB per module.
- Motion gate: zero garment vertices and zero triangle overlaps against the posed body in every clip, including sit.
- Independent review of renders by a different model for every item; at most 3 redo rounds, then record the reason.
- Budgets: body 5k to 10k triangles, hair 1k to 3k, outfit 2k to 6k, shoes up to 3.5k, whole character at most 20k, textures at most 1024 px.
- Licence of every source (Tripo, AI reference image, font) is recorded, not assumed.

## 4. Build phases (each phase ends with measured gates, a local commit and a push to main)

1. Framework (in progress): demo route `?page=chibi-dressup`, module manifest, loader that binds modules to the body skeleton by bone name,
   clip player, gesture layer, saved config, tests. Uses the modules that exist today.
2. Hair: bob (female) in redo, three more styles; modules from the Tripo bob pipeline and new Tripo/Studio generations.
3. Bodies and expressions: male and female base bodies, four expressions.
4. Outfits: four tops, four bottoms, four shoes, each through the motion gate.
5. Actions: carry-object and sit-on-chair clips and props; verify against all modules.
6. Integration notes for the GJH Virtual Mall (version 11) and the future GTA-style game, written as a reusable template.

## 5. Open items and known facts

- Current body: `output/modular-chibi-parts/hand-gestures-astra/base_body.glb` (hand-repaired, 9,512 triangles, 65 joints); the gesture library is in its second redo round.
- Garment generation by Blender scripts did not converge on zero overlap in three rounds for the T-shirt; the hoodie (Tripo) and the shoes are in their last rounds.
- Studio segmentation plus AI completion of a clothed chibi gave 11 very dense parts (6k to 861k triangles) that still have open boundaries,
  so they need retopology and closing in Blender before they can be modules.
