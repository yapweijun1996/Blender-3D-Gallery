import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';
import { launchOptions, serveBuild } from './browser-test-utils.mjs';

const collectionId = 'mall-architectural-lighting';
const catalog = JSON.parse(await fs.readFile('models/catalog.json', 'utf8'));
const assets = catalog.collections.find(collection => collection.id === collectionId).assets;
const output = process.argv[2];
assert.ok(output, 'Pass an output directory for screenshots and results');
assert.equal(assets.length, 10);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const server = process.env.MODEL_QA_URL ? null : await serveBuild();
const url = new URL(process.env.MODEL_QA_URL ?? server.url);
url.searchParams.set('page', 'models');
url.searchParams.set('collection', collectionId);
const browser = await chromium.launch(launchOptions);

async function verifyViewport(width, height) {
  const directory = path.join(output, String(width));
  await fs.mkdir(directory, { recursive: true });
  const context = await browser.newContext({ viewport: { width, height }, hasTouch: width < 500,
    reducedMotion: 'reduce', serviceWorkers: 'block' });
  try {
    await context.addInitScript(() => {
      window.lightingDraws = 0;
      const draw = WebGL2RenderingContext.prototype.drawElements;
      WebGL2RenderingContext.prototype.drawElements = function (...args) {
        window.lightingDraws++;
        return draw.apply(this, args);
      };
    });
    const page = await context.newPage();
    const errors = [], requests = [], results = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    page.on('response', response => { if (response.status() >= 400) errors.push(response.url()); });
    const isModel = response => new URL(response.url()).pathname.endsWith('.glb');
    page.on('request', request => { if (isModel(request)) requests.push(request.url()); });
    await page.goto(url.href);
    await page.waitForFunction(() => document.querySelectorAll('#catalog .asset-card').length === 10);
    assert.equal(await page.locator('#model-collection').inputValue(), collectionId);
    assert.equal(requests.length, 0, 'The collection must use thumbnails before opening a viewer');
    for (const asset of assets) {
      const link = page.locator('#catalog .asset-image[data-asset-id="' + asset.id + '"]');
      await link.scrollIntoViewIfNeeded();
      const image = link.locator('img');
      const poster = await image.evaluate(async img => {
        await img.decode();
        return [img.naturalWidth, img.naturalHeight];
      });
      assert.deepEqual(poster, [480, 360]);
      const draws = await page.evaluate(() => window.lightingDraws);
      const [response] = await Promise.all([page.waitForResponse(isModel), link.click()]);
      const digest = hash(await response.body());
      assert.equal(digest, hash(await fs.readFile(asset.file)), 'Viewer must fetch expected ' + asset.id);
      await page.waitForFunction(start => document.querySelector('#viewer')?.open &&
        !document.querySelector('#reset-view')?.disabled && window.lightingDraws > start,
        draws, { timeout: 60000 });
      assert.equal(await page.locator('#viewer-title').innerText(), asset.name);
      const canvas = page.locator('#viewport canvas');
      const capture = async filename => {
        await canvas.evaluate(el => el.blur());
        await page.evaluate(() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done))));
        return hash(await canvas.screenshot(filename ? { path: filename } : {}));
      };
      const initial = await capture(path.join(directory, asset.id + '.png'));
      await canvas.press('ArrowLeft');
      assert.notEqual(await capture(), initial, 'Orbit did not change ' + asset.id);
      await page.locator('#reset-view').click();
      assert.equal(await capture(), initial, 'Orbit reset did not restore ' + asset.id);
      await canvas.press('+');
      assert.notEqual(await capture(), initial, 'Zoom did not change ' + asset.id);
      await page.locator('#reset-view').click();
      assert.equal(await capture(), initial, 'Zoom reset did not restore ' + asset.id);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.locator('#close-viewer').click();
      assert.equal(await canvas.count(), 0);
      results.push({ id: asset.id, viewport: [width, height], glbSha256: digest, poster,
        orbit: true, zoom: true, reset: true, closed: true });
      console.log('PASS', width, asset.id);
    }
    assert.deepEqual(errors, []);
    return results;
  } finally {
    await context.close();
  }
}

try {
  const results = await Promise.all([verifyViewport(1440, 900), verifyViewport(390, 844)]);
  await fs.writeFile(path.join(output, 'results.json'), JSON.stringify(results.flat(), null, 2) + '\n');
} finally {
  await browser.close();
  if (server) await server.close();
}
