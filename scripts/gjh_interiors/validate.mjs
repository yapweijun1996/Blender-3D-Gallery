// Validate each catalog LOD, including the two runtime-only tiers.
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import validator from "gltf-validator";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, "../..");
const program = JSON.parse(fs.readFileSync(path.join(here, "program.json"), "utf8"));
let count = 0;
let errors = 0;
let warnings = 0;
for (const store of program.stores) {
  const folder = path.join(root, "models", store.slug);
  const names = store.order ? ["lod1.glb", "balanced.glb", "optimized.glb"] : ["lod1.glb", "optimized.glb"];
  const results = {};
  for (const name of names) {
    const bytes = fs.readFileSync(path.join(folder, "exports", name));
    const report = await validator.validateBytes(new Uint8Array(bytes), { uri: name, maxIssues: 0 });
    results[name] = {
      sha256: createHash("sha256").update(bytes).digest("hex"),
      validatorVersion: report.validatorVersion,
      issues: report.issues,
    };
    count++;
    errors += report.issues.numErrors;
    warnings += report.issues.numWarnings;
    for (const issue of report.issues.messages) console.log(store.slug, name, issue.code, issue.message);
  }
  const reportPath = path.join(folder, "reports", "khronos.json");
  const text = JSON.stringify(results, null, 2) + "\n";
  if (process.argv.includes("--write")) {
    fs.mkdirSync(path.dirname(reportPath), { recursive: true });
    fs.writeFileSync(reportPath, text);
  } else if (fs.readFileSync(reportPath, "utf8") !== text) {
    throw new Error("Saved Khronos results differ for " + store.slug);
  }
}
console.log(`${count} GLBs, ${errors} errors, ${warnings} warnings`);
if (errors || warnings) process.exitCode = 1;
