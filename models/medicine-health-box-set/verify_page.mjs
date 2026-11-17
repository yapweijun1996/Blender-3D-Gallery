// Exercise the existing gallery route without changing application code.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { homedir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const dir = fileURLToPath(new URL('.', import.meta.url));
const id = 'medicine-health-box-set';
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const errors = [], requests = [], responseChecks = [];
const expected = createHash('sha256').update(await fs.readFile(dir + 'exports/optimized.glb')).digest('hex');
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, serviceWorkers: 'block' });
  await context.addInitScript(() => {
    window.healthDisplayDraws = 0;
    for (const type of [WebGLRenderingContext, WebGL2RenderingContext]) {
      for (const name of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
        const original = type.prototype[name];
        if (original) type.prototype[name] = function (...args) {
          window.healthDisplayDraws++;
          return original.apply(this, args);
        };
      }
    }
  });
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('requestfailed', request => errors.push(`${request.method()} ${new URL(request.url()).pathname}: ${request.failure()?.errorText}`));
  page.on('response', response => {
    if (new URL(response.url()).pathname.endsWith('.glb')) {
      responseChecks.push((async () => {
        const hash = createHash('sha256').update(await response.body()).digest('hex');
        assert.equal(response.status(), 200);
        assert.equal(hash, expected);
        requests.push({ path: new URL(response.url()).pathname, status: response.status(), sha256: hash });
      })());
    }
  });
  const ready = () => page.waitForFunction(() => document.querySelector('#viewer')?.open
    && document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent === ''
    && window.healthDisplayDraws > 0, null, { timeout: 60000 });
  await page.goto(server.url + '?model=' + id, { waitUntil: 'domcontentloaded' });
  await ready();
  assert.equal(await page.locator('#viewer-title').innerText(), 'Medicine and Health Box Display');
  const canvas = page.locator('#viewport canvas');
  const box = await canvas.boundingBox();
  assert.ok(box && box.width > 200 && box.height > 200);
  const before = await page.evaluate(() => window.healthDisplayDraws);
  await page.mouse.move(box.x + box.width * .5, box.y + box.height * .5);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * .64, box.y + box.height * .53, { steps: 8 });
  await page.mouse.up();
  await page.waitForFunction(count => window.healthDisplayDraws > count, before);
  await page.locator('#reset-view').click();
  await page.reload({ waitUntil: 'domcontentloaded' });
  await ready();
  await page.waitForTimeout(500);
  const screenshot = path.join(homedir(), 'Documents/MallQueue/reports', id + '-page.png');
  await fs.mkdir(path.dirname(screenshot), { recursive: true });
  await page.screenshot({ path: screenshot });
  await Promise.all(responseChecks);
  assert.ok(requests.length >= 2);
  assert.ok(requests.every(request => request.sha256 === expected), 'production resource identity');
  assert.deepEqual(errors, []);
  const report = {
    result: 'PASS', id, browser: 'headless Chromium', browser_version: browser.version(),
    graphics: 'SwiftShader software rendering', viewport: { width: 1440, height: 900 },
    route: '?model=' + id, screenshot, requested_glbs: requests, errors,
    checks: ['Direct model route', 'Real GLB response hash matches measured export', 'Canvas ready and actual WebGL draw calls', 'Pointer orbit redraw', 'Reset control', 'Page refresh'],
    limitations: ['Screenshot requires visual review', 'No physical mobile, WebKit or full mall performance test'],
  };
  await fs.writeFile(dir + 'reports/browser.json', JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
  await server.close();
}
