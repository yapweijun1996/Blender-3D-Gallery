// Local Khronos validator. All modelling and skeletal evaluation run in Blender.
const fs = require('node:fs');
const path = require('node:path');
const validator = require('gltf-validator');

async function main() {
  const reports = {};
  for (const relative of ['hold_actions.glb', 'props/box.glb', 'props/bag.glb', 'props/shelf_item.glb']) {
    const bytes = fs.readFileSync(path.join(__dirname, relative));
    const report = await validator.validateBytes(new Uint8Array(bytes), { uri: relative });
    reports[relative] = report;
    const { numErrors, numWarnings } = report.issues;
    console.log(relative, numErrors, 'errors,', numWarnings, 'warnings');
    if (numErrors || numWarnings) process.exitCode = 1;
  }
  fs.writeFileSync(path.join(__dirname, 'checks/khronos.json'), JSON.stringify(reports, null, 2) + '\n');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
