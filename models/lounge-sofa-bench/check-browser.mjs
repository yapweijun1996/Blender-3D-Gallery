import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const here = new URL('.', import.meta.url);
const id = 'lounge-sofa-bench';
const expected = JSON.parse(await fs.readFile(new URL('reports/assets.json', here)));
const screenshot = path.join(os.homedir(), 'Documents/MallQueue/reports', `${id}-page.png`);
await fs.mkdir(path.dirname(screenshot), { recursive: true });
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const errors = [], loadedHashes = [];
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, serviceWorkers: 'block' });
  await context.addInitScript(() => {
    window.assetDraws = 0;
    window.assetFrameDraws = 0;
    for (const type of [WebGLRenderingContext, WebGL2RenderingContext]) {
      const clear = type.prototype.clear;
      type.prototype.clear = function (...args) {
        window.assetFrameDraws = 0;
        return clear.apply(this, args);
      };
      for (const name of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
        const original = type.prototype[name];
        if (original) type.prototype[name] = function (...args) {
          window.assetDraws++;
          window.assetFrameDraws++;
          return original.apply(this, args);
        };
      }
    }
  });
  const page = await context.newPage();
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('response', response => {
    if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);
  });
  const ready = () => page.waitForFunction(() => document.querySelector('#viewport canvas') &&
    document.querySelector('#viewer-status')?.textContent === '' && window.assetDraws > 0,
    null, { timeout: 60000 });
  const modelUrl = server.url + '?model=' + id;
  const responsePromise = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('.glb'));
  await page.goto(modelUrl, { waitUntil: 'domcontentloaded' });
  const response = await responsePromise;
  loadedHashes.push(createHash('sha256').update(await response.body()).digest('hex'));
  await ready();
  assert.equal(loadedHashes[0], expected.sha256, 'browser consumes the validated GLB');
  assert.equal(await page.locator('#viewport canvas').count(), 1);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  const drawCalls = await page.evaluate(() => window.assetFrameDraws);
  assert.equal(drawCalls, 3, 'three opaque material batches in actual viewer frame');
  const canvas = page.locator('#viewport canvas');
  const initialDraws = await page.evaluate(() => window.assetDraws);
  await canvas.focus();
  await page.keyboard.press('ArrowLeft');
  await page.waitForFunction(before => window.assetDraws > before, initialDraws);
  const beforeReset = await page.evaluate(() => window.assetDraws);
  await page.locator('#reset-view').click();
  await page.waitForFunction(before => window.assetDraws > before, beforeReset);
  await page.screenshot({ path: screenshot, fullPage: false, animations: 'disabled' });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await ready();
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => !document.querySelector('#viewport canvas'));
  await page.goto(modelUrl, { waitUntil: 'domcontentloaded' });
  await ready();
  assert.deepEqual(errors, []);
  const report = { result: 'PASS', id, viewport: [1440, 900], screenshot,
    consumed_glb_sha256: loadedHashes[0], draw_calls_in_model_frame: drawCalls,
    checks: ['real GLB load and rendered frame', 'no horizontal overflow', 'keyboard orbit', 'reset', 'refresh', 'close cleanup', 'reopen'],
    errors, limitations: ['Physical Android/iOS and WebKit not tested', 'Full-mall draw-call budget and performance not measured'] };
  await fs.writeFile(new URL('reports/browser.json', here), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
  await context.close();
} finally {
  await browser.close();
  await server.close();
}
