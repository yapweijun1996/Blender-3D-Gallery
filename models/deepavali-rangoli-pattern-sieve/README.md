# Deepavali Rangoli Pattern Sieve

An original static display of a modern perforated pattern sieve alongside a small powder-pattern study. Its solid 3.4 mm plate contains 29 through-holes in an invented geometric arrangement of open wave fragments, capsules, lozenges and dots. The separate matte tile shows the same orientation and scale in four colors. The whole piece is a fictional museum-style display, not a historical artifact, prescribed motif, brand, or representation of a ritual.

The [Singapore National Heritage Board's Little India Heritage Trail](https://www.roots.gov.sg/-/media/Roots/Files/little-india-heritage-trail/nhb_littleindia-trail-booklet_2018.pdf?hash=2144B81D22C703DFEF5F153EAD36BBE0446D35D6&la=en) documents kolam floor decoration during Deepavali in Singapore. [Madhuri Menon's IDC, IIT Bombay design resource](https://www.dsource.in/resource/rangoli/materials-used-rangolis) separately documents modern perforated plastic/metal rangoli templates and pattern sieves as a tool type. Neither establishes that the tool is required or traditional in Singapore, and no pattern or product design was copied.

## Native source

Editable Blender 5.3.0 source uses separate staging, physical sieve assembly and four modeled powder colors. The deterministic geometric powder variation uses seed 7313. Studio lights and background are excluded, Blender is +Z up/-Y forward and exported glTF is +Y up/+Z forward. No textures or animation.

```sh
blender -b --factory-startup -P generate.py -- --output /tmp/sieve-display --review /tmp/sieve-review
blender -b --factory-startup --python-exit-code 9 -P verify_blender.py -- \
  deepavali-rangoli-pattern-sieve.blend exports/deepavali-rangoli-pattern-sieve.glb
node verify.mjs
```

Blender-native and GLB reimport independently test manifold cutout topology, both directions through each assembled hole, interior walls and matching powder contact. Three GLTFLoader repeats actual ray checks on rendered geometry. Preview is a native studio render of the geometry.

Original project asset; redistribution terms for public downloads are not specified.
