/** Validate the drive demo model kit: Khronos validator, budgets, static-asset rules and required material names. */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const validator = require("gltf-validator");
const directory = path.join(path.dirname(fileURLToPath(import.meta.url)), "kit");
const budgets = { // triangles
  car_hatchback: 2500, car_sedan: 2800, bus: 3500, motorbike: 900, street_lamp: 450, traffic_light: 400, sign_gantry: 700, bus_stop: 900,
  guardrail: 250, road_cone: 120, tree_raintree: 900, tree_palm: 600, tree_street: 400, shrub_hedge: 120, building_hdb: 1800,
  building_tower_glass: 900, building_shophouse: 1800, building_condo: 1600, building_lowrise: 900, landmark_mbs: 3500,
  landmark_checkpoint: 2800, landmark_southkey: 3000,
  // Game-ready versions of existing gallery models (Proton Saga, hatchback, bus, van, truck, motorcycle).
  car_saga: 5600, car_hatchback_hd: 4600, motorbike_hd: 2300, bus_hd: 6600, van_hd: 4600, truck_hd: 5100,
};
const materialNames = new Set(["paint", "glass", "tire", "light", "trim", "wall", "roof", "window", "leaf", "trunk", "metal", "concrete", "chrome", "plate"]);
const failures = [];
for (const [name, limit] of Object.entries(budgets)) {
  const file = path.join(directory, `${name}.glb`);
  if (!fs.existsSync(file)) { failures.push(`${name}: missing`); continue; }
  const bytes = fs.readFileSync(file);
  const report = await validator.validateBytes(new Uint8Array(bytes), { uri: `${name}.glb` });
  if (report.issues.numErrors || report.issues.numWarnings) failures.push(`${name}: validator ${report.issues.numErrors} errors, ${report.issues.numWarnings} warnings`);
  const info = report.info;
  if (info.totalTriangleCount > limit) failures.push(`${name}: ${info.totalTriangleCount} triangles over ${limit}`);
  if (bytes.length > 350_000) failures.push(`${name}: ${bytes.length} bytes over 350 KB`);
  const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString("utf8"));
  if (json.images?.length || json.textures?.length || json.animations?.length || json.skins?.length) failures.push(`${name}: images, textures, animations or skins are not allowed`);
  if ((json.meshes ?? []).reduce((sum, mesh) => sum + mesh.primitives.length, 0) > 16) failures.push(`${name}: more than 16 primitives`);
  for (const material of json.materials ?? []) if (!materialNames.has(material.name)) failures.push(`${name}: unexpected material name ${material.name}`);
}
if (failures.length) { console.error(failures.join("\n")); process.exit(1); }
console.log(`Drive model kit passed: ${Object.keys(budgets).length} models.`);
