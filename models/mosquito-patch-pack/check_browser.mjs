// Exercise the built model page without changing gallery code.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, serviceWorkers: 'block' });
const page = await context.newPage();
const errors = [], responses = [];
page.on('pageerror', error => errors.push(error.message));
page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
page.on('response', response => { if (new URL(response.url()).pathname.endsWith('.glb')) responses.push(response); });
await page.addInitScript(() => {
  window.qaCalls = 0;
  for (const type of [WebGLRenderingContext, WebGL2RenderingContext]) {
    for (const name of ['drawElements', 'drawArrays', 'drawElementsInstanced', 'drawArraysInstanced']) {
      const original = type.prototype[name];
      if (original) type.prototype[name] = function (...args) {
        window.qaCalls++;
        return original.apply(this, args);
      };
    }
  }
});
const ready = () => page.waitForFunction(() => document.querySelector('#viewport canvas') &&
  document.querySelector('#viewer-status')?.textContent === '' && window.qaCalls > 0, null, { timeout: 60000 });
try {
  await page.goto(server.url + '?model=mosquito-patch-pack', { waitUntil: 'domcontentloaded' });
  await ready();
  await page.locator('#viewer[open]').waitFor();
  assert.equal(await page.locator('#viewport canvas').count(), 1);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  const screenshot = path.join(os.homedir(), 'Documents/MallQueue/reports/mosquito-patch-pack-page.png');
  await fs.mkdir(path.dirname(screenshot), { recursive: true });
  await page.screenshot({ path: screenshot });
  const initial = await page.locator('#viewport canvas').screenshot();
  await page.locator('#viewport canvas').focus();
  await page.evaluate(() => { window.qaCalls = 0; });
  await page.keyboard.press('ArrowLeft');
  await page.waitForFunction(() => window.qaCalls > 0);
  const orbitDrawCalls = await page.evaluate(() => window.qaCalls);
  const rotated = await page.locator('#viewport canvas').screenshot();
  assert.ok(!initial.equals(rotated), 'Orbit changes rendered pixels');
  const source = await fs.readFile(new URL('exports/optimized.glb', import.meta.url));
  const expectedHash = createHash('sha256').update(source).digest('hex');
  assert.equal(responses.length, 1);
  const loadedHash = createHash('sha256').update(await responses[0].body()).digest('hex');
  assert.equal(loadedHash, expectedHash);
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => !document.querySelector('#viewer').open && !document.querySelector('#viewport canvas'));
  await page.goto(server.url + '?model=mosquito-patch-pack', { waitUntil: 'domcontentloaded' });
  await ready();
  assert.equal(await page.locator('#viewport canvas').count(), 1);
  assert.deepEqual(errors, []);
  const report = { result: 'PASS', viewport: [1440, 900], backend: 'Headless Chromium / SwiftShader',
    model_page: 'PASS', glb_sha256: loadedHash, loaded_bytes: source.length,
    keyboard_orbit_pixels_changed: true, orbit_draw_calls_observed: orbitDrawCalls,
    close_canvas_disposal: 'PASS', reopen: 'PASS', horizontal_overflow: false, errors, screenshot,
    limitations: 'No physical devices, WebKit or assembled 17-shop mall performance test.' };
  await fs.writeFile(new URL('reports/browser.json', import.meta.url), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  await context.close();
  await browser.close();
  await server.close();
}
