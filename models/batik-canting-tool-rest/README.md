# Batik Canting Tool Rest

Original Malaysian craft-inspired **display**: an independently editable offset wooden handle and padded rest, a copper reservoir with an open mouth and a single physically connected curved hollow tip, a dry insert and a small indigo cloth study with invented botanical linework. No copied textile pattern or artifact, vendor, actual temperature/material specification, workflow, wax animation or operating instruction.

- [Kraftangan Malaysia's Malaysian batik overview](https://kraftangan.gov.my/en/services/announcement/pastikan-batik-malaysia%2C-baru-beli-jangan-salah-pilih-batik-%E2%9C%A8) distinguishes the use of a canting to draw wax-resist patterns in *batik lukis* from block and other techniques.
- [Mohd Asri et al., IIUM Engineering Journal 23(1), p. 311](https://journals.iium.edu.my/ejournal/index.php/iiumej/article/view/1842) describes the wooden handle and small copper reservoir connected to a copper spout. Only those broad historical tool features inform this original model; no figure, tool design or process is reproduced.
- [Jabatan Warisan Negara's 2012 list](https://www.heritage.gov.my/en/2012-recognitions.html) recognizes Batik Malaysia. It does not endorse this illustration.

## Source and physical checks

Blender 5.3.0. Run `blender -b -t 5 --python-exit-code 1 --python generate.py` in this directory. The optional `-- --review /path/to/stills` makes inspection views. Same-version independent Blender generation reproduced the GLB byte-for-byte. Blender +Z up/−Y outward, glTF +Y up/+Z outward. The lights, background and studio camera are never exported.

- `blender -b batik-canting-tool-rest.blend --python-exit-code 1 --python verify_blender.py` checks the editable scene. Use an empty Blender session and append `-- --reimport` to verify the exact GLB after import.
- `node verify.mjs` checks the exported file with the Khronos validator and independent Three.js ray tests for the open bowl, joined copper lumen and outside-only handle saddle.
