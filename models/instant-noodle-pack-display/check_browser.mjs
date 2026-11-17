// Exercise the actual production page and preserve a desktop Chromium screenshot.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const id = 'instant-noodle-pack-display';
const folder = path.resolve('models', id);
const asset = JSON.parse(await fs.readFile(path.join(folder, 'reports/assets.json'), 'utf8'));
const output = path.join(os.homedir(), 'Documents/MallQueue/reports', id + '-page.png');
await fs.mkdir(path.dirname(output), {recursive: true});
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const context = await browser.newContext({viewport: {width: 1440, height: 900}, serviceWorkers: 'block'});
const page = await context.newPage();
const errors = [], failed = [], loaded = [];
page.on('pageerror', error => errors.push(error.message));
page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
page.on('response', response => { if (response.status() >= 400) failed.push(response.status() + ' ' + response.url()); });
page.on('requestfailed', request => failed.push(request.url() + ' ' + request.failure()?.errorText));
const localBytes = await fs.readFile(path.join(folder, 'exports/optimized.glb'));
const expectedHash = createHash('sha256').update(localBytes).digest('hex');
await page.addInitScript(() => {
  window.qaDraws = [];
  for (const type of [WebGLRenderingContext, WebGL2RenderingContext]) {
    for (const name of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
      const original = type.prototype[name];
      if (original) type.prototype[name] = function(...args) {
        window.qaDraws.push({name, mode: args[0], count: args[name.includes('Elements') ? 1 : 2],
          instances: name.includes('Instanced') ? args[name.includes('Elements') ? 4 : 3] : 1,
          time: performance.now()});
        return original.apply(this, args);
      };
    }
  }
});
const ready = async () => {
  await page.waitForFunction(() => document.querySelector('#viewport canvas') &&
    document.querySelector('#viewer-status')?.textContent === '' && window.qaDraws.length > 0,
  null, {timeout: 60000});
  await page.waitForFunction(() => !document.querySelector('#reset-view').disabled);
};
let report;
try {
  // Vite fingerprints production GLB URLs; verify the actual response bytes instead of a source path.
  const [response] = await Promise.all([
    page.waitForResponse(response => new URL(response.url()).pathname.endsWith('.glb'), {timeout: 60000}),
    (async () => {
      await page.goto(server.url + '?model=' + id, {waitUntil: 'domcontentloaded'});
      await ready();
    })(),
  ]);
  assert.equal(response.status(), 200);
  const servedHash = createHash('sha256').update(await response.body()).digest('hex');
  assert.equal(servedHash, expectedHash);
  loaded.push({status: response.status(), sha256: servedHash});
  assert.equal(await page.locator('#viewer-title').innerText(), 'Instant Noodle Pack Display');
  assert.equal(await page.locator('#viewport canvas').count(), 1);
  assert.equal(await page.locator('#viewer-poster').isVisible(), false);
  // After environment precomputation, a keyboard orbit produces ordinary asset draws.
  await page.waitForTimeout(300);
  await page.locator('#viewport canvas').focus();
  await page.evaluate(() => { window.qaDraws = []; });
  await page.keyboard.press('ArrowLeft');
  await page.waitForFunction(() => window.qaDraws.length >= 3);
  await page.waitForTimeout(300);
  const drawEvents = await page.evaluate(() => window.qaDraws);
  const counts = drawEvents.map(event => event.count).sort((a, b) => a - b);
  const expectedCounts = Object.values(asset.parts).map(part => part.triangles * 3).sort((a, b) => a - b);
  // There may be more than one damping frame; every frame must contain the three batches.
  assert.ok(drawEvents.length % 3 === 0);
  for (const count of expectedCounts) assert.equal(counts.filter(value => value === count).length, counts.length / 3);
  assert.ok(drawEvents.every(event => event.mode === 4 && event.instances === 1));
  await page.locator('#reset-view').click();
  await page.waitForTimeout(300);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  await page.screenshot({path: output, fullPage: false});
  await page.reload({waitUntil: 'domcontentloaded'});
  await ready();
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => !document.querySelector('#viewer').open);
  assert.equal(await page.locator('#viewport canvas').count(), 0);
  assert.deepEqual(errors, []);
  assert.deepEqual(failed, []);
  report = {result: 'PASS', browser: 'headless Chromium', viewport: [1440, 900], screenshot: output,
    tested: ['direct model page', 'real GLB response SHA-256', 'visible WebGL canvas', 'keyboard orbit',
      'reset', 'refresh', 'close and canvas cleanup', 'no horizontal overflow'],
    ordinary_asset_draw_calls_per_frame: expectedCounts.length, asset_triangles_per_frame: asset.triangles,
    draw_event_count: drawEvents.length, glb_responses: loaded, errors, failed_requests: failed,
    not_verified: ['physical Android/iOS', 'WebKit', 'full 17-shop mall performance', 'deployment']};
  await fs.writeFile(path.join(folder, 'reports/browser.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  await context.close();
  await browser.close();
  await server.close();
}
