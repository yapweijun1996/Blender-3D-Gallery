const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const validator = require('../../../../../node_modules/gltf-validator');

const root = path.resolve(process.env.SLIPONS_FIT_OUTPUT || path.join(__dirname, '..'));
fs.mkdirSync(path.join(root, 'qa'), {recursive: true});
const name = 'shoes_slipons_v1.glb';
const bytes = fs.readFileSync(path.join(root, name));
validator.validateBytes(bytes, {uri: name, format: 'glb', maxIssues: 0}).then(report => {
  report.glb_sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
  fs.writeFileSync(path.join(root, 'qa', 'validator.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report.issues, null, 2));
  if (report.issues.numErrors || report.issues.numWarnings) process.exitCode = 1;
}).catch(error => {
  console.error(error);
  process.exitCode = 1;
});
