import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { chromium } from 'playwright';
import { Group } from 'three';
import { assembleCrossJunction, assembleTJunction } from '../mall-modules-preview/floor-junctions.js';
import { assembleRoom, roomAssetPaths } from '../mall-modules-preview/room-layout.js';
import { summarizeFrameIntervals } from '../mall-modules-preview/qa/measure-floor-frames.js';
import { launchOptions, recordConsumedGlbHashes, waitForRenderedFrames } from './browser-test-utils.mjs';

const [base, revision] = process.argv.slice(2);
assert.ok(base && revision, 'Usage: node scripts/test-mall-floor-phone-sampler.mjs <preview URL> <full revision>');
const settings = {
  revision, runId: 'desktop-chromium-dry-run', evidence: 'chromium-dry-run',
  device: { model: 'Desktop Chromium, emulated phone viewport', os: process.platform, browser: '',
    refreshMode: 'headless', power: 'unmeasured', thermal: 'unmeasured' },
};
const url = new URL(base);
url.searchParams.set('qaRun', settings.runId);
url.searchParams.set('qaRevision', revision);
const hash = createHash('sha256').update(await readFile(new URL('../' + roomAssetPaths.floor2m, import.meta.url))).digest('hex');

assert.deepEqual(summarizeFrameIntervals([9, 12, 51, 17, 50, 16], 155), {
  samples: 6, elapsedMs: 155, meanFps: 38.71, p50Ms: 16, p95Ms: 51, maxMs: 51, over50Ms: 1,
});
// Derive expected counts from the public placement code, before the shop batches its static meshes.
const sources = Object.fromEntries(Object.keys(roomAssetPaths).map(key => [key, new Group()]));
for (const name of ['HINGE_Left', 'HINGE_Right']) {
  const hinge = new Group(); hinge.name = name; sources.door.add(hinge);
}
const scenes = {
  't-junction': assembleTJunction(sources), 'cross-junction': assembleCrossJunction(sources),
  'enclosed-shop': assembleRoom(sources).group,
};
const browser = await chromium.launch(launchOptions);
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  settings.device.browser = 'Playwright Chromium ' + browser.version();
  await page.addInitScript(recordConsumedGlbHashes);
  const output = { evidence: 'chromium-dry-run', physicalRuns: 0, floorGlbSha256: hash, scenes: [], rejected: {} };
  async function ready(scene) {
    await page.waitForFunction(id => {
      const wrap = document.querySelector('#canvas-wrap');
      return wrap?.dataset.view === id && wrap.querySelector('#canvas-status').dataset.state === 'ready' &&
        wrap.inspectVisitor().drawCalls > 0;
    }, scene, { timeout: 60000 });
    await page.locator('#canvas-wrap canvas').evaluate(canvas => canvas.scrollIntoView({ block: 'center', behavior: 'instant' }));
    await waitForRenderedFrames(page);
  }
  async function open(scene) {
    url.searchParams.set('view', scene);
    await page.goto(url.href);
    await ready(scene);
    await page.evaluate(async () => {
      const { measureFloorFrames } = await import('./qa/measure-floor-frames.js');
      window.measureFloor = options => measureFloorFrames(options);
    });
  }
  async function rejection(name, scene, pattern, overrides = {}) {
    const result = await page.evaluate(opts => window.measureFloor(opts).then(() => 'unexpected success', e => e.message),
      { ...settings, scene, ...overrides });
    assert.match(result, pattern);
    output.rejected[name] = result;
  }
  for (const [scene, group] of Object.entries(scenes)) {
    await open(scene);
    await page.waitForFunction(h => window.consumedModelHashes.includes(h), hash);
    const result = await page.evaluate(opts => window.measureFloor(opts), { ...settings, scene });
    let count = 0;
    group.traverse(o => { if (o.userData.moduleId === 'floor2m') count++; });
    assert.equal(result.floor2mPlacements, count);
    assert.equal(result.evidence, 'chromium-dry-run');
    assert.equal(result.build.revision, revision);
    assert.ok(result.start.drawCalls > 0 && result.end.drawCalls > 0 && result.elapsedMs >= 1500);
    assert.equal(result.end.renderFrame - result.start.renderFrame, result.renderFrames);
    assert.ok(result.renderFrames > 0);
    assert.ok(result.samples > 0 && result.p50Ms <= result.p95Ms && result.p95Ms <= result.maxMs);
    output.scenes.push(result);
  }
  await rejection('automatedHardwareLabel', 'enclosed-shop', /dry-run label/, { evidence: 'physical-phone' });
  await rejection('wrongScene', 't-junction', /requested scene/);
  await rejection('wrongRun', 'enclosed-shop', /requested qaRun/, { runId: 'other-tab' });
  await rejection('wrongRevision', 'enclosed-shop', /expected full revision/, { revision: '0'.repeat(40) });
  await page.locator('#shop-roof').click();
  await rejection('differentRoof', 'enclosed-shop', /Hide the enclosed-shop ceiling/);
  url.searchParams.set('view', 't-junction');
  let allowFloor;
  const gate = new Promise(resolve => { allowFloor = resolve; });
  const floorRoute = '**/mall-floor-module-2m.glb';
  await page.route(floorRoute, async route => { await gate; await route.continue(); });
  try {
    await page.goto(url.href, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('#canvas-status[data-state="loading"]');
    const loading = await page.evaluate(async opts => {
      const { measureFloorFrames } = await import('./qa/measure-floor-frames.js');
      return measureFloorFrames(opts).then(() => 'unexpected success', e => e.message);
    }, { ...settings, scene: 't-junction' });
    assert.match(loading, /requested scene/);
    output.rejected.loadingAsset = loading;
  } finally { allowFloor(); }
  await ready('t-junction');
  await page.unroute(floorRoute);
  await open('t-junction');
  await page.evaluate(() => scrollTo({ top: document.documentElement.scrollHeight, behavior: 'instant' }));
  await waitForRenderedFrames(page);
  await rejection('offscreenCanvas', 't-junction', /visible canvas/);
  await ready('t-junction');
  // Reselecting the cached scene can return to ready between two animation frames.
  await page.evaluate(opts => {
    window.pending = window.measureFloor(opts).then(() => 'unexpected success', error => error.message);
    setTimeout(() => document.querySelector('#grid-layout').dispatchEvent(new Event('change', { bubbles: true })), 650);
  }, { ...settings, scene: 't-junction' });
  output.rejected.cachedReselect = await page.evaluate(() => window.pending);
  assert.match(output.rejected.cachedReselect, /changed during the run/);
  await ready('t-junction');
  // Navigation produces a trusted visibilitychange/pagehide on the old document.
  await page.evaluate(opts => {
    window.measureFloor(opts).catch(e => sessionStorage.setItem('qa-foreground-rejection', e.message));
  }, { ...settings, scene: 't-junction' });
  await page.goto(new URL('./qa/measure-floor-frames.js', url).href);
  output.rejected.pageLeft = await page.evaluate(() => sessionStorage.getItem('qa-foreground-rejection'));
  assert.match(output.rejected.pageLeft, /foreground visibility|page was left/);
  // Three.js exposes the real renderer to DevTools observers. Keep the probe RAF running independently.
  await page.addInitScript(() => {
    window.__THREE_DEVTOOLS__ = new EventTarget();
    window.__THREE_DEVTOOLS__.addEventListener('observe', ({ detail }) => {
      if (detail.isWebGLRenderer) window.qaRenderer = detail;
    });
  });
  await open('t-junction');
  await page.evaluate(() => {
    const render = window.qaRenderer.render;
    let calls = 0;
    window.qaRenderer.render = function (...args) {
      if (++calls % 3 !== 0) return render.apply(this, args);
    };
  });
  const intermittent = await page.evaluate(opts => window.measureFloor(opts), { ...settings, scene: 't-junction' });
  assert.ok(intermittent.callbacksWithoutRender > 0 && intermittent.longestNoRenderMs > 0);
  assert.ok(intermittent.renderFrames > 0 && intermittent.renderFrames < intermittent.samples);
  output.interruptedRenderControl = {
    samples: intermittent.samples, renderFrames: intermittent.renderFrames,
    callbacksWithoutRender: intermittent.callbacksWithoutRender, longestNoRenderMs: intermittent.longestNoRenderMs,
  };
  await page.evaluate(() => window.qaRenderer.setAnimationLoop(null));
  await rejection('frozenRenderer', 't-junction', /no new frames/);
  console.log(JSON.stringify(output, null, 2));
} finally { await browser.close(); }
