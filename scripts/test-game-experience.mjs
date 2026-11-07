import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { chromium } from "playwright";
import {
  serveBuild,
  launchOptions,
  gameReady,
  readGame,
  chargePull,
  releasePull,
  pullShot,
} from "./browser-test-utils.mjs";
const server = await serveBuild(),
  browser = await chromium.launch(launchOptions);
const artifacts =
  process.env.TEST_ARTIFACT_DIR || "/tmp/blender-gallery-left-pull";
await fs.mkdir(artifacts, { recursive: true });
const errors = [],
  results = [];
const wait = (p, phase) =>
  p.waitForFunction(
    (phase) => JSON.parse(window.render_game_to_text()).phase === phase,
    phase,
  );
async function start(page, place = true) {
  await gameReady(page, server.url);
  await page.locator("[data-action=new]").first().click();
  await page.waitForFunction(
    () => !document.querySelector("[data-action=place]").disabled,
  );
  if (!place) return;
  await page.locator("[data-action=place]").click();
  await page.waitForFunction(
    () => !document.querySelector("#power-handle").disabled,
  );
}
async function freeze(page) {
  await page.evaluate(() => {
    const original = requestAnimationFrame,
      queued = [];
    window.requestAnimationFrame = (fn) => {
      queued.push(fn);
      return 0;
    };
    window.restoreFrames = () => {
      window.requestAnimationFrame = original;
      for (const fn of queued) original(fn);
    };
    window.advanceTime(0);
  });
  await page.waitForTimeout(40);
}
async function test(name, fn, options = {}) {
  if (process.env.B3G_PULL_CASE && !name.includes(process.env.B3G_PULL_CASE))
    return;
  const { placement = false, seed = null, ...contextOptions } = options;
  const context = await browser.newContext({
      viewport: { width: 1280, height: 800 },
      serviceWorkers: "block",
      ...contextOptions,
    }),
    page = await context.newPage();
  page.on("pageerror", (e) => errors.push(e.message));
  try {
    if (seed !== null)
      await context.addInitScript((seed) => {
        const original = crypto.getRandomValues.bind(crypto);
        crypto.getRandomValues = (array) => {
          if (array instanceof Uint32Array && array.length === 1) {
            array[0] = seed;
            return array;
          }
          return original(array);
        };
      }, seed);
    await start(page, !placement);
    await fn(page, context);
    console.log("PASS", name);
    results.push({ name, passed: true });
  } catch (e) {
    await page.screenshot({ path: `${artifacts}/failure.png` });
    console.error(name, await readGame(page));
    throw e;
  } finally {
    await context.close();
  }
}
try {
  await test("1 mouse handle drag and release shoots", async (p) => {
    assert.equal(await p.locator("[data-action=shoot],#shot-power").count(), 0);
    await pullShot(p);
    await wait(p, "moving");
    assert.equal((await readGame(p)).committedShots, 1);
  });
  await test(
    "2 real touch handle drag and release shoots",
    async (p, c) => {
      const box = await p.locator("#power-handle").boundingBox(),
        travel = await p
          .locator("#power-track")
          .evaluate(
            (t) =>
              t.clientHeight -
              document.querySelector("#power-handle").offsetHeight,
          ),
        cdp = await c.newCDPSession(p),
        point = { x: box.x + box.width / 2, y: box.y + box.height / 2, id: 1 };
      await cdp.send("Input.dispatchTouchEvent", {
        type: "touchStart",
        touchPoints: [point],
      });
      await cdp.send("Input.dispatchTouchEvent", {
        type: "touchMove",
        touchPoints: [{ ...point, y: point.y + travel * 0.6 }],
      });
      assert.ok((await readGame(p)).pullRatio > 0.55);
      await cdp.send("Input.dispatchTouchEvent", {
        type: "touchEnd",
        touchPoints: [],
      });
      await wait(p, "moving");
      assert.equal((await readGame(p)).committedShots, 1);
    },
    { hasTouch: true, isMobile: true, viewport: { width: 390, height: 844 } },
  );
  for (const [n, ratio] of [
    [3, 0.04],
    [5, -0.3],
  ])
    await test(`${n} weak or reverse pull cancels`, async (p) => {
      const before = await readGame(p);
      await pullShot(p, ratio);
      await p.evaluate(() => window.advanceTime(500));
      const after = await readGame(p);
      assert.equal(after.phase, "aiming");
      assert.equal(after.committedShots, 0);
      assert.equal(after.pullRatio, 0);
      assert.deepEqual(after.balls, before.balls);
    });
  await test("4 long pull clamps at100", async (p) => {
    await chargePull(p, 1.6);
    assert.equal((await readGame(p)).pullRatio, 1);
    await p.keyboard.press("Escape");
    await releasePull(p);
    assert.equal((await readGame(p)).committedShots, 0);
  });
  await test("6 cancel and lost capture never shoot", async (p) => {
    for (const event of ["pointercancel", "lostpointercapture"]) {
      const before = await readGame(p);
      await chargePull(p, 0.6);
      const id = await p.locator("#power-handle").evaluate((el) => {
        for (let id = 0; id < 10; id++) if (el.hasPointerCapture(id)) return id;
        return 1;
      });
      await p
        .locator("#power-handle")
        .dispatchEvent(event, { pointerId: id, pointerType: "mouse" });
      await releasePull(p);
      await p.evaluate(() => window.advanceTime(500));
      assert.deepEqual((await readGame(p)).balls, before.balls);
      assert.equal((await readGame(p)).committedShots, 0);
    }
  });
  await test("7 duplicate up and normal lost capture commit only once", async (p) => {
    await freeze(p);
    await chargePull(p, 0.6);
    await releasePull(p);
    await p
      .locator("#power-handle")
      .dispatchEvent("pointerup", { pointerId: 1 });
    await p.waitForFunction(
      () => JSON.parse(window.render_game_to_text()).interaction === "striking",
    );
    await p.evaluate(() => window.advanceTime(300));
    assert.equal((await readGame(p)).committedShots, 1);
    await p.evaluate(() => window.advanceTime(300));
    assert.equal((await readGame(p)).committedShots, 1);
  });
  await test("8 cue offset proportional and aim locked", async (p) => {
    const before = await readGame(p);
    await chargePull(p, 0.3);
    const low = await readGame(p);
    assert.ok(Math.abs(low.pullRatio - 0.3) < 0.02);
    const h = await p.locator("#power-handle").boundingBox(),
      travel = await p
        .locator("#power-track")
        .evaluate(
          (t) =>
            t.clientHeight -
            document.querySelector("#power-handle").offsetHeight,
        );
    await p.mouse.move(h.x + h.width / 2, h.y + h.height / 2 + travel * 0.3);
    const high = await readGame(p);
    assert.ok(high.cueOffset > low.cueOffset);
    assert.ok(
      Math.abs(
        high.cueOffset / high.pullRatio - low.cueOffset / low.pullRatio,
      ) < 1e-6,
    );
    assert.equal(high.aim, before.aim);
    await p.screenshot({ path: `${artifacts}/charging.png` });
    await p.keyboard.press("Escape");
    await releasePull(p);
  });
  await test("9 no impulse until actual cue contact", async (p) => {
    await freeze(p);
    const before = await readGame(p);
    await pullShot(p, 0.6);
    await p.waitForFunction(
      () => JSON.parse(window.render_game_to_text()).interaction === "striking",
    );
    assert.deepEqual((await readGame(p)).balls, before.balls);
    assert.equal((await readGame(p)).committedShots, 0);
    await p.evaluate(() => window.advanceTime(50));
    assert.equal((await readGame(p)).committedShots, 0);
    assert.deepEqual((await readGame(p)).balls, before.balls);
    await p.evaluate(() => window.advanceTime(70));
    const after = await readGame(p);
    assert.equal(after.committedShots, 1);
    assert.equal(after.phase, "moving");
    assert.ok(Number.isFinite(after.lastContactTipDistance));
    assert.ok(Math.abs(after.lastContactTipDistance) < 0.001);
    await p.screenshot({ path: `${artifacts}/moving.png` });
  });
  const speeds = [];
  for (const ratio of [0.3, 0.8])
    await test(`10 power${ratio} initial speed`, async (p) => {
      await freeze(p);
      await pullShot(p, ratio);
      await p.waitForFunction(
        () =>
          JSON.parse(window.render_game_to_text()).interaction === "striking",
      );
      for (let i = 0; i < 20 && (await readGame(p)).committedShots === 0; i++)
        await p.evaluate(() => window.advanceTime(1000 / 120));
      const state = await readGame(p);
      speeds.push(Math.hypot(state.balls[0].vx, state.balls[0].vz));
      assert.ok(
        Math.abs(speeds.at(-1) - (0.18 + Math.pow(ratio, 1.5) * 2.8)) < 0.01,
      );
    });
  if (speeds.length) assert.ok(speeds[1] > speeds[0]);
  await test("11 moving disables further shooting", async (p) => {
    await pullShot(p);
    await wait(p, "moving");
    assert.equal(await p.locator("#power-handle").isDisabled(), true);
    await p
      .locator("#power-handle")
      .dispatchEvent("pointerup", { pointerId: 1 });
    await p.keyboard.press("Enter");
    assert.equal((await readGame(p)).committedShots, 1);
  });
  await test("12 pause during strike cancels and resume never fires", async (p) => {
    await freeze(p);
    const before = await readGame(p);
    await pullShot(p);
    await p.waitForFunction(
      () => JSON.parse(window.render_game_to_text()).interaction === "striking",
    );
    await p.locator("[data-action=pause]").click();
    await p.evaluate(() => window.advanceTime(500));
    assert.deepEqual((await readGame(p)).balls, before.balls);
    assert.equal((await readGame(p)).committedShots, 0);
    await p.locator("[data-action=continue]").click();
    await p.evaluate(() => window.advanceTime(500));
    assert.equal((await readGame(p)).phase, "aiming");
    assert.equal((await readGame(p)).committedShots, 0);
  });
  await test("13 reload never replays interrupted shot", async (p) => {
    const before = await readGame(p);
    await pullShot(p);
    await wait(p, "moving");
    await gameReady(p, server.url);
    await p.locator("[data-action=resume]").click();
    const after = await readGame(p);
    assert.deepEqual(after.balls, before.balls);
    assert.equal(after.phase, "aiming");
    await p.evaluate(() => window.advanceTime(1000));
    assert.deepEqual((await readGame(p)).balls, before.balls);
  });
  await test("14 turn resolution waits for all balls to settle", async (p) => {
    const before = await readGame(p);
    await pullShot(p);
    await wait(p, "moving");
    assert.equal((await readGame(p)).revision, before.revision);
    await p.evaluate(() => window.advanceTime(26000));
    await p.waitForFunction(
      () =>
        !["moving", "adjudicating"].includes(
          JSON.parse(window.render_game_to_text()).phase,
        ),
    );
    const after = await readGame(p);
    assert.equal(after.revision, before.revision + 1);
    assert.ok(after.balls.every((b) => b.vx === 0 && b.vz === 0));
    assert.notEqual(after.phase, "recovery");
  });
  await test(
    "15 landscape table and controller visible without gesture scrolling",
    async (p, c) => {
      await p.evaluate(() => scrollTo(0, 0));
      const box = await p.locator("#game-viewport").boundingBox(),
        handle = await p.locator("#power-handle").boundingBox();
      for (const b of [box, handle])
        assert.ok(
          b.x >= 0 && b.y >= 0 && b.x + b.width <= 844 && b.y + b.height <= 390,
          JSON.stringify(b),
        );
      const y = await p.evaluate(() => scrollY),
        cdp = await c.newCDPSession(p),
        travel = await p
          .locator("#power-track")
          .evaluate(
            (t) =>
              t.clientHeight -
              document.querySelector("#power-handle").offsetHeight,
          ),
        point = {
          x: handle.x + handle.width / 2,
          y: handle.y + handle.height / 2,
          id: 1,
        };
      await cdp.send("Input.dispatchTouchEvent", {
        type: "touchStart",
        touchPoints: [point],
      });
      await cdp.send("Input.dispatchTouchEvent", {
        type: "touchMove",
        touchPoints: [{ ...point, y: point.y + travel * 0.7 }],
      });
      assert.ok((await readGame(p)).pullRatio > 0.65);
      await p.screenshot({ path: `${artifacts}/landscape-charging.png` });
      assert.equal(await p.evaluate(() => scrollY), y);
      await cdp.send("Input.dispatchTouchEvent", {
        type: "touchCancel",
        touchPoints: [],
      });
      assert.equal((await readGame(p)).committedShots, 0);
    },
    { viewport: { width: 844, height: 390 }, hasTouch: true, isMobile: true },
  );
  await test("keyboard charge release and track click safety", async (p) => {
    await p.locator("#power-track").click({ position: { x: 4, y: 100 } });
    assert.equal((await readGame(p)).committedShots, 0);
    await p.locator("#power-handle").focus();
    for (let i = 0; i < 6; i++) await p.keyboard.press("ArrowDown");
    assert.ok((await readGame(p)).pullRatio >= 0.29);
    await p.keyboard.press("Enter");
    await wait(p, "moving");
    assert.equal((await readGame(p)).committedShots, 1);
  });

  for (const action of ["blur", "resize"])
    await test(`${action} cancels an uncommitted charge`, async (p) => {
      const before = await readGame(p);
      await chargePull(p, 0.6);
      if (action === "blur")
        await p.evaluate(() => dispatchEvent(new Event("blur")));
      else await p.setViewportSize({ width: 1000, height: 750 });
      await releasePull(p);
      await p.evaluate(() => window.advanceTime(500));
      assert.equal((await readGame(p)).committedShots, 0);
      assert.deepEqual((await readGame(p)).balls, before.balls);
    });
  await test("captured pointer may release outside controller; second pointer ignored", async (p) => {
    await freeze(p);
    const gesture = await chargePull(p, 0.6),
      before = await readGame(p);
    await p.locator("#power-handle").dispatchEvent("pointerdown", {
      pointerId: 99,
      pointerType: "touch",
      clientY: 0,
    });
    await p.locator("#power-handle").dispatchEvent("pointermove", {
      pointerId: 99,
      pointerType: "touch",
      clientY: 900,
    });
    assert.equal((await readGame(p)).pullRatio, before.pullRatio);
    await p.mouse.move(gesture.x + 250, gesture.y + gesture.distance * 0.6);
    await releasePull(p);
    await p.waitForFunction(
      () => JSON.parse(window.render_game_to_text()).interaction === "striking",
    );
    await p.evaluate(() => window.advanceTime(150));
    assert.equal((await readGame(p)).committedShots, 1);
  });
  await test(
    "reduced motion preserves a single contact impulse",
    async (p) => {
      await pullShot(p, 0.6);
      await wait(p, "moving");
      assert.equal((await readGame(p)).committedShots, 1);
      assert.equal((await readGame(p)).interaction, "idle");
    },
    { reducedMotion: "reduce" },
  );

  const clockStates = [];
  for (const mode of ["burst", "incremental"])
    await test(
      `fixed-step contact clock ${mode}`,
      async (p) => {
        await freeze(p);
        await pullShot(p, 0.6);
        await p.waitForFunction(
          () =>
            JSON.parse(window.render_game_to_text()).interaction === "striking",
        );
        if (mode === "burst") await p.evaluate(() => window.advanceTime(500));
        else
          for (let i = 0; i < 60; i++)
            await p.evaluate(() => window.advanceTime(1000 / 120));
        clockStates.push((await readGame(p)).balls);
      },
      { seed: 42 },
    );
  if (clockStates.length)
    assert.deepEqual(
      clockStates[0],
      clockStates[1],
      "one500ms burst matches60 fixed steps across contact",
    );

  await test(
    "direct whiteball placement validates release and retains last legal point",
    async (p) => {
      const box = await p.locator("#game-viewport canvas").boundingBox(),
        aspect = box.width / box.height,
        h = Math.max(1.62, 2.82 / aspect),
        scale = box.height / h,
        point = (x, z) => ({
          x: box.x + box.width / 2 + x * scale,
          y: box.y + box.height / 2 + z * scale,
        });
      let from = point(-0.7, 0),
        legal = point(-0.8, 0.1),
        invalid = point(0.5, 0.1);
      await p.mouse.move(from.x, from.y);
      await p.mouse.down();
      await p.mouse.move(legal.x, legal.y);
      await p.mouse.move(invalid.x, invalid.y);
      await p.mouse.up();
      assert.equal((await readGame(p)).phase, "placing");
      assert.ok(
        Math.abs(Number(await p.locator("#place-x").inputValue()) + 0.8) < 0.01,
      );
      assert.ok(
        Math.abs(Number(await p.locator("#place-z").inputValue()) - 0.1) < 0.01,
      );
      from = point(-0.8, 0.1);
      legal = point(-0.9, 0.15);
      await p.mouse.move(from.x, from.y);
      await p.mouse.down();
      await p.mouse.move(legal.x, legal.y);
      await p.mouse.up();
      await wait(p, "aiming");
      assert.ok(Math.abs((await readGame(p)).balls[0].x + 0.9) < 0.01);
      assert.ok(Math.abs((await readGame(p)).balls[0].z - 0.15) < 0.01);
    },
    { placement: true },
  );
  await test("handle accessible label and startup lock", async (p) => {
    const handle = p.locator("#power-handle");
    assert.equal(await handle.getAttribute("role"), "slider");
    assert.ok(
      (await handle.getAttribute("aria-label")) ||
        (await handle.getAttribute("aria-labelledby")),
    );
    await freeze(p);
    await pullShot(p, 0.5);
    await p.waitForFunction(
      () => JSON.parse(window.render_game_to_text()).interaction === "striking",
    );
    const before = await readGame(p);
    await p.locator("#game-viewport").focus();
    await p.keyboard.press("ArrowRight");
    await p.keyboard.press("ArrowUp");
    await handle.dispatchEvent("pointerup", { pointerId: 1 });
    const after = await readGame(p);
    assert.equal(after.aim, before.aim);
    assert.equal(after.intentRatio, before.intentRatio);
    assert.equal(after.committedShots, 0);
    assert.equal(await handle.isDisabled(), true);
  });
  for (const action of ["blur", "resize"]) {
    await test(`${action} during pending ownership save invalidates the shot`, async (p) => {
      const before = await readGame(p);
      await chargePull(p, 0.6);
      await p.evaluate(() => {
        const descriptor = Object.getOwnPropertyDescriptor(
          IDBTransaction.prototype,
          "oncomplete",
        );
        window.holdNextCompletion = true;
        Object.defineProperty(IDBTransaction.prototype, "oncomplete", {
          ...descriptor,
          set(callback) {
            descriptor.set.call(this, function (event) {
              if (window.holdNextCompletion) {
                window.holdNextCompletion = false;
                window.releasePending = () => callback.call(this, event);
              } else callback.call(this, event);
            });
          },
        });
      });
      await releasePull(p);
      await p.waitForFunction(() => !!window.releasePending);
      if (action === "blur")
        await p.evaluate(() => dispatchEvent(new Event("blur")));
      else await p.setViewportSize({ width: 1000, height: 750 });
      await p.evaluate(() => window.releasePending());
      await p.waitForFunction(
        () => JSON.parse(window.render_game_to_text()).interaction === "idle",
      );
      await p.evaluate(() => window.advanceTime(500));
      assert.equal((await readGame(p)).committedShots, 0);
      assert.deepEqual((await readGame(p)).balls, before.balls);
    });
  }
  await test("tap without drag never shoots", async (p) => {
    const before = await readGame(p);
    await p.locator("#power-handle").click();
    await p.evaluate(() => window.advanceTime(500));
    assert.equal((await readGame(p)).committedShots, 0);
    assert.deepEqual((await readGame(p)).balls, before.balls);
  });
  await test("pull clearly below the minimum release threshold cancels", async (p) => {
    const before = await readGame(p);
    await chargePull(p, 0.049);
    assert.ok(Math.abs((await readGame(p)).pullRatio - 0.049) < 1e-6);
    await releasePull(p);
    await p.evaluate(() => window.advanceTime(500));
    const after = await readGame(p);
    assert.equal(after.phase, "aiming");
    assert.equal(after.committedShots, 0);
    assert.deepEqual(after.balls, before.balls);
  });
  await test("exact five percent pull reaches the minimum release threshold", async (p) => {
    await chargePull(p, 0.05);
    assert.ok(Math.abs((await readGame(p)).pullRatio - 0.05) < 1e-6);
    await releasePull(p);
    await wait(p, "moving");
    assert.equal((await readGame(p)).committedShots, 1);
  });
  await test(
    "reset cue placement restores default preview without committing",
    async (p) => {
      const reset = p.getByRole("button", {
        name: "Reset cue position",
        exact: true,
      });
      const originalRange = await p.locator("#place-x").inputValue();
      await p.locator("#place-x").focus();
      await p.keyboard.press("ArrowLeft");
      assert.notEqual(await p.locator("#place-x").inputValue(), originalRange);
      await reset.click();
      assert.ok(
        Math.abs(Number(await p.locator("#place-x").inputValue()) + 0.7) <=
          0.0025,
      );
      assert.ok(Math.abs(Number(await p.locator("#place-z").inputValue())) <= .0025);
      assert.equal((await readGame(p)).phase, "placing");
      assert.equal((await readGame(p)).committedShots, 0);
      await p.locator('[data-action="inspect"]').click();
      assert.equal(await reset.isDisabled(), true);
      await p.locator('[data-action="inspect"]').click();
      assert.equal(await reset.isEnabled(), true);
      await p.locator('[data-action="place"]').click();
      await wait(p, "aiming");
      assert.equal(await p.locator('[data-action="reset-placement"]').isDisabled(), true);
      assert.equal((await readGame(p)).balls[0].x, -0.7);
      assert.equal((await readGame(p)).balls[0].z, 0);
    },
    { placement: true },
  );
  assert.deepEqual(errors, []);
} finally {
  await fs.writeFile(
    `${artifacts}/results.json`,
    JSON.stringify({ results, errors, selection: process.env.B3G_PULL_CASE || null }, null, 2),
  );
  await browser.close();
  await server.close();
}
