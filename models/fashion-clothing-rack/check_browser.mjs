// Exercise the real built gallery; no application code or viewer overrides.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const id = 'fashion-clothing-rack';
const out = path.join(os.homedir(), 'Documents/MallQueue/reports');
await fs.mkdir(out, { recursive: true });
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, serviceWorkers: 'block' });
const errors = [], responses = [];
await context.addInitScript(() => {
  window.qaDraws = 0;
  for (const type of [WebGLRenderingContext, WebGL2RenderingContext]) {
    for (const name of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
      const original = type.prototype[name];
      if (original) type.prototype[name] = function (...args) {
        window.qaDraws++;
        return original.apply(this, args);
      };
    }
  }
});
const page = await context.newPage();
page.on('pageerror', error => errors.push(error.message));
page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
page.on('response', response => { if (new URL(response.url()).pathname.endsWith('.glb')) responses.push(response); });
const screenshot = path.join(out, `${id}-page.png`);
try {
  await page.goto(`${server.url}?model=${id}`, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => document.querySelector('#viewport canvas') &&
    document.querySelector('#viewer-status')?.textContent === '' &&
    document.querySelector('#viewer-poster')?.hidden && window.qaDraws > 0, null, { timeout: 60000 });
  assert.equal(await page.locator('#viewer').evaluate(dialog => dialog.open), true);
  assert.equal(await page.locator('#reset-view').isEnabled(), true);
  assert.equal(responses.length, 1);
  assert.equal(responses[0].status(), 200);
  const loadedHash = createHash('sha256').update(await responses[0].body()).digest('hex');
  const diskHash = createHash('sha256').update(await fs.readFile(`models/${id}/exports/optimized.glb`)).digest('hex');
  assert.equal(loadedHash, diskHash);
  const before = await page.evaluate(() => window.qaDraws);
  const canvas = page.locator('#viewport canvas');
  const rect = await canvas.boundingBox();
  await page.mouse.move(rect.x + rect.width * .48, rect.y + rect.height * .50);
  await page.mouse.down();
  await page.mouse.move(rect.x + rect.width * .64, rect.y + rect.height * .52, { steps: 8 });
  await page.mouse.up();
  await page.waitForFunction(before => window.qaDraws > before, before);
  await page.locator('#reset-view').click();
  await page.waitForFunction(before => window.qaDraws > before + 3, before);
  await page.screenshot({ path: screenshot });
  assert.deepEqual(errors, []);
  const report = { result: 'PASS', viewport: [1440, 900], chromium: browser.version(),
    page_url: `?model=${id}`, loaded_glb_sha256: loadedHash, screenshot,
    checks: ['real GLB HTTP 200 and hash match', 'WebGL draw observed', 'loading overlay cleared', 'pointer orbit', 'reset', 'zero console/page/HTTP errors'],
    webgl_draw_calls_observed: await page.evaluate(() => window.qaDraws), errors,
    limitations: ['physical devices not tested', 'WebKit not tested', 'complete mall frame rate and draw-call budget not measured'] };
  await fs.writeFile(`models/${id}/reports/browser.json`, JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  await context.close();
  await browser.close();
  await server.close();
}
