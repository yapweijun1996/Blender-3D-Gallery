# NASA Saturn candidate

Downloaded 2026-11-05 from [NASA Saturn 3D Model](https://science.nasa.gov/resource/saturn-3d-model/). Credit: NASA Visualization Technology Applications and Development (VTAD). Original file: [Saturn_1_120536.glb](https://assets.science.nasa.gov/content/dam/science/psd/solar/2023/09/s/Saturn_1_120536.glb). NASA's [media guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/) apply; review individual rights and attribution before publication. This is a NASA asset, not an original gallery creation.

- SHA-256: `8dbfde533b13e938408d8aded1d1ce48a084806233f67775371d83013dba7d38`
- Size: 5,476,584 bytes.
- Khronos glTF Validator: zero errors, zero warnings; one informational non-power-of-two image notice and 12 missing bufferView target hints.
- glTF 2.0; three meshes/draw calls; 3,328 triangles; two materials and two embedded PNG textures (4096×3072 and 4096×16); no animations.
- Chromium/Three.js GLTFLoader loaded and rendered the planet and rings; no page errors. See `preview-validation.png`. This is a standalone test, not a gallery integration test.
- Bounding box approximately 2330.90 × 902.04 × 2330.90 units. The existing solar scene assumes normalized assets, so this asset requires normalization and visual review before integration. The large texture also warrants mobile performance checks; the current demo downsamples textures wider than 1024 pixels.
- The original download was not substituted for the existing Blender-created Saturn. Physical devices, Safari/WebKit, and rights for the intended publication have not been independently verified.

## Gallery candidate

`saturn-normalized.glb` retains the original geometry and images and adds a uniform root scale of approximately 0.000858; its maximum width is approximately 2 gallery units. It is registered separately as `nasa-saturn`, while the Solar System demo continues to use the original gallery Saturn. The original download is preserved for provenance. Chromium tests of the built gallery covered search, viewer, attribution, download link and direct-link reload at 390 and 1440 CSS pixels. Physical-device and Safari/WebKit tests remain outstanding.
