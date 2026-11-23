import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { chromium } from 'playwright';
import { furnishingPaths } from '../mall-modules-preview/home-furnishings.js';
import { roomAssetPaths, roomArrival } from '../mall-modules-preview/room-layout.js';
import { launchOptions, recordConsumedGlbHashes } from './browser-test-utils.mjs';

const url = new URL('mall-modules-preview/?view=enclosed-shop', process.env.MALL_PREVIEW_SITE ?? 'http://127.0.0.1:5173/');
const avatar = '**/gjh-mall-visitor.glb';
const expected = await Promise.all(Object.values(roomAssetPaths).map(async path =>
  createHash('sha256').update(await readFile(path)).digest('hex')));
const fixtureHashes = await Promise.all(Object.values(furnishingPaths).map(async path =>
  createHash('sha256').update(await readFile(path)).digest('hex')));
const ready = (page, view) => page.locator('#canvas-wrap[data-view="' + view + '"] #canvas-status[data-state="ready"]')
  .waitFor({ state: 'attached', timeout: 120000 });
const inspect = page => page.locator('#canvas-wrap').evaluate(el => el.inspectVisitor());
const browser = await chromium.launch(launchOptions);
try {
  for (const width of [1080, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 820 }, hasTouch: width === 390 });
    const errors = [], models = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('response', response => {
      if (response.ok() && new URL(response.url()).pathname.endsWith('.glb')) models.push(response);
    });
    await page.addInitScript(recordConsumedGlbHashes);
    await page.goto(url.href, { waitUntil: 'domcontentloaded' });
    await ready(page, 'enclosed-shop');
    const actual = await page.evaluate(() => window.consumedModelHashes);
    assert.deepEqual(actual.sort(), [...expected].sort(), 'direct room view downloads exactly its six model files');
    const canvas = page.locator('#canvas-wrap canvas');
    const roof = page.getByRole('button', { name: /^(Show|Hide) ceiling$/ });
    const floorView = await canvas.screenshot();
    if (process.env.MALL_GRID_SHOTS) await canvas.screenshot({ path: process.env.MALL_GRID_SHOTS + '/room-open-' + width + '.png' });
    await roof.click();
    assert.equal(await roof.getAttribute('aria-pressed'), 'true');
    const covered = await canvas.screenshot();
    assert.ok(!floorView.equals(covered), 'showing the ceiling changes the rendered scene');
    if (process.env.MALL_GRID_SHOTS) await canvas.screenshot({ path: process.env.MALL_GRID_SHOTS + '/room-covered-' + width + '.png' });
    assert.equal(models.length, 6, 'the ceiling toggle reuses the installed cassettes');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    const layouts = page.getByRole('combobox', { name: 'Assembly' });
    await layouts.selectOption('home-furnishings');
    await ready(page, 'home-furnishings');
    const installed = await page.evaluate(() => window.consumedModelHashes);
    assert.deepEqual(installed.sort(), [...expected, ...fixtureHashes].sort(), 'both scenes share the shell and each fixture loads once');
    assert.equal(await roof.getAttribute('aria-pressed'), 'false', 'the showroom opens in cutaway');
    if (process.env.MALL_GRID_SHOTS) await canvas.screenshot({ path: process.env.MALL_GRID_SHOTS + '/home-furnishings-' + width + '.png' });
    await roof.click();
    await layouts.selectOption('enclosed-shop');
    await ready(page, 'enclosed-shop');
    assert.equal(await roof.getAttribute('aria-pressed'), 'true', 'the original shop retains its ceiling setting');
    if (width === 390) {
      await roof.click();
      assert.equal(await roof.getAttribute('aria-pressed'), 'false');
      assert.deepEqual(errors, []);
      await page.close();
      continue;
    }

    // Hold the avatar fetch while switching rooms. One controller must join the
    // newly selected room on completion and must wait for another Walk action.
    let release, inFlight;
    const gate = new Promise(resolve => { release = resolve; });
    const started = new Promise(resolve => { inFlight = resolve; });
    await page.route(avatar, async route => { inFlight(); await gate; await route.continue(); });
    await page.locator('#walk').click();
    await started;
    await page.locator('#assembly-button').click();
    await ready(page, 'assembly');
    release();
    await page.waitForFunction(() => Boolean(document.querySelector('#canvas-wrap').inspectVisitor().visitor));
    assert.equal((await inspect(page)).visitor.walking, false);
    assert.equal(await roof.count(), 0);
    await page.locator('#transition-button').click();
    await page.locator('#grid-layout').selectOption('enclosed-shop');
    await ready(page, 'enclosed-shop');
    assert.deepEqual((await inspect(page)).visitor.position, [roomArrival.x, 0, roomArrival.z]);
    assert.equal(await roof.getAttribute('aria-pressed'), 'true');
    await page.locator('#walk').click();
    await page.waitForFunction(() => document.querySelector('#canvas-wrap').inspectVisitor().visitor.walking);
    async function move(key, target) {
      await canvas.focus();
      await page.keyboard.down(key);
      try {
        await page.waitForFunction(({ key, target }) => {
          const { visitor } = document.querySelector('#canvas-wrap').inspectVisitor();
          if (target === null) return Boolean(visitor.blocked);
          return key === 'ArrowUp' ? visitor.position[2] <= target : visitor.position[2] >= target;
        }, { key, target }, { timeout: 90000 });
      } finally { await page.keyboard.up(key); }
      return (await inspect(page)).visitor.position[2];
    }
    const stopped = await move('ArrowUp', null);
    assert.ok(stopped > 3.6 && stopped < 3.95, 'closed shop stops the visitor outside');
    await page.locator('#reset-visitor').click();
    await page.locator('#doors').click();
    assert.equal((await inspect(page)).angle, 90);
    const threshold = await move('ArrowUp', 3.15);
    assert.ok(threshold > 3 && threshold < 3.3);
    await page.locator('#doors').click();
    assert.match(await page.locator('#walk-message').textContent(), /occupied/);
    assert.equal((await inspect(page)).angle, 90);
    assert.ok(await move('ArrowUp', 1.75) < 1.8, 'walk through the open entrance');
    await page.locator('#doors').click();
    assert.equal((await inspect(page)).angle, 0);
    await page.locator('#doors').click();
    assert.ok(await move('ArrowDown', 4.1) > 4, 'walk back onto the outside apron');
    await page.keyboard.press('Escape');
    assert.equal((await inspect(page)).visitor.walking, false);
    await page.locator('#assembly-button').click();
    await ready(page, 'assembly');
    assert.equal((await inspect(page)).angle, 0, 'each assembly retains its own door state');
    await page.locator('#transition-button').click();
    await layouts.selectOption('home-furnishings');
    await ready(page, 'home-furnishings');
    await page.locator('#doors').click();
    await page.locator('#walk').click();
    assert.ok(await move('ArrowUp', .6) <= .6, 'enter the furnished showroom from the apron');
    assert.ok(await move('ArrowDown', 4.1) >= 4.1, 'leave the displays through the same open doorway');
    await page.keyboard.press('Escape');
    assert.equal(models.filter(r => r.url().endsWith('/gjh-mall-visitor.glb')).length, 1);
    assert.deepEqual(errors, []);
    console.log('PASS enclosed shop, six exact GLBs, ceiling, visitor load during room change, closed/open entry and occupied-door rollback');
    await page.close();
  }
} finally {
  await browser.close();
}
