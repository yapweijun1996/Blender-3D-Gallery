# Lossless model download optimization

The fast Pages workflow from commit `70578584` remains the deployment path. This change reduces the binary model downloads by recompressing existing 8-bit PNG maps. The encoder is Pillow 13.0.0 with PNG optimization enabled. Dimensions, colour mode, pixel samples and PNG colour metadata were independently compared for every embedded image. JPEGs and every non-image buffer retained their bytes, including geometry, indices, tangents, skin joints and weights.

| Gallery asset | Before MiB | After MiB | Reduction |
| --- | ---: | ---: | ---: |
| Rigged Tripo Chibi | 37.05 | 36.75 | 0.80% |
| NASA Earth | 12.35 | 9.45 | 23.42% |
| NASA Jupiter | 10.95 | 8.21 | 25.04% |
| NASA Pluto | 6.68 | 5.90 | 11.70% |

The four exports save 7,034,280 bytes, approximately 6.71 MiB. The Moon PNG produced a larger candidate, so its original export was retained. Source and optimized SHA-256 values and decoded pixel hashes are in [the receipt](optimization.json).

## Reproduce

Run the encoder after exporting a source GLB. It chooses a replacement only when its PNG data is smaller, then checks every non-image buffer before writing. The encoder accepts single-frame 8-bit RGB/RGBA PNG maps. It replaces only IDAT chunks, retaining every other PNG chunk byte-for-byte, including colour metadata, EXIF and physical dimensions. The PNG header must match exactly before an encoded candidate can be used.

```sh
python3 -m venv /tmp/glb-png-tools
/tmp/glb-png-tools/bin/pip install Pillow==13.0.0
/tmp/glb-png-tools/bin/python scripts/optimize-glb-png.py   models/tripo-chibi-rig/rigged-character.glb   models/nasa-solar/earth/model.glb   models/nasa-solar/jupiter/model.glb   models/nasa-solar/pluto/model.glb   --report /tmp/glb-png-report.json
```

A source re-export changes a file identity even when the rendered content is identical. Refresh corresponding source hashes and source byte counts in `models/solar-demo/manifest.json` after recompression, then run the existing solar asset tests. The pre-existing demo exports have been compared against the optimized gallery sources with those tests.

## Verification

All four updated GLBs passed the pinned Khronos validator with zero errors and zero warnings. Their JSON structures matched the originals outside the repacked buffer offsets and lengths. Every non-image buffer payload matched byte-for-byte. Independently decoded image pixels, dimensions, modes and colour metadata matched. The production build and six focused solar tests passed.

All eight Chromium model/viewport comparisons passed at 1440 px and 390 px. The eighteen pairs of captures were pixel-identical before and after optimization. These included rest and rotated views for each planet, and rest, raised-arm and skeleton views for the rigged character. See [the browser results](browser-results.json). This checks rendering and the existing controls on desktop software WebGL; physical phone performance is outside this check.

## Further batches

[Batch 02](batch-02/README.md) evaluates ten further large assets using the same pixel-preserving method, extended to retain all non-IDAT PNG chunks verbatim.
