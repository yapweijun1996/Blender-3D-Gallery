# Chibi Mall Guide v5

A chibi shopping-mall concierge boy in a jade cap and vest holding an arrow sign, rigged and animated. The delivered model is `final/guide.glb`. It was **reconstructed from the reference sheet by an image-to-3D tool (TRELLIS) and then rigged and retouched**; it is not the procedurally built figure that earlier steps of this folder describe (that work is kept as history, see "Earlier approach").

Status: **catalogued development preview with downloads disabled.** The [independent visual review](final/REVIEW.md) calls for rework before final acceptance. Rights clearance remains open (see Rights).

## What is delivered

| File | What |
| --- | --- |
| `final/guide.glb` | The model: one skinned mesh, 20 bones, 4 clips |
| `final/guide.blend` | Editable Blender source of the same (rig, skin weights, actions) |
| `final/guide-views.png`, `final/clips.png`, `final/poses-sample-frames.png` | Renders of the GLB: four views, one frame per clip, sample frames |
| `final/silhouette-overlay.png`, `final/silhouette-iou.json` | Silhouette against reference sheet B |
| `final/*-report.json` | Skin, foot-contact, preparation and texture-retouch reports |
| `final/texture-retouched.png` | The 1024 px texture atlas after retouching |
| `reference/turnaround-b.png` | Reference sheet (AI concept image, rights not cleared) |
| `trellis-trial/` | The reconstruction: pod scripts, 16 candidates (images; the chosen GLB), preparation, retouch, alignment experiments |
| `base-rig/` | Rig, skinning and animation script, landmark tables, check scripts |

## Measured results (2026-11-15)

| Item | Value | How checked |
| --- | --- | --- |
| Triangles / materials / draw calls | 10,464 / 1 / 1 | glTF Validator info |
| glTF Validator | 0 errors, 0 warnings, 0 infos | `gltf-validator` 2.0.0-dev.3.10 |
| File size | 1,938,764 bytes | file system |
| Height | 0.999 m, feet on y = 0 | Three.js bounding box |
| Footprint (x) | -0.327 to 0.287 m, the sign included | Three.js, over all clips |
| Bones | 20, one skinned mesh as a scene root, no weights missing | `skin-report.json`, validator |
| Clips | idle 2.03 s, walk_calm 1.23 s, walk_bouncy 0.83 s, point 1.23 s | Three.js `AnimationMixer` in headless Chromium, no console errors |
| Foot contact | lowest point over the walk clips: -0.2 mm and 0 mm; idle -4 mm (breathing) | Three.js skinned bounding box, 25 samples per clip |
| Silhouette overlap with sheet B | front 0.80, side 0.82, back 0.83 | `final/silhouette_vs_sheet.py` (the sheet's silhouette includes its ground shadow, so the numbers are approximate) |

Budget: 10,464 triangles is far below the 40,000 limit and 1 draw call is below 20, so no separate low-detail GLB was made.

## How it was made

1. The four views of `reference/turnaround-b.png` were fed to Microsoft TRELLIS (`TRELLIS-image-large`) on a rented Runpod RTX 4090, 16 candidates in all (four view sets times four seeds, plus the first trial); see `trellis-trial/README.md` and `trellis-trial/pod/`. Every candidate except the first came out facing +X; candidates are compared in `trellis-trial/candidates/`.
2. Candidate `f3q_s2` (front and three-quarter views, seed 2) was chosen: the most cheerful open mouth, relaxed brows, one sign, clean silhouette. None of the 16 has a closed smile.
3. `trellis-trial/prepare_base.py` (`YAW=-90 NOSPLIT=1`): turned it to face the front, set the material from metallic 1 / roughness 1 (which made it look black) to metallic 0 / roughness 0.55, put the feet on z = 0.
4. `trellis-trial/retouch_texture.py`: repainted the sign's icon as the reference's right-pointing arrow (texels mapped back to the board plane through the mesh's UVs) and lifted the near-black hair to the sheet's chestnut brown (a hue and brightness remap that keeps the original shading).
5. `base-rig/rig_base.py` with `landmarks-f3q_s2.json`: welded the mesh, 20 bones fitted by landmark table, bone-heat skinning, arm weights removed inside the trunk, clips written as actions, foot contact baked by lifting the hips so the lowest vertex sits on the floor, skinned mesh kept as a scene root, GLB exported.

## Decisions made without the owner (the owner delegated the call)

- The TRELLIS reconstruction is the base, not the hand-built figure.
- **The face is fixed** (open smile as reconstructed). No blink, no smile/surprised keys, no eyes mesh: a baked face cannot have them. This does not meet the standard's three-shape-key requirement; it is waived for this character.
- **The sign is part of the body** and moves with the right arm; there is no separate sign prop, no swappable icon, no sockets. The arrow is painted into the texture.
- **Not delivered:** the `wave` clip (the left arm hugs the trunk in this mesh and any lift tears the surface; the code exists behind `WAVE=1` and is off), the `put sign down` clip (the sign is fused to the hand), a low-detail GLB, avatar still images.
- Pods: two community-cloud pods were terminated within minutes because the host's GPU would not initialise; the runs used secure cloud at $0.89/hour. All pods were terminated and `list-pods` read back empty. The total spend is estimated at about $0.9; the billing read returned no records at the time, so confirm it in the Runpod console.

## Known defects (my reading, plus the independent reviews below)

- The expression is a baked open mouth with slightly raised brows, not the sheet's happy smile.
- The texture is soft (1024 px, TRELLIS baking), so the cravat, buttons and badge look smeared next to the sheet's crisp vinyl look.
- A few dark blotches remain on the hair at the top front where the retouch did not reach; the back side of the sign board still shows ragged leftover patches.
- The skinned arms and hands are crude: the arm hugs the trunk; the point clip tilts the sign against the shoulder.
- Shoe soles and the underside of the shoes show dark patches during the walk.
- The mesh is lumpy compared with the sheet.

## Independent review (fresh agents, looked at images only)

Two reviews were run, each by a new agent that was given only image paths and a neutral brief; full texts in `final/REVIEW.md`.

- Review 1, before the retouch: about 60 to 65 percent of the reference. P1: the sign's icon is a blob, not an arrow; worried instead of happy face; near-black matte hair; soft texture; dark patches on the shoes in the walk. "Usable only as a placeholder."
- Review 2, after a first retouch: about 55 to 60 percent. P1: grey-brown retouch blotches on the hair, a jagged black fringe, worried face and small eyes, the sign is a disc with a frayed rim and its back side was smeared with the arrow pointing the wrong way, the point clip squashes the sign. "Would not accept it as the character."
- After review 2 I extended the hair recolour to every dark texel of the brown hair faces (the blotches are gone in my renders) and mirrored the arrow on the back of the board. **The final `guide.glb` has not been reviewed again**; the black fringe between the eyes, the baked expression, the disc-shaped sign and the soft texture are unchanged.

My own estimate for the final state is that it matches the reference in costume colours, proportions and overall silhouette (overlap 0.80 to 0.83) and is clearly short of it in face, hair finish and texture sharpness; treat it as a good placeholder, not as the finished character.

## Not verified

The gallery viewer (`src/viewer.js` shows models at rest and has no animation code), the mall runtime, performance on phones, the sign and hand in motion at full frame rate, any catalog or deployment behaviour, and any rights position. The skinning was judged from still frames, not from playing the clips in a real scene.

## Rights

Original input: an AI-generated reference sheet whose rights are not cleared (`reference/PROVENANCE.md`). TRELLIS code and models are stated to be MIT-licensed on the repository page; the page gives no separate terms for the weight files and the training datasets (Objaverse and others) carry their own licenses, which were not reviewed. Do not publish `final/guide.glb` before the owner has decided this.

## Earlier approach (kept as history, not the deliverable)

Steps 4 to 7 (`config.py`, `kit.py`, `garments.py`, `limbs.py`, `head.py`, `hair.py`, `build_parts.py`, `hair_gate.py`, the `step*-` notes) built the guide procedurally from primitives, with shape keys, a designed face and layered hair; it passed the front head-row silhouette gate but looked far from the reference. `blockout/`, `prototype/blink/` and `step5-parts.md` to `step7d-hair-third-pass.md` document it. `trellis-trial/fit_to_target.py` and `bake_colors.py` are experiments that tried to correct that figure toward the TRELLIS result and did not help; their records are in `trellis-trial/README.md`.

## Rebuild

```sh
# 1. reconstruction on a GPU pod: trellis-trial/pod/ (setup_all.sh and run2.py)
# 2. prepare, retouch, rig (repository root, Blender 5.1.2):
YAW=-90 NOSPLIT=1 blender --background --factory-startup --python models/chibi-mall-guide-v5/trellis-trial/prepare_base.py -- CANDIDATE.glb /tmp/base
blender --background --factory-startup --python models/chibi-mall-guide-v5/trellis-trial/retouch_texture.py -- /tmp/base/base-body.glb /tmp/body-retouched.glb /tmp/retouch
LANDMARKS=models/chibi-mall-guide-v5/base-rig/landmarks-f3q_s2.json blender --background --factory-startup --python models/chibi-mall-guide-v5/base-rig/rig_base.py -- /tmp/body-retouched.glb /tmp/rig
# 3. checks:
node models/chibi-mall-guide-v5/base-rig/check-clips.mjs /tmp/rig/guide-rigged.glb /tmp/clips.png
```

The reconstruction is stochastic on a given seed only if the GPU libraries differ; a different pod may give a different mesh, so the chosen candidate GLB is kept in `trellis-trial/candidates/f3q_s2.glb`.
