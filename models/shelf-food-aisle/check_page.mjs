// Exercise the production model page using the repository's server and browser.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const dir = fileURLToPath(new URL('.', import.meta.url));
const output = path.join(os.homedir(), 'Documents/MallQueue/reports');
await fs.mkdir(output, { recursive: true });
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const errors = [], failures = [], loaded = [];
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, serviceWorkers: 'block' });
  await context.addInitScript(() => {
    window.qaDraws = 0;
    window.qaTriangles = 0;
    window.qaFrames = [];
    for (const type of [WebGLRenderingContext, WebGL2RenderingContext]) {
      for (const name of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
        const original = type.prototype[name];
        if (!original) continue;
        type.prototype[name] = function (...args) {
          window.qaDraws++;
          if (args[0] === this.TRIANGLES) {
            const count = name.startsWith('drawArrays') ? args[2] : args[1];
            const instances = name.endsWith('Instanced') ? args.at(-1) : 1;
            window.qaTriangles += count / 3 * instances;
          }
          return original.apply(this, args);
        };
      }
    }
    const raf = window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame = callback => raf(time => {
      const before = window.qaDraws, triangles = window.qaTriangles;
      callback(time);
      if (window.qaDraws > before) window.qaFrames.push({ calls: window.qaDraws - before, triangles: window.qaTriangles - triangles });
    });
  });
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('response', response => {
    if (response.status() >= 400) failures.push(`${response.status()} ${response.url()}`);
    if (new URL(response.url()).pathname.endsWith('.glb')) {
      loaded.push(response.body().then(body => ({ status: response.status(), bytes: body.length, sha256: createHash('sha256').update(body).digest('hex') })));
    }
  });
  await page.goto(server.url + '?model=shelf-food-aisle', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => document.querySelector('#viewport canvas') &&
    document.querySelector('#viewer-status')?.textContent === '' && window.qaDraws > 0,
  null, { timeout: 60000 });
  const canvas = page.locator('#viewport canvas');
  await canvas.focus();
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('ArrowLeft');
  await page.waitForFunction(() => window.qaFrames.some(frame => frame.calls === 3 && frame.triangles === 16320));
  await page.locator('#reset-view').click();
  await page.screenshot({ path: path.join(output, 'shelf-food-aisle-page.png'), animations: 'disabled' });
  const rendered = await page.evaluate(() => ({
    canvas_count: document.querySelectorAll('#viewport canvas').length,
    viewer_status: document.querySelector('#viewer-status').textContent,
    frames: window.qaFrames.slice(-8),
    horizontal_overflow: document.documentElement.scrollWidth > innerWidth,
  }));
  const assets = JSON.parse(await fs.readFile(dir + 'reports/assets.json', 'utf8'));
  const responses = await Promise.all(loaded);
  assert.ok(responses.length > 0);
  assert.ok(responses.every(item => item.status === 200 && item.sha256 === assets.sha256));
  assert.equal(rendered.canvas_count, 1);
  assert.equal(rendered.horizontal_overflow, false);
  assert.deepEqual(errors, []);
  assert.deepEqual(failures, []);
  const report = {
    result: 'PASS', viewport: { width: 1440, height: 900 },
    browser: await browser.version(), headless: true,
    backend: 'SwiftShader, repository launchOptions',
    screenshot: path.join(output, 'shelf-food-aisle-page.png'),
    tested: ['production model deep link', 'actual matching GLB response', 'WebGL triangles and draw calls', 'keyboard orbit', 'reset'],
    responses, rendered, console_errors: errors, failed_responses: failures,
    not_verified: ['physical Android/iOS', 'WebKit', 'full assembled mall', 'sustained performance'],
  };
  await fs.writeFile(dir + 'reports/browser.json', JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
  await context.close();
} finally {
  await browser.close();
  await server.close();
}
