const crypto = require('node:crypto');
const fs = require('node:fs');
const validator = require('../../../../../node_modules/gltf-validator');
const uri = 'shoes_hightop_v1.glb';
const bytes = fs.readFileSync(uri);
validator.validateBytes(new Uint8Array(bytes), {uri, maxIssues: 2000}).then(report => {
  report.exportSha256 = crypto.createHash('sha256').update(bytes).digest('hex');
  fs.writeFileSync('validator.json', JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report.issues));
  process.exitCode = Number(Boolean(report.issues.numErrors || report.issues.numWarnings));
});
