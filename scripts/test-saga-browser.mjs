import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';
import { loadCatalog } from './catalog.mjs';
import { serveBuild, launchOptions } from './browser-test-utils.mjs';

const catalog = loadCatalog();
const assets = catalog.collections.flatMap(collection => collection.assets);
const saga = assets.find(asset => asset.id === 'proton-saga-1985');
assert.ok(saga, 'Saga must exist in the source catalog');
const output = process.env.TEST_ARTIFACT_DIR || '/tmp/blender-gallery-saga-qa';
await fs.mkdir(output, { recursive: true });
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const results = [];

async function ready(page) {
  await page.waitForFunction(() => document.querySelector('#viewer')?.open &&
    document.querySelector('#viewport canvas') &&
    document.querySelector('#viewer-status')?.textContent === '' && window.sagaDrawCalls > 0,
  null, { timeout: 60000 });
  // Viewer drawing and browser network completion are distinct milestones.
  // Settle the document before deliberate navigation/reload can cancel a late response.
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(350);
}
async function noOverflow(page) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
}
async function changedCanvas(page, action, label) {
  const canvas = page.locator('#viewport canvas');
  const before = await canvas.screenshot();
  const draws = await page.evaluate(() => window.sagaDrawCalls);
  await action(canvas);
  await page.waitForFunction(previous => window.sagaDrawCalls > previous, draws);
  await page.waitForTimeout(400);
  const after = await canvas.screenshot();
  assert.equal(before.equals(after), false, `${label} changes rendered model pixels`);
}

try {
  for (const [label, width, height, touch] of [
    ['desktop', 1440, 900, false], ['tablet', 768, 1024, true],
    ['mobile', 390, 844, true], ['narrow', 320, 720, true],
  ]) {
    const context = await browser.newContext({
      viewport: { width, height }, hasTouch: touch, serviceWorkers: 'block',
    });
    await context.addInitScript(() => {
      window.sagaDrawCalls = 0;
      for (const type of [WebGLRenderingContext, WebGL2RenderingContext]) {
        for (const name of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
          const original = type.prototype[name];
          if (original) type.prototype[name] = function (...args) {
            window.sagaDrawCalls++;
            return original.apply(this, args);
          };
        }
      }
    });
    const page = await context.newPage();
    const failures = [], glbs = [], glbRequests = new Map();
    page.on('pageerror', error => failures.push(error.message));
    page.on('console', message => {
      if (message.type() === 'error') failures.push(message.text());
    });
    page.on('request', request => {
      if (new URL(request.url()).pathname.endsWith('.glb')) {
        let settle;
        const settled = new Promise(resolve => { settle = resolve; });
        glbs.push(request.url());
        glbRequests.set(request, { request, settled, settle, response: null, finished: false, failure: null });
      }
    });
    page.on('response', response => {
      if (response.status() >= 400) failures.push(`${response.status()} ${response.url()}`);
      const record = glbRequests.get(response.request());
      if (record) record.response = response;
    });
    page.on('requestfinished', request => {
      const record = glbRequests.get(request);
      if (record) { record.finished = true; record.settle(); }
    });
    page.on('requestfailed', request => {
      failures.push(`${request.url()} ${request.failure()?.errorText}`);
      const record = glbRequests.get(request);
      if (record) { record.failure = request.failure()?.errorText ?? 'unknown failure'; record.settle(); }
    });
    let checkedResponses = 0;
    const verifyResponses = async () => {
      const records = [...glbRequests.values()];
      assert.ok(records.length > 0, 'at least one GLB request was observed');
      while (checkedResponses < records.length) {
        const record = records[checkedResponses];
        let timer;
        try {
          await Promise.race([
            record.settled,
            new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(`GLB request did not finish: ${record.request.url()}`)), 10000); }),
          ]);
        } finally {
          clearTimeout(timer);
        }
        assert.equal(record.failure, null, 'GLB request must not fail');
        assert.ok(record.response && record.response.status() >= 200 && record.response.status() < 300, 'GLB response must succeed');
        assert.ok(record.finished, 'GLB response body completed before navigation');
        checkedResponses++;
      }
    };
    try {
      await page.goto(server.url);
      assert.equal(await page.locator('#catalog .asset-card').count(), assets.length);
      await page.locator('#model-search').fill('Saga');
      assert.equal(await page.locator('#catalog .asset-card').count(), 1);
      assert.deepEqual(glbs, [], 'browsing and search load no GLBs');
      await noOverflow(page);
      await page.screenshot({ path: path.join(output, `${label}-catalog.png`) });
      const opener = page.locator('#catalog [data-asset-id="proton-saga-1985"]').first();
      assert.equal(await page.locator('#catalog .asset-download').count(), 0);
      await opener.click();
      await ready(page);
      await verifyResponses();
      assert.ok(glbs.some(url => /proton-saga-1985/.test(url)), 'viewer requests the real Saga GLB');
      assert.equal(await page.locator('#viewer-title').innerText(), saga.name);
      assert.equal(await page.locator('#viewer-download').isVisible(), false);
      assert.ok((await page.locator('#viewer-description').innerText()).includes(saga.details.accuracy_notes));
      assert.match(await page.locator('#viewer-metadata').innerText(), /triangles/i);
      await noOverflow(page);
      await page.screenshot({ path: path.join(output, `${label}-viewer.png`) });
      const viewButtons = page.locator('.vehicle-view-buttons button');
      assert.equal(await viewButtons.count(), 4);
      for (const name of ['front', 'rear', 'left', 'right']) {
        const button = page.locator(`[data-vehicle-view="${name}"]`);
        const rect = await button.boundingBox();
        assert.ok(rect.width >= 44 && rect.height >= 44, 'vehicle presets retain touch targets');
        await changedCanvas(page, async () => button.click(), `${name} preset`);
        assert.equal(await button.getAttribute('aria-pressed'), 'true');
        assert.equal(await page.locator('.vehicle-view-buttons [aria-pressed="true"]').count(), 1);
        await page.screenshot({ path: path.join(output, `${label}-${name}.png`) });
        await noOverflow(page);
      }
      // Native button keyboard activation must operate the same presets.
      await page.locator('[data-vehicle-view="front"]').focus();
      await changedCanvas(page, async () => page.keyboard.press('Enter'), 'keyboard front preset');
      assert.equal(await page.locator('[data-vehicle-view="front"]').getAttribute('aria-pressed'), 'true');
      const dialog = page.locator('#viewer');
      for (const fraction of [0, 0.5, 1]) {
        await dialog.evaluate((element, position) => { element.scrollTop = (element.scrollHeight - element.clientHeight) * position; }, fraction);
        const close = await page.locator('#close-viewer').boundingBox();
        assert.ok(close.y >= 0 && close.y + close.height <= height, 'close remains visible throughout dialog scrolling');
        await noOverflow(page);
        await page.screenshot({ path: path.join(output, `${label}-scroll-${fraction}.png`) });
      }
      await dialog.evaluate(element => { element.scrollTop = 0; });
      await changedCanvas(page, async canvas => {
        const box = await canvas.boundingBox();
        await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5);
        await page.mouse.down();
        await page.mouse.move(box.x + box.width * 0.7, box.y + box.height * 0.55, { steps: 12 });
        await page.mouse.up();
      }, 'drag rotation');
      await changedCanvas(page, async canvas => {
        await canvas.hover();
        await page.mouse.wheel(0, -240);
      }, 'wheel zoom');
      await changedCanvas(page, async () => page.locator('#reset-view').click(), 'reset');
      await verifyResponses();
      await page.locator('#close-viewer').click();
      assert.equal(await page.locator('#viewer').evaluate(element => element.open), false);
      assert.equal(await page.locator('#viewport canvas').count(), 0);
      assert.equal(await page.locator('.vehicle-views').count(), 0, 'closing disposes vehicle-only controls');
      assert.equal(await opener.evaluate(element => element === document.activeElement), true);
      const beforeDirectLink = glbRequests.size;
      await page.goto(server.url + '?model=proton-saga-1985');
      await ready(page);
      assert.ok(glbRequests.size > beforeDirectLink, 'direct link requests a fresh GLB');
      await verifyResponses();
      const beforeReload = glbRequests.size;
      await page.reload();
      await ready(page);
      assert.ok(glbRequests.size > beforeReload, 'reload requests a fresh GLB');
      await verifyResponses();
      await noOverflow(page);
      assert.equal(new URL(page.url()).searchParams.get('model'), 'proton-saga-1985');
      assert.equal(checkedResponses, glbRequests.size, 'all observed GLB requests were checked');
      assert.deepEqual(failures, [], 'no browser, network or console errors');
      results.push({ viewport: label, passed: true, glbRequests: glbs.length });
      console.log(`PASS Saga ${label}: search, lazy load, render, four presets, keyboard, scrolling, rotate, zoom, reset, focus, direct link and reload`);
    } catch (error) {
      await page.screenshot({ path: path.join(output, `${label}-failure.png`) }).catch(() => {});
      throw error;
    } finally {
      await context.close();
    }
  }
  await fs.writeFile(path.join(output, 'results.json'), JSON.stringify(results, null, 2) + '\n');
} finally {
  await browser.close();
  await server.close();
}
