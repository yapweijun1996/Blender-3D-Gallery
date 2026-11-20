/** Validate the city kit (game-ready copies of existing gallery models): Khronos validator, budgets, static-asset rules, material names. */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const validator = require("gltf-validator");
const directory = path.join(path.dirname(fileURLToPath(import.meta.url)), "kit");
const budgets = { // triangles
  hdb_block: 2200, hdb_void_deck: 2500, hdb_coffee_shop: 1800, provision_shop: 1200, shoplot: 1800, public_market: 3000, mrt_entrance: 2000,
  hawker_stall: 1500, chicken_rice_stall: 1500, bus_shelter: 900, signal_pole: 500, zebra_crossing: 300, street_sign: 150, heritage_lamp: 500,
  bench: 300, block_sign: 150, playground_slide: 700, playground_swing: 500, rain_tree_hd: 900, angsana_tree: 700, tembusu_tree_hd: 700,
  frangipani_tree: 600, coconut_palm: 600,
};
const materialNames = new Set(["paint", "glass", "tire", "light", "trim", "wall", "roof", "window", "leaf", "trunk", "metal", "concrete", "chrome", "plate"]);
const failures = [];
for (const [name, limit] of Object.entries(budgets)) {
  const file = path.join(directory, `${name}.glb`);
  if (!fs.existsSync(file)) { failures.push(`${name}: missing`); continue; }
  const bytes = fs.readFileSync(file);
  const report = await validator.validateBytes(new Uint8Array(bytes), { uri: `${name}.glb` });
  if (report.issues.numErrors || report.issues.numWarnings) failures.push(`${name}: validator ${report.issues.numErrors} errors, ${report.issues.numWarnings} warnings`);
  if (report.info.totalTriangleCount > limit) failures.push(`${name}: ${report.info.totalTriangleCount} triangles over ${limit}`);
  if (bytes.length > 350_000) failures.push(`${name}: ${bytes.length} bytes over 350 KB`);
  const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString("utf8"));
  if (json.images?.length || json.textures?.length || json.animations?.length || json.skins?.length) failures.push(`${name}: images, textures, animations or skins are not allowed`);
  if ((json.meshes ?? []).reduce((sum, mesh) => sum + mesh.primitives.length, 0) > 16) failures.push(`${name}: more than 16 primitives`);
  for (const material of json.materials ?? []) if (!materialNames.has(material.name)) failures.push(`${name}: unexpected material name ${material.name}`);
}
if (failures.length) { console.error(failures.join("\n")); process.exit(1); }
console.log(`City model kit passed: ${Object.keys(budgets).length} models.`);
