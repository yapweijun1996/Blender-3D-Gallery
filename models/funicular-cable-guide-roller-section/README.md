# Funicular Cable-Guide Roller Section

An original, static sectional exhibit of two continuous inclined rails and one exposed central haul-rope sample. Three separate round sheaves have genuinely concave groove surfaces around the rope. Each has a physical bore, axle and fixed support feet. This is not a rack railroad, surveyed Penang Hill component, real rail-car or installation instruction.

[Penang Hill Corporation](https://corporate.penanghill.gov.my/index.php/en/about-us) manages and operates the Malaysian local funicular. [Doppelmayr's funicular system brochure, pp. 10–11](https://www.doppelmayr.com/uploads/tx_vcs/Standseilbahnen2013_ENG-Doppelmayr_06.pdf) documents the general function of line sheaves on a funicular: guiding the haul rope. No actual Penang Hill component or layout, vendor design, physical clearance or real engineering specification was copied.

## Native reproduction

Blender 5.3.0 with built-in mesh/text tools. Native Blender +Z is up, -Y forward; the GLB has +Y up and +Z forward. Source retains three separately editable grooved assemblies, the rail pair and one continuous rope. Studio camera/lights/backdrop do not ship inside GLB; no other textures or animation.

```sh
blender -b --factory-startup -P generate.py -- --output /tmp/funicular-section --review /tmp/funicular-review
blender -b --factory-startup --python-exit-code 9 -P verify_blender.py -- \
  funicular-cable-guide-roller-section.blend exports/funicular-cable-guide-roller-section.glb
node verify.mjs
```

Native Blender plus independent GLB reimport verify a single closed rope, both rail heads, real grooved near-tangent clearances, through-axle bores, and stationary display joints. Three GLTFLoader repeats exact ray tests on browser geometry; numerical measurements describe the original digital artwork only.

Original project asset; redistribution terms for public downloads are not specified.
