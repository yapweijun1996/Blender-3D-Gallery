import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { messages } from "../src/i18n/index.js";
import { LANGUAGE_STORAGE_KEY } from "../src/i18n/preferences.js";
import { PROPS } from "../src/city/layout.js";
import { launchOptions, serveBuild } from "./browser-test-utils.mjs";

// End-to-end check of ?page=sg-heartland: loads the district, walks, orders food, gets in the car and drives, gets out, languages, phone width.
const offline = process.env.CITY_OFFLINE === "1";
const server = offline ? null : await serveBuild();
const base = server?.url ?? "http://127.0.0.1/Blender-3D-Gallery/";
const staticRoot = path.resolve("dist");
const contentTypes = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json" };

let browser, stopping = false;
try {
  browser = await chromium.launch(offline ? { ...launchOptions, args: ["--single-process", "--in-process-gpu", "--disable-gpu", "--enable-unsafe-swiftshader"] } : launchOptions);
  const context = await browser.newContext({ viewport: { width: 1280, height: 1000 }, serviceWorkers: "block", locale: "en" });
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
  page.setDefaultTimeout(180_000);
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  const stage = page.locator(".city-stage");
  const inspect = () => stage.evaluate(element => element.inspectCity());
  const until = (check, seconds = 400) => page.waitForFunction(check, undefined, { timeout: seconds * 1000, polling: 500 });
  const teleport = (x, z) => stage.evaluate((element, [px, pz]) => element.teleport(px, pz), [x, z]);

  await page.goto(base + "?page=sg-heartland");
  await page.waitForSelector(".city-stage[data-state=ready]");
  assert.equal(await page.locator(".city-heading h1").textContent(), messages.en["demo.sg-heartland.title"]);
  await until(() => document.querySelector(".city-stage").inspectCity().calls > 40);
  const first = await inspect();
  assert.ok(first.triangles > 20_000, `scene drew ${first.triangles} triangles`);
  await until(() => document.querySelector(".city-stage").inspectCity().pedestrians > 0);
  await until(() => document.querySelector(".city-stage").inspectCity().props);

  // Walking changes the position and the clip.
  const before = await inspect();
  await page.keyboard.down("ArrowUp");
  await until(() => document.querySelector(".city-stage").inspectCity().clip === "walk");
  await page.waitForTimeout(1500);
  await page.keyboard.up("ArrowUp");
  const after = await inspect();
  assert.ok(Math.hypot(after.x - before.x, after.z - before.z) > 0.2, "the chibi moved");

  // A day passes and the emotes play.
  await until(() => document.querySelector(".city-stage").inspectCity().hour !== 17.5);
  assert.match(await page.locator(".city-clock").textContent(), /^\d\d:\d\d$/);
  await page.locator('[data-emote="wave"]').click();
  await until(() => document.querySelector(".city-stage").inspectCity().clip === "wave");
  await until(() => document.querySelector(".city-stage").inspectCity().task === null, 60);

  // The hawker centre label, then ordering food at a stall.
  await teleport(0, -12);
  await until(() => document.querySelector(".city-place").textContent === "Hawker centre");
  const stall = PROPS.find(p => p.model === "hawker_stall");
  await teleport(stall.x, stall.z + 2.2);
  await until(() => !document.querySelector(".city-action").hidden && document.querySelector(".city-action").textContent.includes("Order"));
  await page.keyboard.press("e");
  await until(() => document.querySelector(".city-stage").inspectCity().task === "hold");
  await until(() => !document.querySelector(".city-toast").hidden);
  await until(() => document.querySelector(".city-stage").inspectCity().task === null, 60);

  // Get in the Proton Saga, drive, brake, get out.
  const { car } = await inspect();
  await teleport(car.x + 3, car.z);
  await until(() => document.querySelector(".city-action").textContent.includes("Get in"));
  await page.keyboard.press("e");
  await until(() => document.querySelector(".city-stage").inspectCity().mode === "drive");
  await page.keyboard.down("ArrowUp");
  await until(() => document.querySelector(".city-stage").inspectCity().car.speed > 2);
  await page.keyboard.up("ArrowUp");
  await page.keyboard.down("ArrowDown");
  await until(() => document.querySelector(".city-stage").inspectCity().car.speed < 3);
  await page.keyboard.up("ArrowDown");
  await page.keyboard.press("e");
  await until(() => document.querySelector(".city-stage").inspectCity().mode === "walk");

  // Languages and a phone-width layout.
  for (const locale of ["zh-Hans", "ms"]) {
    await page.evaluate(([key, value]) => localStorage.setItem(key, value), [LANGUAGE_STORAGE_KEY, locale]);
    await page.reload();
    await page.waitForSelector(".city-stage[data-state=ready]");
    assert.equal(await page.locator(".city-heading h1").textContent(), messages[locale]["demo.sg-heartland.title"]);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(500);
  assert.deepEqual(await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth })), { viewport: 390, document: 390 });
  await page.locator("#demo-breadcrumb a").click();
  await page.waitForTimeout(500);
  assert.equal(await page.locator("#sg-heartland-page canvas").count(), 0);
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ chromium: browser.version(), triangles: first.triangles, drawCalls: first.calls, consoleErrors: errors.length }, null, 2));
} finally {
  stopping = true;
  await browser?.close();
  await server?.close();
}
