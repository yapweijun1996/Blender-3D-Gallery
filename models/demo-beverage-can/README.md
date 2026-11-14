# Demo Beverage Can

Original fictional 330 mL-ish beverage can study. `generate.py` is the reproducible Blender source; the checked-in legacy helper and placeholder preview are retained under `draft-evidence/` only. The two clips are illustrative assembly states, not a manufacturing or liquid simulation.

Source, structural/motion validation and five actual Blender preview views pass. Product Studio browser integration remains NEEDS REVIEW until switch/retry/resource regression is complete. Earlier draft helpers and placeholder imagery are historical evidence only, not release assets. No real brand or physical manufacturing fidelity is claimed.

Local review commands (host Blender required):

```sh
python3 label.py
"${BLENDER_BIN:?Set BLENDER_BIN to Blender 4.x}" --background --factory-startup --threads 2 --python generate.py
node validate.mjs
"${BLENDER_BIN:?Set BLENDER_BIN to Blender 4.x}" --background --factory-startup --python source-proof.py
```
