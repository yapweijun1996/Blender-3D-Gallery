# GJH Mall Visitor v2 — development preview

This editable procedural Blender character is derived from the gallery's original visitor and informed by the supplied showcase. It is a work in progress, not a finished reproduction of that image or a VRM asset. The source remains separate from v1.

Generate with Blender 5.1.2:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python models/gjh-mall-visitor-v2/generate.py
```

The export uses glTF +Y up, metres, floor Y=0 and front +Z. It contains a skin, a humanoid bone hierarchy, and in-place `idle`, `walk`, `sprint`, `sit`, `stand`, `pickup`, `place`, `push`, and `elevator` clips. The interaction clips are animation prototypes, not complete mall interactions. The source has independently editable parts; the export joins compatible parts by material and customization slot to reduce draw calls.

The export includes both hair and outfit variants, and glTF does not retain Blender's render-visibility setting. Consumers **must** call `createVisitorCustomization(scene)` from `customization.js` before displaying it to hide inactive variants. Choices are per instance; call `dispose()` when the instance is discarded. The gallery viewer does this automatically and offers preview controls.

The separate mall consumer uses v2 by default, with `?visitor=v1` available as a compatibility fallback, with physical shelf pickup/return, contact-calibrated cart and seat poses, rolling wheels, appearance controls and two floors connected by a lift. Physical holding is separate from demo-bag quantities. Geometry LOD1 is generated with `generate-lod.py`; the consumer swaps geometry on the existing skeleton at 11/9 m thresholds. See the consuming repository's `docs/gjh-visitor-v2-verification.md` for measurements and limits. Physical iPhone/Android and full-mall crowd performance remain unverified; there is no 60 FPS guarantee.

Run the asset and customization checks from the gallery repository:

```sh
node --test tests/gjh-visitor-v2.test.mjs
npm run build
node scripts/test-visitor-browser.mjs
```

The asset test checks shoe height, the skeleton, clips and customization state.
The browser test exercises the shared v2 and v3 preview controls with the actual
exports, including resets and recovery from a missing idle clip. These checks
cover gallery previews; mall interaction and physical device performance have
separate acceptance criteria. Rights and provenance are in `metadata.json`.
