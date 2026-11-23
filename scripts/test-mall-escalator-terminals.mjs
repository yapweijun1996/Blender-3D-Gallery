import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { chromium } from 'playwright';
import { escalatorTerminalPaths } from '../mall-modules-preview/escalator-terminal.js';
import { launchOptions, recordConsumedGlbHashes } from './browser-test-utils.mjs';

const url = new URL('mall-modules-preview/?view=escalator-terminals', process.env.MALL_PREVIEW_SITE || 'http://127.0.0.1:5173/');
const output = process.env.MALL_PREVIEW_OUTPUT;
if (output) await mkdir(output, { recursive: true });
const hashes = await Promise.all(Object.values(escalatorTerminalPaths).map(async path =>
  createHash('sha256').update(await readFile(path)).digest('hex')));
const browser = await chromium.launch(launchOptions);
try {
  for (const [width, height] of [[1440, 900], [390, 844]]) {
    const context = await browser.newContext({ viewport: { width, height }, hasTouch: width === 390 });
    await context.addInitScript(recordConsumedGlbHashes);
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(url.href, { waitUntil: 'domcontentloaded' });
    const ready = view => page.locator('#canvas-wrap[data-view="' + view + '"] #canvas-status[data-state=ready]').waitFor({ state: 'attached' });
    await ready('escalator-terminals');
    await page.waitForFunction(expected => expected.every(hash => window.consumedModelHashes.includes(hash)), hashes);
    const lower = page.getByRole('button', { name: 'Inspect lower terminal' });
    const upper = page.getByRole('button', { name: 'Inspect upper terminal' });
    const screenshot = async name => {
      const canvas = page.locator('#canvas-wrap canvas');
      await canvas.evaluate(element => element.scrollIntoView({ block: 'center', behavior: 'instant' }));
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      return canvas.screenshot(output ? { path: join(output, width + '-' + name + '.png') } : {});
    };
    const overview = await screenshot('overview');
    await lower.focus();
    await lower.press('Enter');
    assert.equal(await lower.getAttribute('aria-pressed'), 'true');
    const lowerView = await screenshot('lower');
    assert.ok(!lowerView.equals(overview), 'lower landing opens a close-up');
    await upper.click();
    assert.equal(await lower.getAttribute('aria-pressed'), 'false');
    assert.equal(await upper.getAttribute('aria-pressed'), 'true');
    const upperView = await screenshot('upper');
    assert.ok(!upperView.equals(lowerView), 'upper and lower show distinct joints');
    await page.getByRole('button', { name: 'Reset camera view' }).click();
    assert.equal(await upper.getAttribute('aria-pressed'), 'false');
    assert.ok((await screenshot('reset')).equals(overview), 'reset restores the assembly overview');
    await page.locator('#grid-layout').selectOption('floor-transition');
    await ready('floor-transition');
    assert.equal(await lower.isVisible(), false);
    await page.locator('#grid-layout').selectOption('escalator-terminals');
    await ready('escalator-terminals');
    assert.equal(await upper.getAttribute('aria-pressed'), 'false');
    assert.deepEqual(errors, []);
    console.log(width + 'px passed both landing views, keyboard selection, reset, layout switching and three GLB hashes.');
    await context.close();
  }
} finally {
  await browser.close();
}
