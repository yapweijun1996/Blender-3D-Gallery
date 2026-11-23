const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const validator = require('gltf-validator');
const filename = 'hair_ponytail_v1.glb';
const asset = fs.readFileSync(path.join(__dirname, filename));
validator.validateBytes(new Uint8Array(asset), {uri:filename}).then(report => {
  report.asset_sha256 = crypto.createHash('sha256').update(asset).digest('hex');
  fs.writeFileSync(path.join(__dirname, 'khronos_validation.json'), JSON.stringify(report, null, 2)+'\n');
  console.log(report.issues);
  if (report.issues.numErrors || report.issues.numWarnings) process.exitCode = 1;
}).catch(error => {console.error(error);process.exitCode=1;});
