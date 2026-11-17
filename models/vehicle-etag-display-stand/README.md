# Vehicle E-Tag Display Stand

Original static counter fixture for store S16 (P2). Six rounded windscreen-mount
toll tags sit in two rows of three on a 30-degree solid riser. Each has two
mounting pads, a housing seam and a plain smoke-coloured window. The rear sign
card is blank. No text, brands, external assets, images or textures.

Metres; counter contact centre at the origin. Blender +Z up / -Y front;
glTF +Y up / +Z front. Target envelope W x D x H: 0.50 x 0.35 x 0.40 m.
Measured export values and hashes are in `reports/assets.json` and metadata.
The native source keeps named editable parts; export batches evaluated copies
into three shared material meshes. Studio equipment is excluded.

```sh
blender --background --python-exit-code 1 --python models/vehicle-etag-display-stand/generate.py
# Preserve saved edits instead of rebuilding (add --skip-render to skip previews):
blender --background --python-exit-code 1 --python models/vehicle-etag-display-stand/generate.py -- --export-source
node models/vehicle-etag-display-stand/validate.mjs
blender --background --python-exit-code 1 --python models/vehicle-etag-display-stand/inspect_sources.py
node models/vehicle-etag-display-stand/verify_source_edit.mjs
npm run build
node models/vehicle-etag-display-stand/check_browser.mjs
```

The browser check uses installed Google Chrome with ANGLE Metal on macOS,
loads the built page at 1440 x 900, compares its GLB hash with the validated
export and exercises keyboard orbit and close. Screenshot output is under
`~/Documents/MallQueue/reports/`. Physical phones, WebKit, electronic toll
operation and full mall performance are unverified. Local checks do not imply
publication. Human art review remains pending.
