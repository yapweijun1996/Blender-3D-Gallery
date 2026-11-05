import assert from "node:assert/strict";
import crypto from "node:crypto";
import { chromium } from "playwright";
import { serveBuild, launchOptions, gameReady, readGame } from "./browser-test-utils.mjs";

const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const errors = [];
const track = (page) => page.on("pageerror", (error) => errors.push(error.message));
const hash = (bytes) => crypto.createHash("sha256").update(bytes).digest("hex");
try {
  {
    const context = await browser.newContext();
    await context.addInitScript(() => Object.defineProperty(navigator, "locks", { configurable: true, value: undefined }));
    const a = await context.newPage(); track(a);
    await gameReady(a, server.url);
    await a.locator('[data-action="new"]').first().click();
    await a.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase === "placing");
    const b = await context.newPage(); track(b);
    await b.addInitScript(() => { const now = Date.now.bind(Date); Date.now = () => now() + 60000; });
    await gameReady(b, server.url);
    await b.waitForFunction(() => JSON.parse(window.render_game_to_text()).ownership);
    await b.locator('[data-action="resume"]').click();
    await b.locator('#place-x').evaluate((el) => { el.value = '-0.901'; el.dispatchEvent(new Event('input', { bubbles: true })); });
    await b.locator('[data-action="place"]').click();
    await b.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase === "aiming");
    const latest = await readGame(b);
    await a.bringToFront();
    await a.waitForFunction(() => !JSON.parse(window.render_game_to_text()).ownership, null, { timeout: 15000 });
    assert.equal(await a.locator('[data-action="continue"]').isDisabled(), true);
    await b.close();
    await a.evaluate(() => { const now = Date.now.bind(Date); Date.now = () => now() + 90000; });
    await a.bringToFront();
    await a.waitForFunction(() => JSON.parse(window.render_game_to_text()).ownership, null, { timeout: 15000 });
    const reclaimed = await readGame(a);
    assert.equal(reclaimed.phase, "paused");
    assert.equal(reclaimed.balls[0].x, latest.balls[0].x);
    await a.locator('[data-action="continue"]').click();
    assert.equal((await readGame(a)).phase, "aiming");
    await a.locator('[data-action="shoot"]').click();
    await a.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase === "moving");
    const checkpoint = await a.evaluate(() => new Promise((resolve, reject) => {
      const db = indexedDB.open("blender-gallery-game-v1");
      db.onerror = () => reject(db.error);
      db.onsuccess = () => { const request = db.result.transaction("records").objectStore("records").get("match"); request.onsuccess = () => { resolve(request.result.checkpoint); db.result.close(); }; request.onerror = () => reject(request.error); };
    }));
    assert.equal(checkpoint.balls[0].x, latest.balls[0].x);
    await context.close();
    console.log("PASS reclaimed lease restores latest checkpoint before gameplay and save");
  }
  {
    const context = await browser.newContext();
    await context.addInitScript(() => Object.defineProperty(navigator, "locks", { configurable: true, value: undefined }));
    const a = await context.newPage(); track(a);
    await gameReady(a, server.url);
    await a.locator('[data-action="new"]').first().click();
    await a.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase === "placing");
    await a.evaluate(() => {
      window.originalTransaction = IDBDatabase.prototype.transaction;
      IDBDatabase.prototype.transaction = function (...args) {
        if (this.name === "blender-gallery-game-v1" && args[1] === "readwrite") throw new Error("Injected local save failure");
        return window.originalTransaction.apply(this, args);
      };
    });
    await a.locator('[data-action="place"]').click();
    await a.waitForFunction(() => JSON.parse(window.render_game_to_text()).saveFailed);
    await a.evaluate(() => { IDBDatabase.prototype.transaction = window.originalTransaction; });
    const b = await context.newPage(); track(b);
    await b.addInitScript(() => { const now = Date.now.bind(Date); Date.now = () => now() + 60000; });
    await gameReady(b, server.url);
    await b.locator('[data-action="resume"]').click();
    await b.locator('#place-x').evaluate((el) => { el.value = '-0.901'; el.dispatchEvent(new Event('input', { bubbles: true })); });
    await b.locator('[data-action="place"]').click();
    await b.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase === "aiming");
    await a.bringToFront();
    await a.waitForFunction(() => !JSON.parse(window.render_game_to_text()).ownership, null, { timeout: 15000 });
    await b.close();
    await a.evaluate(() => { const now = Date.now.bind(Date); Date.now = () => now() + 90000; });
    await a.waitForFunction(() => document.querySelector('#menu-save-message').textContent.includes('conflicts'), null, { timeout: 15000 });
    assert.equal(await a.locator('[data-action="continue"]').isDisabled(), true);
    assert.equal(await a.locator('[data-action="restart"]').isDisabled(), true);
    assert.equal(await a.locator('[data-action="discard"]').isVisible(), true);
    await a.locator('[data-action="leave"]').click();
    assert.match(await a.locator('#menu-save-message').innerText(), /conflicts.*leave without saving or reload/i);
    const state = await readGame(a);
    assert.equal(state.saveFailed, true);
    assert.equal(state.balls[0].x, -0.7, "unsaved local state is retained for an explicit decision");
    const cue = await a.evaluate(() => new Promise((resolve) => {
      const db = indexedDB.open("blender-gallery-game-v1");
      db.onsuccess = () => { const r = db.result.transaction("records").objectStore("records").get("match"); r.onsuccess = () => { resolve(r.result.checkpoint.balls[0].x); db.result.close(); }; };
    }));
    assert.equal(cue, -0.901, "newer shared checkpoint is not overwritten");
    await context.close();
    console.log("PASS conflicting unsaved local turn remains protected without overwriting shared checkpoint");
  }
  {
    const context = await browser.newContext();
    await context.addInitScript(() => Object.defineProperty(navigator, "locks", { configurable: true, value: undefined }));
    const a = await context.newPage(); track(a);
    await gameReady(a, server.url);
    await a.locator('[data-action="new"]').first().click();
    await a.locator('[data-action="place"]').click();
    await a.waitForFunction(() => !document.querySelector('[data-action="shoot"]').disabled);
    await a.locator('[data-action="shoot"]').click();
    await a.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase === "moving");
    await a.evaluate(() => {
      const descriptor = Object.getOwnPropertyDescriptor(IDBTransaction.prototype, "oncomplete");
      Object.defineProperty(IDBTransaction.prototype, "oncomplete", {
        ...descriptor,
        set(callback) {
          descriptor.set.call(this, callback && function (event) {
            if (!window.holdCompletion) return callback.call(this, event);
            window.holdCompletion = false;
            window.completionHeld = true;
            window.releaseCompletion = () => callback.call(this, event);
          });
        },
      });
      window.holdCompletion = true;
      window.advanceTime(26000);
    });
    await a.waitForFunction(() => window.completionHeld, null, { timeout: 15000 });
    const b = await context.newPage(); track(b);
    await b.addInitScript(() => { const now = Date.now.bind(Date); Date.now = () => now() + 60000; });
    await gameReady(b, server.url);
    await b.locator('[data-action="new"]').first().click();
    await b.locator('[data-action="confirm-new"]').click();
    await b.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase === "placing");
    await b.waitForFunction(() => !document.querySelector('[data-action="place"]').disabled);
    const newest = await readGame(b);
    await a.bringToFront();
    await b.close();
    await a.evaluate(() => { const now = Date.now.bind(Date); Date.now = () => now() + 90000; });
    await a.waitForTimeout(11000);
    assert.equal((await readGame(a)).phase, "adjudicating", "reconciliation waits for the pending transition");
    await a.evaluate(() => window.releaseCompletion());
    await a.waitForFunction(() => {
      const game = JSON.parse(window.render_game_to_text());
      return game.phase === "paused" && game.ownership && game.revision === 0 && game.balls[0].pocketed;
    }, null, { timeout: 20000 });
    assert.deepEqual((await readGame(a)).balls, newest.balls);
    await context.close();
    console.log("PASS delayed shot save settles before ownership reconciliation");
  }
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await context.newPage(); track(page);
    await page.goto(server.url + "?model=pool-table");
    await page.waitForFunction(() => document.querySelector("#viewport canvas") && document.querySelector("#viewer-status").textContent === "", null, { timeout: 60000 });
    const canvas = page.locator("#viewport canvas");
    assert.equal(await canvas.getAttribute("tabindex"), "0");
    await page.locator("#close-viewer").focus();
    await page.keyboard.press("Tab");
    assert.equal(await canvas.evaluate((el) => document.activeElement === el), true);
    assert.deepEqual(await canvas.evaluate((el) => {
      const style = getComputedStyle(el);
      return { width: style.outlineWidth, style: style.outlineStyle, offset: style.outlineOffset };
    }), { width: "2px", style: "solid", offset: "-4px" }, "keyboard focus indicator remains inside the viewer");
    assert.equal(await canvas.evaluate((el) => el.dispatchEvent(new KeyboardEvent("keydown", { key: "+", ctrlKey: true, bubbles: true, cancelable: true }))), true, "browser zoom shortcut is not intercepted");
    const original = hash(await canvas.screenshot());
    await page.keyboard.press("ArrowRight"); await page.waitForTimeout(500);
    const rotated = hash(await canvas.screenshot());
    assert.notEqual(rotated, original, "keyboard orbit changes the rendered view");
    await page.keyboard.press("+"); await page.waitForTimeout(500);
    assert.notEqual(hash(await canvas.screenshot()), rotated, "keyboard zoom changes the rendered view");
    await page.keyboard.press("Escape");
    assert.equal(await page.locator("#viewer").evaluate((d) => d.open), false);
    await context.close();
    console.log("PASS model viewer keyboard orbit, zoom and Escape");
  }
  {
    const context = await browser.newContext();
    let failed = 0;
    server.setFault(({ relative }) => relative === "build-info.json" ? (failed++, { status: 503 }) : null);
    const page = await context.newPage(); track(page);
    await gameReady(page, server.url);
    await page.waitForFunction(() => document.querySelector("#game-offline-status")?.textContent.includes("unavailable"), null, { timeout: 20000 });
    assert.ok(failed > 0);
    server.setFault(null);
    await page.locator('[data-action="options"]').click();
    await page.locator('[data-action="offline"]').click();
    await page.waitForFunction(() => document.querySelector("#game-offline-status")?.textContent.includes("Offline ready"), null, { timeout: 90000 });
    assert.ok(await page.evaluate(async () => !!(await navigator.serviceWorker.getRegistration())?.active));
    await context.close();
    console.log("PASS failed first worker installation retries offline preparation without reload");
  }
  for (const fallback of [false, true]) {
    const context = await browser.newContext();
    if (fallback) await context.addInitScript(() => Object.defineProperty(window, "BroadcastChannel", { configurable: true, value: undefined }));
    const game = await context.newPage(); track(game);
    await gameReady(game, server.url);
    await game.evaluate(() => navigator.serviceWorker.ready);
    await game.reload();
    await game.waitForFunction(() => navigator.serviceWorker.controller && window.render_game_to_text && JSON.parse(window.render_game_to_text()).ready);
    const index = await context.newPage(); track(index);
    await index.goto(server.url + "?page=demos");
    await index.locator(".demo-offline-status").first().waitFor();
    await game.locator('[data-action="options"]').click();
    await game.locator('[data-action="offline"]').click();
    await game.waitForFunction(() => document.querySelector("#game-offline-status")?.textContent.includes("Offline ready"), null, { timeout: 90000 });
    await index.waitForFunction(() => document.querySelector('.demo-offline-status')?.textContent.includes('Offline ready'), null, { timeout: 15000 });
    await context.close();
    console.log(`PASS completed offline pack refreshes another tab after verification (${fallback ? "storage fallback" : "BroadcastChannel"})`);
  }
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await context.newPage(); track(page);
    await page.goto(server.url + "?page=solar");
    await page.waitForFunction(() => document.querySelector("#solar-status")?.textContent === "", null, { timeout: 60000 });
    for (const method of ["button", "selector"]) {
      await page.selectOption("#solar-select", "earth");
      assert.equal(await page.locator("#solar-name").innerText(), "Earth");
      if (method === "button") await page.locator("#solar-overview").click();
      else await page.selectOption("#solar-select", "");
      assert.equal(await page.locator("#solar-name").innerText(), "Our planetary neighborhood");
      assert.equal(await page.locator("#solar-model-link").isHidden(), true);
    }
    await context.close();
    console.log("PASS solar overview and clear selector restore general information");
  }
  assert.deepEqual(errors, []);
} finally {
  server.setFault(null);
  await browser.close();
  await server.close();
}
