// Inspect the existing model page; no gallery or viewer changes.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright';
import {serveBuild, launchOptions} from '../../scripts/browser-test-utils.mjs';

const dir = new URL('.', import.meta.url);
const measured = JSON.parse(await fs.readFile(new URL('reports/assets.json', dir), 'utf8'));
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const reportDirectory = path.join(os.homedir(), 'Documents/MallQueue/reports');
await fs.mkdir(reportDirectory, {recursive: true});
const errors = [];
try {
  const page = await browser.newPage({viewport: {width: 1440, height: 900}, serviceWorkers: 'block'});
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  await page.addInitScript(() => {
    window.skylightFrames = {};
    window.skylightFrame = 0;
    const raf = window.requestAnimationFrame;
    window.requestAnimationFrame = callback => raf.call(window, time => {
      window.skylightFrame = time;
      callback(time);
    });
    for (const type of [WebGLRenderingContext, WebGL2RenderingContext]) {
      for (const name of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
        const original = type.prototype[name];
        if (!original) continue;
        type.prototype[name] = function(...args) {
          const frame = window.skylightFrame;
          window.skylightFrames[frame] = (window.skylightFrames[frame] ?? 0) + 1;
          return original.apply(this, args);
        };
      }
    }
  });
  // Vite gives the production GLB a content-hashed filename.
  const [response] = await Promise.all([
    page.waitForResponse(response => new URL(response.url()).pathname.endsWith('.glb')),
    page.goto(server.url + '?model=skylight-roof-module')
  ]);
  assert.equal(response.status(), 200);
  const hash = createHash('sha256').update(await response.body()).digest('hex');
  assert.equal(hash, measured.sha256, 'browser loaded the measured GLB');
  await page.waitForFunction(() => document.querySelector('#viewport canvas') &&
    document.querySelector('#viewer-status')?.textContent === '' &&
    Object.values(window.skylightFrames).some(n => n > 0), null, {timeout: 60000});
  assert.match(await page.locator('#viewer-title').innerText(), /Skylight Roof Module/);
  // Exclude the one-time studio environment map bake from model draw counts.
  await page.evaluate(() => { window.skylightFrames = {}; });
  await page.locator('#viewport canvas').press('ArrowLeft');
  await page.waitForFunction(() => Object.values(window.skylightFrames).some(n => n > 0));
  const screenshot = path.join(reportDirectory, 'skylight-roof-module-page.png');
  await page.screenshot({path: screenshot});
  const observed = await page.evaluate(() => {
    const canvas = document.querySelector('#viewport canvas');
    const gl = canvas.getContext('webgl2');
    const extension = gl?.getExtension('WEBGL_debug_renderer_info');
    return {
      max_draw_calls_per_frame: Math.max(...Object.values(window.skylightFrames)),
      canvas: [canvas.width, canvas.height],
      horizontal_overflow: document.documentElement.scrollWidth > innerWidth,
      renderer: extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : 'unavailable'
    };
  });
  assert.ok(observed.max_draw_calls_per_frame > 0 && observed.max_draw_calls_per_frame <= 6);
  assert.equal(observed.horizontal_overflow, false);
  assert.deepEqual(errors, []);
  const report = {result: 'PASS', viewport: [1440, 900], browser: browser.version(), loaded_sha256: hash,
    screenshot, ...observed, errors, scope: 'Single model in headless Chromium; complete mall and physical devices not tested.'};
  await fs.writeFile(new URL('reports/browser.json', dir), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
  await server.close();
}
