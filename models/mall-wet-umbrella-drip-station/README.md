# Mall Wet-Umbrella Drip Station

Original tropical SG/MY-inspired indoor mall entrance fixture, with four high
guides for long umbrellas and four low guides with tip cradles for compact
umbrellas. Includes five closed umbrellas, open side louvers, a sloped drip
tray with a recessed pull, and a Malay/English wayfinding plaque and rain
pictogram. Open slots retain real apertures. The Blender project keeps all
guides, holders and umbrella parts editable; the GLB links repeated guide
profiles. No plastic bag service, brands, official signage, drain plumbing,
or installation/compliance claim. No external art, geometry or textures.

Metres, floor origin; Blender +Z up / −Y front, glTF +Y up / +Z front.
From the repository root, using Blender 5.3 and the WebP CLI:

```sh
D=models/mall-wet-umbrella-drip-station
blender -b -t 4 --python-exit-code 1 --python "$D/generate.py"
cwebp -quiet -resize 512 0 -q 86 "$D/previews/studio.png" -o "$D/previews/studio.webp"
blender -b -t 2 --python-exit-code 1 --python "$D/verify_blender.py"
node "$D/verify.mjs"
```

The studio camera, lights and floor do not export. Verification measures the
empty slots and tray pitch after reimport and validates the candidate's exact
hashes. Blender project serialization can change on rerun; intentionally
refresh measured file digests for a new candidate.
