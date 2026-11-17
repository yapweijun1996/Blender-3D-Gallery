import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const dir = new URL('.', import.meta.url);
const measured = JSON.parse(await fs.readFile(new URL('reports/assets.json', dir), 'utf8'));
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const errors = [], failedRequests = [], viewports = [], sheets = [];
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, serviceWorkers: 'block' });
await context.addInitScript(() => {
  window.pianoQA = { totalDraws: 0, frameDraws: 0, frameTriangles: 0 };
  for (const prototype of [WebGLRenderingContext.prototype, WebGL2RenderingContext.prototype]) {
    const clear = prototype.clear;
    prototype.clear = function (...args) {
      window.pianoQA.frameDraws = 0;
      window.pianoQA.frameTriangles = 0;
      return clear.apply(this, args);
    };
    for (const name of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
      const draw = prototype[name];
      if (!draw) continue;
      prototype[name] = function (...args) {
        window.pianoQA.totalDraws++;
        window.pianoQA.frameDraws++;
        if (args[0] === this.TRIANGLES) {
          const count = name.startsWith('drawElements') ? args[1] : args[2];
          const instances = name.endsWith('Instanced') ? args.at(-1) : 1;
          window.pianoQA.frameTriangles += count / 3 * instances;
        }
        return draw.apply(this, args);
      };
    }
  }
});
const page = await context.newPage();
function observe(page) {
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('requestfailed', request => failedRequests.push(request.failure()?.errorText + ' ' + request.url()));
}
observe(page);
let glbURL;
try {
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 1440 ? 900 : 844 });
    const responsePromise = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('.glb'));
    await page.goto(server.url + '?model=grand-piano', { waitUntil: 'domcontentloaded' });
    const response = await responsePromise;
    assert.equal(response.status(), 200);
    glbURL = response.url();
    const loaded = await response.body();
    assert.equal(createHash('sha256').update(loaded).digest('hex'), measured.sha256, 'gallery received the validated GLB');
    await page.waitForFunction(() => document.querySelector('#viewer')?.open &&
      document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent === '' &&
      window.pianoQA.frameDraws === 4, null, { timeout: 60000 });
    const canvas = page.locator('#viewport canvas');
    await canvas.focus();
    const before = await page.evaluate(() => ({ ...window.pianoQA }));
    assert.equal(before.frameTriangles, measured.variants.lid_open.triangles);
    const output = width === 1440 ? path.join(os.homedir(), 'Documents/MallQueue/reports/grand-piano-page.png') :
      new URL('reports/gallery-390.png', dir).pathname;
    await fs.mkdir(path.dirname(output), { recursive: true });
    await page.screenshot({ path: output });
    const initialPixels = await canvas.screenshot();
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('+');
    await page.waitForFunction(draws => window.pianoQA.totalDraws > draws, before.totalDraws);
    assert.notDeepEqual(initialPixels, await canvas.screenshot(), 'orbit/zoom visibly changes the real rendered model');
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    const after = await page.evaluate(() => ({ ...window.pianoQA }));
    assert.equal(after.frameDraws, 4);
    assert.equal(after.frameTriangles, measured.variants.lid_open.triangles);
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => !document.querySelector('#viewer').open && !document.querySelector('#viewport canvas'));
    viewports.push({ width, height: width === 1440 ? 900 : 844, frame_draw_calls: after.frameDraws,
      frame_triangles: after.frameTriangles, orbit_zoom_pixel_change: true, close_disposes_canvas: true, screenshot: output });
  }
  await page.close();
  // Local Three.js modules support the opt-in scene harness; no network assets.
  const modulesRoot = path.resolve('node_modules/three');
  await context.route('**/__piano_qa__/**', async route => {
    const relative = new URL(route.request().url()).pathname.split('/__piano_qa__/')[1];
    const file = path.resolve(modulesRoot, relative);
    assert.ok(file.startsWith(modulesRoot + path.sep) && file.endsWith('.js'));
    await route.fulfill({ contentType: 'text/javascript', body: await fs.readFile(file) });
  });
  await context.route('**/piano-acceptance.html?*', async route => {
    await route.fulfill({ contentType: 'text/html', body: await fs.readFile(new URL('browser_fixture.html', dir)) });
  });
  for (const width of [1440, 390]) {
    const sheet = await context.newPage();
    observe(sheet);
    await sheet.setViewportSize({ width, height: width === 1440 ? 520 : 650 });
    await sheet.goto(server.url + 'piano-acceptance.html?glb=' + encodeURIComponent(glbURL));
    await sheet.waitForFunction(() => window.pianoVariantQA?.ready, null, { timeout: 60000 });
    const qa = await sheet.evaluate(() => ({ sha256: window.pianoVariantQA.sha256, records: window.pianoVariantQA.records }));
    assert.equal(qa.sha256, measured.sha256);
    for (const record of qa.records) {
      assert.equal(record.draw_calls, 4);
      assert.equal(record.visible_meshes, 4);
      assert.equal(record.triangles, measured.variants['lid_' + record.state].triangles);
      assert.equal(record.active_lid, 'lid_' + record.state);
      assert.equal(record.collider_visible, false);
      assert.ok(Math.abs(record.seat_world_m[1] - 0.55) < 1e-6);
    }
    assert.equal(await sheet.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    const output = new URL(`reports/contact-${width}.png`, dir).pathname;
    await sheet.screenshot({ path: output, fullPage: true });
    const canvas = sheet.locator('canvas').first();
    const before = await canvas.screenshot();
    const moved = await sheet.evaluate(() => window.pianoVariantQA.moveBench());
    assert.equal(moved.body_unchanged, true);
    assert.equal(moved.bench_x, 0.3);
    assert.notDeepEqual(before, await canvas.screenshot(), 'bench can move independently in the rendered GLB');
    sheets.push({ width, ...qa, bench_independent_move: true, screenshot: output });
    await sheet.close();
  }
  assert.deepEqual(errors, []);
  assert.deepEqual(failedRequests, []);
  const report = { result: 'PASS', browser: browser.version(), renderer: 'headless Chromium / SwiftShader',
    loaded_glb_sha256: measured.sha256, viewports, contact_sheets: sheets,
    console_page_errors: errors, failed_requests: failedRequests,
    unverified: ['physical mobile devices', 'full S15 mall assembly and seating gameplay', 'sound and playable keys', 'GPU performance on target hardware'] };
  await fs.writeFile(new URL('reports/browser.json', dir), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  await context.close();
  await browser.close();
  await server.close();
}
