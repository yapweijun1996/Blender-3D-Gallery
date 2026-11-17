import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const dir = new URL('.', import.meta.url);
const spec = JSON.parse(await fs.readFile(new URL('backlog.json', dir), 'utf8'));
const assets = JSON.parse(await fs.readFile(new URL('reports/assets.json', dir), 'utf8'));
const reportDir = path.join(os.homedir(), 'Documents/MallQueue/reports');
await fs.mkdir(reportDir, { recursive: true });
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const errors = [], requests = [], hashes = [];
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, serviceWorkers: 'block' });
  await context.addInitScript(() => {
    window.assetQA = { frame: { calls: 0, triangles: 0 }, frames: [] };
    const proto = WebGL2RenderingContext.prototype;
    const clear = proto.clear, draw = proto.drawElements;
    proto.clear = function (...args) {
      if (window.assetQA.frame.calls) window.assetQA.frames.push(window.assetQA.frame);
      window.assetQA.frame = { calls: 0, triangles: 0 };
      return clear.apply(this, args);
    };
    proto.drawElements = function (mode, count, ...args) {
      window.assetQA.frame.calls++;
      if (mode === this.TRIANGLES) window.assetQA.frame.triangles += count/3;
      return draw.call(this, mode, count, ...args);
    };
  });
  const page = await context.newPage();
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('response', response => {
    if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);
    // Vite emits hashed GLB URLs; collect every actual GLB response and require
    // each consumed body to match this model's measured canonical hash.
    if (new URL(response.url()).pathname.endsWith('.glb')) {
      requests.push(response.body().then(bytes => hashes.push(createHash('sha256').update(bytes).digest('hex'))));
    }
  });
  const ready = async () => {
    await page.waitForFunction(() => document.querySelector('#viewport canvas') &&
      document.querySelector('#viewer-status')?.textContent === '' && window.assetQA.frame.calls >= 3,
    null, { timeout: 60000 });
    await page.waitForTimeout(400);
  };
  await page.goto(server.url+`?model=${spec.slug}`, { waitUntil: 'domcontentloaded' });
  await ready();
  assert.equal(await page.locator('#viewer-title').textContent(), spec.title);
  assert.equal(await page.locator('#viewport canvas').count(), 1);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  const initial = await page.locator('#viewport canvas').screenshot();
  const screenshot = path.join(reportDir, spec.slug+'-page.png');
  await page.screenshot({ path: screenshot });
  await page.locator('#viewport canvas').focus();
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('+');
  await page.waitForTimeout(300);
  const orbit = await page.locator('#viewport canvas').screenshot();
  assert.ok(!initial.equals(orbit), 'real keyboard orbit and zoom change rendered pixels');
  await page.locator('#reset-view').click();
  await page.waitForTimeout(300);
  const reset = await page.locator('#viewport canvas').screenshot();
  assert.ok(initial.equals(reset), 'reset restores original rendered view');
  // Exercise the real viewer controls to inspect all twelve flames at a
  // larger scale without replacing the default-page evidence above.
  const canvas = page.locator('#viewport canvas');
  const box = await canvas.boundingBox();
  await canvas.focus();
  await page.keyboard.press('ArrowLeft');
  await page.keyboard.press('ArrowLeft');
  await page.keyboard.press('ArrowUp');
  await page.mouse.move(box.x+box.width/2, box.y+box.height/2);
  await page.mouse.down({ button: 'right' });
  await page.mouse.move(box.x+box.width/2, box.y+box.height/2-80, { steps: 12 });
  await page.mouse.up({ button: 'right' });
  await page.waitForTimeout(1000);
  for (let i = 0; i < 7; i++) await page.keyboard.press('+');
  await page.waitForTimeout(500);
  const closeup = path.join(reportDir, spec.slug+'-lamps-closeup.png');
  await canvas.screenshot({ path: closeup });
  const graphics = await page.evaluate(() => {
    const gl = document.querySelector('#viewport canvas').getContext('webgl2');
    // Browser screenshots provide the visible evidence; this records the actual
    // graphics backend and draw calls without making an FPS claim.
    return { frames: [...window.assetQA.frames, window.assetQA.frame],
      version: gl.getParameter(gl.VERSION), renderer: gl.getParameter(gl.RENDERER) };
  });
  assert.ok(graphics.frames.some(f => f.calls === 3 && f.triangles === assets.triangles), 'actual three-call model frame');
  await page.locator('#close-viewer').click();
  assert.equal(await page.locator('#viewport canvas').count(), 0);
  await page.goto(server.url+`?model=${spec.slug}`, { waitUntil: 'domcontentloaded' });
  await ready();
  await Promise.all(requests);
  assert.ok(hashes.length >= 2 && hashes.every(hash => hash === assets.sha256), 'consumed GLB matches measured bytes');
  assert.deepEqual(errors, []);
  const report = { result: 'PASS', viewport: [1440, 900], browser: await browser.version(),
    id: spec.slug, consumed_glb_sha256: hashes, screenshot, lamps_closeup: closeup,
    checks: ['direct model page', 'visible WebGL geometry', 'keyboard orbit and zoom', 'pixel-identical reset',
      'twelve-flame closeup using orbit/pan/zoom', 'close disposes canvas', 'reopen',
      'no console/page/HTTP errors', 'no horizontal overflow'],
    measured_draw_calls: 3, measured_triangles_per_model_frame: assets.triangles,
    graphics: { version: graphics.version, renderer: graphics.renderer },
    limits: 'Desktop headless Chromium only; no physical devices, WebKit, full-mall scene or FPS verification.' };
  await fs.writeFile(new URL('reports/browser.json', dir), JSON.stringify(report, null, 2)+'\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
  await server.close();
}
