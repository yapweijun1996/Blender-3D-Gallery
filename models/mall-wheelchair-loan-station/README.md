# Mall Wheelchair Loan Station

An original SG/MY-inspired guest-service loan dock. Low marked docking platform,
open rollout side, rear bumper, bilingual Malay/English sign and separate
returns pocket. The independently authored wheelchair is shown folded, with an
indigo pleated seat/back sling, stowed footrests, visible cross braces, two
spoked main wheels and two small casters. The stand and chair are one
gallery work, with separate editable components in the Blender file.

Fictional static prop. It does not operate a loan service, represent a real
mall, specify any borrowing terms, animate the chair, or certify access,
docking, safe load, medical suitability or installation. No brand or
third-party model/texture. The placard letters use Blender bundled Bfont.

Metres; floor origin; Blender +Z up/−Y front, glTF +Y up/+Z front.

```sh
D=models/mall-wheelchair-loan-station
blender -b -t 4 --python-exit-code 1 --python "$D/generate.py"
cwebp -quiet -resize 512 0 -q 86 "$D/previews/studio.png" -o "$D/previews/studio.webp"
blender -b -t 2 --python-exit-code 1 --python "$D/verify_blender.py"
node "$D/verify.mjs"
```

The studio is not exported. Verify the folded geometry, 4 wheel contacts,
clear front and rear stop with Blender and verify exact hashes with Khronos.
Blender source serialization can vary by run; only refresh measured digests
when intentionally making a new candidate.
