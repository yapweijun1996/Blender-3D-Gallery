import fs from 'node:fs';
import validator from 'gltf-validator';
import { loadCatalog } from './catalog.mjs';

const catalog = loadCatalog();
let errors = 0;
for (const { assets } of catalog.collections) {
  for (const asset of assets) {
    const bytes = fs.readFileSync(asset.file);
    const report = await validator.validateBytes(new Uint8Array(bytes), { uri: asset.file, maxIssues: 100 });
    const { numErrors, numWarnings, messages } = report.issues;
    console.log(`${asset.file}: ${asset.triangles} triangles, ${asset.bytes} bytes, ${numErrors} errors, ${numWarnings} warnings`);
    if (numErrors || numWarnings) {
      errors += numErrors + numWarnings;
      for (const issue of messages.filter(item => item.severity <= 1)) console.error(issue.message);
    }
  }
}
if (errors) process.exitCode = 1;
