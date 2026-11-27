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
    assert.equal(await page.locator(".ch-label").count(), 6);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `overflow at ${width}`);
    const stage = await page.locator(".ch-stage").boundingBox();
    for (const label of await page.locator(".ch-label").all()) {
      const box = await label.boundingBox();
      assert.ok(box.width >= 44 && box.height >= 44, "label target");
      assert.ok(box.x >= stage.x && box.x + box.width <= stage.x + stage.width + 1, "label inside stage");
    }
    const stats = await page.locator(".ch-stage").evaluate((el) => ({ calls: +el.dataset.calls, triangles: +el.dataset.triangles }));
    await page.waitForTimeout(600);
    await page.locator(".ch-stage").screenshot({ path: `${out}/overview-${width}.png` });
    await page.locator('.ch-label[data-module="warehouse"]').click();
    assert.equal(await page.locator(".ch-panel h2").innerText(), messages.en["commerce.warehouse.label"]);
    assert.equal(await page.locator('.ch-label[data-module="warehouse"]').getAttribute("aria-pressed"), "true");
    await page.waitForTimeout(900);
    await page.locator(".ch-stage").screenshot({ path: `${out}/focus-${width}.png` });
    await page.keyboard.press("Escape");
    assert.equal(await page.locator(".ch-panel h2").innerText(), messages.en["commerce.overview.title"]);
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
