# Classic visitor acceptance record

The classic reference outfit was independently reviewed against the supplied sheet. The comparison covers the broad diagonal fringe, asymmetric rear hair, rounded jaw, open happy eyes, violet hood and cuffs, light hem, cargo shorts, shopping bag emblems, shoulder straps and sneakers. Later passes corrected exposed scalp, the central shorts protrusion, the jaw silhouette and a broken shoulder strap in the seated view.

The early [rear](first-pass/back.png), [front](first-pass/front.png), and [seated](first-pass/sit.png) diagnostic images retain the first pass for comparison. Final images come from a clean re-import of the delivered GLB.

## Advisor and manager acceptance

Review used the active KB procedure `agent:auto-manager` 1.5.0 and its design-acceptance loop. Independent visual and module advisors compared the supplied sheet with the exported character. The manager also inspected the real 1440 × 900 and 390 × 844 browser frames and the seated alternate outfit. The classic figure, default expression, detachable parts, joint isolation, cap and jeans, and five actions are the accepted scope. Face variants illustrated on the sheet are outside this build.

## Export and modularity

The default GLB has 2,973 indexed triangles, five materials, a 1.30 m standing height, 27 joints and five clips. The runtime Hair slot has 456 triangles. The Blender source keeps twenty editable hair pieces. There are 38 default slots and two optional slots. The source retains more topology than the exports. The face atlas is packed.

All [41 GLBs](modules.json) were checked by Khronos glTF Validator. The Three.js test exercised all 40 modules against a stable map of the character's original joints across the five clips and a head turn. It exercised both cap/jeans equip orders, removal and re-equipping, conflict visibility, independent fingers, and turning the head after transforming the character root. The main character and standalone modules share the same rest rig.

## Animation and appearance

The [motion check](motion.json) sampled every clip at 121 times on the re-imported default character. Walk support height error stayed within 0.066 mm, run within 0.325 mm. In the defined sitting fixture the measured seat contact differed by about 0.015 mm. Ten individual finger rotations moved their own vertices only. At 13 times per clip, rays cast in 12 directions detected no exposed probes through the shorts fabric above the hems. The test distinguishes the real open cuff from a hole in its side.

The [jeans fit check](jeans-fit.json) detected the original tongue/cuff intersection, then found zero intersections between the jeans and sneaker tongue over 386 evaluated source-mesh pairs at 193 integer animation frames. The re-exported jeans were also equipped and viewed in browser standing and seated. The independent rebuild changed only the optional jeans among the 41 exported GLBs.

The [Chrome WebGL2 captures](browser/report.json) cover front, three-quarter, back, the hat-and-jeans look, and that look in the sit clip. The exact default GLB exposed all five clips as loadable actions with no browser console messages during capture. The default browser frame used 49 draw calls. Its 3,121 submitted triangles include repeat submissions during transparent rendering. The stored geometry count is 2,973. Individual slot swapping and layered face artwork increase draw calls.

A standing character and its optional clothing depend on the supplied rest shape. New outfits and arbitrary retargeted actions need their own fit tests. The supplied eyes, brows and mouth show one happy expression. Each finger has one joint. The hood and sneakers retain simplified low-poly folds. Contact measurements apply to the specified flat floor, chair and motion speeds. Testing did not cover physical mobile GPUs.
