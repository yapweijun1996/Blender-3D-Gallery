import assert from "node:assert/strict";
import { chromium } from "playwright";
import { launchOptions, serveBuild } from "./browser-test-utils.mjs";

// Hold the first Mount Rosie fetch while the player returns to Bayfront.
const mountRosie = { x: -3072, z: -4233, tile: [-13, -17] };
const bayfront = { x: -61, z: -12, tile: [-1, -1] };

function inMountRosie(url) {
  const match = new URL(url).pathname.match(/\/(-?\d+)_(-?\d+)(?:-[\w-]+)?\.json$/);
  return match && Math.abs(Number(match[1]) - mountRosie.tile[0]) <= 2 &&
    Math.abs(Number(match[2]) - mountRosie.tile[1]) <= 2;
}

async function check(browser, url, baseline) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, serviceWorkers: "block" });
  const stage = page.locator(".world-stage[data-state=ready]");
  const gate = Promise.withResolvers();
  const requested = [];
  const pageErrors = [];
  page.on("pageerror", error => pageErrors.push(error.message));

  const move = ({ x, z }) => stage.evaluate((element, [x, z]) => element.teleport(x, z), [x, z]);
  const waitForTile = (tile, idle = false) => page.waitForFunction(({ tile, idle }) => {
    const state = document.querySelector(".world-stage").inspectWorld();
    return state.carTile.every((n, i) => n === tile[i]) &&
      (!idle || (state.loading.pending === 0 && state.loading.ready === 0));
  }, { tile, idle }, { polling: 100, timeout: 150_000 });

  try {
    const world = new URL(url);
    world.searchParams.set("page", "sg-world");
    await page.goto(world.href, { waitUntil: "domcontentloaded" });
    await stage.waitFor({ timeout: 120_000 });
    await page.locator(".drive-pause").click();
    await move(bayfront);
    await waitForTile(bayfront.tile, true);

    await page.route(request => Boolean(inMountRosie(request)), async route => {
      requested.push(route.request().url());
      if (requested.length === 1) await gate.promise;
      await route.continue();
    });
    const first = page.waitForRequest(request => Boolean(inMountRosie(request.url())), { timeout: 90_000 });
    await move(mountRosie);
    await first;
    await waitForTile(mountRosie.tile);
    await move(bayfront);
    await waitForTile(bayfront.tile);
    gate.resolve();
    await waitForTile(bayfront.tile, true);
    const obsolete = requested.length - 1;
    if (baseline) assert.ok(obsolete > 0, "the former queue still fetched the abandoned region");
    else assert.equal(obsolete, 0, "no additional Mount Rosie requests start after leaving");

    const beforeReturn = requested.length;
    await move(mountRosie);
    await waitForTile(mountRosie.tile, true);
    const state = await stage.evaluate(element => {
      element.simulate(.5, { brake: 1 });
      return { loading: element.inspectWorld().loading, road: element.inspectRoad(-2975.17, -4258.98) };
    });
    assert.equal(state.loading.failed, 0);
    assert.equal(state.road.edgeId, "33876790:0");
    assert.equal(state.road.groundY, 0);
    if (!baseline) assert.ok(requested.length > beforeReturn, "returning fetches previously skipped tiles");
    assert.deepEqual(pageErrors, []);
    return { obsolete, requestsOnReturn: requested.length - beforeReturn, road: state.road.edgeId };
  } finally {
    gate.resolve();
    await page.close();
  }
}

let browser, baselineServer, server;
try {
  const site = process.env.WORLD_TILE_QUEUE_SITE;
  if (!site) server = await serveBuild(process.env.WORLD_TILE_QUEUE_DIST);
  if (process.env.WORLD_TILE_QUEUE_BASELINE_DIST) baselineServer = await serveBuild(process.env.WORLD_TILE_QUEUE_BASELINE_DIST);
  browser = await chromium.launch(launchOptions);
  if (baselineServer) console.log("Baseline", await check(browser, baselineServer.url, true));
  console.log("Current", await check(browser, site ?? server.url, false));
} finally {
  await browser?.close();
  await baselineServer?.close();
  await server?.close();
}
