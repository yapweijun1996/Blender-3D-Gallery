import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { messages } from "../src/i18n/index.js";
import { LANGUAGE_STORAGE_KEY } from "../src/i18n/preferences.js";
import { launchOptions, serveBuild } from "./browser-test-utils.mjs";

// End-to-end check of ?page=drive-jb: loads the model kit, drives, stops at the checkpoint, stamps, arrives, replays.
const offline = process.env.DRIVE_OFFLINE === "1";
const server = offline ? null : await serveBuild();
const base = server?.url ?? "http://127.0.0.1/Blender-3D-Gallery/";
const staticRoot = path.resolve("dist");
const contentTypes = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json" };

let browser, stopping = false;
try {
  browser = await chromium.launch(offline ? {
    ...launchOptions, args: ["--single-process", "--in-process-gpu", "--disable-gpu", "--enable-unsafe-swiftshader"],
  } : launchOptions);
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, serviceWorkers: "block", locale: "en" });
  await context.route("**/*", async route => {
    const url = new URL(route.request().url());
    if (!url.href.startsWith(base)) return route.abort();
    if (!offline) return route.continue();
    const rootPath = new URL(base).pathname;
    const file = path.resolve(staticRoot, decodeURIComponent(url.pathname.slice(rootPath.length)) || "index.html");
    if (!file.startsWith(staticRoot + path.sep)) return route.abort();
    try {
      await route.fulfill({ body: await readFile(file), contentType: contentTypes[path.extname(file)] ?? "application/octet-stream" });
    } catch (error) {
      if (stopping) return;
      if (error.code !== "ENOENT") throw error;
      await route.fulfill({ status: 404 });
    }
  });
  const page = await context.newPage();
  page.setDefaultTimeout(120_000);
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  const stage = page.locator(".drive-stage");
  const inspect = () => stage.evaluate(element => element.inspectDrive());
  const until = (check, seconds = 400) => page.waitForFunction(check, undefined, { timeout: seconds * 1000, polling: 500 });
  const driveTo = distance => stage.evaluate((element, value) => element.driveTo(value), distance);

  await page.goto(base + "?page=drive-jb");
  await page.waitForSelector(".drive-stage[data-state=ready]");
  assert.equal(await page.locator(".drive-heading h1").textContent(), messages.en["demo.drive-jb.title"]);

  // The kit loads, the road and scenery draw, and the car starts moving by itself.
  await until(() => document.querySelector(".drive-stage").inspectDrive().calls > 20);
  const first = await inspect();
  assert.equal(first.mode, "auto");
  assert.ok(first.triangles > 20_000, `scene drew ${first.triangles} triangles`);
  await until(() => document.querySelector(".drive-stage").inspectDrive().s > 8);
  await until(() => document.querySelector(".drive-stage").inspectDrive().driver);

  // Switching to manual by button and by keyboard.
  await page.locator('.drive-modes [data-mode="manual"]').click();
  assert.equal(await page.locator('.drive-modes [data-mode="manual"]').getAttribute("aria-pressed"), "true");
  await page.locator('.drive-modes [data-mode="auto"]').click();
  assert.equal((await inspect()).mode, "auto");
  await page.keyboard.down("ArrowUp");
  assert.equal((await inspect()).mode, "manual");
  await page.keyboard.up("ArrowUp");
  await page.locator('.drive-modes [data-mode="auto"]').click();

  // Pause and play.
  await page.locator(".drive-pause").click();
  assert.equal((await inspect()).paused, true);
  await page.locator(".drive-pause").click();

  // Woodlands checkpoint: the car stops, the passport and stamp mini-game opens, the barrier lifts, driving resumes.
  const { stop, length } = await inspect();
  await driveTo(stop - 5);
  await until(() => document.querySelector(".drive-stage").inspectDrive().stage === "passport");
  await page.locator(".drive-passport-action").click();
  // Stamp when the marker is inside the green zone; retry if a slow frame made the click miss.
  for (let attempt = 0; attempt < 12; attempt++) {
    await page.waitForFunction(() => {
      const marker = document.querySelector(".drive-stamp-marker"), zone = document.querySelector(".drive-stamp-zone");
      if (!marker.style.left) return false;
      const m = marker.getBoundingClientRect(), z = zone.getBoundingClientRect(), centre = m.left + m.width / 2;
      return centre > z.left + 14 && centre < z.right - 14;
    }, undefined, { timeout: 120_000, polling: 50 });
    await page.locator(".drive-passport-action").click();
    const stageNow = (await inspect()).stage;
    if (stageNow !== "passport") break;
    await page.waitForTimeout(800);
  }
  await until(() => document.querySelector(".drive-stage").inspectDrive().stage === "drive");
  assert.ok((await inspect()).s >= stop - 6);

  // Arrival and replay (lights and slow traffic are switched off so the run finishes quickly).
  await stage.evaluate(element => element.freeRoad());
  await driveTo(length - 60);
  await until(() => document.querySelector(".drive-stage").inspectDrive().stage === "arrived", 900);
  assert.equal(await page.locator(".drive-arrival").isVisible(), true);
  await page.locator(".drive-replay").click();
  await until(() => document.querySelector(".drive-stage").inspectDrive().s < 100);

  // Languages and a phone-width layout.
  for (const locale of ["zh-Hans", "ms"]) {
    await page.evaluate(([key, value]) => localStorage.setItem(key, value), [LANGUAGE_STORAGE_KEY, locale]);
    await page.reload();
    await page.waitForSelector(".drive-stage[data-state=ready]");
    assert.equal(await page.locator(".drive-heading h1").textContent(), messages[locale]["demo.drive-jb.title"]);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(500);
  assert.deepEqual(await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth })), { viewport: 390, document: 390 });

  // Leaving the page releases the renderer.
  await page.locator("#demo-breadcrumb a").click();
  await page.waitForTimeout(500);
  assert.equal(await page.locator("#drive-jb-page canvas:not(.drive-minimap)").count(), 0);
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ chromium: browser.version(), triangles: first.triangles, drawCalls: first.calls, consoleErrors: errors.length }, null, 2));
} finally {
  stopping = true;
  await browser?.close();
  await server?.close();
}
