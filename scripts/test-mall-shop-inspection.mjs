import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';
import { bakeryPaths } from '../mall-modules-preview/bakery-shop.js';
import { supermarketPaths } from '../mall-modules-preview/supermarket-shop.js';
import { computerPaths } from '../mall-modules-preview/computer-shop.js';
import { beautyPaths } from '../mall-modules-preview/pharmacy-beauty.js';
import { roomAssetPaths } from '../mall-modules-preview/room-layout.js';
import { launchOptions, recordConsumedGlbHashes } from './browser-test-utils.mjs';

const shops = {
  'supermarket': { paths: supermarketPaths, label: 'Inspect cart return', dependency: supermarketPaths.cartReturn },
  'bakery-shop': { paths: bakeryPaths, label: 'Inspect serving tongs', dependency: bakeryPaths.servingTongs },
  'pharmacy-beauty': { paths: beautyPaths, label: 'Inspect tester bar', dependency: beautyPaths.testerBar },
  'computer-shop': { paths: computerPaths, label: 'Inspect demo laptop', dependency: computerPaths.securityTether },
};
const id = process.argv[2];
assert.ok(Object.hasOwn(shops, id), 'Specify a shop: ' + Object.keys(shops).join(' or '));
const shop = shops[id];
const url = new URL('mall-modules-preview/?view=' + id, process.env.MALL_PREVIEW_SITE ?? 'http://127.0.0.1:5173/');
const paths = Object.values({ ...roomAssetPaths, ...shop.paths });
const expected = (await Promise.all(paths.map(async path =>
  createHash('sha256').update(await readFile(path)).digest('hex')))).sort();
const ready = (page, id) => page.locator('#canvas-wrap[data-view="' + id + '"] #canvas-status[data-state="ready"]')
  .waitFor({ state: 'attached', timeout: 120000 });
const rendered = page => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
const readVisitor = page => page.locator('#canvas-wrap').evaluate(el => el.inspectVisitor().visitor);
const browser = await chromium.launch(launchOptions);

try {
  for (const width of [1080, 390]) {
    const touch = width === 390;
    const page = await browser.newPage({ viewport: { width, height: 844 }, hasTouch: touch });
    page.setDefaultTimeout(90000);
    page.setDefaultNavigationTimeout(120000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.addInitScript(recordConsumedGlbHashes);
    if (touch) {
      await page.route('**/' + shop.dependency, route => route.abort(), { times: 1 });
    }
    await page.goto(url.href, { waitUntil: 'domcontentloaded' });
    if (touch) {
      await page.locator('#canvas-status[data-state="error"]').waitFor();
      assert.equal(await page.getByRole('button', { name: shop.label }).count(), 0);
      const layouts = page.getByRole('combobox', { name: 'Assembly' });
      await layouts.selectOption('enclosed-shop');
      await ready(page, 'enclosed-shop');
      await layouts.selectOption(id);
    }
    await ready(page, id);
    assert.deepEqual(await page.evaluate(() => window.consumedModelHashes.slice().sort()), expected);
    assert.equal(await readVisitor(page), null);

    const inspect = page.getByRole('button', { name: shop.label });
    const canvas = page.locator('#canvas-wrap canvas');
    const layouts = page.getByRole('combobox', { name: 'Assembly' });
    const reset = page.getByRole('button', { name: 'Reset camera view' });
    const protocol = await page.context().newCDPSession(page);
    async function shot(name) {
      await canvas.evaluate(element => element.scrollIntoView({ block: 'center', behavior: 'instant' }));
      await rendered(page);
      const clip = await canvas.evaluate(element => {
        const rect = element.getBoundingClientRect();
        return { x: Math.round(rect.x + scrollX), y: Math.round(rect.y + scrollY),
          width: Math.floor(rect.width), height: Math.floor(rect.height), scale: 1 };
      });
      const { data } = await protocol.send('Page.captureScreenshot', { format: 'png', clip, captureBeyondViewport: true });
      if (process.env.MALL_GRID_SHOTS) {
        const path = process.env.MALL_GRID_SHOTS + '/' + id + '-' + name + '-' + width + '.png';
        await writeFile(path, Buffer.from(data, 'base64'));
      }
      // Scroll position can change the outermost antialiased border pixel.
      // Compare the rendered interior directly, including the inspected display.
      return page.evaluate(async encoded => {
        const image = new Image();
        image.src = 'data:image/png;base64,' + encoded;
        await image.decode();
        const surface = document.createElement('canvas');
        surface.width = image.width - 4;
        surface.height = image.height - 4;
        surface.getContext('2d').drawImage(image, -2, -2);
        return surface.toDataURL();
      }, data);
    }
    const overview = await shot('overview');
    if (touch) await inspect.tap();
    else { await inspect.focus(); await page.keyboard.press('Enter'); }
    const detail = await shot('detail');
    assert.ok(overview !== detail, 'inspect moves from the shop overview to the installed fixture');
    await reset.click();
    assert.ok(overview === await shot('reset'), 'reset restores the original view of the shop');
    await page.getByRole('button', { name: 'Show ceiling' }).click();
    await inspect.click();
    assert.ok(detail === await shot('under-roof'), 'the inspection camera stays inside the shop below the ceiling');
    await layouts.selectOption('enclosed-shop');
    await ready(page, 'enclosed-shop');
    assert.equal(await inspect.count(), 0);
    await layouts.selectOption(id);
    await ready(page, id);
    assert.equal(await page.getByRole('button', { name: 'Hide ceiling' }).count(), 1);
    assert.deepEqual(await page.evaluate(() => window.consumedModelHashes.slice().sort()), expected, 'switches reuse installed fixtures');

    if (!touch) {
      // A late visitor download must respect a more recent request to inspect the display.
      let release, started;
      const gate = new Promise(resolve => { release = resolve; });
      const download = new Promise(resolve => { started = resolve; });
      await page.route('**/gjh-mall-visitor.glb', async route => { started(); await gate; await route.continue(); });
      const walk = page.locator('#walk');
      await walk.click();
      await download;
      await inspect.click();
      release();
      await page.waitForFunction(() => Boolean(document.querySelector('#canvas-wrap').inspectVisitor().visitor));
      assert.equal((await readVisitor(page)).walking, false);
      await walk.click();
      assert.equal((await readVisitor(page)).walking, true);
      const before = (await readVisitor(page)).position;
      await inspect.click();
      const after = await readVisitor(page);
      assert.equal(after.walking, false);
      assert.deepEqual(after.position, before, 'inspection preserves visitor position');
      assert.ok(detail === await shot('after-walking'), 'the visitor does not obscure the inspection camera');
    }
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert.deepEqual(errors, []);
    await page.close();
    console.log('PASS', id, width + 'px,', expected.length, 'exact GLBs, inspection, reset, roof and scene selection');
  }
} finally {
  await browser.close();
}
