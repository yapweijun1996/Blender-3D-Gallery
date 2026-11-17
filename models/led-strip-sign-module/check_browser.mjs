import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const dir = fileURLToPath(new URL('.', import.meta.url));
const id = 'led-strip-sign-module';
const screenshot = path.join(os.homedir(), 'Documents/MallQueue/reports', id + '-page.png');
fs.mkdirSync(path.dirname(screenshot), { recursive: true });
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, serviceWorkers: 'block' });
  await context.addInitScript(() => {
    window.signDraws = 0;
    for (const type of [WebGLRenderingContext, WebGL2RenderingContext]) {
      for (const method of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
        const original = type.prototype[method];
        if (original) type.prototype[method] = function (...args) { window.signDraws++; return original.apply(this, args); };
      }
    }
  });
  const page = await context.newPage(), errors = [], glbs = [], failures = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('request', req => { if (new URL(req.url()).pathname.endsWith('.glb')) glbs.push(req.url()); });
  page.on('response', response => { if (response.status() >= 400) failures.push({ url: response.url(), status: response.status() }); });
  await page.goto(server.url, { waitUntil: 'domcontentloaded' });
  await page.locator('#catalog .asset-card').first().waitFor({ state: 'attached', timeout: 90000 });
  await page.locator('#model-search').fill('LED-Strip Sign Module');
  assert.equal(await page.locator('canvas').count(), 0);
  assert.equal(glbs.length, 0, 'catalog stays lazy');
  // Vite fingerprints GLB filenames; verify the loaded bytes by hash instead.
  const response = page.waitForResponse(r => new URL(r.url()).pathname.endsWith('.glb'), { timeout: 90000 });
  await page.locator('[data-asset-id="' + id + '"]').first().click();
  const loadedBytes = await (await response).body();
  const loadedHash = createHash('sha256').update(loadedBytes).digest('hex');
  const fileHash = createHash('sha256').update(fs.readFileSync(dir + 'exports/optimized.glb')).digest('hex');
  assert.equal(loadedHash, fileHash);
  await page.waitForFunction(() => document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent === '' && window.signDraws > 0, null, { timeout: 90000 });
  assert.equal(await page.locator('#viewer-title').innerText(), 'LED-Strip Sign Module');
  assert.equal(new URL(page.url()).searchParams.get('model'), id);
  assert.equal(glbs.length, 1);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  const canvas = page.locator('#viewport canvas');
  const box = await canvas.boundingBox();
  assert.ok(box.width > 0 && box.height > 0);
  const initial = await canvas.screenshot();
  const before = await page.evaluate(() => window.signDraws);
  await page.mouse.move(box.x + box.width * .45, box.y + box.height * .5);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * .68, box.y + box.height * .54, { steps: 8 });
  await page.mouse.up();
  await page.waitForFunction(n => window.signDraws > n, before);
  assert.notDeepEqual(await canvas.screenshot(), initial, 'orbit changes the rendered view');
  await page.locator('#reset-view').click();
  await page.screenshot({ path: screenshot });
  await page.locator('#close-viewer').click();
  assert.equal(await page.locator('#viewport canvas').count(), 0);
  await page.goto(server.url + '?model=' + id, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent === '' && window.signDraws > 0, null, { timeout: 90000 });
  await page.screenshot({ path: screenshot });
  assert.equal(await page.locator('#viewport canvas').count(), 1);
  assert.deepEqual(errors, []);
  assert.deepEqual(failures, []);
  const report = { result: 'PASS', viewport: [1440, 900], browser_version: browser.version(),
    sha256: loadedHash, screenshot, screenshot_sha256: createHash('sha256').update(fs.readFileSync(screenshot)).digest('hex'),
    verified: ['lazy catalog', 'asset card opens real GLB', 'loaded artifact hash matches', 'WebGL draw observed', 'orbit visibly changes rendering', 'reset control', 'viewer disposal', 'direct model URL'],
    console_errors: errors, http_failures: failures,
    not_verified: ['mall Bloom integration', 'physical devices', 'WebKit', 'assembled-mall performance', 'publication'] };
  fs.writeFileSync(dir + 'reports/browser.json', JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report));
  await context.close();
} finally {
  await browser.close();
  await server.close();
}
