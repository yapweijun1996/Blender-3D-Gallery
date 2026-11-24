# Public Bus Fold-Out Boarding Ramp Cutaway

A fictional Singapore public-transport doorway cutaway. Through the two open sides, inspect the sill, alternating independent hollow barrel seats around one real pin, deployed raised-edge ramp and the short fitted toe along a shallow curb cutaway. The empty geometry is a fixed exhibit, not an operating procedure, fleet replica, surveyed location, engineering specification, or accessibility or safety certification.

- [Singapore Ministry of Transport](https://www.mot.gov.sg/news-resources/newsroom/written-reply-to-parliamentary-question-on-inclusion-of-automated-ramps-on-buses-due-for-10th-year-refurbishment/) and [SBS Transit](https://www.sbstransit.com.sg/special-assistance) document manual or deployable boarding ramps in Singapore. [Ricon's fold-over product overview](https://www.riconcorp.com/pages/products_transit_fr2e.asp) confirms the general fold-over transit ramp class only. No suggestion of a Singapore supplier, prototype, specified ramp angle, or actual bus design.
- Original independent named meshes, axle, sill and ramp profiles, text, and studio render. No third-party graphics, geometry, markings, person, mobility aid, or decorative animation.
- Blender 4.3.2; native axes +Z up/−Y front and glTF +Y up/+Z front. Stage and lights are not exported. All units represent only this fictional model.
- Reproduce into a new directory: `blender -b --python-exit-code 9 --python generate.py -- --output /tmp/new-bus-ramp`. Use `--skip-render` for only native source/GLB or `--review /tmp/new-ramp-detail` for separate press-free previews.
- Check exact geometry in source and GLB reimport with `blender -b --python-exit-code 9 --python verify_blender.py`, and verify GLB/Khronos/Three.js with `node verify.mjs`.
