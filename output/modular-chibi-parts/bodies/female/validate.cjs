const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const validator = require("gltf-validator");

async function main() {
  for (const name of process.argv.slice(2)) {
    const file = path.resolve(__dirname, name);
    if (path.dirname(file) !== __dirname) throw new Error("Expected a GLB in the female output directory");
    const bytes = fs.readFileSync(file);
    const report = await validator.validateBytes(new Uint8Array(bytes), { uri: path.basename(file) });
    report.sha256 = crypto.createHash("sha256").update(bytes).digest("hex");
    fs.writeFileSync(file.replace(/\.glb$/, ".validator.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(path.basename(file), report.issues.numErrors, report.issues.numWarnings, report.sha256);
    if (report.issues.numErrors || report.issues.numWarnings) process.exitCode = 1;
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
