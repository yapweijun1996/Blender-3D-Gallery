import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { chromium } from "playwright";
import { serveBuild, launchOptions } from "./browser-test-utils.mjs";
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const artifacts =
  process.env.TEST_ARTIFACT_DIR || "models/solar-system/reports";
await fs.mkdir(artifacts, { recursive: true });
const results = [];
async function waitForPausedDraws(page) {
  await page.evaluate(() => {
    window.solarDrawSample = {
      count: window.solarDrawCalls,
      since: performance.now(),
    };
  });
  await page.waitForFunction(
    () => {
      const sample = window.solarDrawSample;
      if (sample.count !== window.solarDrawCalls) {
        sample.count = window.solarDrawCalls;
        sample.since = performance.now();
      }
      return performance.now() - sample.since >= 200;
    },
    null,
    { polling: 100 },
  );
  return page.evaluate(() => window.solarDrawCalls);
}
async function returnToModels(page) {
  if (await page.locator("#menu-trigger").isVisible())
    await page.locator("#menu-trigger").click();
  await page.getByRole("link", { name: "3D Models", exact: true }).click();
}
try {
  for (const width of [1440, 768, 390, 320]) {
    const page = await browser.newPage({
      viewport: { width, height: width === 1440 ? 1000 : 844 },
    });
    // Software WebGL screenshots can take longer under shared runner load.
    page.setDefaultTimeout(90000);
    await page.addInitScript(() => {
      window.solarDrawCalls = 0;
      for (const context of [WebGLRenderingContext, WebGL2RenderingContext]) {
        for (const method of [
          "drawArrays",
          "drawElements",
          "drawArraysInstanced",
          "drawElementsInstanced",
        ]) {
          const original = context.prototype[method];
          if (!original) continue;
          context.prototype[method] = function (...args) {
            window.solarDrawCalls++;
            return original.apply(this, args);
          };
        }
      }
    });
    const errors = [],
      cancellations = [], modelRequests = [];
    page.on("request", (request) => {
      if (new URL(request.url()).pathname.endsWith(".glb")) modelRequests.push(new URL(request.url()).pathname);
    });
    page.on("requestfailed", (request) => {
      const error = request.failure()?.errorText;
      if (error === "net::ERR_ABORTED") cancellations.push(request.url());
      else errors.push(request.url() + ": " + error);
    });
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => {
      if (m.type() === "error") errors.push(m.text());
    });
    console.log("CHECK viewport", width);
    await page.goto(server.url + "?page=solar");
    try {
      await page.waitForFunction(
        () => document.querySelector("#solar-status")?.textContent === "",
        null,
        { timeout: 60000 },
      );
    } catch (error) {
      console.error(
        "LOAD FAILED",
        width,
        await page.locator("#solar-page").innerText(),
        errors,
      );
      throw error;
    }
    assert.equal(await page.locator("#solar-select option").count(), 18);
    assert.equal(modelRequests.length, 17, "one model request per scene body");
    for (const id of ["nasa-earth", "nasa-moon", "nasa-saturn", "nasa-vesta", "solar-asteroid-03"]) {
      assert.ok(modelRequests.some(url => url.includes(`${id}-`)), `optimized model requested: ${id}`);
    }
    await page.selectOption("#solar-speed", "0");
    await page.waitForTimeout(350);
    const pausedDraws = await page.evaluate(() => window.solarDrawCalls);
    assert.ok(pausedDraws > 0, "the scene rendered before pausing");
    await page.waitForTimeout(350);
    assert.equal(
      await page.evaluate(() => window.solarDrawCalls),
      pausedDraws,
      "paused scene stops GPU draw calls",
    );
    await page.screenshot({
      path: `${artifacts}/scene-${width}.png`,
      fullPage: false,
    });
    for (const position of [0, 0.5, 1]) {
      await page.evaluate(
        (position) =>
          scrollTo(
            0,
            (document.documentElement.scrollHeight - innerHeight) * position,
          ),
        position,
      );
      assert.equal(
        await page.evaluate(
          () => document.documentElement.scrollWidth > innerWidth,
        ),
        false,
      );
    }
    await page.evaluate(() => scrollTo(0, 0));
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    );
    assert.equal(overflow, false, `overflow at ${width}`);
    for (const id of ["earth", "saturn", "sun", "comet"]) {
      await page.selectOption("#solar-select", id);
      assert.notEqual(
        await page.textContent("#solar-name"),
        "Our planetary neighborhood",
      );
      await page.screenshot({
        path: `${artifacts}/scene-${width}-${id}.png`,
        fullPage: false,
      });
    }
    for (const [id, linkId] of [["sun", "nasa-sun"], ["earth", "nasa-earth"], ["saturn", "nasa-saturn"], ["moon", "nasa-moon"], ["asteroid-01", "nasa-vesta"], ["asteroid-02", "nasa-eros"], ["comet", "nasa-tempel-1"]]) {
      await page.selectOption("#solar-select", id);
      assert.equal(await page.locator("#solar-model-link").getAttribute("href"), `?model=${linkId}`);
      assert.match(await page.locator("#solar-accuracy").innerText(), /NASA/);
    }
    await page.selectOption("#solar-select", "comet");
    assert.match(await page.locator("#solar-name").innerText(), /Tempel 1/);
    assert.match(await page.locator("#solar-facts").innerText(), /Illustrative/);
    await page.selectOption("#solar-scale", "realistic");
    assert.match(await page.textContent("#solar-scale-note"), /one shared/);
    await page.selectOption("#solar-select", "earth");
    await page.screenshot({
      path: `${artifacts}/realistic-${width}-earth.png`,
      fullPage: false,
    });
    await page.click("#solar-overview");
    await page.selectOption("#solar-scale", "presentation");
    const animationDrawsBefore = await waitForPausedDraws(page);
    await page.locator("#solar-canvas canvas").evaluate((canvas) => canvas.scrollIntoView({ behavior: "instant", block: "start" }));
    const still = await page.locator("#solar-canvas canvas").screenshot();
    await page.selectOption("#solar-speed", "100");
    await page.waitForFunction(
      (previous) => window.solarDrawCalls > previous,
      animationDrawsBefore,
      { polling: 100 },
    );
    // Pause after verified animation progress so screenshot stability checks
    // do not run alongside the continuous render loop.
    await page.selectOption("#solar-speed", "0");
    const animationDrawsAfter = await waitForPausedDraws(page);
    assert.ok(
      animationDrawsAfter > animationDrawsBefore,
      "animation advances GPU draw calls",
    );
    await page.locator("#solar-canvas canvas").evaluate((canvas) => canvas.scrollIntoView({ behavior: "instant", block: "start" }));
    const moving = await page.locator("#solar-canvas canvas").screenshot();
    assert.notDeepEqual(still, moving, "animation changes rendered output");
    assert.equal(
      await page.evaluate(() => window.solarDrawCalls),
      animationDrawsAfter,
      "paused animation remains settled during capture",
    );
    await returnToModels(page);
    assert.equal(await page.locator("#solar-page canvas").count(), 0);
    await page.locator("[data-asset-id=solar-saturn]").first().click();
    await page.waitForFunction(
      () =>
        document.querySelector("#viewport canvas") &&
        !document.querySelector("#viewer-status").textContent,
    );
    await page.screenshot({
      path: `${artifacts}/gallery-viewer-${width}.png`,
      fullPage: false,
    });
    await page.click("#reset-view");
    await page.click("#close-viewer");
    assert.equal(await page.locator("#viewport canvas").count(), 0);
    assert.deepEqual(errors, []);
    results.push({
      width,
      transportCancellations: cancellations,
      animationDrawsBefore,
      animationDrawsAfter,
      status: "PASS",
      scenarios: [
        "direct route",
        "17 models",
        "selection",
        "focus",
        "realistic ratios",
        "pause speed",
        "paused scene stops GPU draw calls",
        "overview",
        "gallery return",
        "viewer reset close",
        "no overflow",
        "no browser errors",
      ],
    });
    await page.close();
    console.log("PASS solar scene", width);
  }
  const page = await browser.newPage();
  await page.goto(server.url + "?page=solar");
  await returnToModels(page);
  await page.waitForTimeout(1000);
  assert.equal(await page.locator("#solar-page canvas").count(), 0);
  await page.close();
  results.push({ status: "PASS", scenario: "cancel in-flight route load" });
  server.setFault(({ relative }) => relative.includes("nasa-earth-") && relative.endsWith(".glb") ? { status: 503 } : null);
  const failurePage = await browser.newPage();
  await failurePage.goto(server.url + "?page=solar");
  await failurePage.waitForFunction(() => document.querySelector("#solar-status")?.textContent.includes("could not load"), null, { timeout: 60000 });
  await returnToModels(failurePage);
  assert.equal(await failurePage.locator("#solar-page canvas").count(), 0);
  server.setFault(null);
  await failurePage.goto(server.url + "?page=solar");
  await failurePage.waitForFunction(() => document.querySelector("#solar-status")?.textContent === "", null, { timeout: 60000 });
  assert.equal(await failurePage.locator("#solar-select option").count(), 18);
  await failurePage.close();
  results.push({ status: "PASS", scenario: "optimized model failure and route retry" });
  await fs.writeFile(
    `${artifacts}/scene-validation.json`,
    JSON.stringify(results, null, 2) + "\n",
  );
} finally {
  await browser.close();
  await server.close();
}
