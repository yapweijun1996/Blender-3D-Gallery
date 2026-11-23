import assert from "node:assert/strict";
import { mkdir, mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { chromium } from "playwright";
import { serveBuild } from "./browser-test-utils.mjs";
import profile from "./world/fort-canning-integration.json" with { type: "json" };
import { createFortCanningMergeGeometry } from "../src/world/tunnel-integration/merge-geometry.js";
import { FORT_CANNING_TILES } from "../src/world/tunnel-integration/route.js";
import { nearestTunnelSection } from "../src/world/tunnel-prototype/geometry.js";

const site = process.env.STREAMED_TUNNEL_SITE;
const output = process.env.STREAMED_TUNNEL_SHOTS ?? await mkdtemp(join(tmpdir(), "gallery-world-tunnel-browser-"));
const server = site ? { url: new URL("./", site).href, close() {} } : await serveBuild(process.env.STREAMED_TUNNEL_DIST);
const { lanes: { link }, seam } = createFortCanningMergeGeometry(profile);
const missingTile = "-8_-8";
const tileAsset = /(?:^|\/)(-\d+_-\d+)(?:-[\w-]+)?\.json$/;
const staging = { x: -1087.095, z: -1263.21, heading: -.702138 }; // Victoria Street, outside the terrain replacement.
const opening = link.find(({ y }) => y < -1.2);
const fortCanningRoad = profile.crossings.find(({ edgeId }) => edgeId === "646730739:0");
const leftLane = fortCanningRoad.points.map(([x, z], index, points) => {
  const before = points[Math.max(0, index - 1)], after = points[Math.min(index + 1, points.length - 1)];
  const dx = after[0] - before[0], dz = after[1] - before[1], length = Math.hypot(dx, dz);
  return [x + dz / length * 1.7, z - dx / length * 1.7];
});
let positionOnRoad = 0;
const upperRoad = leftLane.map(([x, z], index, points) => {
  if (index) positionOnRoad += Math.hypot(x - points[index - 1][0], z - points[index - 1][1]);
  return { x, y: 0, z, s: positionOnRoad };
});

function sample(path, station) {
  const next = path.findIndex(({ s }) => s > station);
  const index = next < 0 ? path.length - 1 : next;
  const a = path[index - 1], b = path[index];
  const offset = (station - a.s) / (b.s - a.s);
  return { x: a.x + (b.x - a.x) * offset, z: a.z + (b.z - a.z) * offset,
    heading: Math.atan2(b.x - a.x, b.z - a.z) };
}

function teleport(stage, { x, z, heading = 0 }) {
  return stage.evaluate((element, args) => element.teleport(...args), [x, z, heading]);
}

function settle(stage) {
  return stage.evaluate(element => element.simulate(1.5, { brake: 1 }));
}

async function drive(stage, path, { label, from, through, to, pace, merge = null, crossingShot = null }) {
  await teleport(stage, sample(path, from));
  const parked = await settle(stage);
  assert.equal(parked.groundedWheels, 4, `${label} starts with four supported wheels`);

  let diagnostics = { farthest: from, minimumY: parked.y, maxLateral: 0, crossingY: null, seamSamples: 0, stalled: 0 };
  // Yield to the real frame loop between batches so it can stream and render while simulated controls drive the same car.
  for (let batch = 0; batch < 30 && diagnostics.farthest < to; batch++) {
    diagnostics = await stage.evaluate((element, { path, through, to, pace, merge, totals, capture }) => {
      const clamp = (n, min, max) => Math.max(min, Math.min(max, n));
      function project({ x, z }) {
        let nearest, best = Infinity;
        for (let index = 1; index < path.length; index++) {
          const a = path[index - 1], b = path[index];
          const dx = b.x - a.x, dz = b.z - a.z;
          const t = clamp(((x - a.x) * dx + (z - a.z) * dz) / (dx * dx + dz * dz), 0, 1);
          const distance = (x - a.x - t * dx) ** 2 + (z - a.z - t * dz) ** 2;
          if (distance < best) {
            best = distance;
            nearest = { s: a.s + (b.s - a.s) * t, y: a.y + (b.y - a.y) * t, lateral: Math.sqrt(best) };
          }
        }
        return nearest;
      }
      let state = element.inspectWorld();
      for (let tick = 0; tick < 90; tick++) {
        const on = project(state);
        const clearance = state.y - on.y;
        if (state.fortCanning !== "active" || state.flipped || clearance < .22 || clearance > 1.25 || on.lateral > 4.1) {
          throw new Error(`Drive left the expected deck at ${JSON.stringify({ on, clearance, state })}`);
        }
        totals.minimumY = Math.min(totals.minimumY, state.y);
        totals.maxLateral = Math.max(totals.maxLateral, on.lateral);
        if (Math.abs(on.s - through) < 1.1) {
          totals.crossingY = state.y;
          if (capture) return totals;
        }
        if (merge != null && Math.abs(on.s - merge) < 4) {
          if (state.groundedWheels !== 4) throw new Error(`Lost wheel contact at the merge: ${JSON.stringify({ on, state })}`);
          totals.seamSamples++;
        }
        if (on.s > totals.farthest + .2) {
          totals.farthest = on.s;
          totals.stalled = 0;
        } else if (++totals.stalled > 260) {
          throw new Error(`Drive did not advance at ${JSON.stringify({ on, state })}`);
        }
        if (on.s >= to) return { ...totals, farthest: on.s, finalY: state.y, finalWheels: state.groundedWheels, damage: state.damage };

        const targetS = Math.min(on.s + 4 + state.speed * .12, path.at(-1).s);
        const next = path.findIndex(point => point.s > targetS);
        const index = next < 0 ? path.length - 1 : next;
        const a = path[index - 1], b = path[index];
        const t = (targetS - a.s) / (b.s - a.s);
        const targetX = a.x + (b.x - a.x) * t, targetZ = a.z + (b.z - a.z) * t;
        const angle = Math.atan2(targetX - state.x, targetZ - state.z) - state.heading;
        state = element.simulate(.1, {
          throttle: state.speed < pace ? 1 : 0,
          brake: state.speed > pace + 1 ? .6 : 0,
          steer: clamp(2.3 * Math.atan2(Math.sin(angle), Math.cos(angle)), -1, 1),
        });
      }
      return totals;
    }, { path, through, to, pace, merge, totals: diagnostics, capture: Boolean(crossingShot && diagnostics.crossingY == null) });
    await stage.page().waitForTimeout(25);
    if (crossingShot && diagnostics.crossingY != null) {
      await stage.locator(":scope > canvas").screenshot({ path: join(output, crossingShot) });
      crossingShot = null;
    }
  }
  assert.ok(diagnostics.farthest >= to && diagnostics.crossingY != null,
    `${label} completed through the mapped crossing: ${JSON.stringify(diagnostics)}`);
  assert.equal(diagnostics.finalWheels, 4, `${label} finishes on four supported wheels`);
  return diagnostics;
}

let browser;
try {
  await mkdir(output, { recursive: true });
  browser = await chromium.launch({ channel: "chrome", args: ["--enable-unsafe-swiftshader"] });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "en", serviceWorkers: "block" });
  const page = await context.newPage();
  page.setDefaultTimeout(45_000);
  const requests = new Map(), injected = new Set(), errors = [];
  let fault = true;
  await page.route("**/*.json", async route => {
    const url = route.request().url();
    const tile = new URL(url).pathname.match(tileAsset)?.[1];
    if (FORT_CANNING_TILES.includes(tile)) requests.set(tile, (requests.get(tile) ?? 0) + 1);
    if (!fault || tile !== missingTile) return route.continue();
    injected.add(url);
    return route.fulfill({ status: 503, contentType: "text/plain", body: "Injected missing Fort Canning tile" });
  });
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => {
    if (message.type() !== "error") return;
    const body = message.text();
    if (injected.has(message.location().url) && /\b503\b/.test(body)) return;
    if (injected.size && body.includes(`tile ${missingTile}: HTTP 503`)) return;
    errors.push(body);
  });

  await page.goto(`${server.url}?page=sg-world`, { waitUntil: "domcontentloaded" });
  const stage = page.locator("#sg-world-page .drive-stage[data-state=ready]");
  const inspect = () => stage.evaluate(element => element.inspectWorld());
  const pause = page.locator(".drive-pause");
  await stage.waitFor({ timeout: 120_000 });
  assert.equal(await page.locator(".tunnel-stage").count(), 0);
  const first = await inspect();
  assert.equal(first.fortCanning, "idle", "the distant Bayfront start uses the ordinary ground");
  const { start } = first;
  const waitForStatus = status => page.waitForFunction(wanted =>
    document.querySelector(".world-stage")?.inspectWorld?.().fortCanning === wanted, status, { polling: 100 });
  const waitForCell = ({ x, z }) => page.waitForFunction(([tx, tz]) => {
    const cell = document.querySelector(".world-stage")?.inspectWorld?.().carTile;
    return cell?.[0] === tx && cell?.[1] === tz;
  }, [Math.floor(x / 250), Math.floor(z / 250)], { polling: 100 });

  await teleport(stage, staging);
  await waitForStatus("failed");
  assert.ok(injected.size > 0, `the required ${missingTile} request was blocked`);
  await teleport(stage, opening);
  const baseline = await settle(stage);
  assert.equal(baseline.fortCanning, "failed");
  assert.ok(baseline.y > .35 && baseline.y < 1.15 && baseline.groundedWheels === 4,
    `the uncut fallback supports the car over the future open ramp: ${JSON.stringify(baseline)}`);

  fault = false;
  const attempts = requests.get(missingTile);
  await teleport(stage, start);
  await waitForCell(start);
  await teleport(stage, staging);
  await waitForStatus("active");
  assert.ok(requests.get(missingTile) > attempts, "returning to the preload area fetched the missing tile again");
  assert.ok(FORT_CANNING_TILES.every(tile => requests.has(tile)), "every required map tile was requested");
  assert.ok((await inspect()).traffic > 0, "world traffic is enabled");

  await pause.click();
  const upperStation = nearestTunnelSection(upperRoad, fortCanningRoad.at).s;
  const upper = await drive(stage, upperRoad, { label: "Fort Canning Road", from: upperStation - 13, through: upperStation,
    to: upperStation + 15, pace: 11.5 });
  assert.ok(upper.crossingY > .35 && upper.crossingY < 1.15, "the upper crossing still drives at the surface level");
  await stage.locator(":scope > canvas").screenshot({ path: join(output, "fort-canning-road.png") });

  const lowerStation = nearestTunnelSection(link, fortCanningRoad.at).s;
  const lower = await drive(stage, link, { label: "Fort Canning Link", from: 1, through: lowerStation,
    to: seam.stations.link + 24, pace: 10.5, merge: seam.stations.link, crossingShot: "fort-canning-link-interior.png" });
  assert.ok(lower.crossingY < -4.1 && upper.crossingY - lower.crossingY > 4.9,
    `upper and lower routes retain their distinct decks: ${upper.crossingY}, ${lower.crossingY}`);
  assert.ok(lower.seamSamples > 5 && Math.abs(lower.finalY - baseline.y) < .15,
    `the run samples the merge and returns to the surface: ${JSON.stringify(lower)}`);
  await stage.locator(":scope > canvas").screenshot({ path: join(output, "penang-road-exit.png") });

  await pause.click();
  await teleport(stage, start);
  await waitForCell(start);
  await page.waitForFunction(() => document.querySelector(".world-stage")?.inspectWorld?.().nearbyTraffic > 0,
    undefined, { polling: 100 });
  const bayfront = await settle(stage);
  assert.equal(bayfront.fortCanning, "active", "traveling away from the tunnel preserves the published route");
  assert.ok(bayfront.nearbyTraffic > 0 && bayfront.groundedWheels === 4 && Math.abs(bayfront.y - baseline.y) < .15,
    `Bayfront has local traffic and ordinary road support after returning: ${JSON.stringify(bayfront)}`);

  await pause.click();
  const bore = link.find(({ y }) => y < -5.48).s + 12;
  await drive(stage, link, { label: "Fort Canning return", from: 1, through: bore - 7, to: bore, pace: 10.5 });
  const beforeSwap = await settle(stage);
  assert.ok(beforeSwap.y < -4.1 && beforeSwap.speed < .2, "the car is parked on the lower road before changing vehicle");
  await page.locator(".world-vehicle").click();
  const afterSwap = await inspect();
  assert.notEqual(afterSwap.vehicleId, beforeSwap.vehicleId);
  assert.ok(afterSwap.groundedWheels === 4 && Math.abs(afterSwap.y - beforeSwap.y) < .25,
    `a vehicle change preserves the actual tunnel deck: ${JSON.stringify(afterSwap)}`);

  await page.locator("#demo-breadcrumb a").click();
  await page.waitForFunction(() => !document.querySelector("#sg-world-page .world-stage > canvas"));
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ result: "PASS", fallbackY: baseline.y, upper, lower,
    bayfront: { y: bayfront.y, nearbyTraffic: bayfront.nearbyTraffic },
    tunnelSwap: { from: beforeSwap.vehicleId, to: afterSwap.vehicleId, y: afterSwap.y }, screenshots: output }));
} finally {
  await browser?.close();
  await server.close();
}
