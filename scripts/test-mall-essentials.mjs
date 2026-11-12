import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from './browser-test-utils.mjs';

// Run after npm run build. This verifies the actual production-build GLBs, not a mock viewer.
const ids = ['mall-directory-kiosk', 'mall-advertising-lightbox', 'mall-trash-bin', 'mall-display-shelf'];
const catalog = JSON.parse(await fs.readFile(new URL('../models/catalog.json', import.meta.url), 'utf8'));
const collection = catalog.collections.find(item => item.id === 'mall-essentials');
assert.ok(collection, 'the furniture collection must be registered');
assert.deepEqual(collection.assets.map(asset => asset.id), ids);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const sourceAssets = new Map();
for (const asset of collection.assets) {
  assert.equal(asset.downloadable, false, `${asset.id}: no public redistribution grant`);
  const bytes = await fs.readFile(asset.file);
  sourceAssets.set(asset.id, { ...asset, sha256: hash(bytes), bytes: bytes.length });
}

const artifacts = process.env.MALL_QA_DIR || '/tmp/blender-mall-essentials-qa';
await fs.mkdir(artifacts, { recursive: true });
const results = [];
const server = await serveBuild();
let browser;
let failure;
const viewports = [[1440, 900], [768, 1024], [390, 844]];

async function createPage(width, height) {
  const context = await browser.newContext({
    viewport: { width, height }, reducedMotion: 'reduce', serviceWorkers: 'block',
  });
  await context.addInitScript(() => {
    window.furnitureDraws = 0;
    window.mallConsumedGlbs = [];
    // Observe bytes actually returned to GLTFLoader. Chromium cannot always expose
    // streamed response bodies through Network.getResponseBody, even before reload.
    // The original buffer and all network/response behavior are preserved.
    const arrayBuffer = Response.prototype.arrayBuffer;
    Response.prototype.arrayBuffer = async function (...args) {
      const bytes = await arrayBuffer.apply(this, args);
      const header = new Uint8Array(bytes, 0, Math.min(12, bytes.byteLength));
      if (header.length >= 12 && header[0] === 103 && header[1] === 108 &&
          header[2] === 84 && header[3] === 70) {
        const digest = await crypto.subtle.digest('SHA-256', bytes);
        window.mallConsumedGlbs.push({
          sha256: [...new Uint8Array(digest)].map(v => v.toString(16).padStart(2, '0')).join(''),
          bytes: bytes.byteLength,
          version: new DataView(bytes).getUint32(4, true),
          declaredBytes: new DataView(bytes).getUint32(8, true),
        });
      }
      return bytes;
    };
    for (const Context of [window.WebGLRenderingContext, window.WebGL2RenderingContext]) {
      if (!Context) continue;
      for (const name of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
        const original = Context.prototype[name];
        if (typeof original !== 'function') continue;
        Context.prototype[name] = function (...args) {
          window.furnitureDraws++;
          return original.apply(this, args);
        };
      }
    }
  });
  const page = await context.newPage();
  const errors = [];
  const requests = [];
  const responses = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('request', request => {
    if (new URL(request.url()).pathname.endsWith('.glb')) requests.push(request.url());
  });
  page.on('requestfailed', request => errors.push(`${request.url()}: ${request.failure()?.errorText}`));
  page.on('response', response => {
    if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);
    if (new URL(response.url()).pathname.endsWith('.glb')) responses.push(response);
  });
  return { context, page, errors, requests, responses };
}

async function noOverflow(page) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
}

async function viewerReady(page, previousDraws = 0) {
  await page.waitForFunction(previous =>
    document.querySelector('#viewer')?.open &&
    document.querySelector('#viewport canvas') &&
    document.querySelector('#viewer-status')?.textContent === '' &&
    window.furnitureDraws > previous,
  previousDraws, { timeout: 60000 });
  assert.equal(await page.locator('#retry-view').isVisible(), false);
  assert.equal(await page.locator('#reset-view').isEnabled(), true);
}

async function settleDraws(page) {
  // OrbitControls damping is finite; require the on-demand viewer to become idle.
  for (let attempt = 0; attempt < 30; attempt++) {
    const before = await page.evaluate(() => window.furnitureDraws);
    await page.waitForTimeout(150);
    if (await page.evaluate(() => window.furnitureDraws) === before) return before;
  }
  throw new Error('The furniture viewer did not settle to an idle render state');
}

async function canvasCapture(page, filename) {
  const canvas = page.locator('#viewport canvas');
  await canvas.scrollIntoViewIfNeeded();
  await canvas.focus();
  await settleDraws(page);
  return hash(await canvas.screenshot({ path: path.join(artifacts, filename) }));
}

async function actualAssetResponses(responses, asset, page) {
  assert.ok(responses.length > 0, `${asset.id}: a real GLB must be requested`);
  for (const response of responses) {
    assert.ok(new URL(response.url()).pathname.includes(asset.id), 'no unrelated model is loaded');
    assert.equal(response.status(), 200);
  }
  const consumed = await page.evaluate(() => window.mallConsumedGlbs);
  assert.ok(consumed.length > 0, 'the viewer must actually consume a complete GLB');
  for (const body of consumed) {
    assert.equal(body.version, 2);
    assert.equal(body.declaredBytes, body.bytes);
    assert.equal(body.bytes, asset.bytes);
    assert.equal(body.sha256, asset.sha256, 'viewer-consumed GLB must match registered export');
  }
  return consumed;
}

try {
  browser = await chromium.launch(launchOptions);
  for (const [width, height] of viewports) {
    const discovery = await createPage(width, height);
    try {
      const { page, errors, requests } = discovery;
      await page.goto(server.url, { waitUntil: 'networkidle' });
      await page.locator('#model-collection').selectOption(collection.id);
      assert.equal(await page.locator('#catalog .asset-card').count(), 4);
      assert.equal(await page.locator('#catalog .asset-download').count(), 0);
      for (const id of ids) {
        const card = page.locator('#catalog .asset-card').filter({ has: page.locator(`[data-asset-id="${id}"]`) });
        assert.equal(await card.count(), 1);
        const image = card.locator('img');
        await image.scrollIntoViewIfNeeded();
        await image.evaluate(image => image.decode());
        assert.ok(await image.evaluate(image => image.naturalWidth > 0 && image.naturalHeight > 0));
        const posterUrl = await image.getAttribute('src');
        assert.ok(new URL(posterUrl, server.url).pathname.startsWith('/Blender-3D-Gallery/'));
      }
      await page.locator('#model-search').fill('directory kiosk');
      assert.equal(await page.locator('#catalog .asset-card').count(), 1);
      assert.equal(await page.locator('#catalog [data-asset-id="mall-directory-kiosk"]').count(), 2);
      await page.locator('#model-search').fill('');
      await noOverflow(page);
      assert.deepEqual(requests, [], 'static discovery must not eagerly fetch GLBs');
      assert.equal(await page.locator('canvas').count(), 0);
      assert.equal(await page.evaluate(() => window.furnitureDraws), 0);
      await page.evaluate(() => scrollTo(0, 0));
      await page.screenshot({ path: path.join(artifacts, `collection-${width}.png`) });
      assert.deepEqual(errors, []);
      results.push({ test: 'discovery', width, passed: true, decodedThumbnails: 4, eagerGlbRequests: 0 });
      console.log('PASS discovery', width);
    } finally {
      await discovery.context.close();
    }

    for (const id of ids) {
      const asset = sourceAssets.get(id);
      const fixture = await createPage(width, height);
      const record = { test: 'viewer', id, width, passed: false, glbSha256: asset.sha256, glbBytes: asset.bytes };
      try {
        const { page, responses, errors } = fixture;
        await page.goto(server.url + '?model=' + id, { waitUntil: 'networkidle' });
        await viewerReady(page);
        assert.equal(await page.locator('#viewer-title').innerText(), asset.name);
        assert.equal(await page.locator('#viewer-download').isVisible(), false);
        assert.ok((await page.locator('#viewer-metadata').innerText()).includes(asset.license));
        assert.match(asset.license, /redistribution terms have not been specified/i);
        await noOverflow(page);
        const canvas = page.locator('#viewport canvas');
        await canvas.scrollIntoViewIfNeeded();
        const bounds = await canvas.boundingBox();
        assert.ok(bounds && bounds.width > 0 && bounds.height > 0);
        assert.ok(bounds.x >= -1 && bounds.x + bounds.width <= width + 1, 'canvas fits the viewport width');
        assert.ok(bounds.y >= -1 && bounds.y + bounds.height <= height + 1, 'canvas fits the viewport height');
        record.canvasBounds = bounds;
        record.images = {};
        record.images.initial = await canvasCapture(page, `${id}-${width}-initial.png`);
        await page.screenshot({ path: path.join(artifacts, `${id}-${width}-viewer.png`) });
        const initialDraws = await page.evaluate(() => window.furnitureDraws);
        await canvas.press('ArrowRight');
        await canvas.press('ArrowRight');
        await page.waitForFunction(before => window.furnitureDraws > before, initialDraws);
        record.images.rotated = await canvasCapture(page, `${id}-${width}-rotated.png`);
        assert.notEqual(record.images.rotated, record.images.initial, 'keyboard orbit changes actual rendered pixels');
        const rotatedDraws = await page.evaluate(() => window.furnitureDraws);
        await canvas.press('PageUp');
        await page.waitForFunction(before => window.furnitureDraws > before, rotatedDraws);
        record.images.zoomed = await canvasCapture(page, `${id}-${width}-zoomed.png`);
        assert.notEqual(record.images.zoomed, record.images.rotated, 'keyboard zoom changes actual rendered pixels');
        const zoomedDraws = await page.evaluate(() => window.furnitureDraws);
        await page.locator('#reset-view').click();
        await page.waitForFunction(before => window.furnitureDraws > before, zoomedDraws);
        record.images.reset = await canvasCapture(page, `${id}-${width}-reset.png`);
        assert.notEqual(record.images.reset, record.images.zoomed, 'reset changes the zoomed view');

        // Verify consumed bytes in each document before reload clears its observations.
        await actualAssetResponses(responses, asset, page);
        await page.reload({ waitUntil: 'networkidle' });
        await viewerReady(page);
        assert.equal(new URL(page.url()).searchParams.get('model'), id);
        await actualAssetResponses(responses, asset, page);
        await page.keyboard.press('Escape');
        await page.waitForFunction(() => !document.querySelector('#viewer').open);
        assert.equal(await page.locator('#viewport canvas').count(), 0);
        assert.equal(await page.evaluate(() => document.activeElement?.dataset.assetId), id);
        const closedDraws = await page.evaluate(() => window.furnitureDraws);
        await page.waitForTimeout(250);
        assert.equal(await page.evaluate(() => window.furnitureDraws), closedDraws, 'closed viewer releases its render loop');
        await page.locator(`#catalog [data-asset-id="${id}"]`).first().click();
        await viewerReady(page, closedDraws);
        await page.locator('#close-viewer').click();
        assert.equal(await page.locator('#viewport canvas').count(), 0);
        assert.equal(await page.evaluate(() => document.activeElement?.dataset.assetId), id);
        await actualAssetResponses(responses, asset, page);
        record.glbResponses = responses.length;
        record.consumedGlbs = await actualAssetResponses(responses, asset, page);
        record.errors = errors;
        record.interactionChecksPassed = true;
        assert.deepEqual(errors, []);
        record.passed = true;
        console.log('PASS viewer', id, width);
      } catch (error) {
        record.error = error.message;
        await fixture.page.screenshot({ path: path.join(artifacts, `${id}-${width}-failure.png`) }).catch(() => {});
        failure ??= error;
        console.error('FAIL viewer', id, width, error.message);
      } finally {
        results.push(record);
        await fixture.context.close();
      }
    }
  }
  if (failure) process.exitCode = 1;
} catch (error) {
  failure = error;
  throw error;
} finally {
  await fs.writeFile(path.join(artifacts, 'results.json'), JSON.stringify({
    passed: !failure && results.length === viewports.length * (ids.length + 1) && results.every(result => result.passed),
    browserVersion: browser?.version(),
    environment: 'Built deployment subpath, Chromium/SwiftShader, localhost, reduced motion, service workers blocked',
    results,
    error: failure?.message,
    limitations: [
      'Canvas bounds are measured; final artistic framing and clipping require review of the saved model screenshots.',
      'Keyboard orbit/zoom are exercised; physical touch gestures and mobile GPU performance are not measured.',
      'Hidden download controls do not prevent retrieval of a publicly rendered GLB or grant redistribution rights.',
    ],
  }, null, 2) + '\n');
  await browser?.close();
  await server.close();
}
