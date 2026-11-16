// Run after npm run build. Saves the actual model page and runtime evidence.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright';
import {serveBuild, launchOptions} from '../../scripts/browser-test-utils.mjs';

const dir = new URL('.', import.meta.url);
const reportDir = path.join(os.homedir(), 'Documents/MallQueue/reports');
await fs.mkdir(reportDir, {recursive: true});
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const errors = [], failures = [];
try {
  const context = await browser.newContext({viewport: {width: 1440, height: 900}, serviceWorkers: 'block'});
  await context.addInitScript(() => {
    window.assetFrames = [];
    let active;
    const raf = window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame = callback => raf(time => {
      active = {calls: 0, triangles: 0};
      window.assetFrames.push(active);
      callback(time);
      active = undefined;
    });
    for (const type of [WebGLRenderingContext, WebGL2RenderingContext]) {
      for (const name of ['drawArrays', 'drawElements']) {
        const original = type.prototype[name];
        type.prototype[name] = function(mode, a, b, ...rest) {
          if (active) {
            active.calls++;
            if (mode === this.TRIANGLES) active.triangles += (name === 'drawArrays' ? b : a) / 3;
          }
          return original.call(this, mode, a, b, ...rest);
        };
      }
    }
  });
  const page = await context.newPage();
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('response', r => { if (r.status() >= 400) failures.push(`${r.status()} ${r.url()}`); });
  // Production builds fingerprint asset filenames; verify actual response bytes.
  const responsePromise = page.waitForResponse(r => new URL(r.url()).pathname.endsWith('.glb'));
  await page.goto(server.url + '?model=aquarium-tank', {waitUntil: 'domcontentloaded'});
  const response = await responsePromise;
  const loadedHash = createHash('sha256').update(await response.body()).digest('hex');
  const sourceBytes = await fs.readFile(new URL('exports/optimized.glb', dir));
  assert.equal(loadedHash, createHash('sha256').update(sourceBytes).digest('hex'));
  await page.waitForFunction(() => document.querySelector('#viewport canvas') &&
    document.querySelector('#viewer-status')?.textContent === '' && window.assetFrames.some(f => f.calls > 0), null, {timeout: 60000});
  assert.equal(await page.locator('#viewer-title').innerText(), 'Aquarium Tank');
  assert.ok(await page.locator('#viewer').evaluate(el => el.open));
  const screenshot = path.join(reportDir, 'aquarium-tank-page.png');
  await page.screenshot({path: screenshot});
  const frames = await page.evaluate(() => window.assetFrames.filter(f => f.calls > 0));
  const maxCalls = Math.max(...frames.map(f => f.calls));
  assert.ok(maxCalls <= 6, `bounded aquarium draw calls: ${maxCalls}`);
  const canvas = page.locator('#viewport canvas');
  await canvas.focus();
  await page.keyboard.press('ArrowLeft');
  await page.waitForFunction(n => window.assetFrames.filter(f => f.calls > 0).length > n, frames.length);
  await page.screenshot({path: path.join(reportDir, 'aquarium-tank-orbit.png')});
  const beforeReset = await page.evaluate(() => window.assetFrames.filter(f => f.calls > 0).length);
  await page.locator('#reset-view').click();
  await page.waitForFunction(n => window.assetFrames.filter(f => f.calls > 0).length > n, beforeReset);
  assert.deepEqual(errors, []);
  assert.deepEqual(failures, []);
  const result = {result: 'PASS', viewport: [1440, 900], browser: await browser.version(),
    loaded_sha256: loadedHash, screenshot, model_draw_calls_per_frame: maxCalls,
    initial_render_frames: frames, keyboard_orbit: 'PASS', reset: 'PASS', errors, failed_responses: failures,
    limitations: 'Headless Chromium with SwiftShader only; no physical devices, WebKit or full mall assembly.'};
  await fs.writeFile(new URL('reports/browser.json', dir), JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result, null, 2));
  await context.close();
} finally {
  await browser.close();
  await server.close();
}
