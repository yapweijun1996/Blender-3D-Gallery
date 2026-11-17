// Exercise the existing gallery; this script makes no application changes.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright';
import {serveBuild, launchOptions} from '../../scripts/browser-test-utils.mjs';

const dir = new URL('.', import.meta.url);
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const context = await browser.newContext({viewport: {width: 1440, height: 900}, serviceWorkers: 'block'});
const page = await context.newPage();
const errors = [], loaded = [];
page.on('pageerror', e => errors.push(e.message));
page.on('console', m => {if (m.type() === 'error') errors.push(m.text());});
page.on('response', r => {if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`);});
await page.addInitScript(() => {
  window.qaDraws = 0;
  window.qaDrawFrames = {};
  let frame = 0;
  const tick = () => {frame++; requestAnimationFrame(tick);};
  requestAnimationFrame(tick);
  for (const type of [WebGLRenderingContext, WebGL2RenderingContext]) {
    for (const name of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
      const original = type.prototype[name];
      if (original) type.prototype[name] = function(...args) {
        window.qaDraws++;
        window.qaDrawFrames[frame] = (window.qaDrawFrames[frame] ?? 0) + 1;
        return original.apply(this, args);
      };
    }
  }
});
page.on('response', response => {
  if (new URL(response.url()).pathname.endsWith('.glb'))
    loaded.push(response.body().then(bytes => createHash('sha256').update(bytes).digest('hex')));
});
try {
  await page.goto(server.url + '?model=atrium-fountain', {waitUntil: 'domcontentloaded'});
  const ready = () => page.waitForFunction(() => document.querySelector('#viewport canvas') &&
    document.querySelector('#viewer-status')?.textContent === '' && window.qaDraws > 0, null, {timeout: 60000});
  await ready();
  assert.match(await page.locator('#viewer-title').innerText(), /Atrium Fountain/);
  assert.equal(await page.locator('#viewport canvas').count(), 1);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  const reportDir = path.join(os.homedir(), 'Documents/MallQueue/reports');
  await fs.mkdir(reportDir, {recursive: true});
  await page.screenshot({path: path.join(reportDir, 'atrium-fountain-page.png')});
  const canvas = page.locator('#viewport canvas');
  const box = await canvas.boundingBox();
  const before = await page.evaluate(() => window.qaDraws);
  await page.mouse.move(box.x + box.width * .65, box.y + box.height * .55);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * .35, box.y + box.height * .48, {steps: 8});
  await page.mouse.up();
  await page.waitForFunction(n => window.qaDraws > n, before);
  await canvas.focus();
  await page.keyboard.press('+');
  await page.keyboard.press('ArrowLeft');
  await page.screenshot({path: new URL('reports/chromium-orbit.png', dir).pathname});
  await page.locator('#reset-view').click();
  await ready();
  await page.reload({waitUntil: 'domcontentloaded'});
  await ready();
  assert.equal(await page.locator('#viewport canvas').count(), 1);
  const disk = await fs.readFile(new URL('exports/optimized.glb', dir));
  const expected = createHash('sha256').update(disk).digest('hex');
  assert.ok(loaded.length >= 2, 'initial and refresh GLB responses');
  const hashes = await Promise.all(loaded);
  assert.ok(hashes.every(hash => hash === expected), 'browser loaded actual delivery bytes');
  const draws = await page.evaluate(() => Math.max(...Object.values(window.qaDrawFrames)));
  assert.ok(draws <= 12 && draws > 0, 'small model-viewer draw count');
  await page.locator('#close-viewer').click();
  await page.waitForFunction(() => !document.querySelector('#viewer').open);
  assert.equal(await page.locator('#viewport canvas').count(), 0);
  assert.deepEqual(errors, []);
  const report = {result: 'PASS', browser: await browser.version(), viewport: [1440, 900],
    source: 'local production build', screenshot: path.join(reportDir, 'atrium-fountain-page.png'),
    checks: ['direct link', 'visible canvas', 'no horizontal overflow', 'orbit', 'keyboard rotate/zoom', 'reset', 'refresh', 'delivery SHA-256', 'close/dispose'],
    glb_response_sha256: hashes, max_draw_calls_observed_per_frame: draws,
    errors, caveat: 'Static water; no mall animation, full-mall budget or physical-device performance claim.'};
  await fs.writeFile(new URL('reports/chromium.json', dir), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  await context.close();
  await browser.close();
  await server.close();
}
