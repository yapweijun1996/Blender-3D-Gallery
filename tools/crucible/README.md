# Crucible recipe to GLB

Turns a `crucible.scene` JSON recipe into a GLB through the Crucible MCP server (MIT, `@codepawlhq/crucible`). Needs Chrome and ffmpeg. Text in recipes must be ASCII.

```bash
cd tools/crucible && npm install
node export-glb.mjs <recipe.json> <out.glb> [look.png]
```

Register the result in the gallery with `node scripts/register-gallery-model.mjs --id ... --glb out.glb --preview look.png ...`.
