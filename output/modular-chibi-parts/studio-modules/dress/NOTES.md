# Pastel pink A-line dress fitting

The dress is a skinned fitting candidate. The T-pose clears both collision checks. The motion gate remains open.

## Export

- GLB 2,487,720 bytes and BLEND 6,508,337 bytes.
- 1 dress mesh, 3,544 triangles, 2,596 exported vertices, 65 master joints, and 4 maximum influences. The GLB contains no animations.
- The local Khronos glTF Validator 2.0.0-dev.3.10 reports 0 errors and 0 warnings.
- GLB SHA-256 `8f7fa1522bc4289702f217b7026cf31efd068099a1c4af18c0256a58f26cfa6a`.
- BLEND SHA-256 `9f6f10d71fa42b3a2e1b045959aa8cc1a5f5aca62dfa9a48eb6303b4ea6de208`.
- Source GLB SHA-256 `8083dc5790de03e28054237b681295b80d4736b79c7b8dabee9d0cf05adc7cf5`.
- The hem opening spans Z 0.2405–0.2517 m. The cuff-loop centroids fall 43.2% (left) and 46.3% (right) from shoulder joint to elbow joint along X.
- Position-welded geometry has 4 open boundary loops and 0 edges shared by more than two faces.

## Supplied checker RESULT tables

Counts show the maximum in one sampled frame. All signed distances below are in mm. The vertex checker samples 12 times per clip and the triangle checker samples every third frame.

### Vertex checker

| Clip | Max inside vertices | Minimum distance (mm) |
|---|---:|---:|
| rest | 0 | +3.799 |
| walk | 124 | -17.700 |
| run | 210 | -22.600 |
| wave | 109 | -17.800 |
| jump | 109 | -17.400 |
| idle | 111 | -16.300 |
| nod | 109 | -15.800 |
| dance | 71 | -15.100 |

### Triangle checker

| Clip | Max overlap pairs | Minimum distance (mm) |
|---|---:|---:|
| rest | 0 | +3.799 |
| walk | 481 | -18.400 |
| run | 513 | -24.300 |
| wave | 277 | -17.800 |
| jump | 399 | -18.300 |
| idle | 282 | -16.300 |
| nod | 277 | -15.800 |
| dance | 126 | -15.100 |

## Half-frame RESULT

The 824 poses include rest, each half-frame, both clip endpoints and checker sample times. Garment and body zones describe the closest point for the deepest signed vertex in each clip. Per-zone triangle witness depths are sampled estimates in [dense_check.json](dense_check.json).

| Clip | Poses | Inside | Pairs | Min (mm) | Frame of min | Garment / body zone |
|---|---:|---:|---:|---:|---:|---|
| rest | 1 | 0 | 0 | +3.799 | 1 | shoulder and armpit / `LeftArm` |
| walk | 113 | 150 | 592 | -18.394 | 22 | bodice / `LeftArm` |
| run | 61 | 220 | 706 | -24.306 | 9 | hem / `RightLeg` |
| wave | 129 | 109 | 277 | -17.820 | 19 | bodice / `LeftForeArm` |
| jump | 101 | 117 | 399 | -18.448 | 38.5 | skirt / `LeftHand` |
| idle | 177 | 111 | 284 | -16.305 | 66 | shoulder and armpit / `Spine1` |
| nod | 113 | 109 | 278 | -15.783 | 0 | shoulder and armpit / `Spine1` |
| dance | 129 | 71 | 126 | -15.189 | 50 | shoulder and armpit / `Spine1` |

In the unmodified master body, the left arm and trunk or upper-leg region already overlap at Walk 22 (69 pairs), Wave 19 (70), Jump 38.5 (83), Idle 66 (61) and Nod 0 (61). These body-to-body counts compare disjoint anatomical regions and exclude the shared shoulder connection.

## Rest clearance

0 exported vertices exceed 30 mm of signed clearance.

| Zone | Vertices | Min (mm) | P10 (mm) | Median (mm) | P90 (mm) | P95 (mm) | Max (mm) |
|---|---:|---:|---:|---:|---:|---:|---:|
| all | 2,596 | 3.799 | 5.971 | 15.161 | 23.874 | 24.313 | 26.156 |
| bodice | 500 | 4.216 | 9.028 | 14.708 | 21.113 | 22.448 | 24.258 |
| hem | 574 | 9.305 | 16.456 | 22.310 | 24.507 | 24.689 | 25.202 |
| neck | 395 | 4.360 | 4.897 | 8.431 | 16.276 | 17.746 | 20.600 |
| shoulder and armpit | 228 | 3.799 | 5.944 | 15.681 | 23.846 | 24.147 | 24.768 |
| skirt | 565 | 3.805 | 5.126 | 13.997 | 22.893 | 24.201 | 26.156 |
| sleeve | 334 | 4.435 | 5.288 | 11.253 | 19.025 | 19.732 | 22.966 |

## Renders

Six T-pose views and four motion frames are in [renders](renders). The file hashes, rendering settings and frame choices are recorded next to the images in [manifest.json](renders/manifest.json). The motion frames are walk 31.5, run 15.5, wave 14.5, jump 7.

Direct and independent review found a seated round neck, open cuffs, a continuous hem and intact pink material in the six T-pose views. The cuffs read shorter than the reference barrel sleeves and have raised tips. The front hem has a shallow center pucker. A dark pinpoint below the right cuff falls on an armpit repair face in a local ray test. Walk, Wave and Jump show no obvious fabric tears in the pictured angles. The Run view shows a skin-colored sliver at the hand and front-left skirt, so the visual gate remains open.

## Inputs and fit

The supplied 6,330-triangle Tripo surface imports in Blender with +Z up, sleeves along X and the lower neckline facing −Y. The glTF front is +Z. The pastel pink dress reference was found at `../../generated2/top-04-dress-tpose.png`. The requested `generated` directory contained the hoodie, tee and bottom references.

The Blender build welds geometric duplicates while retaining corner UVs, removes the connected interior liner and false caps, repairs small concave armpit cutouts, and keeps open neck, cuff and hem loops. A piecewise landmark transform aligns the fabric with the waist, shoulders and arm axes. The original material and its base-color, roughness/metallic and normal maps are retained at 1024 × 1024. The exporter includes tangents for the normal map.

Weights start with barycentric interpolation on the nearest master-body triangle. A bilateral hip and thigh blend spans the skirt center and tapers into the nearest-body binding above the hip. The solver bounds skin weights to four normalized influences and retains the master skeleton and quaternion rotation modes. All clips use their named Blender 5 action slots.

The first bake estimates each vertex's largest outward requirement across the 824-pose sweep with a 2.05 mm target. Subsequent updates compare local displacement and weight trials, using worst sampled positions in each clip to choose trials and the full sweep to evaluate the result. The rest guard backtracks on folded faces, triangle contacts and clearance outside the rest band. Long intersecting edges are eligible for subdivision when their corners already clear. Motion margin and rest guards can conflict where a limb moves into or through the master body.

The 12 update slots were evaluated. Splitting 261 contact-prone edges produced 4,064 triangles. Its best result had the same 24.3 mm deepest penetration and more triangle contacts across the sweep. Later offset and weight trials either exceeded the rest cap or increased the combined penetration and overlap score. The delivered export uses the initial fitted surface and weights, which had the lowest score of the rest-compliant candidates. [Iteration results](fit_history.json).

## Reproduction

A fresh export of the selected fitted surface matched the delivered GLB byte for byte. The independent BLEND save had a different file hash. The entire 12-slot solver run was performed once.

Run with the guarded Blender binary and `DYLD_INSERT_LIBRARIES` supplied in the task. Use the directory containing this file as the working directory. The fitter reuses math and mesh routines from the local hoodie round 2 and 3 scripts.

```sh
VECLIB_MAXIMUM_THREADS=1 "$BLENDER" -b -noaudio -t 6 --python-exit-code 1 --python fit_dress.py
"$BLENDER" -b -noaudio -t 6 --python-exit-code 1 --python fit_dress.py -- checkers
"$BLENDER" -b -noaudio -t 6 --python-exit-code 1 --python fit_dress.py -- verify renders
```

The wrapper runs the supplied vertex and triangle measurement and frame-sampling sections without editing either checker. It writes distinct reports because the two original scripts use the same JSON filename. The textured PNGs use Cycles CPU at 12 samples in place of the headless Workbench rendering section. The dense check reimports the exported GLB and evaluates Blender's armature modifier at every half-frame, including both endpoints and the original checker samples. The paired count and minimum signed distance can occur at different frames.
