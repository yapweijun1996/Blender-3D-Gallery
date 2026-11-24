# Roti Jala Lace Pouring Cup

An original Malaysian food-heritage inspired still life: one handled five-outlet acuan cup on an unrelated, deliberately open illustrative support, with a separately modeled lacy crêpe on a dish. The cup has an open mouth and five genuinely continuous floor-to-tip bores, and the net sample contains physical gaps between its nonuniform ribbons. No brand, vendor, actual cookware specification, replica, recipe or cooking demo is represented.

- Malaysia's [Department of National Heritage](https://www.heritage.gov.my/en/pengisytiharan-2009.html) lists *roti jala* among its declared intangible heritage foods.
- Malaysia's [National Department for Culture and Arts (JKKN)](https://pemetaanbudaya.jkkn.gov.my/senibudaya/detail/1191), in its separate Perlis kuih karas entry, mentions contemporary three- or five-nozzle *acuan roti jala*. This is narrow support for the utensil class, **not** the modeled finish, geometry, design stand, official origin or exclusive form.
- The [Dewan Bahasa dan Pustaka dictionary](https://prpm.dbp.gov.my/Cari1?d=15740&keyword=jala-jala) describes *roti kirai/roti jala* as round and netlike. No outside photos, artwork or lettering were copied.

## Source and checks

Blender 5.3.0. In this directory run `blender -b -t 5 --python-exit-code 1 --python generate.py`. Add `-- --review /path/to/stills` for optional review views. Blender +Z up and −Y outward; glTF +Y up and +Z outward. Geometry, materials, transforms and oriented faces reproduced identically on two native runs. The spoon-tip UV sphere index traversal order can change, affecting whole-file digest but not topology, materials or render. The exact reviewed artifact is pinned in metadata.

- `blender -b roti-jala-lace-pouring-cup.blend --python-exit-code 1 --python verify_blender.py` checks the physical source. Run with an empty Blender session and `-- --reimport` to audit the exact exported GLB independently.
- `node verify.mjs` applies the Khronos validator and a separate Three.js loader ray audit. The gallery exhibit is static; it has no liquid, heating, recipe or commerce simulation.
