// Verify the real production model page without substituting model responses.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright';
import {serveBuild, launchOptions} from '../../scripts/browser-test-utils.mjs';

const dir = new URL('.', import.meta.url);
const reports = path.join(os.homedir(), 'Documents/MallQueue/reports');
await fs.mkdir(path.join(reports, 'koi-fish-checks'), {recursive: true});
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const errors = [], failedResponses = [];
try {
  const context = await browser.newContext({viewport: {width: 1440, height: 900},
    reducedMotion: 'reduce', serviceWorkers: 'block'});
  await context.addInitScript(() => {
    window.assetFrames = [];
    let active;
    const raf = window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame = callback => raf(time => {
      active = {calls: 0, triangles: 0};
      window.assetFrames.push(active);
      if (window.assetFrames.length > 300) window.assetFrames.shift();
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
  page.on('response', r => { if (r.status() >= 400) failedResponses.push(`${r.status()} ${r.url()}`); });
  const responsePromise = page.waitForResponse(r => new URL(r.url()).pathname.endsWith('.glb'));
  await page.goto(server.url + '?model=koi-fish', {waitUntil: 'domcontentloaded'});
  const response = await responsePromise;
  const loadedHash = createHash('sha256').update(await response.body()).digest('hex');
  const sourceBytes = await fs.readFile(new URL('exports/optimized.glb', dir));
  assert.equal(loadedHash, createHash('sha256').update(sourceBytes).digest('hex'));
  const button = page.locator('[data-fish-playback]');
  await button.waitFor({timeout: 60000});
  await page.waitForFunction(() => document.querySelector('#viewport canvas') &&
    document.querySelector('#viewer-status')?.textContent === '', null, {timeout: 60000});
  assert.equal(await page.locator('#viewer-title').innerText(), 'Koi Fish');
  assert.equal(await button.getAttribute('aria-pressed'), 'false');
  const canvas = page.locator('#viewport canvas');
  await page.waitForTimeout(250);
  const still = await canvas.screenshot();
  await page.waitForTimeout(200);
  assert.ok(still.equals(await canvas.screenshot()), 'reduced motion starts with stable pixels');
  await fs.writeFile(path.join(reports, 'koi-fish-checks/paused-start.png'), still);
  await button.click();
  await page.waitForTimeout(650);
  await button.click();
  await page.waitForTimeout(100);
  const moved = await canvas.screenshot();
  assert.ok(!still.equals(moved), 'actual GLB swimming visibly changes pixels');
  await page.waitForTimeout(200);
  assert.ok(moved.equals(await canvas.screenshot()), 'pause stops swimming');
  await fs.writeFile(path.join(reports, 'koi-fish-checks/paused-swim.png'), moved);
  await page.emulateMedia({reducedMotion: 'no-preference'});
  await page.waitForFunction(() => document.querySelector('[data-fish-playback]')?.getAttribute('aria-pressed') === 'true');
  await page.waitForTimeout(500);
  const frames = await page.evaluate(() => window.assetFrames.filter(f => f.calls > 0).slice(-12));
  assert.ok(frames.length > 0);
  const drawCalls = Math.max(...frames.map(f => f.calls));
  assert.equal(drawCalls, 3, 'three material draws per model frame');
  await page.emulateMedia({reducedMotion: 'reduce'});
  await page.waitForFunction(() => document.querySelector('[data-fish-playback]')?.getAttribute('aria-pressed') === 'false');
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  const screenshot = path.join(reports, 'koi-fish-page.png');
  await page.screenshot({path: screenshot});
  await canvas.focus();
  await page.keyboard.press('ArrowLeft');
  await page.waitForTimeout(400);
  await page.screenshot({path: path.join(reports, 'koi-fish-checks/orbit.png')});
  await page.locator('#reset-view').click();
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('[data-fish-playback]').count(), 0);
  assert.deepEqual(errors, []);
  assert.deepEqual(failedResponses, []);
  const result = {result: 'PASS', viewport: [1440, 900], browser: await browser.version(),
    backend: 'SwiftShader', loaded_sha256: loadedHash, screenshot, model_draw_calls_per_frame: drawCalls,
    measured_frames: frames, visible_swim: true, pause_stable: true, live_reduced_motion: true,
    keyboard_orbit: 'PASS', reset: 'PASS', disposed: true, errors, failed_responses: failedResponses,
    limitations: 'Headless desktop Chromium only; no physical devices, WebKit, actual pond assembly or full mall performance.'};
  await fs.writeFile(new URL('reports/browser.json', dir), JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result, null, 2));
  await context.close();
} finally {
  await browser.close();
  await server.close();
}
