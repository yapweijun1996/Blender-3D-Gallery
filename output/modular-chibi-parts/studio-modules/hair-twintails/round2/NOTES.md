# Chestnut twin tails, round 2

**Visual and technical gates passed.** The shipped GLB contains one skinned hair mesh, one PBR material, 2,994 triangles and three embedded 1024 × 1024 PNG textures. It occupies 1,861,856 bytes. Khronos glTF Validator 2.0.0-dev.3.10 returned zero errors, warnings, infos and hints. The editable Blender scene also contains the master body for fitting.

## What changed

- **Ponytails and fringe.** The original connected shell had a pinched fold with near-black diffuse colour baked into the exposed wall. A neutral-material render separated the shape from the painted mark. An unlit base-colour render exposed a second fault, several faces sampled the same texels. The repair redistributes the fold vertices, restores the outer lobe from its flanks, and reconstructs a shallow strand channel. The albedo, normal and material values at the fringe flecks and tail fold are rebuilt from nearby surface samples. Dark baked occlusion was reduced in chestnut recesses.
- **UVs and normals.** At atlas resolution, 338 exterior texel centers belonged to overlapping triangle interiors. The repair moved 88 overlapping or severely compressed triangles to individually padded charts, transformed the normals into the new tangent frames and dilated the three maps up to 24 texels into free space. The same exterior scan then found zero overlapping texel centers. The intentional shared lining swatch is excluded from this measurement.
- **Rear cap and hem.** The old part was a modeled groove with a matching dark line in the texture. Paired strips of intact hair supply the cross-section, colour and mapped normals across the center. Thirty-eight inserted rim vertices let the nape and temple follow a smoother contour. The lower rear exterior was fitted over the lining, and the thin temple return was separated from the outward-facing cheek lock. Winding was recalculated. Both versions have one connected shell after welding attribute splits, with zero open edges. The inspection found no detached islands to delete.
- **Attachment.** The exported joint names, hierarchy, order and inverse bind matrices match the 65-joint master. Head weights remain dominant. Neck rises smoothly to 10.50% on the low rear hair. Each vertex has at most two positive, normalized weights. The exported module has no animation of its own.

## Visual evidence

The reference is the front-facing `../../../white-bg/hair-03-twin-tails.png`. The back and sides are assessed against the original fitted hairstyle. The independent reviewer inspected the final six-view sheet and the five paired closeups, with round 1 at left and round 2 at right.

| Feature | Independent judgment on the final GLB |
| --- | --- |
| Outer tail, profile and three-quarter | PASS. The black slit and a triangular brown stain seen during repair have disappeared in both views. A broad highlight follows the curl. |
| Fringe just right of center | PASS. The scattered black marks are gone and the overlapping pointed locks stay distinct. |
| Rear cap and nape | PASS. The bands cross the center, the dark vertical groove is gone and the lower edge follows a shallow continuous arc. |
| Temple and eye opening | PASS. The dark polygon behind the cheek lock is gone. Both frontal irises remain visible. Hair occluded zero of the 5,958, 4,817 and 4,798 baseline-visible eye pixels in the front and two three-quarter views. |
| Reference identity | PASS. The high twin attachments, violet ties, chestnut S-curls, central fringe and cheek locks remain recognizable. |

The Blender 5.1.2 Cycles CPU renders used the original AgX colour transform, denoising, 12 samples, studio world and three lights. The orthographic scale was 0.73, the target was (0.001, 0, 0.812) and each panel was 570 × 570. The closeups use a render border at three times the panel resolution with the same camera transform and projection. The six views are front, three-quarter +X, three-quarter −X, +X profile, back and −X profile.

## Pixel counts

The mask includes a pixel when the center ray first sees the exported hair mesh, including its ties, before the fitted body. Face, eyes, background and open space between the free curls are excluded. Each round uses its own geometry and the same mask algorithm. RGB was read from the display PNG. The two reported definitions of the 12% threshold use Rec. 709 coefficients (0.2126, 0.7152, 0.0722). **Linear Y** uses sRGB decoding before the weighted sum. **Display Y′** uses encoded RGB to count visually near-black pixels. Each count uses a strict less-than comparison. The round-1 recapture matched the supplied fit sheet byte for byte in all six hair masks.

| View | Hair pixels R1 | Hair pixels R2 | Linear Y < 12% R1 | Linear Y < 12% R2 | Display Y′ < 12% R1 | Display Y′ < 12% R2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Front | 84,881 | 84,258 | 51,521 | 49,028 | 10,327 | 5,860 |
| Three-quarter +X | 80,921 | 80,566 | 40,696 | 38,303 | 5,453 | 2,990 |
| Three-quarter −X | 81,949 | 81,417 | 48,597 | 46,258 | 6,947 | 3,305 |
| Left profile | 75,033 | 75,849 | 35,597 | 34,354 | 3,402 | 1,735 |
| Back | 117,116 | 117,101 | 64,468 | 59,114 | 7,532 | 2,720 |
| Right profile | 74,965 | 75,735 | 45,370 | 44,855 | 5,968 | 2,982 |
| Total | 514,865 | 514,926 | 286,249 | 271,912 | 39,629 | 19,592 |

All six views decreased under both definitions. Linear-Y dark pixels fell by 14,337 (5.0%). Display near-black pixels fell by 20,037 (50.6%). The total visible hair mask grew by 61 pixels.

## Motion and fit

Both supplied scripts ran unchanged on the exact final GLB, the rigged master and the shared motion GLB. The vertex checker samples 12 frames per clip. The triangle checker samples every third integer frame. The original clips, action slots, frame selections and distance calculations are preserved. A frame handler uses the original studio Cycles CPU fallback for the four checker images per script. The raw JSON and action frames are retained separately under `checks/vertex/` and `checks/triangle/`. Distances are in metres. The checkers round clip distances to four decimals.

### Vertex RESULT

| Pose or clip | Maximum vertices inside the body | Minimum signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.006161289 |
| walk | 0 | 0.006100000 |
| run | 0 | 0.005400000 |
| wave | 0 | 0.006200000 |
| jump | 0 | 0.006200000 |
| idle | 0 | 0.006200000 |
| nod | 0 | 0.006200000 |
| dance | 0 | 0.006200000 |

### Triangle RESULT

| Pose or clip | Maximum hair–body triangle pairs | Minimum signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.006161289 |
| walk | 0 | 0.006100000 |
| run | 0 | 0.005400000 |
| wave | 0 | 0.006200000 |
| jump | 0 | 0.006200000 |
| idle | 0 | 0.006200000 |
| nod | 0 | 0.006200000 |
| dance | 0 | 0.006100000 |

A separate sweep of all 416 integer rest/clip samples, including endpoints, found zero body penetrations and zero hair–body triangle overlaps. The lowest measured signed vertex clearance was 5.382352 mm during run. Dense static sampling of the whole garment surface gave 4.207558 mm minimum Euclidean clearance and 2.809874 mm minimum signed projection. Static crown clearance was 10.464430 mm.

## Remaining imperfections

At three-times closeup scale the outer tails and low temple locks show mild planar shading. The nape arc has slight corners at its ends, and the tail ridges read broader than in the frontal illustration. The reference supplies no side or rear view.

The layer arrangement still has hair-on-hair intersections. A separate static BVH test on the reimported GLBs found 509 nonadjacent hair-triangle pairs in round 1 and 559 in round 2. The triangle count and the rim tessellation differ between the two meshes. These are self-contacts within the hair. The motion tables measure hair against the body. Subframe animation and other lighting setups were outside the measurements.

## Rebuild

Run in this directory with the local guarded Blender executable. The read-only round-1 blend is the modeling input. The script imports the original fit helpers for the camera, lighting, master-rig and clearance checks. The only external executable used by the Python pipeline is Node.js for the already-installed Khronos validator.

```sh
mkdir -p .work
modular_tools=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
TMPDIR="$PWD/.work" DYLD_INSERT_LIBRARIES="$modular_tools/guard.dylib" \
  "$modular_tools/B/Blender.app/Contents/MacOS/Blender" -b -noaudio \
  --python-exit-code 1 --python "$PWD/fit_hair_r2.py"
```

The default stages are `build baseline views compare audit`. Every successful geometry export runs both supplied motion checkers before the build stage returns. Pixel counts and render hashes are in `visual_check.json`. The validator report, build statistics, separate shell test, eye tests and all-frame results are under `checks/`.

## File identity

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| hair_twintails_v2.glb | 1,861,856 | `22dd264ee6216431cdd97a748f31a41ff6751170816bbbd01c79dbaa68735c6c` |
| hair_twintails_v2.blend | 2,668,574 | `36d064b8ac582b447090c10df7682385dd35814e2a6185cfaf7d8fa89a249751` |
| fit_hair_r2.py | 34,373 | `bd3ce4b2f0a89ccf66baa958f8eada38f4234f60d9bedc772b9cb8e30a8b28aa` |
| fit_views_v2.png | 2,399,813 | `0376923f90f1e4294c1da5e07022e2728e4059217aff17def6e1861ad489b759` |
| hair_twintails_v1.glb | 1,805,916 | `d8a2ea69efc3d309f30a9dac7511fccea23964d801defdd12b3cf18a65777688` |
| hair_twintails_v1.blend | 2,630,637 | `db9fff9041eb20ca53ed5ba018eda3114044e1fd53fdaa59dad839f68740bccb` |
| fit_views.png | 2,436,621 | `f8da24adbe35d88037cc0cecaec802d810bf80078aa17df2851d2d6603a1c420` |
| hair-03-twin-tails.png | 693,982 | `b1dfac70cb3f808f8e17d1de04aba9ceb570fd12b864297adc3dc49053b57e33` |
