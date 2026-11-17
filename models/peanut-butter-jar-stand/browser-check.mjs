import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import os from 'node:os';
import path from 'node:path';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const dir = fileURLToPath(new URL('.', import.meta.url));
const slug = 'peanut-butter-jar-stand';
const reports = path.join(os.homedir(), 'Documents/MallQueue/reports');
await fs.mkdir(reports, {recursive:true});
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const context = await browser.newContext({viewport:{width:1440,height:900}, serviceWorkers:'block'});
await context.addInitScript(() => {
  window.qaDrawCalls = 0;
  for (const type of [WebGLRenderingContext, WebGL2RenderingContext]) {
    for (const name of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
      const original = type.prototype[name];
      if (original) type.prototype[name] = function(...args) { window.qaDrawCalls++; return original.apply(this, args); };
    }
  }
});
const page = await context.newPage();
const errors = [];
page.on('pageerror', e => errors.push(e.message));
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
page.on('response', r => { if (r.status() >= 400) errors.push(`${r.status()} ${new URL(r.url()).pathname}`); });
try {
  const responsePromise = page.waitForResponse(r => new URL(r.url()).pathname.endsWith('.glb'));
  await page.goto(server.url + '?model=' + slug, {waitUntil:'domcontentloaded'});
  const response = await responsePromise;
  assert.equal(response.status(), 200);
  const hash = createHash('sha256').update(await response.body()).digest('hex');
  const metrics = JSON.parse(await fs.readFile(dir + 'reports/assets.json', 'utf8'));
  assert.equal(hash, metrics.sha256);
  await page.waitForFunction(() => document.querySelector('#viewer')?.open && document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent === '' && window.qaDrawCalls > 0, null, {timeout:60000});
  assert.equal(await page.locator('#viewer-title').innerText(), 'Peanut-Butter Jar Display Stand');
  const canvas = page.locator('#viewport canvas');
  const box = await canvas.boundingBox();
  assert.ok(box.width > 300 && box.height > 300);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  // Let the existing fit-camera transition reach its displayed resting state.
  await page.waitForTimeout(1800);
  const screenshot = path.join(reports, slug + '-page.png');
  await page.screenshot({path:screenshot});
  const draws = await page.evaluate(() => window.qaDrawCalls);
  await page.mouse.move(box.x + box.width * .5, box.y + box.height * .5);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * .65, box.y + box.height * .46, {steps:8});
  await page.mouse.up();
  await page.waitForFunction(n => window.qaDrawCalls > n, draws);
  await page.locator('#reset-view').click();
  await page.waitForTimeout(1000);
  await page.locator('#close-viewer').click();
  assert.equal(await page.locator('#viewport canvas').count(), 0);
  await page.goto(server.url + '?model=' + slug, {waitUntil:'domcontentloaded'});
  await page.waitForFunction(() => document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent === '', null, {timeout:60000});
  assert.deepEqual(errors, []);
  const report = {result:'PASS', viewport:[1440,900], engine:'headless Chromium / SwiftShader', actual_glb_sha256:hash, http_status:response.status(), canvas_size:{width:box.width,height:box.height}, draw_calls_observed:draws, orbit_reset_close_reopen:'PASS', errors, screenshot, limitation:'Single-model software WebGL smoke test; no complete-mall performance or physical-device result.'};
  await fs.writeFile(dir + 'reports/browser.json', JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report));
} finally {
  await browser.close();
  await server.close();
}
