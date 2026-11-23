import assert from "node:assert/strict";
import { chromium } from "playwright";
import { launchOptions, serveBuild } from "./browser-test-utils.mjs";

const APPROACH = "646887291:0"; // Mount Rosie Road
const PRIVATE_ARM = "33876790:0";
const PUBLIC_ROADS = new Set(["33875671:0", "33875672:1", "261041684:0", "261041685:0",
  "646368536:0", "646886085:0", "274465127:0"]); // Goldhill Avenue, Goldhill Place and Mount Rosie Terrace.
const requiredTiles = ["-13_-18", "-12_-18", "-13_-17", "-12_-17"];
const observer = { x: -3072, z: -4233 }; // Park clear of the junction, within the ambient spawn radius.
const start = { x: -2975.1743, z: -4258.9831, heading: .5243 }; // A straight section of the private arm.

async function observeTraffic(stage, baseline) {
  const approaches = new Set(), completedApproaches = new Set(), privateVisits = new Set(), privateTurns = new Set(), movingPublic = new Set();
  const firstPublicPose = new Map();
  let seconds = 0;
  while (seconds < 120) {
    const frames = await stage.evaluate(element => Array.from({ length: 20 }, () => {
      element.simulate(.25, { brake: 1 });
      return element.inspectTraffic();
    }));
    for (const cars of frames) {
      seconds += .25;
      for (const car of cars) {
        if (car.edgeId === APPROACH) approaches.add(car.id);
        if (car.edgeId === PRIVATE_ARM) {
          privateVisits.add(car.id);
          if (approaches.has(car.id)) privateTurns.add(car.id);
        }
        if (!PUBLIC_ROADS.has(car.edgeId)) continue;
        const first = firstPublicPose.get(car.id);
        if (!first) firstPublicPose.set(car.id, car);
        else if (Math.hypot(car.x - first.x, car.z - first.z) > 3) movingPublic.add(car.id);
      }
      for (const id of approaches) {
        if (!cars.some(car => car.id === id && car.edgeId === APPROACH)) completedApproaches.add(id);
      }
    }
    if (!baseline) assert.equal(privateVisits.size, 0, "ambient vehicles stay off the mapped private arm");
    if (movingPublic.size && (baseline ? privateTurns.size : seconds >= 20 && completedApproaches.size >= 2)) break;
  }
  assert.ok(movingPublic.size, "ambient cars continue to move along public roads near Mount Rosie");
  if (baseline) assert.ok(privateTurns.size > 0, "a baseline car takes the private turn from the public approach");
  else assert.ok(completedApproaches.size >= 2, "ambient cars reach and finish traversing the public Mount Rosie approach");
  return { seconds, approaches: approaches.size, completedApproaches: completedApproaches.size, privateVisits: privateVisits.size,
    privateTurns: privateTurns.size, movingPublic: movingPublic.size };
}

async function drivePrivateRoad(page, stage, pause) {
  await stage.evaluate((element, pose) => {
    element.teleport(pose.x, pose.z, pose.heading);
    element.simulate(1.5, { brake: 1 });
  }, start);
  const before = await stage.evaluate(element => element.inspectWorld());
  const support = await stage.evaluate((element, point) => element.inspectRoad(point.x, point.z), start);
  assert.equal(support.edgeId, PRIVATE_ARM, "the private road remains in the player's mapped geometry");
  assert.equal(support.groundY, 0, "the private road still has ground support");
  assert.ok(before.groundedWheels >= 3, "the player's wheels settle on the road");
  await pause.click();
  await page.clock.pauseAt(await page.evaluate(() => Date.now() + 3000));
  let after = before, advance = 0;
  try {
    await page.keyboard.down("ArrowUp");
    for (let elapsed = 0; elapsed < 5000 && advance <= 6; elapsed += 100) {
      await page.clock.runFor(100);
      after = await stage.evaluate(element => element.inspectWorld());
      advance = (after.x - before.x) * Math.sin(start.heading) + (after.z - before.z) * Math.cos(start.heading);
    }
  } finally {
    try {
      await page.keyboard.up("ArrowUp");
    } finally {
      await page.clock.resume();
    }
  }
  const dx = after.x - before.x, dz = after.z - before.z;
  const crossTrack = Math.abs(dx * Math.cos(start.heading) - dz * Math.sin(start.heading));
  assert.ok(advance > 6 && advance < 30 && crossTrack < 2, `keyboard driving follows the private road: ${JSON.stringify({ advance, crossTrack, after })}`);
  assert.ok(after.groundedWheels >= 3 && after.damage < .05, "the player remains grounded without a collision");
  assert.equal(await stage.evaluate((element, point) => element.inspectRoad(point.x, point.z).edgeId, after), PRIVATE_ARM);
  return { advance, crossTrack, groundedWheels: after.groundedWheels, damage: after.damage };
}

async function loadMountRosie(page, stage, pause) {
  // Drain Bayfront's serial tile queue before requesting the remote neighborhood.
  await pause.click();
  await page.waitForFunction(() => {
    const { loading } = document.querySelector(".world-stage").inspectWorld();
    return !loading.pending && !loading.ready;
  }, null, { polling: 250, timeout: 120_000 });
  const arrivals = requiredTiles.map(key => page.waitForResponse(response => {
    const tile = new URL(response.url()).pathname.match(/\/(-?\d+_-?\d+)(?:-[\w-]+)?\.json$/)?.[1];
    return tile === key && response.ok();
  }, { timeout: 150_000 }));
  // Use a complete local graph so ambient spawn choices include the same neighboring roads.
  const installed = page.waitForFunction(() => {
    const { carTile, loading } = document.querySelector(".world-stage").inspectWorld();
    if (loading.failed) throw new Error("world tile stream failed");
    return carTile[0] === -13 && carTile[1] === -17 && !loading.pending && !loading.ready;
  }, null, { polling: 250, timeout: 150_000 });
  await Promise.all([...arrivals, installed, stage.evaluate((element, point) => element.teleport(point.x, point.z), observer)]);
  const edges = await stage.evaluate((element, arm) => {
    element.simulate(.1, { brake: 1 });
    return [element.inspectRoad(-2985.9, -4266.825).edgeId,
      element.inspectRoad(-3021.366, -4195.242).edgeId, element.inspectRoad(arm.x, arm.z).edgeId];
  }, start);
  assert.deepEqual(edges, [APPROACH, "33875671:0", PRIVATE_ARM], "the public feeder, public approach and private arm are installed");
}

async function checkWorld(browser, baseUrl, baseline = false) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, serviceWorkers: "block", locale: "en" });
  try {
    const page = await context.newPage();
    await page.clock.install();
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
    const url = new URL(baseUrl);
    url.searchParams.set("page", "sg-world");
    await page.goto(url.href, { waitUntil: "domcontentloaded" });
    const stage = page.locator(".world-stage[data-state=ready]");
    await stage.waitFor({ timeout: 120_000 });
    assert.ok(await stage.evaluate(element => typeof element.inspectTraffic === "function"), "the world exposes live traffic diagnostics");
    const pause = page.locator(".drive-pause");
    await loadMountRosie(page, stage, pause);
    const traffic = await observeTraffic(stage, baseline);
    const drive = await drivePrivateRoad(page, stage, pause);
    assert.equal(await stage.evaluate(element => element.inspectWorld().loading.failed), 0, "world tiles load successfully");
    assert.deepEqual(errors, []);
    return { ...traffic, drive };
  } finally {
    await context.close();
  }
}

let browser, server, baselineServer;
try {
  const site = process.env.WORLD_ACCESS_SITE;
  if (!site) server = await serveBuild(process.env.WORLD_ACCESS_DIST);
  const baselineDir = process.env.WORLD_ACCESS_BASELINE_DIST;
  if (baselineDir) baselineServer = await serveBuild(baselineDir);
  browser = await chromium.launch(launchOptions);
  const baseline = baselineServer && await checkWorld(browser, baselineServer.url, true);
  const successor = await checkWorld(browser, site ?? server.url);
  console.log(JSON.stringify({ baseline, successor }));
} finally {
  await browser?.close();
  await server?.close();
  await baselineServer?.close();
}
