# TRELLIS multi-view trial (2026-11-15), NOT part of the accepted model

An experiment: reconstruct the Mall Guide from the four views of reference sheet B with Microsoft TRELLIS (`microsoft/TRELLIS-image-large`, multi-image mode). It is a baked, single-mesh reconstruction; it has no parts, no rig and no shape keys, and it is not registered or approved for any use.

## How it was made

- Pod: Runpod secure cloud RTX 4090 (price shown by the create call: $0.89/hour), image `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`. Two earlier community-cloud pods were terminated within minutes because the host's `/dev/nvidia-uvm` returned an I/O error and CUDA would not initialise. The final pod was terminated after the run; `list-pods` read back empty.
- Input: the four cells of `reference/turnaround-b.png` (front, three-quarter, side, back) padded to squares, passed to `pipeline.run_multi_image`; seeds 1 to 4; sampler steps 12 (sparse structure cfg 7.5, slat cfg 3); GLB via `postprocessing_utils.to_glb(simplify=0.95, texture_size=1024)`.
- Setup fixes needed on the pod (for reproducibility): `nvdiffrast` installed with `--no-build-isolation`; `xformers==0.0.28.post1` with `--no-deps` (the setup script had no build for torch 2.4.1 + CUDA 12.4); `xops.fmha.BlockDiagonalMask` replaced by `xops.fmha.attn_bias.BlockDiagonalMask` in three TRELLIS files; a stub `kaolin.utils.testing.check_tensor`; apt packages libegl1, libgl1, libgles2, libusb-1.0-0 and X11 libraries for open3d; `ATTN_BACKEND=xformers`, `SPCONV_ALGO=native`.
- Viewing: `shoot-glb.mjs` renders four views in headless Chromium with the repository's Three.js. It reads the WebGL drawing buffer and checks for visible content in each view before saving the PNG.

## Results (my reading, not independent)

- Seed 1 is the only one that faces front and reads as the guide: chestnut bob with chunky back locks, jade cap, vest, white gloves, sneakers, the sign. `result_s1.glb`: 10,306 triangles, 1 material, 1 draw call, glTF Validator 0 errors and 0 warnings, 1.47 MB, about 0.53 x 1.00 x 0.52 m.
- Seeds 2 to 4 come out turned sideways; seed 3 has two signs. The multi-view fusion is unstable (the TRELLIS page says "tuning-free, results may vary").
- Faults of seed 1: the face is smeared and the expression is an open "surprised" mouth, not the sheet's smile; the 1024 px texture is soft; the mesh is lumpy; the hair is one fused mass. The held sign is merged into the body.
- In my viewer all results look very dark. I did not check the material factors, so I cannot say whether that is the model's material (for example metallic) or my lighting.

## Rights and provenance

TRELLIS code and models are MIT-licensed per the repository page; the page gives no separate terms for the weight files, and the training data sources have their own licenses (not reviewed). The input is the AI-generated reference sheet whose rights are not cleared. Nothing here is committed or published.

## Using seed 1 as a correction target (same day)

`align_compare.py` imports `result_s1.glb`, moves it by a translation only (soles on z = 0, x and y fitted on the shoes; its own scale of about 1.00 m is kept) and measures the 3D distance and the silhouette overlap with the built figure. `fit_to_target.py` then runs a coordinate descent over 22 config values (cap, head, hair thickness/width/offset multipliers, vest, shorts, arms, legs). The held sign is excluded from the measurement (the figure has no sign).

| | Before the fit | After the fit |
| --- | --- | --- |
| Objective J (mean target-to-ours plus mean ours-to-target, mm) | 44.4 | 33.5 |
| Target to ours, mean / p95 (mm, 11k samples) | 25.2 / 75.2 | 24.3 / 68.6 |
| Silhouette overlap IoU, front / three-quarter / side / back | 0.805 / 0.724 / 0.628 / 0.805 | 0.799 / 0.732 / 0.592 / 0.799 |

Reading: the objective improved by a quarter but the silhouettes did not (side view got worse). The remaining differences are shape details and the target's own blobbiness, not the overall scale of the parts, so tuning a few numbers cannot close them. The fit also uses all vertices of the figure, including hidden interior ones, which inflates the ours-to-target term. The fitted values are saved as `fit/fit-seed1.json.proposed` and are NOT loaded: `config.py` reads `models/chibi-mall-guide-v5/fit.json` if that file exists (copy the proposed file there to enable it); the accepted values are unchanged. The fitted figure has a larger head and a wider cap, and its face keys were not rebuilt or re-validated.

Files: `fit/` (log, history, overlays before and after, reports, figure render after the fit).

## Outcome (later the same day)

Sixteen candidates were made (four view sets times four seeds, plus the first trial); `candidates/` has side-by-side renders and the chosen GLB `f3q_s2.glb`. Every candidate except the first faces +X; none has a closed smile. `f3q_s2` was chosen, prepared (`prepare_base.py`, `YAW=-90 NOSPLIT=1`), retouched (`retouch_texture.py`) and rigged (`../base-rig/rig_base.py`) into `../final/guide.glb`; see `../README.md`. The earlier idea of correcting the hand-built figure toward the target (`fit_to_target.py`, `bake_colors.py`, `align_compare.py`) did not help and was dropped; `align_compare.py` and `bake_colors.py` queried the target through an object-space BVH in some versions, so their distance numbers before the `world_bvh` fix are unreliable (the fit numbers above, which used world-space arrays, are not affected).
