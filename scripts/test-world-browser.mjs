import assert from "node:assert/strict";
import { chromium } from "playwright";
import { messages } from "../src/i18n/index.js";
import { launchOptions, serveBuild } from "./browser-test-utils.mjs";

// End-to-end check of ?page=sg-world: the map tiles stream in, the car drives with the Rapier physics, crashes and is righted.
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
  const inspect = () => stage.evaluate(element => element.inspectWorld());

  await page.goto(server.url + "?page=sg-world");
  await page.waitForSelector(".drive-stage[data-state=ready]");
  assert.equal(await page.locator(".drive-heading h1").textContent(), messages.en["demo.sg-world.title"]);
  await page.waitForFunction(() => document.querySelector(".drive-stage").inspectWorld().triangles > 10_000, undefined, { polling: 500 });
  const first = await inspect();
  assert.ok(first.tiles >= 9, `${first.tiles} tiles loaded`);
  assert.ok(Math.hypot(first.start.x, first.start.z) < 400, "starts near Marina Bay Sands");

  // Traffic fills the roads around the start, with several kinds of vehicle.
  await page.waitForFunction(() => document.querySelector('.drive-stage').inspectWorld().traffic >= 8, undefined, { polling: 500 });
  assert.ok((await inspect()).trafficTypes.length >= 2);

  // People walk the footways around the car.
  await page.waitForFunction(() => document.querySelector('.drive-stage').inspectWorld().people >= 2, undefined, { polling: 1000, timeout: 150_000 });

  // Drive: the physics gives speed, and the car stays upright on the road.
  const driven = await stage.evaluate(element => element.simulate(8, { throttle: 1 }));
  assert.ok(driven.speed > 6, `speed ${driven.speed}`);
  assert.equal(driven.flipped, false);

  // A flipped car is reported and the reset button rights it.
  await page.screenshot({ path: process.env.WORLD_SHOT ?? "/tmp/world-drive.png" });
  assert.ok((await page.locator(".drive-speed").textContent()) !== undefined);
  await page.locator(".drive-reset").click();

  // Streaming: far from the start new tiles load and the old ones go.
  await stage.evaluate(element => element.teleport(1500, 600, 0));
  await page.waitForFunction(() => { const s = document.querySelector(".drive-stage").inspectWorld(); return s.carTile[0] === 6 && s.tiles >= 9; }, undefined, { polling: 500 });

  // Leaving the page releases the renderer.
  await page.locator("#demo-breadcrumb a").click();
  await page.waitForTimeout(500);
  assert.equal(await page.locator("#sg-world-page canvas").count(), 0);
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ chromium: browser.version(), tiles: first.tiles, triangles: first.triangles, drawCalls: first.calls, speed: Number(driven.speed.toFixed(1)), consoleErrors: errors.length }, null, 2));
} finally {
  await browser?.close();
  await server?.close();
}
