import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { chromium, webkit } from "playwright";
import {
  serveBuild,
  launchOptions,
  gameReady,
  readGame,
  writeCheckpoint,
} from "./browser-test-utils.mjs";
import { makeRack, TABLE, groupOf } from "../src/game/table.js";
import { RULES_VERSION } from "../src/game/rules.js";

const server = await serveBuild(),
  artifacts = process.env.TEST_ARTIFACT_DIR || "/tmp/blender-gallery-game-qa",
  qualityArtifacts = path.join(artifacts, "quality");
await fs.mkdir(artifacts, { recursive: true });
await fs.mkdir(qualityArtifacts, { recursive: true });
const browser = await chromium.launch(launchOptions),
  results = [],
  errors = [];
const run = async (name, fn, options = {}) => {
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    ...options,
  });
  const page = await context.newPage();
  page.on("pageerror", (e) => errors.push(name + ": " + e.message));
  try {
    await fn(page, context);
    results.push({ name, passed: true });
    console.log("PASS", name);
  } catch (e) {
    await page
      .screenshot({ path: path.join(artifacts, "failure.png") })
      .catch(() => {});
    console.error(
      "FAILED",
      name,
      await page
        .evaluate(() => window.render_game_to_text?.())
        .catch(() => null),
    );
    throw e;
  } finally {
    await context.close();
  }
};
const waitPhase = (page, phase) =>
  page.waitForFunction(
    (phase) => JSON.parse(window.render_game_to_text()).phase === phase,
    phase,
  );
const start = async (page) => {
  await page.click("[data-action=new]");
  await waitPhase(page, "placing");
  await page.click("[data-action=place]");
  await waitPhase(page, "aiming");
  await page.waitForFunction(() => {
    const shoot = document.querySelector('[data-action="shoot"]');
    return shoot && shoot.getClientRects().length > 0 && !shoot.disabled;
  });
};
// On short phones retain a playable table and check both controls before clicks
// can auto-scroll them; the user may make one bounded, explicit page scroll.
const revealShortScreen = async (page, width, height, actions) => {
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  if (width <= 650 && height <= 650) {
    await page.evaluate((actions) => {
      const selectors = ["#game-viewport", ...actions.map((action) => `[data-action="${action}"]`)];
      const bottom = Math.max(...selectors.map((selector) => document.querySelector(selector).getBoundingClientRect().bottom));
      window.scrollBy({ top: Math.max(0, bottom - innerHeight + 8), behavior: "instant" });
    }, actions);
    assert.ok(await page.evaluate(() => scrollY) <= height / 2, "controls and table require at most half a screen of scrolling");
  }
};
// Follow the visible navigation rather than the retired per-demo top-level links.
const navigateTo = async (page, destination) => {
  const section = destination === "game" ? "demos" : destination;
  const desktopLink = page.locator(`.desktop-nav [data-page="${section}"]`);
  if (await desktopLink.isVisible()) await desktopLink.click();
  else {
    await page.locator("#menu-trigger").click();
    await page.locator(`#mobile-menu [data-page="${section}"]`).click();
  }
  if (destination === "game") {
    await page.locator('#demos-page .demo-card a[data-page="game"]').first().click();
  }
};
const setRange = (page, id, value) =>
  page.locator(id).evaluate((el, value) => {
    el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
  }, String(value));
const delayTransactionCompletion = () => {
  window.__hiddenForTest = false;
  Object.defineProperty(document, "hidden", { configurable: true, get: () => window.__hiddenForTest });
  const descriptor = Object.getOwnPropertyDescriptor(IDBTransaction.prototype, "oncomplete");
  Object.defineProperty(IDBTransaction.prototype, "oncomplete", {
    ...descriptor,
    set(callback) {
      descriptor.set.call(this, callback && function (event) {
        if (!window.__delaySave) return callback.call(this, event);
        if (window.__skipCompletions > 0) {
          window.__skipCompletions--;
          return callback.call(this, event);
        }
        window.__delaySave = false;
        window.__saveDelayed = true;
        setTimeout(() => callback.call(this, event), 650);
      });
    },
  });
};
const holdGameTableResponse = async page => {
  const pattern = /\/table-[^/]+\.glb(?:\?.*)?$/;
  let release, markRequested, markFinished;
  const gate = new Promise(resolve => { release = resolve; });
  const requested = new Promise(resolve => { markRequested = resolve; });
  const finished = new Promise(resolve => { markFinished = resolve; });
  await page.route(pattern, async route => {
    try {
      const response = await route.fetch();
      if (!response.ok()) throw new Error(`Table request failed: ${response.status()}`);
      markRequested();
      await gate;
      await route.fulfill({response});
      markFinished(null);
    } catch (error) {
      markFinished(error.message);
    }
  });
  return { requested, finished, release, remove: () => page.unroute(pattern) };
};
const withDeadline = async (promise, label) => {
  let timer;
  try {
    return await Promise.race([promise, new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error(`Timed out: ${label}`)), 10000);
    })]);
  } finally {
    clearTimeout(timer);
  }
};
try {
  await run("gameplay keyboard shortcuts require table focus", async (page, context) => {
    await context.addInitScript(() => {
      const transaction = IDBDatabase.prototype.transaction;
      IDBDatabase.prototype.transaction = function (...args) {
        if (this.name === "blender-gallery-game-v1" && window.__trackGameTransactions)
          window.__gameTransactionCount++;
        return transaction.apply(this, args);
      };
    });
    await gameReady(page, server.url);
    await start(page);
    await page.waitForFunction(() => !document.querySelector('[data-action="shoot"]').disabled);
    await page.locator("#game-title").click();
    const initial = await readGame(page);
    await page.evaluate(() => { window.__gameTransactionCount = 0; window.__trackGameTransactions = true; });
    await page.keyboard.press("Space");
    const transactions = await page.evaluate(() => {
      window.__trackGameTransactions = false;
      return window.__gameTransactionCount;
    });
    assert.equal(transactions, 0, "Space outside the table must not start a save or ownership renewal");
    await page.evaluate(() => new Promise((resolve, reject) => {
      const request = indexedDB.open("blender-gallery-game-v1", 1);
      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        const db = request.result, tx = db.transaction("records", "readwrite");
        tx.oncomplete = () => { db.close(); resolve(); };
        tx.onerror = () => reject(tx.error);
      };
    }));
    const outside = await readGame(page);
    assert.equal(outside.phase, "aiming");
    assert.equal(outside.revision, initial.revision);
    assert.deepEqual(outside.balls, initial.balls);
    await page.locator("#game-viewport").focus();
    const before = await readGame(page);
    await page.keyboard.press("ArrowLeft");
    assert.notEqual((await readGame(page)).aim, before.aim);
    await page.evaluate(() => { window.__gameTransactionCount = 0; window.__trackGameTransactions = true; });
    await page.keyboard.press("Space");
    await waitPhase(page, "moving");
    assert.ok(await page.evaluate(() => window.__gameTransactionCount) >= 2, "focused Space renews ownership and saves the pending shot");
  });
  await run("backgrounding during shot startup cancels the impulse after the save", async (page, context) => {
    await context.addInitScript(delayTransactionCompletion);
    await gameReady(page, server.url);
    await start(page);
    await page.waitForFunction(() => !document.querySelector('[data-action="shoot"]').disabled);
    await page.evaluate(() => {
      window.__delaySave = true;
      document.querySelector('[data-action="shoot"]').click();
      window.__hiddenForTest = true;
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await page.waitForFunction(() => window.__saveDelayed);
    await waitPhase(page, "paused");
    const paused = await readGame(page);
    await page.evaluate(() => {
      window.__hiddenForTest = false;
      document.dispatchEvent(new Event("visibilitychange"));
      window.advanceTime(1000);
    });
    assert.deepEqual((await readGame(page)).balls, paused.balls);
    assert.equal(await page.locator("#game-menu").isVisible(), true);
    await page.click('[data-action="continue"]');
    await waitPhase(page, "aiming");
    assert.deepEqual((await readGame(page)).balls, paused.balls, "resume does not fire a canceled shot");
    await page.click('[data-action="shoot"]');
    await waitPhase(page, "moving");
  });
  for (const stage of ["renew", "checkpoint", "adjudication"]) {
    await run(`WebGL loss during ${stage} cannot continue the shot`, async (page, context) => {
      await context.addInitScript(delayTransactionCompletion);
      await gameReady(page, server.url);
      await start(page);
      await page.waitForFunction(() => !document.querySelector('[data-action="shoot"]').disabled);
      if (stage === "adjudication") {
        await page.click('[data-action="shoot"]');
        await waitPhase(page, "moving");
      }
      await page.evaluate(stage => {
        window.__delaySave = true;
        window.__skipCompletions = stage === "checkpoint" ? 1 : 0;
        if (stage === "adjudication") window.advanceTime(26000);
        else document.querySelector('[data-action="shoot"]').click();
      }, stage);
      await page.waitForFunction(() => window.__saveDelayed);
      await page.evaluate(() => document.querySelector('#game-viewport canvas').getContext('webgl2').getExtension('WEBGL_lose_context').loseContext());
      await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).contextLost);
      await page.waitForTimeout(800);
      const lost = await readGame(page);
      assert.equal(lost.phase, 'recovery');
      assert.equal(await page.locator('[data-action="shoot"]').isVisible(), false);
      await page.click('[data-action="restore"]');
      await page.waitForFunction(() => window.render_game_to_text && JSON.parse(window.render_game_to_text()).ready && !JSON.parse(window.render_game_to_text()).contextLost);
      await page.click('[data-action="resume"]');
      assert.deepEqual((await readGame(page)).balls, lost.balls);
    });
  }
  await run("WebGL loss closes blocking game dialogs and exposes recovery", async page => {
    await gameReady(page, server.url);
    await start(page);
    for (const dialog of ['pause', 'restart', 'rules', 'options']) {
      if (dialog === 'pause' || dialog === 'restart') {
        await page.click('[data-action="pause"]');
        if (dialog === 'restart') await page.click('[data-action="restart"]');
      } else await page.click(`[data-action="${dialog}"]`);
      await page.evaluate(() => document.querySelector('#game-viewport canvas').getContext('webgl2').getExtension('WEBGL_lose_context').loseContext());
      await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).contextLost);
      assert.equal(await page.locator('#game-page dialog[open]').count(), 0);
      assert.equal((await readGame(page)).phase, 'recovery');
      await page.click('[data-action="restore"]');
      await page.waitForFunction(() => window.render_game_to_text && JSON.parse(window.render_game_to_text()).ready && !JSON.parse(window.render_game_to_text()).contextLost);
      await page.click('[data-action="resume"]');
      await page.waitForFunction(() => document.querySelector('.game-shell').dataset.phase === 'aiming');
    }
  });
  for (const operation of ["new", "place", "adjudication"]) {
    await run(`backgrounding while ${operation} is saving preserves the pause`, async (page, context) => {
      await context.addInitScript(delayTransactionCompletion);
      await gameReady(page, server.url);
      if (operation !== "new") {
        await page.click('[data-action="new"]');
        await page.waitForFunction(() => document.querySelector('.game-shell').dataset.phase === 'placing');
        // The placing phase is visible while the new-match checkpoint is still saving.
        await page.locator('[data-action="place"]').waitFor({ state: "visible" });
        await page.waitForFunction(() => !document.querySelector('[data-action="place"]').disabled);
      }
      if (operation === "adjudication") {
        await page.click('[data-action="place"]');
        await page.waitForFunction(() => !document.querySelector('[data-action="shoot"]').disabled);
        await page.click('[data-action="shoot"]');
        await waitPhase(page, "moving");
      }
      await page.evaluate(operation => {
        window.__delaySave = true;
        if (operation === "adjudication") window.advanceTime(26000);
        else document.querySelector(`[data-action="${operation}"]`).click();
        if (operation === "place" && JSON.parse(window.render_game_to_text()).phase !== "aiming")
          throw new Error("Placement did not start before backgrounding");
        window.__hiddenForTest = true;
        document.dispatchEvent(new Event("visibilitychange"));
      }, operation);
      await page.waitForFunction(() => window.__saveDelayed);
      await waitPhase(page, "paused");
      await page.evaluate(() => { window.__hiddenForTest = false; document.dispatchEvent(new Event("visibilitychange")); });
      assert.equal(await page.locator('#game-menu').isVisible(), true);
      await page.click('[data-action="continue"]');
      const next = (await readGame(page)).phase;
      assert.ok(operation === "new" ? next === "placing" : operation === "place" ? next === "aiming" : ["aiming", "placing"].includes(next), next);
    });
  }
  await run("leaving during a pending hidden shot cannot open a stale dialog", async (page, context) => {
    await context.addInitScript(delayTransactionCompletion);
    await gameReady(page, server.url);
    await start(page);
    await page.waitForFunction(() => !document.querySelector('[data-action="shoot"]').disabled);
    await page.evaluate(() => {
      window.__delaySave = true;
      document.querySelector('[data-action="shoot"]').click();
      window.__hiddenForTest = true;
      document.dispatchEvent(new Event("visibilitychange"));
      document.querySelector('[data-page="gallery"]').click();
    });
    await page.waitForSelector('#catalog .asset-card');
    await page.waitForTimeout(900);
    assert.equal(await page.locator('#game-page dialog[open]').count(), 0);
    assert.equal(await page.evaluate(() => typeof window.render_game_to_text), 'undefined');
  });
  await run("late Web Lock is released when the game route is abandoned", async (page, context) => {
    await context.addInitScript(() => {
      const request = navigator.locks.request.bind(navigator.locks);
      let first = true;
      navigator.locks.request = (...args) => {
        if (!first) return request(...args);
        first = false;
        window.__lockQueued = true;
        return new Promise((resolve, reject) => setTimeout(() => {
          window.__lockAttempted = true;
          request(...args).then(resolve, reject);
        }, 700));
      };
    });
    await page.goto(server.url + "?page=game");
    await page.waitForFunction(() => window.__lockQueued);
    await navigateTo(page, "gallery");
    await page.waitForSelector("#catalog .asset-card");
    await page.waitForFunction(() => window.__lockAttempted);
    await page.waitForTimeout(150);
    const held = await page.evaluate(async () => (await navigator.locks.query()).held.map(lock => lock.name));
    assert.ok(!held.includes("blender-gallery-game-owner"), JSON.stringify(held));
    await navigateTo(page, "game");
    await page.waitForFunction(() => window.render_game_to_text && JSON.parse(window.render_game_to_text()).ready);
    assert.equal((await readGame(page)).ownership, true);
    assert.equal(await page.locator('[data-action="new"]').first().isEnabled(), true);
  });
  await run("IndexedDB lease transfers when Web Locks are unavailable", async (page, context) => {
    await context.addInitScript(() => Object.defineProperty(navigator, 'locks', {configurable:true,value:undefined}));
    await gameReady(page, server.url);
    await start(page);
    const second = await context.newPage();
    await gameReady(second, server.url);
    assert.equal((await readGame(second)).ownership, false);
    await navigateTo(page, "gallery");
    await second.bringToFront();
    await second.waitForFunction(() => JSON.parse(window.render_game_to_text()).ownership, null, {timeout:12000});
    assert.equal(await second.locator('[data-action="resume"]').isEnabled(), true);
    await second.click('[data-action="resume"]');
    assert.equal((await readGame(second)).phase, 'aiming');
  });
  await run("mobile storage failure remains visible during play", async (page, context) => {
    await context.addInitScript(() => { indexedDB.open = () => { throw new Error("Injected storage unavailable"); }; });
    await gameReady(page, server.url);
    await start(page);
    assert.equal(await page.locator("#save-status").isVisible(), true);
    assert.match(await page.locator("#save-status").innerText(), /Autosave unavailable/);
  }, { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  await run("restarting resets the match without duplicating its animation loop", async (page, context) => {
    await context.addInitScript(() => {
      const request = window.requestAnimationFrame.bind(window), cancel = window.cancelAnimationFrame.bind(window);
      const pending = new Set();
      window.__gameFrames = { pending, max: 0 };
      window.requestAnimationFrame = callback => {
        if (String(callback).includes("injected.utils.builtins")) return request(callback);
        const id = request(time => { pending.delete(id); callback(time); });
        pending.add(id);
        window.__gameFrames.max = Math.max(window.__gameFrames.max, pending.size);
        return id;
      };
      window.cancelAnimationFrame = id => { pending.delete(id); cancel(id); };
    });
    await gameReady(page, server.url);
    await start(page);
    await setRange(page, "#aim-angle", 37);
    await setRange(page, "#shot-power", 75);
    for (let i = 0; i < 3; i++) {
      await page.click('[data-action="pause"]');
      await page.click('[data-action="restart"]');
      await page.click('[data-action="confirm-new"]');
      await page.waitForFunction(() => document.querySelector('.game-shell').dataset.phase === 'placing');
      const state = await readGame(page);
      assert.equal(state.player, 0);
      assert.equal(state.revision, 0);
      assert.deepEqual(state.groups, [null, null]);
      assert.equal(state.aim, 0);
      assert.equal(state.power, 0.45);
      assert.deepEqual(state.balls.filter(ball => ball.pocketed).map(ball => ball.id), [0]);
    }
    assert.equal(await page.evaluate(() => window.__gameFrames.max), 1);
    await navigateTo(page, "gallery");
    assert.equal(await page.evaluate(() => window.__gameFrames.pending.size), 0);
  });
  for (const fault of ["missing", "invalid"]) {
    await run(`${fault} game assets show a usable retry`, async (page) => {
      await page.route("**/*.glb", route => fault === "missing"
        ? route.fulfill({ status: 404, body: "missing" })
        : route.fulfill({ status: 200, contentType: "model/gltf-binary", body: "invalid glb" }));
      await page.goto(server.url + "?page=game");
      await page.waitForSelector("#game-load-error:visible");
      assert.equal(await page.locator('[data-action="retry-load"]').isEnabled(), true);
      assert.equal(await page.locator('[data-action="back-to-gallery"]').isVisible(), true);
      assert.doesNotMatch(await page.locator("#save-status").innerText(), /404|invalid glb|Unexpected token/);
      if (fault === "invalid") {
        await page.click('[data-action="back-to-gallery"]');
        await page.waitForSelector('#catalog .asset-card');
        await navigateTo(page, "game");
        await page.waitForSelector('#game-load-error:visible');
      }
      await page.unroute("**/*.glb");
      await page.click('[data-action="retry-load"]');
      await page.waitForFunction(() => window.render_game_to_text && JSON.parse(window.render_game_to_text()).ready);
      assert.equal(await page.locator('[data-action="new"]').first().isEnabled(), true);
    });
  }
  await run("unavailable WebGL offers recovery and a working retry", async (page, context) => {
    await context.addInitScript(() => {
      const original = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function (type, ...args) {
        if (!sessionStorage.getItem("test-webgl-allowed") && /^(webgl2?|experimental-webgl)$/.test(type)) return null;
        return original.call(this, type, ...args);
      };
    });
    await page.goto(server.url + "?page=game");
    await page.waitForSelector("#game-load-error:visible");
    assert.doesNotMatch(await page.locator("#save-status").innerText(), /WebGLRenderer/);
    await page.evaluate(() => sessionStorage.setItem("test-webgl-allowed", "1"));
    await page.click('[data-action="retry-load"]');
    await page.waitForFunction(() => window.render_game_to_text && JSON.parse(window.render_game_to_text()).ready);
  });
  await run("graphics quality changes resolution without resetting the match", async (page) => {
    await gameReady(page, server.url);
    await start(page);
    const before = await readGame(page);
    const dimensions = () => page.locator('#game-viewport canvas').evaluate(canvas => ({
      width:canvas.width, height:canvas.height, cssWidth:canvas.clientWidth, cssHeight:canvas.clientHeight,
    }));
    const standard = await dimensions();
    await page.click('[data-action="options"]');
    assert.equal(await page.locator('#graphics-quality').inputValue(), 'standard');
    await page.locator('#graphics-quality').selectOption('performance');
    const performance = await dimensions();
    assert.equal(performance.width, performance.cssWidth);
    assert.equal(performance.height, performance.cssHeight);
    assert.ok(standard.width > performance.width && standard.height > performance.height);
    assert.deepEqual((await readGame(page)).balls, before.balls);
    assert.equal((await readGame(page)).phase, before.phase);
    await page.screenshot({path:path.join(qualityArtifacts, '390-options-open.png')});
    await page.locator('#graphics-quality').selectOption('standard');
    assert.deepEqual(await dimensions(), standard);
    await page.click('[data-action="close-options"]');
    assert.equal(await page.locator('#game-options').isVisible(), false);
    assert.deepEqual((await readGame(page)).balls, before.balls);
    await page.screenshot({path:path.join(qualityArtifacts, '390-options-closed.png')});
  }, {viewport:{width:390,height:844}, deviceScaleFactor:3, hasTouch:true, isMobile:true});
  await run("desktop graphics options open and close", async page => {
    await gameReady(page, server.url);
    await start(page);
    await page.click('[data-action="options"]');
    await page.screenshot({path:path.join(qualityArtifacts, '1440-options-open.png')});
    await page.click('[data-action="close-options"]');
    await page.screenshot({path:path.join(qualityArtifacts, '1440-options-closed.png')});
  }, {viewport:{width:1440,height:900}});
  for (const [width, height] of [[320,568],[360,800],[390,844],[1440,900]]) {
    await run(`touch targets and viewport remain usable at ${width}x${height}`, async (page) => {
      await gameReady(page, server.url);
      await start(page);
      await revealShortScreen(page, width, height, ["shoot", "pause"]);
      const layout = await page.evaluate(() => {
        const rect = selector => {
          const r = document.querySelector(selector).getBoundingClientRect();
          return {top:r.top,bottom:r.bottom,width:r.width,height:r.height};
        };
        return { width:innerWidth, height:innerHeight, scrollWidth:document.documentElement.scrollWidth,
          board:rect('#game-viewport'), shoot:rect('[data-action="shoot"]'), pause:rect('[data-action="pause"]'),
          rules:rect('[data-action="rules"]'), inspect:rect('[data-action="inspect"]'), options:rect('[data-action="options"]'),
          hint:rect('.control-note') };
      });
      assert.equal(layout.scrollWidth, width, JSON.stringify(layout));
      for (const button of [layout.rules, layout.inspect, layout.options, layout.shoot, layout.pause])
        assert.ok(button.width >= 44 && button.height >= 44, JSON.stringify(layout));
      assert.ok(layout.board.top >= 0 && layout.board.bottom <= height, JSON.stringify(layout));
      assert.ok(layout.shoot.bottom <= height && layout.pause.bottom <= height, JSON.stringify(layout));
      if (width === 320 && height === 568) assert.ok(layout.board.height >= 190, JSON.stringify(layout));
      if (width < 600) {
        assert.equal(await page.locator('.control-note').isVisible(), true);
        assert.match(await page.locator('.control-note').innerText(), /Drag to aim.*Shoot/);
        assert.ok(layout.hint.bottom <= layout.shoot.top, JSON.stringify(layout));
      }
      await page.screenshot({path:path.join(artifacts, `targets-${width}x${height}.png`)});
    }, { viewport: {width,height}, hasTouch: width < 600, isMobile: width < 600 });
  }
  await run("Game to About and back to Gallery preserves navigation", async page => {
    await gameReady(page, server.url);
    await start(page);
    assert.equal(await page.locator('.source-link').getAttribute('href'), 'https://github.com/yapweijun1996/Blender-3D-Gallery');
    await navigateTo(page, "about");
    await page.waitForFunction(() => {
      const section = document.querySelector('#about'), rect = section.getBoundingClientRect();
      return !document.querySelector('#about-page').hidden && rect.bottom > 0 && rect.top < innerHeight;
    });
    assert.equal(await page.locator('#game-page canvas').count(), 0);
    assert.equal(await page.evaluate(() => typeof window.render_game_to_text), 'undefined');
    assert.match(await page.locator('#about').innerText(), /collection of real 3D objects/);
    await navigateTo(page, "gallery");
    assert.ok(await page.locator('#catalog .asset-card').count() > 0);
    assert.equal(new URL(page.url()).searchParams.get('page'), 'models');
  });
  await run("resizing an active match preserves state and usable controls", async page => {
    await gameReady(page, server.url);
    await start(page);
    await page.waitForFunction(() => !document.querySelector('[data-action="shoot"]').disabled);
    const matchId = () => page.evaluate(() => new Promise((resolve, reject) => {
      const request = indexedDB.open('blender-gallery-game-v1', 1);
      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        const db = request.result, transaction = db.transaction('records', 'readonly');
        const get = transaction.objectStore('records').get('match');
        get.onsuccess = () => resolve(get.result?.checkpoint?.matchId);
        get.onerror = () => reject(get.error);
        transaction.oncomplete = () => db.close();
      };
    }));
    const before = await readGame(page), id = await matchId(), canvas = await page.locator('#game-viewport canvas').elementHandle();
    assert.ok(id);
    for (const [width, height] of [[844,390],[390,844]]) {
      await page.setViewportSize({width,height});
      await page.waitForFunction(([w,h]) => innerWidth === w && innerHeight === h &&
        document.querySelector('#game-viewport canvas').width === document.querySelector('#game-viewport').clientWidth &&
        document.querySelector('#game-viewport canvas').height === document.querySelector('#game-viewport').clientHeight, [width,height]);
      assert.equal(await page.evaluate(el => el === document.querySelector('#game-viewport canvas'), canvas), true);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), width);
      assert.equal(await page.locator('.control-note').isVisible(), true);
      for (const action of ['shoot','pause']) {
        const button = page.locator(`[data-action="${action}"]`);
        assert.equal(await button.isEnabled(), true);
        await button.scrollIntoViewIfNeeded();
        const box = await button.boundingBox();
        assert.ok(box.width >= 44 && box.height >= 44 && box.y >= 0 && box.y + box.height <= height, JSON.stringify(box));
      }
      await page.click('[data-action="pause"]');
      await waitPhase(page, 'paused');
      await page.click('[data-action="continue"]');
      await waitPhase(page, 'aiming');
      const after = await readGame(page);
      assert.equal(await matchId(), id);
      assert.equal(after.revision, before.revision);
      assert.equal(after.player, before.player);
      assert.deepEqual(after.groups, before.groups);
      assert.deepEqual(after.balls, before.balls);
      await page.screenshot({path:path.join(artifacts, `resize-${width}x${height}.png`)});
    }
  }, {viewport:{width:390,height:844},deviceScaleFactor:1,hasTouch:true,isMobile:true});
  await run("reduced motion disables smooth scrolling without disabling play", async page => {
    await gameReady(page, server.url);
    assert.equal(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches), true);
    assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior), 'auto');
    await page.emulateMedia({reducedMotion:'no-preference'});
    assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior), 'smooth');
    await page.emulateMedia({reducedMotion:'reduce'});
    await start(page);
    await page.waitForFunction(() => !document.querySelector('[data-action="shoot"]').disabled);
    await page.locator('#game-viewport').focus();
    const before = await readGame(page);
    await page.keyboard.press('ArrowRight');
    assert.notEqual((await readGame(page)).aim, before.aim);
    await page.keyboard.press('Space');
    await waitPhase(page, 'moving');
    await page.click('[data-action="pause"]');
    const paused = await readGame(page);
    await page.evaluate(() => window.advanceTime(1000));
    assert.deepEqual((await readGame(page)).balls, paused.balls);
    await page.click('[data-action="continue"]');
    await page.evaluate(() => window.advanceTime(26000));
    await page.waitForFunction(() => !['moving','adjudicating'].includes(JSON.parse(window.render_game_to_text()).phase));
    assert.notEqual((await readGame(page)).phase, 'recovery');
  }, {viewport:{width:390,height:844},hasTouch:true,isMobile:true,reducedMotion:'reduce'});
  for (const width of [320,390]) {
    await run(`assigned-group progress is available at ${width}px`, async (page, context) => {
      await page.goto(server.url);
      const match = { schema:1, rulesVersion:RULES_VERSION, tableVersion:TABLE.version, matchId:"progress-fixture", revision:8,
        phase:"aiming", player:0, groups:["solids","stripes"], break:false, ballInHand:false, winner:null, balls:makeRack(42) };
      for (const ball of match.balls) if (groupOf(ball.id) === "solids") ball.pocketed = true;
      await writeCheckpoint(page, match);
      await gameReady(page, server.url);
      await page.click('[data-action="resume"]');
      await page.waitForFunction(() => document.querySelector('#player-0 .remaining-compact').textContent === '8 ball next');
      assert.equal(await page.locator('#player-0 .remaining-compact').isVisible(), true);
      assert.equal(await page.locator('#player-1 .remaining-compact').innerText(), '7 left');
      const cdp = await context.newCDPSession(page);
      await cdp.send('Accessibility.enable');
      const tree = await cdp.send('Accessibility.getFullAXTree');
      const text = tree.nodes.filter(node => !node.ignored && node.role?.value === 'StaticText').map(node => node.name?.value);
      assert.equal(text.filter(value => value === 'solids cleared; 8 ball next.').length, 1);
      assert.equal(text.filter(value => value === 'stripes remaining: balls 9, 10, 11, 12, 13, 14, 15.').length, 1);
      assert.equal(text.includes('7 left'), false);
      const layout = await page.locator('.player-card').evaluateAll(cards => cards.map(card => {
        const r=card.getBoundingClientRect(), group=card.querySelector('.player-group').getBoundingClientRect(), progress=card.querySelector('.remaining-compact').getBoundingClientRect();
        return {right:r.right,groupRight:group.right,progressLeft:progress.left,progressRight:progress.right};
      }));
      assert.ok(layout.every(item => item.progressRight <= item.right && item.progressLeft >= item.groupRight), JSON.stringify(layout));
      await page.screenshot({path:path.join(artifacts, `progress-${width}.png`)});
    }, { viewport:{width,height:width===320?568:844}, hasTouch:true, isMobile:true });
  }
  await run("active touch hands off safely when fingers end or cancel", async (page, context) => {
    await gameReady(page, server.url);
    await start(page);
    await page.waitForFunction(() => !document.querySelector('[data-action="shoot"]').disabled);
    await page.evaluate(() => scrollTo(0, 0));
    const cdp = await context.newCDPSession(page), rect = await page.locator('#game-viewport canvas').boundingBox();
    const point = (id, x, y) => ({id, x:rect.x + rect.width*x, y:rect.y + rect.height*y});
    const a=point(1,.4,.5), b=point(2,.7,.6), a2=point(1,.2,.2), b2=point(2,.2,.2), c=point(3,.7,.5), c2=point(3,.3,.3);
    await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[a]});
    const initial = (await readGame(page)).aim;
    await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[a,b]});
    assert.equal((await readGame(page)).aim, initial);
    await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[b]});
    await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[a2]});
    assert.notEqual((await readGame(page)).aim, initial);
    await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
    await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[a]});
    await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[a,b]});
    await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[a]});
    const handoff = (await readGame(page)).aim;
    await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[b2]});
    assert.notEqual((await readGame(page)).aim, handoff);
    await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
    await page.evaluate(() => {
      window.__touchPointerIds = [];
      document.querySelector('#game-viewport canvas').addEventListener('pointerdown', event => window.__touchPointerIds.push(event.pointerId));
    });
    await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[a]});
    await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[a,b]});
    const firstPointer = await page.evaluate(() => window.__touchPointerIds[0]);
    await page.locator('#game-viewport canvas').dispatchEvent('pointercancel', {bubbles:true,pointerType:'touch',pointerId:firstPointer});
    const canceled = (await readGame(page)).aim;
    await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[a,b2]});
    assert.notEqual((await readGame(page)).aim, canceled);
    await cdp.send('Input.dispatchTouchEvent',{type:'touchCancel',touchPoints:[]});
    await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[c]});
    const next = (await readGame(page)).aim;
    await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[c2]});
    assert.notEqual((await readGame(page)).aim, next);
    await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  }, {viewport:{width:390,height:844}, hasTouch:true, isMobile:true});
  await run("late GLB response cannot revive a disposed game route", async page => {
    const gate = await holdGameTableResponse(page), pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    try {
      await page.goto(server.url + '?page=game');
      await withDeadline(gate.requested, 'table response held');
      await page.waitForSelector('#game-viewport canvas');
      assert.equal((await readGame(page)).ready, false);
      await navigateTo(page, "gallery");
      await page.waitForSelector('#catalog .asset-card');
      gate.release();
      assert.equal(await withDeadline(gate.finished, 'late table response'), null);
      await page.waitForLoadState('networkidle');
      assert.equal(await page.locator('#game-page canvas').count(), 0);
      assert.equal(await page.evaluate(() => typeof window.render_game_to_text), 'undefined');
      assert.equal(await page.evaluate(() => typeof window.advanceTime), 'undefined');
      assert.deepEqual(pageErrors, []);
      await gate.remove();
      await navigateTo(page, "game");
      await page.waitForFunction(() => window.render_game_to_text && JSON.parse(window.render_game_to_text()).ready, null, {timeout:60000});
      assert.equal(await page.locator('#game-page canvas').count(), 1);
      assert.equal((await readGame(page)).ownership, true);
      assert.deepEqual(pageErrors, []);
    } finally {
      gate.release();
      await gate.remove();
    }
  });
  await run("WebGL loss during GLB loading leaves a working recovery", async page => {
    const gate = await holdGameTableResponse(page), pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    try {
      await page.goto(server.url + '?page=game');
      await withDeadline(gate.requested, 'table response held');
      await page.waitForSelector('#game-viewport canvas');
      assert.equal((await readGame(page)).ready, false);
      const supported = await page.evaluate(() => {
        const gl = document.querySelector('#game-viewport canvas').getContext('webgl2');
        const extension = gl?.getExtension('WEBGL_lose_context');
        if (!extension) return false;
        extension.loseContext();
        return true;
      });
      assert.equal(supported, true);
      await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).contextLost);
      assert.equal((await readGame(page)).phase, 'setup');
      assert.equal(await page.locator('[data-action="new"]').first().isDisabled(), true);
      assert.equal(await page.locator('[data-action="restore"]').isVisible(), true);
      gate.release();
      assert.equal(await withDeadline(gate.finished, 'table response after context loss'), null);
      await page.waitForLoadState('networkidle');
      const lost = await readGame(page);
      assert.equal(lost.contextLost, true);
      assert.equal(lost.phase, 'setup');
      assert.equal(await page.locator('[data-action="new"]').first().isDisabled(), true);
      assert.deepEqual(pageErrors, []);
      await gate.remove();
      await page.click('[data-action="restore"]');
      await page.waitForFunction(() => window.render_game_to_text && JSON.parse(window.render_game_to_text()).ready && !JSON.parse(window.render_game_to_text()).contextLost, null, {timeout:60000});
      assert.equal(await page.locator('[data-action="new"]').first().isEnabled(), true);
      assert.deepEqual(pageErrors, []);
    } finally {
      gate.release();
      await gate.remove();
    }
  });
  await run("first entry exposes Start and the complete table", async page => {
    for (const [width,height] of [[1280,720],[390,844],[320,568]]) {
      await page.setViewportSize({width,height});
      await gameReady(page,server.url);
      const boxes=await page.evaluate(()=>{
        const start=document.querySelector('[data-action=new]').getBoundingClientRect();
        const board=document.querySelector('.game-board').getBoundingClientRect();
        return {startBottom:start.bottom,boardBottom:board.bottom,height:innerHeight};
      });
      assert.ok(boxes.startBottom<=height,JSON.stringify(boxes));
      assert.ok(boxes.boardBottom<=height,JSON.stringify(boxes));
      await page.screenshot({path:path.join(artifacts,`entry-${width}.png`)});
    }
  });
  await run(
    "start, invalid placement, single impulse, pause and shot settlement",
    async (page) => {
      await gameReady(page, server.url);
      await page.click("[data-action=new]");
      await setRange(page, "#place-x", 0.4);
      assert.equal(await page.isDisabled("[data-action=place]"), true);
      await setRange(page, "#place-x", -0.7);
      await page.click("[data-action=place]");
      const before = await readGame(page);
      await setRange(page, "#shot-power", 75);
      await page.waitForFunction(
        () => !document.querySelector("[data-action=shoot]").disabled,
      );
      await page.evaluate(() => {
        const b = document.querySelector("[data-action=shoot]");
        b.click();
        b.click();
      });
      await waitPhase(page, "moving");
      await page.click("[data-action=pause]");
      const paused = await readGame(page);
      await page.evaluate(() => window.advanceTime(1000));
      assert.deepEqual((await readGame(page)).balls, paused.balls);
      await page.click("[data-action=continue]");
      await page.evaluate(() => window.advanceTime(26000));
      await page.waitForFunction(
        () =>
          !["moving", "adjudicating"].includes(
            JSON.parse(window.render_game_to_text()).phase,
          ),
      );
      const after = await readGame(page);
      assert.equal(after.revision, before.revision + 1);
      assert.equal(after.break, false);
      assert.notEqual(after.phase, "recovery");
      await page.screenshot({
        path: path.join(artifacts, "desktop-after-break.png"),
      });
      await page.reload();
      await page.waitForFunction(
        () =>
          window.render_game_to_text &&
          JSON.parse(window.render_game_to_text()).ready,
      );
      assert.equal(await page.isDisabled("[data-action=resume]"), false);
      await page.click("[data-action=resume]");
      assert.deepEqual((await readGame(page)).balls, after.balls);
    },
  );
  await run("interrupted shot restores pre-shot checkpoint", async (page) => {
    await gameReady(page, server.url);
    await start(page);
    const before = await readGame(page);
    await page.click("[data-action=shoot]");
    await waitPhase(page, "moving");
    await page.reload();
    await page.waitForFunction(
      () =>
        window.render_game_to_text &&
        JSON.parse(window.render_game_to_text()).ready,
    );
    await page.click("[data-action=resume]");
    const restored = await readGame(page);
    assert.deepEqual(restored.balls, before.balls);
    assert.equal(restored.player, before.player);
    assert.match(restored.message, /Interrupted/);
  });
  await run(
    "one navigation confirmation and repeated Game navigation remains usable",
    async (page) => {
      await page.goto(server.url + "?page=demos");
      await page.evaluate(() => {
        document.querySelector("[data-page=game]").click();
        document.querySelector("[data-page=game]").click();
      });
      await page.waitForFunction(
        () =>
          window.render_game_to_text &&
          JSON.parse(window.render_game_to_text()).ready,
      );
      await start(page);
      await page.click("[data-action=shoot]");
      await waitPhase(page, "moving");
      let dialogs = 0;
      page.on("dialog", async (d) => {
        dialogs++;
        await d.accept();
      });
      await navigateTo(page, "gallery");
      assert.equal(dialogs, 1);
      await page.waitForSelector("#catalog .asset-card");
      assert.equal(await page.locator("#game-page canvas").count(), 0);
    },
  );
  for (const [width, height] of [
    [320, 568],
    [390, 844],
    [844, 390],
  ])
    await run(
      `touch layout ${width}x${height}`,
      async (page) => {
        await gameReady(page, server.url);
        const assertControlsInViewport = async (actions, phase) => {
          for (const action of actions) {
            await page.locator(`[data-action="${action}"]`).waitFor({ state: "visible" });
          }
          // Check the explicitly positioned viewport before click auto-scroll can hide clipping.
          await revealShortScreen(page, width, height, actions);
          const controls = await page.evaluate((actions) => actions.map(action => {
            const rect = document.querySelector(`[data-action="${action}"]`).getBoundingClientRect();
            return { action, top: rect.top, bottom: rect.bottom, width: rect.width, height: rect.height };
          }), actions);
          for (const control of controls) {
            assert.ok(control.width >= 44 && control.height >= 44, `${phase}: ${JSON.stringify(control)}`);
            assert.ok(control.top >= 0 && control.bottom <= height, `${phase} ${width}x${height}: ${JSON.stringify(control)}`);
          }
          const board = await page.locator("#game-viewport").boundingBox();
          assert.ok(board && board.y >= 0 && board.y + board.height <= height, `${phase}: ${JSON.stringify(board)}`);
          if (width === 320 && height === 568) assert.ok(board.height >= 190, `${phase}: ${JSON.stringify(board)}`);
          if (width === 844 && height === 390) assert.ok(board.height >= 220, `${phase}: ${JSON.stringify(board)}`);
        };
        await page.click("[data-action=new]");
        await waitPhase(page, "placing");
        await assertControlsInViewport(["place", "pause"], "placing");
        await page.click("[data-action=place]");
        await waitPhase(page, "aiming");
        await assertControlsInViewport(["shoot", "pause"], "aiming");
        const measured = await page.evaluate(() => {
          const a = document
              .querySelector("#game-viewport")
              .getBoundingClientRect(),
            b = document
              .querySelector("[data-action=shoot]")
              .getBoundingClientRect();
          return {
            top: Math.min(a.top, b.top),
            bottom: Math.max(a.bottom, b.bottom),
            overflow: document.documentElement.scrollWidth - innerWidth,
            h: innerHeight,
          };
        });
        assert.ok(
          measured.bottom - measured.top <= height,
          JSON.stringify(measured),
        );
        assert.ok(measured.overflow <= 0);
        await page.screenshot({
          path: path.join(artifacts, `mobile-${width}x${height}.png`),
        });
      },
      { viewport: { width, height }, hasTouch: true, isMobile: true },
    );
  await run(
    "multi-tab ownership transfers after the first tab closes",
    async (page, context) => {
      await gameReady(page, server.url);
      await start(page);
      const second = await context.newPage();
      await gameReady(second, server.url);
      assert.equal(await second.isDisabled("[data-action=new]"), true);
      await page.close();
      await second.waitForFunction(
        () => !document.querySelector("[data-action=resume]").disabled,
        {},
        { timeout: 12000 },
      );
      await second.click("[data-action=resume]");
      assert.equal((await readGame(second)).phase, "aiming");
    },
  );
  await run(
    "storage failure keeps the match until an explicit discard",
    async (page, context) => {
      await context.addInitScript(() => {
        indexedDB.open = () => {
          throw new Error("Injected storage unavailable");
        };
      });
      await gameReady(page, server.url);
      await start(page);
      await page.click("[data-action=pause]");
      await page.click("[data-action=leave]");
      assert.equal(await page.isVisible("#game-menu"), true);
      assert.equal(await page.isVisible("[data-action=discard]"), true);
      assert.match(
        await page.textContent("#menu-save-message"),
        /Saving failed/,
      );
      assert.equal((await readGame(page)).phase, "paused");
    },
  );
  await run("corrupt checkpoint falls back to a new match", async (page) => {
    await page.goto(server.url);
    const m = {
      schema: 1,
      rulesVersion: RULES_VERSION,
      tableVersion: TABLE.version,
      matchId: "corrupt",
      revision: 0,
      phase: "aiming",
      player: 0,
      groups: [null, null],
      break: false,
      ballInHand: false,
      winner: null,
      balls: makeRack(1),
    };
    m.balls[3] = null;
    await writeCheckpoint(page, m);
    await gameReady(page, server.url);
    assert.match(await page.textContent("#save-status"), /incompatible/);
    assert.equal(await page.isDisabled("[data-action=new]"), false);
    assert.equal(await page.isDisabled("[data-action=resume]"), true);
  });
  await run(
    "eligible eight is physically potted and ends the match once",
    async (page) => {
      await page.goto(server.url);
      const m = {
        schema: 1,
        rulesVersion: RULES_VERSION,
        tableVersion: TABLE.version,
        matchId: "eight-fixture",
        revision: 8,
        phase: "aiming",
        player: 0,
        groups: ["solids", "stripes"],
        break: false,
        ballInHand: false,
        winner: null,
        balls: makeRack(42),
      };
      for (const b of m.balls)
        if (groupOf(b.id) === "solids") b.pocketed = true;
      Object.assign(m.balls[0], { x: 0, z: 0.2 });
      Object.assign(m.balls[8], { x: 0, z: 0.38 });
      await writeCheckpoint(page, m);
      await gameReady(page, server.url);
      await page.click("[data-action=resume]");
      await setRange(page, "#aim-angle", 90);
      await setRange(page, "#shot-power", 25);
      await page.click("[data-action=shoot]");
      await waitPhase(page, "moving");
      await page.evaluate(() => window.advanceTime(26000));
      await waitPhase(page, "finished");
      const end = await readGame(page);
      assert.equal(end.winner, 0);
      assert.equal(end.revision, 9);
      assert.equal(end.balls.find((b) => b.id === 8).pocketed, true);
      assert.match(await page.textContent("#game-turn"), /Player 1 wins/);
      await page.screenshot({
        path: path.join(artifacts, "winning-eight.png"),
      });
    },
  );
  await run(
    "WebGL context loss before and during a match offers working reload",
    async (page) => {
      const lose = () => {
        const c = document.querySelector("#game-viewport canvas");
        c.getContext("webgl2").getExtension("WEBGL_lose_context").loseContext();
      };
      await gameReady(page, server.url);
      await page.evaluate(lose);
      await page.waitForFunction(
        () => JSON.parse(window.render_game_to_text()).contextLost,
      );
      assert.equal(await page.isVisible("[data-action=restore]"), true);
      assert.match(await page.textContent("#game-status"), /interrupted/);
      await page.click("[data-action=restore]");
      await page.waitForFunction(
        () =>
          window.render_game_to_text &&
          JSON.parse(window.render_game_to_text()).ready &&
          !JSON.parse(window.render_game_to_text()).contextLost,
      );
      await start(page);
      await page.evaluate(lose);
      await page.waitForFunction(
        () => JSON.parse(window.render_game_to_text()).contextLost,
      );
      assert.equal(await page.isVisible("[data-action=shoot]"), false);
      await page.click("[data-action=restore]");
      await page.waitForFunction(
        () =>
          window.render_game_to_text &&
          JSON.parse(window.render_game_to_text()).ready &&
          !JSON.parse(window.render_game_to_text()).contextLost,
      );
      await page.click("[data-action=resume]");
      assert.equal((await readGame(page)).phase, "aiming");
    },
  );
  await run(
    "all gallery assets preview and download independently",
    async (page) => {
      const glbs = [];
      page.on("request", (r) => {
        if (r.url().endsWith(".glb")) glbs.push(r.url());
      });
      await page.goto(server.url);
      assert.equal(await page.locator(".asset-card").count(), 39);
      assert.equal(glbs.length, 0);
      const ids = await page
        .locator("[data-asset-id]")
        .evaluateAll((els) => els.map((el) => el.dataset.assetId));
      for (const id of ids) {
        await page.click(`[data-asset-id="${id}"]`);
        await page.waitForSelector("#viewport canvas");
        await page.waitForFunction(
          () =>
            !document
              .querySelector("#viewer-status")
              .textContent.includes("Loading"),
        );
        assert.doesNotMatch(
          await page.textContent("#viewer-status"),
          /unavailable/i,
        );
        const href = await page.getAttribute("#viewer-download", "href");
        const response = await page.request.get(new URL(href, server.url).href);
        assert.equal(response.status(), 200);
        assert.equal((await response.body()).subarray(0, 4).toString(), "glTF");
        await page.click("#reset-view");
        await page.click("#close-viewer");
        assert.equal(await page.locator("#viewport canvas").count(), 0);
      }
      for (const id of ["ball-08", "eight-ball-billiards"]) {
        await page.goto(server.url + "?model=" + id);
        await page.waitForSelector("#viewport canvas");
        assert.equal(await page.isVisible("#viewer"), true);
        await page.click("#close-viewer");
      }
    },
  );
  assert.deepEqual(errors, []);
  try {
    const wk = await webkit.launch({ headless: true });
    try {
      const p = await wk.newPage({ viewport: { width: 390, height: 844 } });
      await gameReady(p, server.url);
      await start(p);
      await p.click("[data-action=shoot]");
      await waitPhase(p, "moving");
      await p.evaluate(() => window.advanceTime(26000));
      await p.waitForFunction(
        () =>
          !["moving", "adjudicating"].includes(
            JSON.parse(window.render_game_to_text()).phase,
          ),
      );
      assert.notEqual((await readGame(p)).phase, "recovery");
      await p.screenshot({
        path: path.join(artifacts, "webkit-after-shot.png"),
      });
      results.push({ name: "WebKit mobile viewport shot smoke", passed: true });
      console.log("PASS WebKit shot smoke");
    } finally {
      await wk.close();
    }
  } catch (e) {
    throw e;
  }
  await fs.writeFile(
    path.join(artifacts, "results.json"),
    JSON.stringify({ results, errors }, null, 2),
  );
} finally {
  await browser.close();
  await server.close();
}
