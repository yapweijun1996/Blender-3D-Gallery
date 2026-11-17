# Lossless model downloads, batch 02

Ten further large PNG-textured assets were evaluated with Pillow 13.0.0. Nine exports became smaller, saving 7,762,576 bytes (7.40 MiB), a 19.58% reduction across the changed group. NASA Mercury kept its original bytes because its candidate was larger.

| Model | Before MiB | After MiB | Reduction |
| --- | ---: | ---: | ---: |
| Saturn (NASA) | 5.22 | 3.94 | 24.52% |
| Vesta (NASA) | 5.11 | 4.84 | 5.27% |
| Moon | 4.47 | 3.51 | 21.46% |
| Sun (NASA) | 4.14 | 3.44 | 16.96% |
| Pluto | 4.08 | 3.17 | 22.29% |
| Mercury | 4.04 | 2.58 | 36.08% |
| Mars (NASA) | 3.88 | 3.31 | 14.72% |
| Earth | 3.54 | 3.15 | 11.12% |
| Mars | 3.34 | 2.48 | 25.81% |

## Image and asset preservation

The encoder now replaces only PNG IDAT chunks. Every other PNG chunk, including IHDR, sRGB, gamma, chromaticity, EXIF and physical dimensions, is retained byte-for-byte. The original and replacement PNG headers must match exactly. The script independently reopens each candidate to compare its mode, dimensions, pixel bytes and metadata before using it.

A separate decoder-based check compared every embedded image before and after the change. All decoded pixels, modes, dimensions, metadata and non-IDAT chunk bytes matched. See [image verification](image-verification.json) and [encoding receipts with SHA-256 and pixel hashes](optimization.json).

The actual exported GLBs were parsed independently. Every non-image buffer retained its payload, and all scene, node, mesh, accessor, material, sampler and texture definitions matched. All nine Khronos validation results were zero errors and zero warnings. Four source identity and byte-count records in the Solar demo manifest were refreshed. Its demo exports retain their previous bytes.

## Reproduce

Use the [existing encoder setup](../README.md#reproduce), then pass the files listed in the encoding receipt to `scripts/optimize-glb-png.py`. Its output report records only exports that actually became smaller. To check the affected gallery and Solar references, run the following commands from the repository root.

```sh
node --test tests/solar-demo-assets.test.mjs tests/solar-frame-gate.test.mjs tests/solar-nasa.test.mjs tests/nasa-solar.test.mjs tests/nasa-saturn.test.mjs tests/nasa-moon-comet.test.mjs tests/registry.test.mjs
npm run build:deploy
```

The focused suite passed all 20 tests and the production build passed. Full CI resource validation remains an optional manual workflow input.

## Browser comparison

All 18 model/viewport cases passed in Chromium at 1440 × 900 and 390 × 900. Each model was checked at rest and after rotation, producing 36 pixel-identical before/after capture pairs. The viewer consumed the expected source and optimized SHA-256 identities, with zero console or page errors. See [browser results](browser-results.json). Physical phone hardware and frame-rate performance remain unmeasured.
