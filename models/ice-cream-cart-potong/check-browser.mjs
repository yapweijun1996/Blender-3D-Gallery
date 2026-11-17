// Production-gallery acceptance; screenshots/contact sheets do not modify gallery UI.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright';
import {serveBuild, launchOptions} from '../../scripts/browser-test-utils.mjs';

const dir = fileURLToPath(new URL('.', import.meta.url));
const ownerReports = '/Users/admin/Documents/MallQueue/reports';
const id = 'ice-cream-cart-potong';
await fs.mkdir(ownerReports, {recursive: true});
const bytes = await fs.readFile(path.join(dir, 'exports/optimized.glb'));
const sha256 = createHash('sha256').update(bytes).digest('hex');
const browser = await chromium.launch(launchOptions);
const server = await serveBuild();
const results = [];
try {
  for (const [width, height] of [[1440, 900], [390, 844]]) {
    const context = await browser.newContext({viewport: {width, height}, reducedMotion: 'reduce', serviceWorkers: 'block'});
    const page = await context.newPage();
    const errors = [];
    const result = {width, height, runtime: 'Desktop headless Chromium; viewport emulation', passed: false, errors};
    try {
      await page.addInitScript(() => {
        window.cartQA = {consumed: [], frameCalls: 0, totalCalls: 0};
        const native = Response.prototype.arrayBuffer;
        Response.prototype.arrayBuffer = async function (...args) {
          const b = await native.apply(this, args);
          if (b.byteLength >= 4 && new DataView(b).getUint32(0, true) === 0x46546c67) {
            const hash = await crypto.subtle.digest('SHA-256', b);
            window.cartQA.consumed.push({bytes: b.byteLength, sha256: [...new Uint8Array(hash)].map(n => n.toString(16).padStart(2, '0')).join('')});
          }
          return b;
        };
        for (const type of [window.WebGLRenderingContext, window.WebGL2RenderingContext]) {
          if (!type) continue;
          const clear = type.prototype.clear;
          type.prototype.clear = function (...args) {window.cartQA.frameCalls = 0; return clear.apply(this, args);};
          for (const key of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
            const draw = type.prototype[key];
            if (draw) type.prototype[key] = function (...args) {
              window.cartQA.frameCalls++;
              window.cartQA.totalCalls++;
              return draw.apply(this, args);
            };
          }
        }
      });
      page.on('console', m => {if (m.type() === 'error') errors.push(m.text());});
      page.on('pageerror', e => errors.push(e.message));
      page.on('requestfailed', r => errors.push(r.url() + ': ' + r.failure()?.errorText));
      page.on('response', r => {if (r.status() >= 400) errors.push(r.status() + ' ' + r.url());});
      await page.goto(server.url + '?model=' + id, {waitUntil: 'domcontentloaded'});
      await page.waitForFunction(() => document.querySelector('#viewer')?.open &&
        document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent === '' &&
        window.cartQA?.frameCalls > 0, null, {timeout: 60000});
      assert.equal(await page.locator('#viewer-title').innerText(), 'Potong Ice-Cream Cart');
      const canvas = page.locator('#viewport canvas');
      const screenshot = async (name, destination) => {
        await canvas.evaluate(el => el.blur());
        await page.waitForTimeout(500);
        const buffer = await canvas.screenshot({path: destination ?? path.join(dir, 'reports', `${name}-${width}.png`)});
        return createHash('sha256').update(buffer).digest('hex');
      };
      const initial = await screenshot('viewer');
      result.draw_calls_per_render = await page.evaluate(() => window.cartQA.frameCalls);
      assert.equal(result.draw_calls_per_render, 6, 'actual default-scene instance draw budget');
      await canvas.press('ArrowRight');
      const orbit = await screenshot('orbit');
      assert.notEqual(orbit, initial, 'orbit changes real pixels');
      await canvas.press('PageUp');
      const zoom = await screenshot('zoom');
      assert.notEqual(zoom, orbit, 'zoom changes real pixels');
      await page.locator('#reset-view').click();
      const reset = await screenshot('reset');
      assert.equal(reset, initial, 'reset restores the initial view');
      await page.screenshot({path: path.join(ownerReports, width === 1440 ? `${id}-page.png` : `${id}-${width}-page.png`)});
      result.horizontal_overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
      assert.equal(result.horizontal_overflow, false);
      result.consumed = await page.evaluate(() => window.cartQA.consumed);
      assert.ok(result.consumed.some(a => a.sha256 === sha256 && a.bytes === bytes.length), 'actual loaded GLB identity');
      await page.locator('#close-viewer').click();
      assert.equal(await canvas.count(), 0, 'close removes canvas');
      const stopped = await page.evaluate(() => window.cartQA.totalCalls);
      await page.waitForTimeout(300);
      assert.equal(await page.evaluate(() => window.cartQA.totalCalls), stopped);
      await page.locator(`#catalog [data-asset-id="${id}"]`).first().click();
      await page.waitForFunction(() => document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent === '');
      const reopened = await screenshot('reopened');
      assert.equal(reopened, initial, 'reopen restores the same asset and view');
      assert.deepEqual(errors, []);
      result.pixel_hashes = {initial, orbit, zoom, reset, reopened};
      result.passed = true;
      console.log('PASS production gallery', width, 'draw calls', result.draw_calls_per_render);
    } catch (error) {
      result.failure = error.message;
      await page.screenshot({path: path.join(dir, 'reports', `browser-failure-${width}.png`)}).catch(() => {});
      console.error('FAIL production gallery', width, error.message);
    } finally {
      results.push(result);
      await context.close();
    }
  }

  // Render-review artifact only: original Blender views plus the actual viewer canvas.
  const images = [];
  for (const [label, file] of [['Hero', 'previews/hero.png'], ['Front', 'previews/front.png'],
    ['Side', 'previews/side.png'], ['Three quarter', 'previews/3q.png'],
    ['Gallery 1440', 'reports/viewer-1440.png'], ['Gallery 390', 'reports/viewer-390.png']]) {
    images.push({label, src: 'data:image/png;base64,' + (await fs.readFile(path.join(dir, file))).toString('base64')});
  }
  for (const width of [1440, 390]) {
    const page = await browser.newPage({viewport: {width, height: 1000}});
    await page.setContent(`<html lang="en"><style>*{box-sizing:border-box}body{margin:0;padding:20px;background:#eee7d9;color:#34433d;font:16px system-ui}h1{font-size:24px;margin:0 0 4px}p{margin:0 0 16px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}figure{margin:0;background:#fffaf1;border-radius:12px;overflow:hidden}img{width:100%;aspect-ratio:1;object-fit:contain;background:#566066;display:block}figcaption{padding:8px 12px;font-weight:600}@media(max-width:600px){body{padding:12px}h1{font-size:20px}.grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}figcaption{font-size:12px;padding:7px}}</style><h1>Potong Ice-Cream Cart</h1><p>Original procedural asset · P1 · S03</p><main class="grid">${images.map(i => `<figure><img alt="${i.label}" src="${i.src}"><figcaption>${i.label}</figcaption></figure>`).join('')}</main></html>`);
    await page.evaluate(() => Promise.all([...document.images].map(i => i.decode())));
    await page.screenshot({path: path.join(dir, 'previews', `contact-${width}.png`), fullPage: true});
    await page.close();
  }
} finally {
  const report = {browser: browser.version(), sha256, source_glb_bytes: bytes.length,
    physical_android: 'NOT TESTED', physical_ios: 'NOT TESTED', webkit: 'NOT TESTED', results};
  await fs.writeFile(path.join(dir, 'reports/browser.json'), JSON.stringify(report, null, 2) + '\n');
  await browser.close();
  await server.close();
}
if (results.length !== 2 || results.some(r => !r.passed)) process.exitCode = 1;
