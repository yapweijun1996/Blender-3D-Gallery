# 3D asset standard

Status: proposed contract; validate tooling and budgets with real assets before adoption.

Each interactive work must have a real, browser-inspectable glTF 2.0 GLB, not just a render. Keep a Blender source file and procedural generator when available and appropriate to share. Record Blender version, dependencies, invocation, seed where relevant and third-party attribution. Preview images must represent the exported model faithfully.

## Metadata

Each model should have a unique lowercase kebab-case slug, title, summary, description, controlled category, tags, creation date, author and creation method, Blender version, relative asset paths, license and attribution, measured metrics, and a `draft`, `validated` or `published` status. A publication date is recorded only when publication actually happens. Validate paths against approved public asset roots and treat displayed text as untrusted.

Suggested measured metrics are GLB bytes, triangle and vertex counts, maximum texture dimensions and animation clip count. Never invent metrics or infer a model's category or license from its filename. Source code and artwork may have different licenses.

## Export and admission

1. Use an intentional origin, scale and transforms; check mesh bounds, normals, UVs and texture references. Verify materials and effects survive glTF export.
2. Validate the GLB with the Khronos glTF Validator, inspect reported errors and warnings, and measure geometry and file sizes. Test any compression and its decoder on target devices.
3. Check image decoding, representative composition and asset paths. Inspect the actual model in the browser on desktop and mobile, including camera fit, rotation, zoom and reset.
4. Review provenance, rights, attribution and visual quality. Only approved, validated entries enter the published catalog; failures remain drafts.

Candidate budgets for measurement: prefer GLB files at or below 5 MiB and 100,000 triangles; review larger assets and require an explicit exception for materially larger files. Typical texture dimensions should not exceed 2048 pixels without justification. Prefer thumbnails under 150 KiB and posters under 300 KiB when visual quality allows. These are targets, not measured guarantees.

## Optional Gallery preview settings (implemented)

Existing `display.previewRotationY` remains required and unchanged. The following
optional fields affect Gallery presentation only, not exported/source geometry,
Game or Solar scenes, material definitions, downloads or the visible UI:

```json
{
  "previewRotationY": 0,
  "previewCameraDirection": [1, -1.4, 1],
  "previewLighting": {
    "directionalPosition": [4, -7, 5],
    "hemisphereIntensity": 2,
    "directionalIntensity": 2.1
  }
}
```

- `previewCameraDirection` is the world/glTF-space vector **from the model bounds
  centre toward the camera**, after `previewRotationY`. The viewer normalizes it
  and retains automatic distance fitting, orbit/zoom limits and per-model reset.
- `directionalPosition` is the white key light's world-space position, aimed at
  the world origin, matching the existing Three.js light convention. The other
  hemisphere colours, vehicle studio and rendering presets do not change.
- Vectors are exactly three finite numbers, each in [-100,100], with length at
  least 0.000001. Camera X/Z length must also be at least 0.000001 to avoid a
  vertical look-at pole. Lighting intensities are finite numbers in [0,10]; zero
  is allowed and does not trigger a default.
- Each omitted field retains its old default independently. No camera override
  keeps the exact existing vehicle, solar, ball or generic camera branch. No
  lighting override keeps hemisphere intensity 2, key intensity 2.1 and position
  [4,7,5]. Empty `previewLighting: {}` also retains all defaults.
- Known invalid values (including null, strings and non-finite numbers) fail
  catalog validation/build; they are not clamped/coerced or silently substituted.
  Unknown metadata fields remain accepted and preserved, as before.

The ceiling uses only camera and key-position overrides. See
[verification](verification/preview-config.md) for baseline comparisons and limits.
