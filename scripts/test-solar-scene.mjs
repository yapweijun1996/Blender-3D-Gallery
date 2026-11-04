import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { chromium } from "playwright";
import { serveBuild, launchOptions } from "./browser-test-utils.mjs";
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const artifacts = "models/solar-system/reports";
const results = [];
try {
  for (const width of [1440, 768, 390, 320]) {
    const page = await browser.newPage({
      viewport: { width, height: width === 1440 ? 1000 : 844 },
    });
    const errors = [],
      cancellations = [];
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
    await page.selectOption("#solar-speed", "0");
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
    await page.selectOption("#solar-scale", "realistic");
    assert.match(await page.textContent("#solar-scale-note"), /one shared/);
    await page.selectOption("#solar-select", "earth");
    await page.screenshot({
      path: `${artifacts}/realistic-${width}-earth.png`,
      fullPage: false,
    });
    await page.click("#solar-overview");
    await page.selectOption("#solar-scale", "presentation");
    const still = await page.locator("#solar-canvas canvas").screenshot();
    await page.selectOption("#solar-speed", "100");
    await page.waitForTimeout(400);
    const moving = await page.locator("#solar-canvas canvas").screenshot();
    assert.notDeepEqual(still, moving, "animation changes rendered output");
    await page.selectOption("#solar-speed", "0");
    await page.getByRole("link", { name: "Gallery", exact: true }).click();
    assert.equal(await page.locator("#solar-page canvas").count(), 0);
    await page.locator("[data-asset-id=solar-saturn]").click();
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
      status: "PASS",
      scenarios: [
        "direct route",
        "17 models",
        "selection",
        "focus",
        "realistic ratios",
        "pause speed",
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
  await page.getByRole("link", { name: "Gallery", exact: true }).click();
  await page.waitForTimeout(1000);
  assert.equal(await page.locator("#solar-page canvas").count(), 0);
  await page.close();
  results.push({ status: "PASS", scenario: "cancel in-flight route load" });
  await fs.writeFile(
    `${artifacts}/scene-validation.json`,
    JSON.stringify(results, null, 2) + "\n",
  );
} finally {
  await browser.close();
  await server.close();
}
