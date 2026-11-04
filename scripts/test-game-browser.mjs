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
  artifacts = process.env.TEST_ARTIFACT_DIR || "/tmp/blender-gallery-game-qa";
await fs.mkdir(artifacts, { recursive: true });
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
};
const setRange = (page, id, value) =>
  page.locator(id).evaluate((el, value) => {
    el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
  }, String(value));
try {
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
      await page.goto(server.url);
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
      await page.click("[data-page=gallery]");
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
        await start(page);
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
      assert.equal(await page.locator(".asset-card").count(), 22);
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
