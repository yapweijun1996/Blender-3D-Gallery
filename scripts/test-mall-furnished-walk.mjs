import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { join } from 'node:path';
import { chromium } from 'playwright';

const url = new URL('mall-modules-preview/', process.env.MALL_PREVIEW_SITE ?? 'http://127.0.0.1:5173/');
const shots = process.env.MALL_WALK_SHOTS;
if (shots) await mkdir(shots, { recursive: true });
const browser = await chromium.launch({ channel: 'chrome', headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 900, height: 720 }, hasTouch: true });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  const loaded = new Set();
  page.on('response', r => { if (r.ok() && /\.glb$/.test(new URL(r.url()).pathname)) loaded.add(new URL(r.url()).pathname); });
  const canvas = page.locator('#canvas-wrap canvas');
  const state = () => page.locator('#canvas-wrap').evaluate(el => el.inspectVisitor());
  const position = async () => (await state()).visitor.position;
  const activate = async id => {
    const button = page.locator('#' + id);
    await button.focus();
    await page.keyboard.press('Enter');
  };
  const hold = async (keys, ms) => {
    for (const key of keys) await page.keyboard.down(key);
    try { await page.clock.runFor(ms); }
    finally { for (const key of keys) await page.keyboard.up(key); }
  };
  // Route distances use the real controller speed. Movement goes through its
  // regular keyboard handlers. The test clock only makes the frame count repeatable.
  async function stepTo(x, z) {
    const [ox, , oz] = await position();
    const dx = x - ox, dz = z - oz, keys = [];
    if (Math.abs(dx) > .025) keys.push(dx > 0 ? 'ArrowRight' : 'ArrowLeft');
    if (Math.abs(dz) > .025) keys.push(dz > 0 ? 'ArrowDown' : 'ArrowUp');
    const ms = Math.round(Math.hypot(dx, dz) / .95 * 1000);
    await hold(keys, ms);
    const [px, , pz] = await position();
    assert.ok(Math.hypot(px - x, pz - z) < .07, 'keyboard waypoint ' + JSON.stringify({ x, z, px, pz, keys }));
  }

  await page.clock.install();
  await page.goto(url.href, { waitUntil: 'domcontentloaded' });
  await page.locator('#canvas-status[data-state=ready]').waitFor({ state: 'attached', timeout: 120000 });
  assert.equal((await state()).angle, 0);
  const assemblyDrawCalls = (await state()).drawCalls;
  assert.equal((await state()).visitor, null);
  assert.equal([...loaded].some(path => path.includes('gjh-mall-visitor')), false);
  console.log('Assembly ready; loading visitor');
  await activate('walk');
  await page.waitForFunction(() => document.querySelector('#canvas-wrap').inspectVisitor().visitor?.walking, { }, { timeout: 90000 });
  await page.clock.pauseAt(await page.evaluate(() => Date.now() + 1000));
  assert.equal(await canvas.evaluate(el => el === document.activeElement), true);
  await stepTo(-1.98, 2.08); await stepTo(-1.98, -.09);
  await stepTo(-1.76, -.31); await stepTo(-1.65, -.31);
  await hold(['ArrowUp'], 1100);
  console.log('Reached the closed west entrance');
  const closedStop = (await position())[2];
  assert.ok(closedStop > -.56 && closedStop < -.47, 'shut door stops the body before the threshold: ' + closedStop);
  await activate('reset-visitor');
  await activate('doors');
  assert.equal((await state()).angle, 90);
  await stepTo(-1.98, 2.08); await stepTo(-1.98, -.09);
  await stepTo(-1.76, -.31); await stepTo(-1.65, -.31);
  await stepTo(-1.65, -1.2);
  await activate('doors');
  assert.equal((await state()).angle, 90);
  assert.match(await page.locator('#walk-message').textContent(), /occupied/i);
  await stepTo(-1.65, -2.08);
  console.log('Cleared occupied-door rollback and entered through the west door');
  const west = await position();
  assert.ok(await canvas.evaluate(el => {
    const bounds = el.getBoundingClientRect();
    return bounds.top >= -1 && bounds.bottom <= innerHeight + 1;
  }), 'the whole canvas is in view after operating the door');

  if (shots) await page.screenshot({ path: join(shots, 'west-shop.png') });
  await stepTo(1.65, -2.08);
  const east = await position();
  await stepTo(1.65, -.31); await stepTo(1.76, -.31);
  await stepTo(1.98, -.09); await stepTo(1.98, 2.08); await stepTo(0, 2.08);
  console.log('Returned through the east shop to arrival');
  await activate('doors');
  assert.equal((await state()).angle, 0);
  await page.keyboard.press('Escape');
  assert.equal((await state()).visitor.walking, false);
  await page.locator('[data-module=wallCorner]').focus();
  await page.keyboard.press('Enter');
  await page.waitForFunction(() => document.querySelector('#canvas-wrap').dataset.view === 'wallCorner', { }, { polling: 50 });
  assert.equal(await page.locator('#walk-tools').isVisible(), false);
  await activate('assembly-button');
  await page.waitForFunction(() => document.querySelector('#canvas-wrap').dataset.view === 'assembly', { }, { polling: 50 });
  assert.equal(await page.locator('#walk-tools').isVisible(), true);

  await page.setViewportSize({ width: 390, height: 844 });
  await activate('walk');
  const pad = page.locator('#joystick');
  await pad.evaluate(button => button.scrollIntoView({ block: 'center' }));
  const b = await pad.boundingBox(), client = await page.context().newCDPSession(page);
  await client.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [
    { x: b.x + b.width - 8, y: b.y + b.height / 2, id: 1 },
  ] });
  await page.clock.runFor(400);
  await client.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  const touch = await position();
  assert.ok(touch[0] > .2 && (await state()).visitor.pointer === null);
  await page.clock.runFor(200);
  assert.deepEqual(await position(), touch, 'touch release stops the visitor');
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  assert.ok(loaded.has('/models/gjh-mall-visitor/exports/gjh-mall-visitor.glb'));
  assert.deepEqual(errors, []);
  if (shots) await page.screenshot({ path: join(shots, 'touch-controls.png') });
  await page.close();

  // A visitor asset failure must leave both door and module inspection usable.
  const retry = await browser.newPage();
  const avatar = '**/gjh-mall-visitor.glb';
  await retry.route(avatar, route => route.abort());
  await retry.goto(url.href, { waitUntil: 'domcontentloaded' });
  await retry.locator('#canvas-wrap[data-view=assembly]').waitFor({ timeout: 120000 });
  await retry.locator('#walk').click();
  await retry.getByRole('status').filter({ hasText: 'Unable to load the visitor.' }).waitFor();
  assert.equal(await retry.locator('#walk').isEnabled(), true);
  await retry.locator('#doors').click();
  assert.equal(await retry.locator('#doors').getAttribute('aria-pressed'), 'true');
  await retry.locator('[data-module=wallCorner]').click();
  await retry.locator('#canvas-wrap[data-view=wallCorner]').waitFor();
  await retry.locator('#assembly-button').click();
  await retry.locator('#canvas-wrap[data-view=assembly]').waitFor();
  await retry.unroute(avatar);
  await retry.locator('#walk').click();
  await retry.waitForFunction(() => document.querySelector('#canvas-wrap').inspectVisitor().visitor?.walking);
  await retry.close();
  console.log(JSON.stringify({ visitorAssetRetry: true, assemblyDrawCalls, closedStop, west, east, touch, loadedGlbs: loaded.size, errors }));
} finally {
  await browser.close();
}
