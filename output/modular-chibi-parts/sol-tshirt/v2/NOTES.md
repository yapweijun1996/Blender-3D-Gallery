# Short-sleeve T-shirt v2

Build with Blender 5.1.2 and the rigged master and motion GLB at their repository paths. Add `--check --cpu-render` after Blender's `--` separator to regenerate the JSON and four PNGs. The supplied checker measures the exported GLB. Its PNGs use CPU Cycles because headless Workbench aborted on this host.

The GLB has 1,731 triangles, one solid sea-green material, 65 matching Mixamo bones, up to four normalized weights per vertex, and no body mesh or animation. Khronos glTF Validator reported zero errors and warnings. A second build produced a byte-identical GLB. The round neckline has a continuous rim. The cuff rims average 40.2% and 41.4% of upper-arm length. The hem reaches 0.425–0.454 m in the bind pose. Minimum torso clearance is 0.002125 m.

| RESULT | Max vertices inside | Min signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.001986 |
| walk | 0 | 0.0007 |
| run | 0 | 0.0007 |
| wave | 0 | 0.0011 |
| jump | 0 | 0.0010 |
| idle | 0 | 0.0011 |
| nod | 0 | 0.0011 |
| dance | 0 | 0.0013 |

The lofted cuffs and fitted shoulder weights address sleeve-to-torso contact in run and dance. The shaped hem and local fit address arm-to-hem contact in walk, wave, jump, idle and nod. Pose-guided position and weight fitting works across the seven clips. Final local refinement between checker samples also cleared the remaining walk and nod deficits.

All 415 integer frames across the seven actions also passed the vertex criterion. Face testing still found 34 shirt/body triangle pairs in the bind pose and up to 190 in walk. Local folds remain around the sleeve roots. The right cuff has a local extension and the hem rises unevenly at one side. Subframes were not checked.
