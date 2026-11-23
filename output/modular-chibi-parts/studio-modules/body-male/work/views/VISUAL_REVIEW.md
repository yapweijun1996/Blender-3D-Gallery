# Independent visual review of the male body and hand library

The reviewer inspected the supplied design image, the original Studio GLB, and the rendered final body and gesture exports. All nine gestures are recognizable on both hands. The final fists show external thumb wrapping and closed finger silhouettes. Both pinch and OK show opposing thumb and index tips.

| Reviewed asset | SHA-256 |
| --- | --- |
| Male body | `09d5e03d5da489e350432bb521e59255393a167a2847ae602b7d92a6a102e387` |
| Gesture library | `140e8d616494344c13f23f895e690588a05b671fb6ce72441e152741ff1ad310` |
| Studio source | `6bdceb1bf381678860f1f55dd0c23beafc4aff02cb0e83a6398fea62a56f80e9` |
| Design PNG | `7411174dbc36c7c7661fd69730821acdb1783bf9d0ff3e42dc0091a5231797ce` |

## Gesture appearance

| Gesture | Observation for left and right |
| --- | --- |
| Fist | Four tips turn inward against the palm. The thumb crosses the exposed surface of the folded index. The side profile shows a shallow shaded recess. The earlier open tunnel and the buried thumb have cleared. |
| Open relaxed | The fingers have individual gaps, a slight bend in profile, and a projecting tapered thumb. |
| Point | The index is extended. The other three long fingers fold into the palm, and the thumb rests along the side of the index. |
| Thumbs up | The thumb rises clearly above all four curled fingers. The palmar and thumb-side views show a closed grip. |
| Peace | Index and middle form a distinct V, with ring and pinky folded. The thumb stays close to the extended index. |
| OK | The index and thumb form a ring. The other fingers stay extended. The two magnified views show a narrow contact line on each hand. |
| Grip small | The four fingertips curve over the 40 mm cylinder. The thumb opposes them underneath. The recorded gauge fits between these surfaces on each side. |
| Pinch | The thumb and index tips oppose one another. The other fingers curl more than in OK. The magnified profile shows faceted tip edges approaching closely. |
| Open wide | The four long fingers fan apart more widely than in open relaxed, and the thumb opens away from the palm. |

The surface checks put thumb-to-index separation at 0.24941 / 0.24924 mm for pinch and 0.24799 / 0.24784 mm for OK, listed left / right. The sampled index pulp within 0.5 mm of the opposing thumb spans approximately 6.9 mm² in each gesture. The four fist finger pads are 0.36931–0.40422 mm from the palm across both hands. Measured skin clearances and witness coordinates are available separately. [Export measurements](../audit/MEASUREMENTS.md)

The earlier fist silhouettes exposed central openings of 47.841 / 47.552 mm², and thumbs-up exposed 48.169 / 49.884 mm². The final orthographic radial images have zero enclosed background components of four or more pixels in all four cases. The detector uses an eight-connected flood fill within three 8-bit RGB levels of the studio background. These values describe the projection from the fixed camera. [Earlier measurements](review_history/before_compact_openings.json) · [Final radial measurements](fold_openings.json)

## Rest appearance and remaining detail

The source's brown eyes, bald head, ears, shorts and feet remain recognizable in the final front and three-quarter renders. The dorsal and palmar views show the separated fingers and an extended, tapered thumb. The front view now shows the hands edge-on. The source PNG supplies a single frontal design view. The required rest orientation and gestures supply the interpretation of the hidden palm surfaces. [Studio baseline](baseline/rest_front.png) · [Final rest](rest/rest_front.png) · [Hand in dorsal view](rest/rest_L_dorsal.png)

The mean absolute display-referred RGB differences in matched 640 × 640 front crops are 0.471 of 255 for the head (39,206 foreground pixels), 0.830 for the eye crop (12,987), and 0.232 for the torso, shorts, legs and feet crop (44,214). Corresponding 95th-percentile channel differences are 2, 4 and 1 levels, with maxima of 153, 47 and 50. These are rendered-image measurements and include denoiser and sampling differences. [Crop and camera data](appearance_comparison.json)

Some knuckle and fingertip silhouettes show angular facets at macro scale. The tips retain a narrow rounded edge, with no modeled pad compression. A light warm transition remains at the palm heel and a tiny darker mark appears at the wrist edge in some views. The earlier straight knuckle band and dark rectangular ring-finger patch have cleared.

## Capture evidence

Blender 5.1.2 imported both delivered GLBs for the gesture captures. Each clip was assigned to the matching action slot on the reimported body armature, and the mesh retained its exported material. Orthographic Cycles CPU captures use 10 samples for the 54 standard views (384 × 320) and 16 detail views (540 × 390), 8 samples for the matched rest views (640 × 640 frontal), and 12 samples for the solid 40 mm gauge views (520 × 390). The gauge uses the recorded axis from the independent export measurements. Every individual view records its source hashes and camera settings. [54-view contact sheet](../contact_sheet.png) · [16 closeups](hand_closeups.png) · [Gauge viewed from the palm](grip_40mm_L_palmar.png) · [Gauge viewed from its end](grip_40mm_R_end.png) · [Gauge manifest](grip_manifest.json) · [Sheet manifest](sheet_manifest.json) · [Left renders](renders/manifest_L.json) · [Right renders](renders/manifest_R.json)
