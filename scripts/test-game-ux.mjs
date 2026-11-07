import { pullShot, chargePull, releasePull, setPullRatio } from "./browser-test-utils.mjs";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import { chromium } from "playwright";
import { serveBuild, launchOptions, gameReady, readGame, writeCheckpoint } from "./browser-test-utils.mjs";
import { TABLE, makeRack, groupOf } from "../src/game/table.js";
import { RULES_VERSION } from "../src/game/rules.js";

const external = process.env.B3G_UX_URL;
const server = external ? { url: external, close: async () => {} } : await serveBuild();
const browser = await chromium.launch(launchOptions);
const errors = [];
const digest = (bytes) => crypto.createHash("sha256").update(bytes).digest("hex");
const viewportState = (page) => page.evaluate(() => ({
  x: document.querySelector('#place-x').value,
  z: document.querySelector('#place-z').value,
  phase: JSON.parse(window.render_game_to_text()).phase,
}));
try {
  for (const { width, height, touch } of [
    { width: 390, height: 844, touch: true },
    { width: 1280, height: 800, touch: false },
  ]) {
    const context = await browser.newContext({ viewport: { width, height }, hasTouch: touch, isMobile: touch });
    const page = await context.newPage();
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
    await gameReady(page, server.url);
    const act = (selector) => touch ? page.locator(selector).first().tap() : page.locator(selector).first().click();
    await act('[data-action="new"]');
    await page.waitForFunction(() => document.querySelector('.game-shell').dataset.phase === 'placing');
    await page.waitForFunction(() => !document.querySelector('[data-action="place"]').disabled);
    const canvas = page.locator('#game-viewport canvas');
    await page.locator('#place-x').focus();
    await page.keyboard.press('Escape');
    assert.equal((await readGame(page)).phase, 'placing', 'Escape on a focused input is not captured by the table');
    assert.equal(await page.locator('#game-menu').evaluate((dialog) => dialog.open), false);
    if (!touch && await page.evaluate(() => document.fullscreenEnabled)) {
      await page.locator('#game-viewport').focus();
      await page.keyboard.press('f');
      await page.waitForFunction(() => !!document.fullscreenElement);
      await page.evaluate(() => {
        window.fullscreenEscapePrevented = null;
        window.addEventListener('keydown', (event) => {
          if (event.key === 'Escape') queueMicrotask(() => { window.fullscreenEscapePrevented = event.defaultPrevented; });
        }, { once: true });
      });
      await page.keyboard.press('Escape');
      await page.waitForFunction(() => typeof window.fullscreenEscapePrevented === 'boolean');
      assert.equal(await page.evaluate(() => window.fullscreenEscapePrevented), false, 'fullscreen Escape remains available to the browser');
      assert.equal((await readGame(page)).phase, 'placing', 'fullscreen Escape does not open the pause menu');
      // Headless Chromium does not perform the host-browser fullscreen exit.
      if (await page.evaluate(() => !!document.fullscreenElement)) await page.evaluate(() => document.exitFullscreen());
      await page.waitForFunction(() => !document.fullscreenElement);
    }
    await page.evaluate(() => scrollTo(0, 0));
    const beforeInspection = digest(await canvas.screenshot({path:`/tmp/left-pull-inspect-before-${width}.png`}));
    await act('[data-action="inspect"]');
    assert.equal((await readGame(page)).inspection, true);
    assert.equal(await page.locator('[data-action="place"]').isDisabled(), true);
    assert.equal(await page.locator('#place-x').isDisabled(), true);
    assert.equal(await page.locator('#place-z').isDisabled(), true);
    assert.match(await page.locator('#placement-hint').innerText(), /return to placement/i);
    assert.match(await page.locator('#game-status').innerText(), /inspect mode.*return to placement/i);
    assert.equal(await page.locator('[data-action="inspect"]').innerText(), 'Return to placement');
    assert.match(await page.locator('#game-viewport').getAttribute('aria-label'), /arrow keys to orbit/i);
    const beforeInput = await viewportState(page);
    await page.locator('#game-viewport').focus();
    const inspectBefore = digest(await canvas.screenshot());
    await page.keyboard.press('ArrowRight');
    await page.waitForTimeout(100);
    const rotated = digest(await canvas.screenshot());
    assert.notEqual(rotated, inspectBefore, 'keyboard arrow orbits inspection camera');
    await page.keyboard.press('+');
    await page.waitForTimeout(100);
    assert.notEqual(digest(await canvas.screenshot()), rotated, 'keyboard plus zooms inspection camera');
    if (touch) {
      const beforePinch = digest(await canvas.screenshot());
      const box = await canvas.boundingBox();
      const x = box.x + box.width / 2, y = box.y + box.height / 2;
      const cdp = await context.newCDPSession(page);
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: x - 25, y, id: 1 }] });
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: x - 25, y, id: 1 }, { x: x + 25, y, id: 2 }] });
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: x - 55, y, id: 1 }, { x: x + 55, y, id: 2 }] });
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
      await page.waitForTimeout(150);
      assert.notEqual(digest(await canvas.screenshot()), beforePinch, 'touch pinch remains available in inspection');
      await cdp.detach();
    }
    await page.keyboard.press('Enter');
    assert.deepEqual(await viewportState(page), beforeInput, 'inspection keys do not move or confirm cue placement');
    assert.equal(await page.locator('#game-viewport').evaluate((el) => el.dispatchEvent(new KeyboardEvent('keydown', { key: '+', ctrlKey: true, bubbles: true, cancelable: true }))), true, 'browser zoom shortcut is not intercepted');
    await page.keyboard.press('Escape');
    await page.locator('#game-menu').waitFor({ state: 'visible' });
    assert.equal((await readGame(page)).phase, 'paused');
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => !document.querySelector('#game-menu').open);
    assert.equal((await readGame(page)).phase, 'placing', 'a second Escape resumes through the dialog');
    assert.equal((await readGame(page)).inspection, true, 'pause/resume retains explicit inspect mode');
    assert.equal(await page.locator('[data-action="place"]').isDisabled(), true);
    await act('[data-action="inspect"]');
    assert.equal((await readGame(page)).inspection, false);
    assert.equal(await page.locator('[data-action="place"]').isEnabled(), true);
    await page.evaluate(() => scrollTo(0, 0));
    assert.equal(digest(await canvas.screenshot({path:`/tmp/left-pull-inspect-after-${width}.png`})), beforeInspection, 'return to aim resets camera rotation and zoom');
    await act('[data-action="place"]');
    await page.waitForFunction(() => !document.querySelector('#power-handle').disabled);
    await act('[data-action="inspect"]');
    assert.equal(await page.locator('#power-handle').isDisabled(), true);
    assert.equal(await page.locator('[data-action="inspect"]').innerText(), 'Return to aim');
    assert.match(await page.locator('.control-note').innerText(), /return to aim before shooting/i);
    await page.locator('#game-viewport').focus();
    const aiming = await readGame(page);
    await page.keyboard.press('Space');
    assert.deepEqual((await readGame(page)).balls, aiming.balls);
    assert.equal((await readGame(page)).phase, 'aiming');
    await act('[data-action="pause"]');
    await page.locator('#game-menu').waitFor({ state: 'visible' });
    await act('[data-action="continue"]');
    assert.equal((await readGame(page)).inspection, true);
    assert.equal(await page.locator('#power-handle').isDisabled(), true);
    await act('[data-action="inspect"]');
    assert.equal(await page.locator('#power-handle').isEnabled(), true);
    await pullShot(page);
    await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase === 'moving');
    assert.equal(await page.locator('[data-action="inspect"]').isDisabled(), true, 'inspection cannot interrupt a moving shot');
    await page.evaluate(() => window.advanceTime(26000));
    await page.waitForFunction(() => !['moving', 'adjudicating'].includes(JSON.parse(window.render_game_to_text()).phase), null, { timeout: 30000 });
    console.log(`PASS ${width}×${height}: inspection placement, keyboard orbit/zoom, pause, return and shooting`);
    await context.close();
  }
  {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
    const page = await context.newPage();
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto(server.url);
    await page.waitForSelector('#catalog .asset-card');
    const match = { schema: 1, rulesVersion: RULES_VERSION, tableVersion: TABLE.version,
      matchId: 'finished-inspection-fixture', revision: 9, phase: 'finished', player: 0,
      groups: ['solids', 'stripes'], break: false, ballInHand: false, winner: 0, balls: makeRack(42) };
    for (const ball of match.balls) if (groupOf(ball.id) === 'solids' || ball.id === 8) ball.pocketed = true;
    await writeCheckpoint(page, match);
    await gameReady(page, server.url);
    await page.locator('[data-action="resume"]').tap();
    await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase === 'finished');
    await page.locator('[data-action="inspect"]').tap();
    assert.equal(await page.locator('[data-action="inspect"]').innerText(), 'Return to table');
    assert.match(await page.locator('#game-viewport').getAttribute('aria-label'), /Return to table/);
    await page.locator('[data-action="inspect"]').tap();
    assert.equal((await readGame(page)).phase, 'finished');
    assert.equal((await readGame(page)).winner, 0);
    console.log('PASS finished-match inspection returns to table without altering the winner');
    await context.close();
  }
  for (const [width, height] of [[320, 568], [390, 844], [844, 390]]) {
    const context = await browser.newContext({ viewport: { width, height }, hasTouch: true, isMobile: true });
    const page = await context.newPage();
    page.on('pageerror', (e) => errors.push(e.message));
    await gameReady(page, server.url);
    await page.evaluate(() => {
      for (const [edge, value] of Object.entries({ top: 20, right: 12, bottom: 24, left: 12 }))
        document.documentElement.style.setProperty(`--safe-${edge}`, `${value}px`);
    });
    await page.locator('[data-action="new"]').first().tap();
    await page.waitForFunction(() => !document.querySelector('[data-action="place"]').disabled);
    await page.locator('[data-action="inspect"]').tap();
    const caption = await page.evaluate(() => {
      const parent = document.querySelector('.game-table-caption').getBoundingClientRect();
      const children = ['inspect', 'options'].map((action) => {
        const el = document.querySelector(`[data-action="${action}"]`), r = el.getBoundingClientRect();
        return { left:r.left, right:r.right, width:r.width, height:r.height, textFits:el.scrollHeight <= el.clientHeight + 1 };
      });
      return { left:parent.left, right:parent.right, children, overflow:document.documentElement.scrollWidth > innerWidth };
    });
    assert.equal(caption.overflow, false, 'inspection caption does not cause document overflow');
    for (const item of caption.children) {
      assert.ok(item.width >= 44 && item.height >= 44 && item.textFits && item.left >= caption.left - 1 && item.right <= caption.right + 1, `caption controls remain usable: ${JSON.stringify(caption)}`);
    }
    assert.ok(caption.children[0].right <= caption.children[1].left + 1, 'inspection and app options do not overlap');
    await page.locator('[data-action="inspect"]').tap();
    const canvas = page.locator('#game-viewport canvas');
    await canvas.scrollIntoViewIfNeeded();
    const box = await canvas.boundingBox();
    const geometry = (rect) => {
      const aspect = rect.width / rect.height, portrait = aspect < 1;
      // Independently mirror the documented full-table envelope and top-down orientation.
      const worldHeight = portrait ? Math.max(2.82, 1.62 / aspect) : Math.max(1.62, 2.82 / aspect);
      const scale = rect.height / worldHeight;
      return {
        tableWidth: (portrait ? 1.40 : 2.54) * scale,
        tableHeight: (portrait ? 2.54 : 1.40) * scale,
        point: (x, z) => ({
          x: rect.x + rect.width / 2 + (portrait ? z : x) * scale,
          y: rect.y + rect.height / 2 + (portrait ? -x : z) * scale,
        }),
      };
    };
    const { tableWidth, tableHeight, point } = geometry(box);
    assert.ok(tableWidth <= box.width + 1 && tableHeight <= box.height + 1, 'full authored table fits in the canvas');
    const placement = point(-0.8, 0.2);
    const origin = point(-0.7, 0), cdpPlacement = await context.newCDPSession(page);
    await cdpPlacement.send('Input.dispatchTouchEvent', {type:'touchStart',touchPoints:[{x:origin.x,y:origin.y,id:1}]});
    await cdpPlacement.send('Input.dispatchTouchEvent', {type:'touchMove',touchPoints:[{x:placement.x,y:placement.y,id:1}]});
    await cdpPlacement.send('Input.dispatchTouchEvent', {type:'touchEnd',touchPoints:[]});
    await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase === 'aiming');
    const selected = await viewportState(page);
    assert.ok(Math.abs(Number(selected.x) + 0.8) < 0.015 && Math.abs(Number(selected.z) - 0.2) < 0.015,
      `touch placement maps to table coordinates: ${JSON.stringify(selected)}`);
    assert.equal(selected.phase, 'aiming', 'valid whiteball drag commits placement without shooting');
    await page.waitForFunction(() => !document.querySelector('#power-handle').disabled);
    await canvas.scrollIntoViewIfNeeded();
    const nextBox = await canvas.boundingBox();
    const aim = geometry(nextBox).point(0.3, -0.1);
    const aimStart = geometry(nextBox).point(0.1, -0.1);
    const beforeAim = await readGame(page);
    await page.touchscreen.tap(aim.x, aim.y);
    assert.equal((await readGame(page)).aim, beforeAim.aim, 'a plain tap does not change aim');
    assert.equal(await page.evaluate(({x,y}) => document.elementFromPoint(x,y)?.tagName, aimStart), 'CANVAS', 'touch drag starts on the table');
    await cdpPlacement.send('Input.dispatchTouchEvent', {type:'touchStart',touchPoints:[{x:aimStart.x,y:aimStart.y,id:2}]});
    await cdpPlacement.send('Input.dispatchTouchEvent', {type:'touchMove',touchPoints:[{x:aim.x,y:aim.y,id:2}]});
    await cdpPlacement.send('Input.dispatchTouchEvent', {type:'touchEnd',touchPoints:[]});
    const state = await readGame(page);
    assert.equal(state.phase, 'aiming', 'aiming does not shoot');
    assert.equal(state.committedShots, beforeAim.committedShots, 'touch aiming does not commit a shot');
    assert.ok(Math.abs(state.aim - Math.atan2(-0.3, 1.1)) < 0.03, `touch drag aims from the cue ball toward the selected felt point: ${state.aim}`);
    const left = page.locator('[data-action="aim-left"]'), right = page.locator('[data-action="aim-right"]');
    assert.equal(await left.isVisible(), true, 'fine aim is visible during touch play');
    for (const button of [left, right]) {
      const target = await button.boundingBox();
      assert.ok(target.width >= 44 && target.height >= 44, 'fine-aim touch targets are at least 44px');
    }
    await left.tap();
    assert.ok(Math.abs((await readGame(page)).aim - state.aim + Math.PI / 180) < 1e-7, 'fine left adjusts aim by one degree');
    await right.tap();
    assert.ok(Math.abs((await readGame(page)).aim - state.aim) < 1e-7, 'fine right returns to the previous aim');
    console.log(`PASS ${width}×${height}: table fits ${Math.round(box.width)}×${Math.round(box.height)}, projected ${Math.round(tableWidth)}×${Math.round(tableHeight)}; touch placement and aim map correctly`);
    await context.close();
  }
  {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
    const page = await context.newPage();
    page.on('pageerror', (e) => errors.push(e.message));
    await gameReady(page, server.url);
    await page.locator('[data-action="new"]').first().tap();
    await page.waitForFunction(() => !document.querySelector('[data-action="place"]').disabled);
    await page.locator('[data-action="inspect"]').tap();
    await page.locator('[data-action="pause"]').tap();
    await page.locator('#game-menu').waitFor({ state: 'visible' });
    await page.evaluate(() => document.querySelector('#game-viewport canvas').getContext('webgl2').getExtension('WEBGL_lose_context').loseContext());
    await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).contextLost);
    assert.equal(await page.locator('#game-menu').evaluate((dialog) => dialog.open), false);
    assert.equal(await page.locator('[data-action="inspect"]').isDisabled(), true);
    assert.match(await page.locator('#game-status').innerText(), /3D view interrupted/i);
    await page.locator('[data-action="restore"]').tap();
    await page.waitForFunction(() => window.render_game_to_text && JSON.parse(window.render_game_to_text()).ready && !JSON.parse(window.render_game_to_text()).contextLost, null, { timeout: 60000 });
    assert.equal(await page.locator('[data-action="resume"]').isEnabled(), true);
    console.log('PASS context loss while inspecting and paused offers saved-game recovery');
    await context.close();
  }
  assert.deepEqual(errors, []);
} finally {
  await browser.close();
  await server.close();
}
