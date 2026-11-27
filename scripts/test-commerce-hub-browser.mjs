// Production-build browser check for the Commerce Network demo. The CSP stays enforced.
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { chromium } from "playwright";
import { serveBuild, launchOptions } from "./browser-test-utils.mjs";
import { messages } from "../src/i18n/index.js";

const out = process.env.TEST_ARTIFACT_DIR || "output/commerce-hub-browser";
await fs.mkdir(out, { recursive: true });
const server = await serveBuild("dist");
const browser = await chromium.launch(launchOptions);
const pass = (text) => console.log("PASS " + text);
// Points on each module's own body in the 1536x1024 composition frame.
const CLICKS = {
  shop: [[260, 380], [290, 520]], warehouse: [[820, 150], [640, 270]], delivery: [[1150, 430], [1440, 505]],
  payment: [[370, 720], [372, 800]], analytics: [[760, 880], [765, 945]], automation: [[1150, 700], [1145, 800]],
  bags: [[720, 470], [768, 640]],
};
const ready = (page) => page.locator('.ch-stage[data-state="ready"]').waitFor({ timeout: 60000 });

async function open(options = {}) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, serviceWorkers: "block", ...options });
  const page = await context.newPage();
  const errors = [];
  page.on("console", (message) => message.type() === "error" && errors.push(message.text()));
  page.on("pageerror", (error) => errors.push(error.message));
  return { context, page, errors };
}

try {
  for (const [width, height] of [[1440, 900], [768, 1024], [375, 812]]) {
    const { context, page, errors } = await open({ viewport: { width, height }, hasTouch: width < 700 });
    await page.goto(server.url + "?page=commerce-hub");
    await ready(page);
    assert.equal(await page.locator("canvas").count(), 1);
    assert.equal(await page.locator(".ch-label").count(), 7);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `overflow at ${width}`);
    const stage = await page.locator(".ch-stage").boundingBox();
    for (const label of await page.locator('.ch-label:not([data-module="bags"])').all()) {
      const box = await label.boundingBox();
      assert.ok(box.width >= 44 && box.height >= 44, "label target");
      assert.ok(box.x >= stage.x && box.x + box.width <= stage.x + stage.width + 1, "label inside stage");
    }
    const stats = await page.locator(".ch-stage").evaluate((el) => ({ calls: +el.dataset.calls, triangles: +el.dataset.triangles }));
    await page.waitForTimeout(600);
    await page.locator(".ch-stage").screenshot({ path: `${out}/overview-${width}.png` });
    // Every module must actually be drawn: a broken transform would silently hide its triangles.
    assert.ok(stats.triangles > 150_000, `all modules rendered (${stats.triangles})`);
    await page.locator('.ch-label[data-module="warehouse"]').click();
    assert.equal(await page.locator(".ch-panel h2").innerText(), messages.en["commerce.warehouse.label"]);
    assert.equal(await page.locator('.ch-label[data-module="warehouse"]').getAttribute("aria-pressed"), "true");
    await page.waitForTimeout(900);
    await page.locator(".ch-stage").screenshot({ path: `${out}/focus-${width}.png` });
    await page.keyboard.press("Escape");
    assert.equal(await page.locator(".ch-panel h2").innerText(), messages.en["commerce.overview.title"]);
    // Zoom out and in with the buttons, then click the bags themselves.
    await page.waitForTimeout(900);
    const canvas = page.locator(".ch-stage canvas");
    const before = await canvas.screenshot();
    await page.locator('[data-zoom="out"]').click();
    await page.waitForTimeout(200);
    assert.ok(!before.equals(await canvas.screenshot()), "zoom out changes the view");
    await page.locator('[data-zoom="reset"]').click();
    await page.waitForTimeout(900);
    const box = await canvas.boundingBox();
    // A drag that returns to its start must not select anything.
    const cx = box.x + box.width / 2, cy = box.y + box.height / 2;
    await page.mouse.move(cx, cy);
    await page.mouse.down();
    await page.mouse.move(cx + 80, cy, { steps: 4 });
    await page.mouse.move(cx, cy, { steps: 4 });
    await page.mouse.up();
    assert.equal(await page.locator(".ch-panel h2").innerText(), messages.en["commerce.overview.title"]);
    await page.locator('[data-zoom="reset"]').click();
    await page.waitForTimeout(900);
    await page.mouse.click(box.x + box.width * 0.5, box.y + box.height * (box.width / box.height > 1.2 ? 0.5 : 0.52));
    assert.equal(await page.locator(".ch-panel h2").innerText(), messages.en["commerce.bags.label"]);
    await page.keyboard.press("Escape");
    // Click every module's own body, not only the centre.
    for (const id of ["shop", "warehouse", "delivery", "payment", "analytics", "automation", "bags"]) {
      await page.locator('[data-zoom="reset"]').click();
      await page.waitForTimeout(800);
      const area = await canvas.boundingBox();
      for (const [px, py] of CLICKS[id]) {
        // Anchor-frame pixels to canvas pixels: the frame is fitted inside the canvas and centred.
        const unit = Math.min(area.width / 1536, area.height / 1024);
        await page.mouse.click(area.x + area.width / 2 + (px - 768) * unit, area.y + area.height / 2 + (py - 512) * unit);
        assert.equal(await page.locator(".ch-panel h2").innerText(), messages.en[`commerce.${id}.label`], `${id} at ${px},${py} (${width}px)`);
        await page.locator('[data-zoom="reset"]').click();
        await page.waitForTimeout(800);
      }
    }
    assert.deepEqual(errors, []);
    pass(`${width}px loads seven modules, labels focus and Escape returns (${stats.calls} first-frame calls, ${stats.triangles} triangles)`);
    await context.close();
  }
  for (const language of ["zh-Hans", "ms"]) {
    const { context, page, errors } = await open();
    await page.addInitScript((value) => localStorage.setItem("b3g:language:v1", value), language);
    await page.goto(server.url + "?page=commerce-hub");
    await ready(page);
    const shown = await page.evaluate(() => document.documentElement.lang);
    if (shown !== language) {
      await page.locator(".language-trigger").first().click();
      await page.locator(`[data-language="${language}"], [lang="${language}"], input[value="${language}"]`).first().click();
      await page.keyboard.press("Escape");
    }
    assert.equal(await page.locator(".commerce-hub h1").innerText(), messages[language]["commerce.title"]);
    assert.equal(await page.locator('.ch-label[data-module="shop"]').innerText(), messages[language]["commerce.shop.label"]);
    await page.waitForTimeout(500);
    await page.locator(".ch-stage").screenshot({ path: `${out}/overview-${language}.png` });
    assert.deepEqual(errors, []);
    pass(`${language} labels and headings`);
    await context.close();
  }
  {
    const { context, page, errors } = await open({ reducedMotion: "reduce" });
    await page.goto(server.url + "?page=commerce-hub");
    await ready(page);
    await page.waitForTimeout(400);
    const first = await page.locator(".ch-stage canvas").screenshot();
    await page.waitForTimeout(900);
    assert.ok(first.equals(await page.locator(".ch-stage canvas").screenshot()), "reduced motion is still");
    assert.deepEqual(errors, []);
    pass("reduced motion keeps a still frame");
    await context.close();
  }
  {
    const { context, page, errors } = await open();
    await page.goto(server.url + "?page=commerce-hub");
    await ready(page);
    const first = await page.locator(".ch-stage canvas").screenshot();
    await page.waitForTimeout(900);
    assert.ok(!first.equals(await page.locator(".ch-stage canvas").screenshot()), "scene animates");
    await page.evaluate(() => { window.hubCanvas = document.querySelector(".ch-stage canvas"); });
    await page.locator("#demo-breadcrumb a").click();
    await page.locator('.demo-card[data-demo-id="commerce-hub"]').waitFor();
    assert.ok(await page.evaluate(() => (window.hubCanvas.getContext("webgl2") ?? window.hubCanvas.getContext("webgl")).isContextLost()), "context released");
    pass("animates, then releases its WebGL context on leaving");
    // Return inside the same document, so a stale disposed instance would be caught.
    await page.locator('.demo-card[data-demo-id="commerce-hub"] h2 a').click();
    await ready(page);
    assert.ok(await page.evaluate(() => {
      const canvas = document.querySelector(".ch-stage canvas");
      return canvas !== window.hubCanvas && !(canvas.getContext("webgl2") ?? canvas.getContext("webgl")).isContextLost();
    }), "remounted with a live context");
    pass("returning in the same document mounts a fresh live canvas");
    await page.evaluate(() => {
      const canvas = document.querySelector(".ch-stage canvas");
      (canvas.getContext("webgl2") ?? canvas.getContext("webgl")).getExtension("WEBGL_lose_context").loseContext();
    });
    await page.locator('.ch-stage[data-state="interrupted"] .ch-loading button').waitFor();
    assert.equal(await page.locator(".ch-stage").getAttribute("aria-busy"), "false");
    assert.ok(await page.locator(".ch-reset").isDisabled());
    assert.equal(await page.locator("[data-zoom]:disabled").count(), 3);
    pass("context loss shows a focusable recovery and disables controls");
    assert.deepEqual(errors, []);
    await context.close();
  }
  {
    const { context, page } = await open();
    let fail = true;
    await page.route(/shop-[^/]*\.glb/, (route) => (fail ? route.abort() : route.continue()));
    await page.goto(server.url + "?page=commerce-hub");
    await page.locator('.ch-stage[data-state="error"]').waitFor();
    // A language change must not delete the retry button.
    await page.locator(".language-trigger").first().click();
    await page.locator('[data-language="ms"], [lang="ms"], input[value="ms"]').first().click();
    await page.keyboard.press("Escape");
    assert.equal(await page.locator(".ch-loading button").count(), 1);
    fail = false;
    await page.locator(".ch-loading button").click();
    await ready(page);
    pass(`a failed module offers retry and recovers (steady frame ${await page.locator(".ch-stage").getAttribute("data-frame-calls")} calls)`);
    await context.close();
  }
} finally {
  await browser.close();
  await server.close();
}
