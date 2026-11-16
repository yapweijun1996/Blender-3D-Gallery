// Production build, real Chromium/WebGL, decoded GLB hash and viewer controls.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const here = fileURLToPath(new URL('.', import.meta.url));
const expectedBytes = await fs.readFile(here + 'exports/optimized.glb');
const sha256 = buffer => createHash('sha256').update(buffer).digest('hex');
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, serviceWorkers: 'block', reducedMotion: 'reduce' });
  const errors = [], pending = [];
  let loadedHash;
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('response', response => {
    if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);
    if (new URL(response.url()).pathname.endsWith('.glb') && response.request().resourceType() === 'fetch') {
      pending.push(response.body().then(buffer => { loadedHash = sha256(buffer); }));
    }
  });
  await page.addInitScript(() => {
    window.assetDraws = [];
    window.assetFrame = 0;
    const raf = window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame = callback => raf(time => { window.assetFrame = time; callback(time); });
    for (const Type of [WebGLRenderingContext, WebGL2RenderingContext]) {
      for (const method of ['drawElements', 'drawArrays']) {
        const original = Type.prototype[method];
        Type.prototype[method] = function (...args) {
          window.assetDraws.push({ frame: window.assetFrame, count: method === 'drawElements' ? args[1] : args[2], mode: args[0] });
          return original.apply(this, args);
        };
      }
    }
  });
  await page.goto(`${server.url}?model=stacked-can-pyramid`, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => document.querySelector('#viewport canvas') &&
    document.querySelector('#viewer-status')?.textContent === '' && window.assetDraws.length > 0, null, { timeout: 60000 });
  await Promise.all(pending);
  assert.equal(loadedHash, sha256(expectedBytes));
  const screenshot = `${process.env.HOME}/Documents/MallQueue/reports/stacked-can-pyramid-page.png`;
  await page.screenshot({ path: screenshot });
  const canvas = page.locator('#viewport canvas');
  const resting = await canvas.screenshot();
  // Exclude one-time environment-map preparation; measure viewer frames below.
  await page.evaluate(() => { window.assetDraws = []; });
  await canvas.focus();
  const initial = await canvas.screenshot();
  await page.keyboard.press('ArrowLeft');
  await page.waitForTimeout(300);
  const rotated = await canvas.screenshot();
  assert.ok(!initial.equals(rotated), 'keyboard rotation changes visible model');
  await page.keyboard.press('+');
  await page.waitForTimeout(300);
  assert.ok(!rotated.equals(await canvas.screenshot()), 'zoom changes visible model');
  await page.getByRole('button', { name: /Reset view/ }).click();
  await page.waitForTimeout(300);
  assert.ok(resting.equals(await canvas.screenshot()), 'reset restores the original model view');
  const metrics = await page.evaluate(() => {
    const frames = new Map();
    for (const draw of window.assetDraws) {
      const frame = frames.get(draw.frame) ?? { calls: 0, triangles: 0 };
      frame.calls++;
      if (draw.mode === 4) frame.triangles += draw.count / 3;
      frames.set(draw.frame, frame);
    }
    const canvas = document.querySelector('#viewport canvas');
    const gl = canvas.getContext('webgl2');
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    return {
      observed_frames: frames.size,
      max_draw_calls_per_frame: Math.max(...[...frames.values()].map(f => f.calls)),
      max_triangles_per_frame: Math.max(...[...frames.values()].map(f => f.triangles)),
      renderer: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : 'unavailable',
      context_lost: gl.isContextLost(), overflow: document.documentElement.scrollWidth > innerWidth,
    };
  });
  assert.equal(metrics.context_lost, false);
  assert.equal(metrics.overflow, false);
  assert.equal(errors.length, 0, errors.join('\n'));
  assert.ok(metrics.max_draw_calls_per_frame <= 6, 'model uses three primitives; viewer may add passes');
  const report = {
    result: 'PASS', viewport: [1440, 900], screenshot, loaded_sha256: loadedHash,
    expected_sha256: sha256(expectedBytes), controls: 'rotation and zoom change pixels; reset restores exact pixels',
    browser_version: browser.version(), errors, ...metrics,
    scope: 'Local production build on desktop Chromium only; full mall and physical devices unverified',
  };
  await fs.writeFile(here + 'reports/browser.json', JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
  await server.close();
}
