# Pasar Dacing Steelyard Scale

Original Malaysian market heritage-inspired educational model, not a museum replica. The demonstrator is a wooden display base with a fixed fork and reference pivot, an asymmetrical brass beam with unnumbered marks, a hanging pan with a fixed three-mango sample, and a captive sliding counterweight. The pan and weight assemblies remain upright. Nothing is weighed or calibrated; no actual mass, calibration, operating claim, supplier, or transaction is represented.

- Malaysia's [Department of Museums education catalog](https://myipim.jmm.gov.my/LandingSyllabus) lists *Dacing Timbang* under Muzium Negeri Sembilan, for cultural reference only.
- The [National Library Board of Singapore's documented daching history](https://biblioasia.nlb.gov.sg/all-sections/vol-16-issue-1-apr-jun-2020-milestones-to-the-metric-system/), including National Archives historical photographs and publications, describes the beam, pan and counterweight form. No image, design drawing, text or marks were reproduced. The display fixture, mangoes and finish are original geometry.

## Source, motion and validation

Blender 5.3.0. In this directory run `blender -b -t 5 --python-exit-code 1 --python generate.py` to reproduce the editable source, standalone GLB and 512px preview. Use `-- --review /path/to/stills` for optional pose and fulcrum detail views. The two clean native generations produced byte-identical posters and the same oriented triangles; Blender may reorder the shared mango index buffer without changing winding, geometry, materials, scene, or clips. The published candidate digest is in the metadata.

Blender +Z up and −Y outward; glTF +Y up and +Z outward. In the 2.2 s native clip `DACING_FIND_BALANCE`, the poise slides monotonically on the long arm, the short arm rises from a 9° tilt and levels out, and the final pose holds. The fulcrum and display stay fixed; pan and poise inverse pivots maintain vertical orientation.

- `node verify.mjs` applies Khronos validation and independently samples all four native tracks in Three.js over 133 times, including between authored samples.
- `blender -b pasar-dacing-steelyard-scale.blend --python-exit-code 1 --python verify_blender.py` audits the editable source; `blender -b --python-exit-code 1 --python verify_blender.py -- --reimport` audits the GLB in Blender.
- Interactive Gallery behavior is scoped to this one model. Controls balance/reset the visual demonstration, not the weight of a real object.
