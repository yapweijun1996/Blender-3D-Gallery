const fs = require('node:fs');
const path = require('node:path');
const validator = require(path.resolve(__dirname, '../../../../../../node_modules/gltf-validator'));
(async () => {
  const results = {};
  for (const name of ['body_male_v1.glb', 'hand_gestures_male.glb']) {
    const data = fs.readFileSync(path.resolve(__dirname, '..', name));
    const result = await validator.validateBytes(new Uint8Array(data), {uri: name, maxIssues: 10000});
    results[name] = {sha256: require('node:crypto').createHash('sha256').update(data).digest('hex'), ...result};
    console.log(name, result.issues.numErrors, 'errors,', result.issues.numWarnings, 'warnings,', result.issues.numInfos, 'infos');
  }
  fs.writeFileSync(path.resolve(__dirname, 'khronos.json'), JSON.stringify(results, null, 2));
})().catch(error => { console.error(error); process.exitCode = 1; });
