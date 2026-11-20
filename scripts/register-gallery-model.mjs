// Put a finished model into the gallery: models/<id>/<id>.glb, a preview, a README and a catalog entry.
// Usage: node scripts/register-gallery-model.mjs --id id --name "Name" --category Landmark --tags "A,B" --description "..." --glb file.glb --preview shot.png
//        [--collection singapore-open-world --collection-name "Singapore Open World" --collection-description "..."] [--source "text"] [--tool "Blender 5.1.2 via Codex"]
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const args = Object.fromEntries(process.argv.slice(2).reduce((pairs, token, index, list) => token.startsWith("--") ? [...pairs, [token.slice(2), list[index + 1]]] : pairs, []));
for (const key of ["id", "name", "category", "description", "glb", "preview"]) if (!args[key]) { console.error(`missing --${key}`); process.exit(2); }
if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(args.id)) { console.error("id must be a lowercase slug"); process.exit(2); }
const collectionId = args.collection ?? "singapore-open-world";
const root = path.resolve(import.meta.dirname, "..");
const folder = path.join(root, "models", args.id);
fs.mkdirSync(folder, { recursive: true });
const glbTarget = path.join(folder, `${args.id}.glb`);
fs.copyFileSync(args.glb, glbTarget);
execFileSync("cwebp", ["-quiet", "-q", "82", "-resize", "640", "0", args.preview, "-o", path.join(folder, "preview.webp")]);

const require = createRequire(import.meta.url);
const validator = require("gltf-validator");
const bytes = fs.readFileSync(glbTarget);
const report = await validator.validateBytes(new Uint8Array(bytes), { uri: `${args.id}.glb` });
if (report.issues.numErrors || report.issues.numWarnings) { console.error(`validator: ${report.issues.numErrors} errors, ${report.issues.numWarnings} warnings`); process.exit(1); }
fs.writeFileSync(path.join(folder, "README.md"), `# ${args.name}

${args.description}

- Tool: ${args.tool ?? "Blender 5.1.2 driven by GPT 6.2 (Codex)"}.
- Source: ${args.source ?? "Original model made for the Singapore open-world study; proportions follow public facts about the real place. No official endorsement."}
- Verification: Khronos glTF validator 0 errors and 0 warnings; ${report.info.totalTriangleCount} triangles; ${bytes.length} bytes.
- Map and place data in the open-world game come from OpenStreetMap contributors (ODbL).
`);

const catalogPath = path.join(root, "models", "catalog.json");
const catalog = JSON.parse(fs.readFileSync(catalogPath, "utf8"));
let collection = catalog.collections.find(item => item.id === collectionId);
if (!collection) {
  collection = { id: collectionId, name: args["collection-name"] ?? "Singapore Open World", description: args["collection-description"] ?? "Models for the Singapore open-world study: landmarks, street furniture, vegetation, vehicles and MRT.", assets: [] };
  catalog.collections.push(collection);
}
const entry = { id: args.id, name: args.name, category: args.category, tags: (args.tags ?? "").split(",").map(tag => tag.trim()).filter(Boolean), description: args.description, file: `models/${args.id}/${args.id}.glb`, thumbnail: `models/${args.id}/preview.webp` };
const existing = collection.assets.findIndex(item => item.id === args.id);
if (existing >= 0) collection.assets[existing] = entry; else collection.assets.push(entry);
fs.writeFileSync(catalogPath, JSON.stringify(catalog, null, 2) + "\n");
console.log(`registered ${args.id}: ${report.info.totalTriangleCount} triangles, ${bytes.length} bytes in collection ${collectionId}`);
