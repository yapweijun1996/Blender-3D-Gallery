/** Validate the commerce hub modules: Khronos validator, budgets, no textures and the animated part names. */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const validator = require("gltf-validator");
const directory = path.join(path.dirname(fileURLToPath(import.meta.url)), "exports");
// [triangles, bytes, named parts the demo animates]
const modules = {
  bags: [11_500, 270_000, ["Bag_Large", "Bag_Medium", "Bag_Small"]],
  shop: [27_000, 720_000, ["Shop_Glass"]],
  warehouse: [24_000, 730_000, ["Conveyor_Box_1", "Conveyor_Box_2", "Conveyor_Box_3"]],
  delivery: [20_000, 500_000, ["Truck_Body", "Truck_Wheel_FL"]],
  payment: [7_200, 175_000, ["Card_Top", "Card_Middle", "Card_Bottom"]],
  analytics: [7_200, 175_000, ["Bar_Low", "Bar_Mid", "Bar_High"]],
  automation: [6_500, 175_000, ["Output_Card", "Indicator"]],
};
const failures = [];
let triangles = 0, bytes = 0;
for (const [name, [triangleLimit, byteLimit, parts]] of Object.entries(modules)) {
  const data = fs.readFileSync(path.join(directory, `${name}.glb`));
  const report = await validator.validateBytes(new Uint8Array(data), { uri: `${name}.glb` });
  if (report.issues.numErrors || report.issues.numWarnings) failures.push(`${name}: validator ${report.issues.numErrors} errors, ${report.issues.numWarnings} warnings`);
  if (report.info.totalTriangleCount > triangleLimit) failures.push(`${name}: ${report.info.totalTriangleCount} triangles over ${triangleLimit}`);
  if (data.length > byteLimit) failures.push(`${name}: ${data.length} bytes over ${byteLimit}`);
  const json = JSON.parse(data.subarray(20, 20 + data.readUInt32LE(12)).toString("utf8"));
  if (json.images?.length || json.textures?.length || json.animations?.length || json.skins?.length) failures.push(`${name}: images, textures, animations or skins are not allowed`);
  const names = new Set(json.nodes.map((node) => node.name));
  for (const part of parts) if (!names.has(part)) failures.push(`${name}: missing part ${part}`);
  triangles += report.info.totalTriangleCount;
  bytes += data.length;
}
if (triangles > 100_000 || bytes > 3_000_000) failures.push(`scene: ${triangles} triangles, ${bytes} bytes over the 100,000 / 3 MB budget`);
if (failures.length) { console.error(failures.join("\n")); process.exit(1); }
console.log(`Commerce hub modules passed: ${Object.keys(modules).length} models, ${triangles} triangles, ${bytes} bytes.`);
