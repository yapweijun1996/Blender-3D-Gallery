import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { chromium } from 'playwright';
import { cornerFloorPath, floorEdgePaths } from '../mall-modules-preview/floor-edge.js';
import { floorTransitionPaths } from '../mall-modules-preview/floor-transition.js';
import { shellAssetPaths } from '../mall-modules-preview/shell-layout.js';
import { wallCornerPath, wallRunPath } from '../mall-modules-preview/wall-run.js';
import { launchOptions, recordConsumedGlbHashes } from './browser-test-utils.mjs';

const url = new URL('mall-modules-preview/?view=floor-transition', process.env.MALL_PREVIEW_SITE ?? 'http://127.0.0.1:5173/');
const hashes = await Promise.all(Object.values(floorTransitionPaths).map(async path =>
  createHash('sha256').update(await readFile(path)).digest('hex')));
const shellViews = [
  ['t-junction'],
  ['cross-junction'],
  ['corner-floor', cornerFloorPath],
  ['finished-edge', ...Object.values(floorEdgePaths)],
  ['wall-run', wallRunPath],
  ['wall-ceiling', shellAssetPaths.ceiling],
  ['wall-corner', wallCornerPath],
];
const browser = await chromium.launch(launchOptions);
try {
  for (const width of [1080, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 800 }, hasTouch: width === 390 });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.addInitScript(recordConsumedGlbHashes);
    // Fail the opt-in model once. Selecting the same view must make a fresh request.
    const blocked = '**/' + floorTransitionPaths.floor2m;
    await page.route(blocked, route => route.abort());
    await page.goto(url.href, { waitUntil: 'domcontentloaded' });
    await page.locator('#canvas-status[data-state="error"]').waitFor({ timeout: 90000 });
    await page.unroute(blocked);
    const transition = page.getByRole('button', { name: 'Floor grid transition' });
    await transition.focus();
    await page.keyboard.press('Enter');
    const ready = view => page.locator('#canvas-wrap[data-view="' + view + '"] #canvas-status[data-state="ready"]').waitFor({ state: 'attached', timeout: 90000 });
    await ready('floor-transition');
    assert.deepEqual((await page.evaluate(() => window.consumedModelHashes)).sort(), [...hashes].sort());
    assert.equal(await transition.getAttribute('aria-pressed'), 'true');
    assert.equal(await page.locator('#walk-tools').isVisible(), false);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.getByRole('button', { name: 'Reset camera view' }).click();
    if (process.env.MALL_GRID_SHOTS) await page.locator('#canvas-wrap').screenshot({
      path: process.env.MALL_GRID_SHOTS + '/floor-transition-' + width + '.png',
    });
    const layouts = page.getByRole('combobox', { name: 'Assembly' });
    const expected = [...hashes];
    let threeWayImage;
    for (const [view, ...files] of shellViews) {
      await layouts.selectOption(view);
      await ready(view);
      if (view === 't-junction') threeWayImage = await page.locator('canvas').first().screenshot();
      if (view === 'cross-junction') {
        const fourWayImage = await page.locator('canvas').first().screenshot();
        assert.ok(!threeWayImage.equals(fourWayImage), 'the fourth arm changes the rendered junction');
      }
      for (const file of files) expected.push(createHash('sha256').update(await readFile(file)).digest('hex'));
      assert.deepEqual((await page.evaluate(() => window.consumedModelHashes)).sort(), [...expected].sort());
      if (process.env.MALL_GRID_SHOTS) await page.locator('#canvas-wrap').screenshot({
        path: process.env.MALL_GRID_SHOTS + '/' + view + '-' + width + '.png',
      });
    }
    await layouts.selectOption('floor-transition');
    await ready('floor-transition');
    await page.locator('[data-module="floor"]').click();
    await ready('floor');
    await page.locator('#assembly-button').click();
    await ready('assembly');
    assert.ok(await page.getByRole('button', { name: 'Walk visitor' }).isVisible());
    await transition.click();
    await ready('floor-transition');
    assert.deepEqual(errors, []);
    console.log('PASS', width, 'px,', expected.length, 'distinct assembly GLBs, failed load and retry, individual floor and corridor');
    await page.close();
  }
} finally {
  await browser.close();
}
