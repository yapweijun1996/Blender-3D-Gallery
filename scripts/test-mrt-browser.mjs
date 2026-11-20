import assert from "node:assert/strict";
import { chromium } from "playwright";
import { messages } from "../src/i18n/index.js";
import { launchOptions, serveBuild } from "./browser-test-utils.mjs";

// End-to-end check of ?page=sg-mrt: the station builds, the train stops at the platform, the doors open and shut, the views switch.
const server = await serveBuild();
let browser;
try {
  browser = await chromium.launch(launchOptions);
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, serviceWorkers: "block", locale: "en" });
  const page = await context.newPage();
  page.setDefaultTimeout(120_000);
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  const stage = page.locator(".drive-stage");
  const inspect = () => stage.evaluate(element => element.inspectMrt());
  const at = seconds => stage.evaluate((element, value) => element.setClock(value), seconds);

  await page.goto(server.url + "?page=sg-mrt");
  await page.waitForSelector(".drive-stage[data-state=ready]");
  assert.equal(await page.locator(".drive-heading h1").textContent(), messages.en["demo.sg-mrt.title"]);
  const built = await inspect();
  assert.equal(built.carriages, 3);
  assert.equal(built.screenDoors, 6);

  // Passengers load after the first frame, then wait on the platform.
  await page.waitForFunction(() => document.querySelector('.drive-stage').inspectMrt().loadedPeople >= 3, undefined, { polling: 1000, timeout: 150_000 });
  await at(2);
  await page.waitForFunction(() => document.querySelector('.drive-stage').inspectMrt().people >= 2, undefined, { polling: 500 });

  // Stopped at the platform with the doors open, then shut, then gone.
  await at(20);
  await page.waitForFunction(() => { const s = document.querySelector(".drive-stage").inspectMrt(); return s.phase === "boarding" && Math.abs(s.x) < 0.01; });
  const boarding = await inspect();
  assert.ok(Math.abs(boarding.x) < 0.01 && boarding.doors === 1, `stopped at ${boarding.x}`);
  assert.equal(await page.locator(".mrt-status").textContent(), messages.en["mrt.status.boarding"]);
  await page.screenshot({ path: process.env.MRT_SHOT ?? "/tmp/mrt-platform.png" });
  await at(2);
  await page.waitForFunction(() => { const s = document.querySelector(".drive-stage").inspectMrt(); return s.phase === "arriving" && s.x < -20; });

  // Views.
  for (const view of ["inside", "overview", "platform"]) {
    await page.locator(`[data-view="${view}"]`).click();
    assert.equal(await page.locator(`[data-view="${view}"]`).getAttribute("aria-pressed"), "true");
    assert.equal((await inspect()).view, view);
  }

  // Phone width, and leaving releases the renderer.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(400);
  assert.deepEqual(await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth })), { viewport: 390, document: 390 });
  await page.locator("#demo-breadcrumb a").click();
  await page.waitForTimeout(500);
  assert.equal(await page.locator("#sg-mrt-page canvas").count(), 0);
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ chromium: browser.version(), triangles: built.triangles, drawCalls: built.calls, consoleErrors: errors.length }, null, 2));
} finally {
  await browser?.close();
  await server?.close();
}
