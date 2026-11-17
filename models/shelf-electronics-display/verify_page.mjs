import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const dir = path.dirname(new URL(import.meta.url).pathname);
const id = 'shelf-electronics-display';
const reports = path.join(os.homedir(), 'Documents/MallQueue/reports');
await fs.mkdir(reports, { recursive: true });
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const expectedHash = sha(await fs.readFile(path.join(dir, 'exports/optimized.glb')));
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const errors = [];
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, serviceWorkers: 'block' });
  await context.addInitScript(() => {
    window.qaDrawCalls = 0;
    for (const type of [WebGLRenderingContext, WebGL2RenderingContext]) {
      for (const name of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
        const original = type.prototype[name];
        if (original) type.prototype[name] = function (...args) { window.qaDrawCalls++; return original.apply(this, args); };
      }
    }
  });
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
  // Vite fingerprints the delivery URL; verify the response bytes against the source GLB.
  const responsePromise = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('.glb'));
  await page.goto(`${server.url}?model=${id}`, { waitUntil: 'domcontentloaded' });
  const response = await responsePromise;
  assert.equal(response.status(), 200);
  assert.equal(sha(await response.body()), expectedHash);
  await page.waitForFunction(() => document.querySelector('#viewport canvas') &&
    document.querySelector('#viewer-status')?.textContent === '' && window.qaDrawCalls > 0, null, { timeout: 60000 });
  assert.equal(await page.locator('#viewer-title').innerText(), 'Electronics Store Display Shelf');
  const canvas = page.locator('#viewport canvas');
  await canvas.focus();
  const first = await canvas.screenshot();
  await page.screenshot({ path: path.join(reports, `${id}-page.png`) });
  const drawsBefore = await page.evaluate(() => window.qaDrawCalls);
  await page.keyboard.press('ArrowRight');
  await page.waitForFunction(count => window.qaDrawCalls > count, drawsBefore);
  const second = await canvas.screenshot();
  assert.notEqual(sha(first), sha(second), 'keyboard rotation changes rendered pixels');
  assert.deepEqual(errors, []);
  const report = { result: 'PASS', browser: 'headless Chromium / SwiftShader',
    browser_version: browser.version(), viewport: { width: 1440, height: 900 },
    glb_http_status: response.status(), glb_sha256: expectedHash, actual_webgl_draws: true,
    keyboard_rotation_pixel_change: true, console_page_http_errors: errors,
    screenshot: path.join(reports, `${id}-page.png`),
    limits: ['Local production build only', 'Physical mobile, WebKit and complete mall performance not tested'] };
  await fs.writeFile(path.join(dir, 'reports/browser.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
  await server.close();
}
