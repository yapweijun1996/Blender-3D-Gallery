import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const dir = fileURLToPath(new URL('.', import.meta.url));
const reportDir = path.join(os.homedir(), 'Documents/MallQueue/reports');
fs.mkdirSync(reportDir, { recursive: true });
const sha = data => createHash('sha256').update(data).digest('hex');
const expectedHash = sha(fs.readFileSync(dir + 'exports/optimized.glb'));
const expectedIds = JSON.parse(fs.readFileSync(new URL('../catalog.json', import.meta.url)))
  .collections.flatMap(collection => collection.assets.map(asset => asset.id)).sort();
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  await page.addInitScript(() => {
    window.qaDrawCalls = 0;
    for (const type of [WebGLRenderingContext, WebGL2RenderingContext]) {
      for (const name of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
        const original = type.prototype[name];
        if (original) type.prototype[name] = function (...args) {
          window.qaDrawCalls++;
          return original.apply(this, args);
        };
      }
    }
  });
  const errors = [];
  page.on('pageerror', error => errors.push(String(error)));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  const responsePromise = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('.glb'));
  await page.goto(server.url + '?model=pharmacy-counter', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => document.querySelector('#viewer-title')?.textContent === 'Pharmacy Counter'
    && document.querySelector('#viewer-poster')?.hidden
    && document.querySelector('#reset-view')?.disabled === false
    && window.qaDrawCalls > 0, null, { timeout: 60000 });
  const response = await responsePromise;
  assert.equal(response.status(), 200);
  assert.equal(sha(await response.body()), expectedHash, 'browser loaded the tested GLB');
  assert.deepEqual(await page.locator('#catalog .asset-card').evaluateAll(
    cards => cards.map(card => card.querySelector('a[data-asset-id]')?.dataset.assetId).sort()),
    expectedIds, 'Production catalog preserves all registered assets');
  const canvas = page.locator('#viewport canvas');
  assert.equal(await canvas.count(), 1);
  const box = await canvas.boundingBox();
  assert.ok(box?.width > 200 && box?.height > 200);
  await page.mouse.move(box.x + box.width * .5, box.y + box.height * .5);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * .5 + 90, box.y + box.height * .5 + 30, { steps: 8 });
  await page.mouse.up();
  await page.locator('#reset-view').click();
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const screenshot = path.join(reportDir, 'pharmacy-counter-page.png');
  await page.screenshot({ path: screenshot, animations: 'disabled' });
  assert.deepEqual(errors, []);
  const report = {
    result: 'PASS', browser: 'headless Chromium', browser_version: browser.version(),
    viewport: { width: 1440, height: 900 }, screenshot, glb_sha256: expectedHash,
    glb_response: response.status(), canvas_count: 1, canvas_size: [box.width, box.height],
    flow: 'Open model URL, load actual GLB, orbit, reset, capture page', errors,
    catalog_membership: 'PASS', build: await (await page.request.get(server.url + 'build-info.json')).json(),
    scope: 'Local production build with software WebGL; no physical device or full mall performance claim',
  };
  fs.writeFileSync(dir + 'reports/browser.json', JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
  await server.close();
}
