import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';
import { serveBuild } from '../../scripts/browser-test-utils.mjs';

const id = 'headphone-display-stand';
const dir = new URL('.', import.meta.url);
const asset = JSON.parse(await fs.readFile(new URL('reports/assets.json', dir), 'utf8'));
const reports = path.join(os.homedir(), 'Documents/MallQueue/reports');
await fs.mkdir(reports, { recursive: true });
const server = await serveBuild();
const browser = await chromium.launch({ headless: true,
  executablePath: process.env.GALLERY_CHROME ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  args: ['--use-angle=metal', '--enable-webgl'] });
const errors = [], failedResponses = [], loaded = [];
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, serviceWorkers: 'block' });
  await context.addInitScript(() => {
    window.assetDrawCalls = 0;
    for (const type of [WebGLRenderingContext, WebGL2RenderingContext]) {
      for (const name of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
        const original = type.prototype[name];
        if (original) type.prototype[name] = function (...args) {
          window.assetDrawCalls++;
          return original.apply(this, args);
        };
      }
    }
  });
  const page = await context.newPage();
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('response', r => { if (r.status() >= 400) failedResponses.push(`${r.status()} ${r.url()}`); });
  const modelResponse = page.waitForResponse(r => new URL(r.url()).pathname.endsWith('.glb'));
  await page.goto(server.url + '?model=' + id, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => document.querySelector('#viewport canvas') &&
    document.querySelector('#viewer-status')?.textContent === '' && window.assetDrawCalls > 0, null, { timeout: 60000 });
  assert.equal(await page.locator('#viewer').evaluate(el => el.open), true);
  const response = await modelResponse;
  const bytes = await response.body();
  loaded.push({ file: new URL(response.url()).pathname.split('/').at(-1), bytes: bytes.length,
    sha256: createHash('sha256').update(bytes).digest('hex') });
  assert.equal(loaded[0].sha256, asset.sha256);
  const screenshot = path.join(reports, id + '-page.png');
  await page.screenshot({ path: screenshot });
  const canvas = page.locator('#viewport canvas');
  await canvas.focus();
  const before = await page.evaluate(() => window.assetDrawCalls);
  await page.keyboard.press('ArrowLeft');
  await page.waitForFunction(n => window.assetDrawCalls > n, before);
  await page.screenshot({ path: path.join(reports, id + '-orbit.png') });
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => !document.querySelector('#viewer').open && !document.querySelector('#viewport canvas'));
  assert.deepEqual(errors, []);
  assert.deepEqual(failedResponses, []);
  const result = { result: 'PASS', viewport: [1440, 900], browser: await browser.version(),
    backend: 'Chromium ANGLE Metal', loaded, errors, failedResponses, screenshot,
    checks: ['Built model page opens with real WebGL draws', 'Loaded GLB hash matches validated export',
      'Keyboard orbit draws another frame', 'Escape closes viewer and releases its canvas'],
    not_verified: ['Physical Android/iOS', 'WebKit', 'Full 17-shop mall assembly or frame rate'] };
  await fs.writeFile(new URL('reports/browser.json', dir), JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result));
} finally {
  await browser.close();
  await server.close();
}
