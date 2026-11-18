# Modular chibi for the web: acceptance checklist

Status: v0.1, 2026-11-18. Built from the GJH modular chibi work (Tripo CLI, Tripo Studio,
Blender, Codex). Every line is a gate: PASS needs a number or a render, not an opinion.
Related: `docs/gjh-modular-chibi-tripo-pipeline.md`, `docs/tripo-settings-and-experience.md`.

## 1. Base body

- [ ] 5,000 to 10,000 triangles, height 1.0, feet on z=0, faces glTF +Z, left side is +X.
- [ ] T-pose, palms down, thumb forward, five separate fingers with visible gaps.
- [ ] Left-right mirror error below 0.001.
- [ ] 65 `mixamorig:*` bones (Hips, Spine to Head, arms, legs, toes, 4 segments per finger chain).
- [ ] Every vertex weighted, at most 4 influences, no finger-to-finger weight bleed (count 0).
- [ ] Exported GLB: 1 mesh, 1 skin, 65 joints, no animation.

## 2. Fingers and gestures (flexible hands)

- [ ] Gesture library for both hands: fist, open relaxed, point, thumbs up, peace, OK, grip small, pinch, open wide.
- [ ] Per gesture, measured: thumbs up (thumb tip above the other tips, other four curled), OK and pinch (thumb tip to index tip under 1 cm), fist (all tips within 2.5 cm of the palm), grip small (gap 1.5 to 3 cm).
- [ ] 0 non-adjacent triangle intersections in every gesture; render palm, back and thumb side for both hands and look at them.
- [ ] Gestures are single-frame clips on finger bones only, so they layer on top of any body animation.

## 3. Natural movement (game-like)

- [ ] Clips on the same bone names: idle, walk, run, wave, jump, nod, dance (existing set in `models/tripo-chibi-motion/motion.glb`).
- [ ] No foot sliding or floor penetration in walk and run; arms swing; head stays level.
- [ ] Skinned shoulders, elbows, hips and knees look smooth in the extreme frames (render them).
- [ ] Two instances animate independently (SkeletonUtils.clone, one mixer each).

## 4. Modules (hair, hat, top, bottom, shoes, accessories)

- [ ] One mesh-only skinned GLB per module, same 65 bone names, at most 4 influences, 1024 px textures.
- [ ] Budgets: hair 1k to 3k tris, outfit 2k to 6k, shoes 1k to 3.5k, accessory 0.2k to 1.5k, whole character at most 20k.
- [ ] MOTION GATE (the one that failed most often): for rest, walk, run, wave, jump, idle, nod and dance, measured over every frame:
  - garment vertices inside the posed body = 0 (`motion_check.py`),
  - garment-triangle against body-triangle overlap pairs = 0 (`motion_check_tri.py`),
  - minimum signed distance at least 0.0005 m, rest clearance in the torso at most 0.02 m (hoodie 0.03 m).
  A T-pose pass alone is worthless: three garments passed T-pose and failed motion by 30 to 190 vertices.
- [ ] Visual gate: six views (front, two three-quarters, side, back) rendered and viewed; no daylight between hair and head, no seams, eyes unobstructed.
- [ ] Independent review by a different model that only sees renders and numbers; every FAIL goes back for a fix (maximum 3 rounds).
- [ ] Licence of the source (Tripo output, AI reference image, font) recorded; never inferred.

## 5. Web runtime and demo

- [ ] Load 3D only when the page is opened; loading, error and accessibility fallbacks.
- [ ] Modules bind to the body skeleton by bone name; swapping one module never reloads the body.
- [ ] Config (module ids and clip) saved locally and restored after reload.
- [ ] Desktop and 390 px mobile screenshots, no horizontal overflow, no console errors.
- [ ] `npm run validate:assets`, `npm test`, `npm run build` exit 0; Khronos validator 0 errors and 0 warnings on every GLB.

## 6. Tripo Studio, what it is good for

See `docs/tripo-settings-and-experience.md`. Summary of observed behaviour:
Studio retopology and the CLI P2 body both fuse the fingers, so hands are repaired in Blender;
Segment (custom prompt) and Fill Parts are the Studio route to closed garment parts and are being evaluated;
Rig presets (Mixamo, ActorCore, UE5, VRM, Unity) and text-prompted Animate cost 20 credits each.
