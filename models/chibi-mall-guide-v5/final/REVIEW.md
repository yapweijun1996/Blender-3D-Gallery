# Independent reviews of the rigged guide (2026-11-15)

Both reviewers were fresh agents with no access to my reasoning; they looked only at images (`reference/turnaround-b.png`, `final/guide-views.png`, `final/clips.png`, plus the silhouette overlay in review 1 and the texture atlas in review 2) and wrote a report. Their text is reproduced in condensed form; severity labels are theirs.

## Review 1 (before the texture retouch): about 60 to 65 percent
- P1 the sign shows a blobby glyph, not the reference's clean arrow; P1 the sign in the silhouette overlay is a smaller, rounder, tilted lozenge held lower and further out; P1 the expression is a wide open worried mouth with raised slanted brows instead of the happy smile, eyes smaller and flatter; P1 the hair is near-black, matte and spiky instead of glossy chocolate petal locks; P1 soft painterly texture, smudged cravat, buttons and badge; P1 walk frames show dark smeared shoes and a tilted sign in the point clip.
- P2 cap button smaller and flatter; torso and shorts wider than the reference; right glove greyish; stiff vest and arm in the side view.
- Verdict: costume palette and chibi proportions well preserved; not acceptable as the character as is; a placeholder.

## Review 2 (after a first retouch of the sign arrow and hair colour): about 55 to 60 percent
- P1 grey-brown hard-edged stains on the hair (retouch residue), also visible as scribbles in the clip frames; P1 jagged black zigzag fringe over the eyes, matte cracked hair with vein-like lines; P1 worried "o" mouth, heavy black brows, smaller lower eyes; P1 the sign is a round disc with a frayed gold rim, its back is smeared and the arrow pointed the wrong way, the side view shows no sign; P1 point clip squashes the sign edge-on.
- P2 darker flatter cap; greyish gloves; small ruffle instead of a cream bow; black sole patches in the walk; the atlas shows black ellipses, dark outline bleeding and hard brown strokes.
- Could not judge: whether the black ellipses map to visible surface; hidden hair behind the cap; hands.
- Verdict: costume colours and proportions right; hair, expression, sign and texture quality not; not acceptable until fixed; a rough placeholder.

## What was changed afterwards
Hair recolour extended to all dark texels of the brown hair faces (the greenish cap faces are skipped), and the arrow is mirrored on the back of the board. The final GLB was rebuilt and re-validated (0 errors, 0 warnings, clips load) but **not reviewed a third time**.

## Review 3 of the final export (2026-11-23)

**Visual verdict: REWORK.** Keep the current development preview designation. The build passes this technical recheck, while the reference match still needs work.

| Reference criterion | Result | Evidence |
| --- | --- | --- |
| Chibi proportions and uniform palette | PASS | Front and three-quarter views retain the large head, jade cap and vest, cream sleeves, and dark shorts. |
| Face | FAIL | Front and three-quarter views show a fixed open O mouth and heavy, raised brows. The reference has larger eyes and a cheerful smile. |
| Hair shape and finish | FAIL | Most hair now reads chestnut, but the front has a dark, jagged fringe and the side and rear views show seams across the locks. The reference uses smooth, broad, layered locks. |
| Sign shape, finish and readability | FAIL | The green right arrow reads on both faces. The board is nearly round with a rough rim and brown patches on the back. The reference has a clean rounded rectangle and gold rim. The board disappears in the sampled side view and turns nearly edge-on in the point frame. |
| Costume details and visible deformation | FAIL | The badge and neckwear are soft at close range. The two sampled walk poses show dark sole patches. |

Repair priorities are the face and fringe geometry, then a clean, separately modelled sign with a grip and orientation that preserve readability in motion. Recheck the walk soles and small costume details before another appearance review.

The review used `reference/turnaround-b.png` (SHA-256 `3c66e097afdbb0cb68aefc72641bb979e67a55f19acff61c8ee3ef5ffce9d462`) and `final/guide.glb` (SHA-256 `886f1c5b1220c795efc2aa8c4a69192e9ac2e167c91a4521bccd890d26210e3c`). Headless Chromium with software WebGL and Three.js 0.187.0 regenerated the 2240 × 560 front, 35°, side and rear sheet with `trellis-trial/shoot-glb.mjs`. It regenerated the 2000 × 320 clip sheet with `base-rig/check-clips.mjs`. Both renders matched the tracked files byte for byte:

- `guide-views.png`: SHA-256 `4a0d0cb802d9286c8d3ecc3fa675b519e7fa7a3782a1935d1598faf316f9a916`.
- `clips.png`: SHA-256 `795290d07c21520f930e83360f322874ced6678e7b89761679b10ab337783d5b`.

Khronos validation reported zero errors and warnings, 10,464 triangles, one material and one draw call. The browser loaded the exact GLB, sampled each of its four clips at 25 times, and logged no errors. Blender 5.1.2 read `final/guide.blend` with embedded script execution disabled and found one rig with 20 bones, one mesh with no shape keys, and four actions. The source SHA-256 was `2fd2d87c41274efdb991a11ee85404776b130e41c384482b1b0c478a70fd5d60`. The Node-only `base-rig/check_glb.mjs` could not load this textured export because Three.js expects browser `self` for image loading. Validation and thumbnail rendering ran separately.

The review covers the captured four-view sheet and one visible pose per clip. Opposite-side close-ups, continuous mall playback, physical-device performance, owner acceptance and rights clearance remain unverified.
