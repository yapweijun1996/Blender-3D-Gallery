import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import validator from 'gltf-validator';
import { chromium } from 'playwright';
import { launchOptions, serveBuild } from '../../../scripts/browser-test-utils.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const asset = resolve(here, '..');
const modelName = 'indigo-ninja-head.glb';
const bytes = await readFile(join(asset, 'exports', modelName));
const result = await validator.validateBytes(new Uint8Array(bytes), { uri: modelName });
assert.equal(result.issues.numErrors, 0, JSON.stringify(result.issues.messages));
const jsonLength = bytes.readUInt32LE(12);
const document = JSON.parse(bytes.toString('utf8', 20, 20 + jsonLength));
const resources = [...document.buffers, ...(document.images ?? [])];
assert.ok(resources.every(item => !item.uri || item.uri.startsWith('data:')), 'GLB must be self-contained');

const output = join(asset, 'previews', 'runtime');
await mkdir(output, { recursive: true });
const report = {
  file: modelName,
  sha256: createHash('sha256').update(bytes).digest('hex'),
  fileBytes: bytes.length,
  validatorVersion: result.validatorVersion,
  issues: result.issues,
  meshes: document.meshes.length,
  materials: document.materials?.map(material => material.name) ?? [],
  images: document.images?.map(image => image.mimeType) ?? [],
  embedded: true,
  views: [],
};
const server = await serveBuild(resolve(here, '../../..'));
let browser;
try {
  browser = await chromium.launch({ ...launchOptions, channel: 'chrome' });
  report.chrome = browser.version();
  const page = await browser.newPage({ viewport: { width: 672, height: 672 }, deviceScaleFactor: 1 });
  // Capture the same byte snapshot that passed validation, including during an active rebuild.
  await page.route('**/exports/' + modelName, route => route.fulfill({ body: bytes, contentType: 'model/gltf-binary' }));
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error') errors.push(message.text());
  });
  await page.goto(server.url + 'models/indigo-ninja-head/qa/viewer.html');
  await page.waitForFunction(() => window.captureNinja || window.loadError, undefined, { timeout: 90000, polling: 200 })
    .catch(error => { throw new Error([error.message, ...errors].join('\n')); });
  assert.equal(await page.evaluate(() => window.loadError), undefined, errors.join('\n'));
  report.runtime = await page.evaluate(() => window.modelStats);
  assert.ok(report.runtime.triangles > 0 && report.runtime.meshInstances > 0);
  assert.ok(report.runtime.extentsMeters.every(value => Number.isFinite(value) && value > 0));
  const views = [
    ['front', 0], ['three-quarter', 35], ['profile', 90], ['back', 180],
    ['avatar-100', 35, 100], ['silhouette-100', 35, 100, true],
  ];
  for (const [name, angle, size = 672, silhouette = false] of views) {
    const stats = await page.evaluate(args => window.captureNinja(...args), [angle, size, silhouette]);
    assert.ok(stats.minScreenMargin > 0, `${name} clips geometry`);
    assert.ok(stats.drawCalls > 0);
    const capture = await page.locator('canvas').screenshot({ path: join(output, name + '.png') });
    report.views.push({ name, angle, ...stats, sha256: createHash('sha256').update(capture).digest('hex') });
  }
  assert.deepEqual(errors, []);
  assert.ok(bytes.equals(await readFile(join(asset, 'exports', modelName))), 'Export changed during review; rerun QA');
  await writeFile(join(here, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ sha256: report.sha256, triangles: report.runtime.triangles, views: report.views.length,
    errors: result.issues.numErrors, warnings: result.issues.numWarnings }));
} finally {
  await browser?.close();
  await server.close();
}
