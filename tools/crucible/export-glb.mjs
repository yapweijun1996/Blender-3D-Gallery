// Usage: node export-glb.mjs <recipe.json> <out.glb> [look.png]
// Creates the scene from a crucible.scene recipe, exports it as a GLB and optionally saves a review image.
import fs from "node:fs";
import { connect } from "./mcp.mjs";

const [recipePath, out, look] = process.argv.slice(2);
if (!recipePath || !out) { console.error("usage: node export-glb.mjs <recipe.json> <out.glb> [look.png]"); process.exit(2); }
const recipe = JSON.parse(fs.readFileSync(recipePath, "utf8"));
const m = await connect();
try {
  const created = await m.data("scene_create", { recipe }, 300000);
  const sessionId = created.sessionId;
  const inspected = await m.data("scene_inspect", { sessionId });
  console.log("inspect:", JSON.stringify(inspected).slice(0, 600));
  const exported = await m.call("scene_export_glb", { sessionId }, 300000);
  const blocks = exported.content ?? [];
  console.log("export blocks:", blocks.map(block => `${block.type}:${(block.text ?? block.data ?? block.uri ?? "").toString().slice(0, 120)}`));
  const structured = exported.structuredContent;
  if (structured) console.log("structured:", JSON.stringify(structured).slice(0, 400));
  const bin = blocks.find(block => block.type === "resource" || block.type === "blob");
  const glbPath = structured?.path ?? structured?.file ?? structured?.glbPath;
  if (glbPath && fs.existsSync(glbPath)) fs.copyFileSync(glbPath, out);
  else if (structured?.base64 || structured?.data) fs.writeFileSync(out, Buffer.from(structured.base64 ?? structured.data, "base64"));
  else if (bin?.resource?.blob) fs.writeFileSync(out, Buffer.from(bin.resource.blob, "base64"));
  else console.log("could not find the GLB bytes in the result; see the printed blocks");
  if (look) {
    const view = await m.call("scene_look", { sessionId, width: 1024, height: 768 }, 180000);
    const image = view.content.find(block => block.type === "image");
    if (image) fs.writeFileSync(look, Buffer.from(image.data, "base64"));
  }
  console.log(fs.existsSync(out) ? `wrote ${out} (${fs.statSync(out).size} bytes)` : "no GLB written");
} finally { await m.close(); }
