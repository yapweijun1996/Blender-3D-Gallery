import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const dir = new URL('.', import.meta.url);
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const expected = await fs.readFile(new URL('exports/optimized.glb', dir));
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, serviceWorkers: 'block' });
  await context.addInitScript(() => {
    window.restaurantQA = { draws: 0 };
    for (const type of [WebGLRenderingContext, WebGL2RenderingContext]) {
      for (const method of ['drawElements', 'drawArrays']) {
        const original = type.prototype[method];
        type.prototype[method] = function (...args) {
          window.restaurantQA.draws++;
          return original.apply(this, args);
        };
      }
    }
  });
  const page = await context.newPage();
  const errors = [], warnings = [], failedRequests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
    if (msg.type() === 'warning') warnings.push(msg.text());
  });
  page.on('requestfailed', request => failedRequests.push({ url: request.url(), error: request.failure()?.errorText }));
  const responsePromise = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('.glb'));
  await page.goto(server.url + '?model=restaurant-food-props', { waitUntil: 'domcontentloaded' });
  const response = await responsePromise;
  assert.equal(response.status(), 200);
  assert.equal(sha256(await response.body()), sha256(expected), 'Browser consumes tested GLB');
  await page.waitForFunction(() => document.querySelector('#viewport canvas') &&
    document.querySelector('#viewer-status')?.textContent === '' && window.restaurantQA.draws > 0, null, { timeout: 60000 });
  await page.waitForTimeout(500);
  assert.ok((await page.locator('body').innerText()).includes('Restaurant Food Props'));
  const canvas = page.locator('#viewport canvas');
  await canvas.focus();
  const before = await canvas.screenshot();
  await page.keyboard.press('ArrowLeft');
  await page.waitForTimeout(300);
  const after = await canvas.screenshot();
  assert.ok(!before.equals(after), 'Keyboard orbit visibly changes actual rendered geometry');
  const evidence = await page.evaluate(() => ({ viewport: [innerWidth, innerHeight],
    canvas: { width: document.querySelector('#viewport canvas').width, height: document.querySelector('#viewport canvas').height },
    webgl_draws: window.restaurantQA.draws, horizontal_overflow: document.documentElement.scrollWidth > innerWidth,
    viewer_status: document.querySelector('#viewer-status').textContent }));
  assert.equal(evidence.horizontal_overflow, false);
  assert.deepEqual(errors, []);
  assert.deepEqual(failedRequests, []);
  const screenshot = process.env.MALL_REPORT_SCREENSHOT ?? '/Users/admin/Documents/MallQueue/reports/restaurant-food-props-page.png';
  await page.screenshot({ path: screenshot, fullPage: false });
  const report = { result: 'PASS', browser: 'Headless Chromium / SwiftShader', production_build: true,
    sha256: sha256(expected), ...evidence, keyboard_orbit: 'PASS: canvas pixels change', errors, warnings,
    failedRequests, screenshot, scope: 'Desktop 1440x900 production gallery page; no mini-game, full mall, physical-device or WebKit verification' };
  await fs.writeFile(new URL('reports/browser.json', dir), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report));
  await context.close();
} finally {
  await browser.close();
  await server.close();
}
