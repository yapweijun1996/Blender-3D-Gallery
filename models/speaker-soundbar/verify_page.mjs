import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const dir = fileURLToPath(new URL('.', import.meta.url));
const reportDir = path.join(os.homedir(), 'Documents/MallQueue/reports');
fs.mkdirSync(reportDir, { recursive: true });
const sha = data => createHash('sha256').update(data).digest('hex');
const expectedHash = sha(fs.readFileSync(dir + 'exports/optimized.glb'));
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', error => errors.push(String(error)));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  const responsePromise = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('.glb'));
  await page.goto(server.url + '?model=speaker-soundbar', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => document.querySelector('#viewer-title')?.textContent === 'Speaker and Soundbar'
    && document.querySelector('#viewer-poster')?.hidden
    && document.querySelector('#reset-view')?.disabled === false, null, { timeout: 60000 });
  const response = await responsePromise;
  assert.equal(response.status(), 200);
  assert.equal(sha(await response.body()), expectedHash, 'browser loaded the tested GLB');
  const canvas = page.locator('#viewport canvas');
  assert.equal(await canvas.count(), 1);
  const box = await canvas.boundingBox();
  assert.ok(box?.width > 200 && box?.height > 200);
  await page.mouse.move(box.x + box.width * .5, box.y + box.height * .5);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * .5 + 90, box.y + box.height * .5 + 30, { steps: 8 });
  await page.mouse.up();
  await page.locator('#reset-view').click();
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const screenshot = path.join(reportDir, 'speaker-soundbar-page.png');
  await page.screenshot({ path: screenshot, animations: 'disabled' });
  assert.deepEqual(errors, []);
  const report = {
    result: 'PASS', browser: 'headless Chromium', browser_version: browser.version(),
    viewport: { width: 1440, height: 900 }, screenshot, glb_sha256: expectedHash,
    glb_response: response.status(), canvas_count: 1, canvas_size: [box.width, box.height],
    flow: 'Open model URL, load actual GLB, orbit, reset, capture page', errors,
    scope: 'Local production build with software WebGL; no physical device or full mall performance claim',
  };
  fs.writeFileSync(dir + 'reports/browser.json', JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
  await server.close();
}
