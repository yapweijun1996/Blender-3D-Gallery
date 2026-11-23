import assert from "node:assert/strict";
import { mkdir, mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { chromium } from "playwright";
import { buildTile, TILE_SIZE } from "../src/world/tile-mesh.js";
import { nearestTunnelSection } from "../src/world/tunnel-prototype/geometry.js";
import { serveBuild } from "./browser-test-utils.mjs";

export async function runWorldPassageBrowser({ env, tile, approach, covered, departure, neighbors, excludedServices, roof,
  direction, approachLead, requiredLaneCount, requiredWidth = 17, liveTraffic }) {
  const ids = [...approach, ...covered, ...departure];
  const roads = new Map(tile.roads.map(road => [road.id, road]));
  const tileKey = `${tile.x}_${tile.z}`;
  const toWorld = ([x, z]) => ({ x: x + tile.x * TILE_SIZE, y: 0, z: z + tile.z * TILE_SIZE });
  const stations = new Map();
  const path = [];
  for (const id of ids) {
    const points = roads.get(id).geometry.map(toWorld);
    const start = path.at(-1)?.s ?? 0;
    if (path.length) {
      const { x, y, z } = path.at(-1);
      assert.deepEqual(points.shift(), { x, y, z }, "mapped edges join");
    }
    for (const point of points) {
      const previous = path.at(-1);
      path.push({ ...point, s: previous ? previous.s + Math.hypot(point.x - previous.x, point.z - previous.z) : 0 });
    }
    stations.set(id, { start, end: path.at(-1).s });
  }
  const entry = stations.get(covered[0]).start, exit = stations.get(covered.at(-1)).end;
  const middle = (entry + exit) / 2;
  const roadAtStation = station => roads.get(ids.find(id => station < stations.get(id).end) ?? ids.at(-1));

  const site = process.env[`${env}_SITE`];
  const browserProfile = process.env[`${env}_PROFILE`] ?? "desktop";
  assert.ok(["desktop", "mobile"].includes(browserProfile), `${env}_PROFILE must be desktop or mobile`);
  const mobile = browserProfile === "mobile";
  const shots = process.env[`${env}_SHOTS`] ?? await mkdtemp(join(tmpdir(), "gallery-world-passage-browser-"));
  const output = direction ? join(shots, direction) : shots;
  const server = site ? { url: new URL("./", site).href, close() {} } : await serveBuild(process.env[`${env}_DIST`]);

  function sample(station) {
    const i = path.findIndex(({ s }) => s > station);
    const end = i < 0 ? path.length - 1 : Math.max(1, i);
    const a = path[end - 1], b = path[end];
    const amount = (station - a.s) / (b.s - a.s);
    const dx = b.x - a.x, dz = b.z - a.z;
    return { x: a.x + amount * dx, z: a.z + amount * dz, heading: Math.atan2(dx, dz) };
  }

  function midpoint(roadId) {
    const geometry = roads.get(roadId).geometry;
    const a = geometry.at(-2), b = geometry.at(-1);
    return toWorld([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]);
  }

  function laneCenters(station) {
    const point = sample(station);
    const { lanes, width, id } = roadAtStation(station);
    assert.ok(Number.isInteger(lanes) && lanes > 0 && width > 0, `${id} declares its lane count and carriageway width`);
    assert.equal(lanes, requiredLaneCount ?? 5, `${id} retains its mapped lanes`);
    assert.equal(width, requiredWidth, `${id} retains its mapped width`);
    return Array.from({ length: lanes }, (_, lane) => {
      const offset = (lane - (lanes - 1) / 2) * width / lanes;
      return { x: point.x + Math.cos(point.heading) * offset, z: point.z - Math.sin(point.heading) * offset };
    });
  }

  function includesXZ(triangles, x, z, height = .03) {
    const cross = (ax, az, bx, bz) => (bx - ax) * (z - az) - (bz - az) * (x - ax);
    for (let i = 0; i < triangles.length; i += 9) {
      const [ax, ay, az, bx, by, bz, cx, cy, cz] = triangles.subarray(i, i + 9);
      if (Math.abs(ay - height) + Math.abs(by - height) + Math.abs(cy - height) > .001) continue;
      if (Math.abs((bx - ax) * (cz - az) - (bz - az) * (cx - ax)) < 1e-6) continue;
      const values = [cross(ax, az, bx, bz), cross(bx, bz, cx, cz), cross(cx, cz, ax, az)];
      if (values.every(value => value >= -1e-4) || values.every(value => value <= 1e-4)) return true;
    }
    return false;
  }

  function verifyRenderGeometry() {
    const roadIds = [...ids, ...neighbors];
    const { ground } = buildTile({ x: tile.x, z: tile.z, roadSurfaces: tile.roadSurfaces, roads: roadIds.map(id => roads.get(id)) });
    const { buildings } = buildTile({ x: tile.x, z: tile.z,
      buildings: tile.buildings.filter(building => building.id === roof.buildingId) });
    try {
      const coveredStations = covered.map(id => { const { start, end } = stations.get(id); return (start + end) / 2; });
      const roofTriangles = buildings.getAttribute("position").array;
      const roofHeights = Array.from(roofTriangles).filter((_, index) => index % 3 === 1);
      if (roof.raised) assert.ok(Math.abs(Math.min(...roofHeights) - roof.soffit) < .001, "the entire raised structure starts at its simulated soffit");
      assert.ok(Math.abs(Math.max(...roofHeights) - roof.top) < .001, "the rendered roof top matches the game model height");
      for (const station of coveredStations) {
        const { x, z } = sample(station);
        assert.ok(includesXZ(roofTriangles, x, z, roof.soffit), `a modeled soffit covers the centre lane at ${station.toFixed(2)}m`);
        assert.ok(includesXZ(roofTriangles, x, z, roof.top), `a modeled roof covers the centre lane at ${station.toFixed(2)}m`);
      }
      const triangles = ground.getAttribute("position").array;
      for (const station of [entry - 3, ...coveredStations, exit + 3]) {
        for (const [lane, { x, z }] of laneCenters(station).entries()) {
          assert.ok(includesXZ(triangles, x, z), `asphalt is drawn in lane ${lane + 1} at ${station.toFixed(2)}m`);
        }
      }
      for (const id of neighbors) {
        const point = midpoint(id);
        assert.ok(includesXZ(triangles, point.x, point.z), `the adjoining ${id} still draws its asphalt`);
      }
    } finally {
      ground?.dispose();
      buildings?.dispose();
    }
  }

  function teleport(stage, { x, z, heading }) {
    return stage.evaluate((element, args) => element.teleport(...args), [x, z, heading]);
  }

  const inspect = stage => stage.evaluate(element => element.inspectWorld());
  const keys = { gas: "ArrowUp", left: "ArrowLeft", right: "ArrowRight" };

  async function driveControls(page, stage) {
    let held = [];
    let device, points;
    if (mobile) {
      await stage.locator('[data-key="gas"]').scrollIntoViewIfNeeded();
      const viewport = page.viewportSize();
      points = await stage.evaluate((element, viewport) => {
        const points = {};
        element.testTouches = [];
        for (const [index, name] of ["gas", "left", "right"].entries()) {
          const button = element.querySelector(`[data-key="${name}"]`);
          const box = button.getBoundingClientRect();
          const x = box.x + box.width / 2, y = box.y + box.height / 2;
          if (x < 0 || x >= viewport.width || y < 0 || y >= viewport.height) throw new Error(`${name} is outside the touch viewport`);
          points[name] = { x, y, id: index + 1 };
          button.addEventListener("pointerdown", event => {
            if (event.pointerType === "touch") element.testTouches.push(name);
          });
        }
        return points;
      }, viewport);
      device = await page.context().newCDPSession(page);
    }

    async function set(next) {
      const released = held.filter(name => !next.includes(name));
      const added = next.filter(name => !held.includes(name));
      if (device) {
        if (released.length) await device.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: released.map(name => points[name]) });
        if (added.length) await device.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: next.map(name => points[name]) });
      } else {
        for (const name of released) await page.keyboard.up(keys[name]);
        for (const name of added) await page.keyboard.down(keys[name]);
      }
      held = next;
    }

    return {
      set,
      async close() {
        if (!device) return set([]);
        try {
          if (held.length) await device.send("Input.dispatchTouchEvent", { type: "touchCancel", touchPoints: [] });
        } finally {
          await device.detach();
        }
      },
    };
  }

  async function parkAtApproach(page, stage) {
    const requests = new Map();
    function recordTile(request) {
      const tilePath = new URL(request.url()).pathname.match(/\/(-?\d+)_(-?\d+)(?:-[\w-]+)?\.json$/);
      if (tilePath) requests.set(`${tilePath[1]}_${tilePath[2]}`, tilePath.slice(1).map(Number));
    }
    if (mobile) {
      await page.waitForFunction(() => {
        const state = document.querySelector(".world-stage")?.inspectWorld?.();
        return state?.carTile?.[0] === Math.floor(state.x / 250) && state.carTile[1] === Math.floor(state.z / 250) &&
          state.loading.pending === 0 && state.loading.ready === 0;
      }, undefined, { polling: 100 });
      page.on("request", recordTile);
    }
    const response = page.waitForResponse(candidate => {
      const { pathname } = new URL(candidate.url());
      return pathname.match(/\/(-?\d+_-?\d+)(?:-[\w-]+)?\.json$/)?.[1] === tileKey && candidate.ok();
    });
    const spawn = sample(approachLead == null ? 2 : entry - approachLead);
    // Start the touch run a few degrees off heading so it must also steer.
    await teleport(stage, { ...spawn, heading: spawn.heading + (mobile ? .075 : 0) });
    await response;
    await page.waitForFunction(({ x, z }) => {
      const state = document.querySelector(".world-stage")?.inspectWorld?.();
      return state?.carTile?.[0] === x && state.carTile[1] === z && state.loading.pending === 0 && state.loading.ready === 0;
    }, { x: tile.x, z: tile.z }, { polling: 100 });
    const settled = await stage.evaluate(element => element.simulate(1, { brake: 1 }));
    assert.ok(settled.groundedWheels === 4 && Math.abs(settled.y - .684) < .15, "approach supports the ordinary-world car");
    if (mobile) {
      page.off("request", recordTile);
      assert.ok(requests.has(tileKey) && [...requests.values()].every(([x, z]) => Math.abs(x - tile.x) <= 1 && Math.abs(z - tile.z) <= 1),
        `new approach requests stay within the mobile 3×3 ring: ${JSON.stringify([...requests.keys()])}`);
    }
    return { ...settled, requestedTiles: [...requests.keys()] };
  }

  async function drive(page, stage, before, expectWall) {
    let farthest = 0, minimumWheels = 4, floorMin = before.y, floorMax = before.y;
    let under = 0, maxLateral = 0;
    const input = await driveControls(page, stage);
    const started = performance.now();
    try {
      while (performance.now() - started < 25_000) {
        const state = await inspect(stage);
        const on = nearestTunnelSection(path, state);
        farthest = Math.max(farthest, on.s);
        maxLateral = Math.max(maxLateral, Math.abs(on.lateral));
        assert.ok(!state.flipped && Math.abs(state.y - before.y) < .25, `the drive stays on grade: ${JSON.stringify({ state, on })}`);
        if (expectWall && state.damage > .015 && state.speed < 3) {
          const wall = Math.abs(on.s - entry) < 4 ? "entry" : Math.abs(on.s - exit) < 4 ? "exit" : null;
          if (wall) return { wall, farthest, damage: state.damage, wheelSupport: state.groundedWheels };
        }
        if (on.s >= entry && on.s <= exit) {
          under++;
          minimumWheels = Math.min(minimumWheels, state.groundedWheels);
          floorMin = Math.min(floorMin, state.y);
          floorMax = Math.max(floorMax, state.y);
        }
        if (on.s > exit + 7) {
          assert.ok(!expectWall, "the baseline should block the same center lane");
          assert.ok(under >= 8 && minimumWheels === 4, "all wheels remain on the floor between the two portals");
          assert.ok(Math.abs(state.y - before.y) < .12 && state.damage < .015 && maxLateral < 1.4,
            `the car exits on the same grade without damage: ${JSON.stringify({ state, maxLateral })}`);
          return { farthest, minimumWheels, floorMin, floorMax, under, maxLateral, damage: state.damage };
        }
        const aim = sample(on.s + 5);
        const delta = Math.atan2(aim.x - state.x, aim.z - state.z) - state.heading;
        const angle = Math.atan2(Math.sin(delta), Math.cos(delta));
        const controls = state.speed < 11 ? ["gas"] : [];
        if (angle > .05) controls.push("left");
        else if (angle < -.05) controls.push("right");
        await input.set(controls);
        await page.waitForTimeout(60);
      }
      assert.fail(`vehicle failed to ${expectWall ? "reach the old wall" : "pass both portals"} near ${farthest.toFixed(2)}m: ${JSON.stringify(await inspect(stage))}`);
    } finally {
      await input.close();
    }
  }

  async function photograph(stage, { eye, target, car, name }) {
    const view = sample(eye), focus = sample(target);
    await teleport(stage, sample(car));
    await stage.evaluate((element, view) => element.setView(view), {
      position: [view.x, 2.35, view.z], target: [focus.x, 1.55, focus.z],
    });
    await stage.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    await stage.locator(":scope > canvas").screenshot({ path: join(output, name) });
  }

  async function roadAt(stage, point) {
    return stage.evaluate((element, { x, z }) => element.inspectRoad(x, z), point);
  }

  async function observeLiveTraffic(stage) {
    // Move the player clear of the road and boundedly vary the normal traffic spawn area if needed.
    const lookouts = [[entry + .2, -85], [exit - .2, 95], [entry + .2, -115]].map(([station, distance]) => {
      const point = sample(station);
      const dx = Math.sin(point.heading), dz = Math.cos(point.heading);
      return [point.x + dx * distance + dz * 12, point.z + dz * distance - dx * 12, point.heading];
    });
    const observed = await stage.evaluate((element, { covered, departure, forbidden, laneCounts, lookouts }) => {
      const coveredCars = new Set(), transitions = [];
      let maxActive = 0, coveredSamples = 0, windows = 0;
      for (const lookout of lookouts) {
        element.teleport(...lookout);
        windows++;
        let previous = new Map();
        for (let tick = 0; tick < 360; tick++) {
          element.simulate(.2, { brake: 1 });
          const cars = element.inspectTraffic();
          maxActive = Math.max(maxActive, cars.length);
          for (const car of cars) {
            if (covered.includes(car.edgeId)) {
              coveredSamples++;
              coveredCars.add(car.id);
              if (Math.abs(car.y) > .02 || car.lane < 0 || car.lane >= laneCounts[car.edgeId]) throw new Error(`An AI car is off the modeled carriageway: ${JSON.stringify(car)}`);
            }
            const prior = previous.get(car.id);
            if (prior?.edgeId !== covered.at(-1) || prior.edgeId === car.edgeId) continue;
            if (forbidden.includes(car.edgeId)) throw new Error(`An AI car left the passage for an excluded driveway: ${JSON.stringify(car)}`);
            if (car.edgeId === departure[0]) {
              if (prior.lane !== car.lane) throw new Error(`An AI car changed lanes at the portal: ${JSON.stringify({ prior, car })}`);
              transitions.push({ id: car.id, lane: car.lane });
            }
          }
          previous = new Map(cars.map(car => [car.id, car]));
        }
        if (transitions.length > 0) break;
      }
      return { maxActive, coveredCars: coveredCars.size, coveredSamples, transitions, windows };
    }, { covered, departure, forbidden: liveTraffic.forbidden, lookouts,
      laneCounts: Object.fromEntries(covered.map(id => [id, roads.get(id).lanes])) });
    assert.ok(observed.coveredCars > 0 && observed.transitions.length > 0,
      `live AI must traverse the covered road and leave by the intended exit in its original lane: ${JSON.stringify(observed)}`);
    return observed;
  }

  async function check(browser, url, expectWall = false) {
    const device = mobile ? { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true }
      : { viewport: { width: 1440, height: 900 } };
    const context = await browser.newContext({ ...device, serviceWorkers: "block", locale: "en" });
    try {
      const page = await context.newPage();
      page.setDefaultTimeout(45_000);
      const errors = [];
      page.on("pageerror", error => errors.push(error.message));
      page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
      await page.goto(`${url}?page=sg-world`, { waitUntil: "domcontentloaded" });
      const stage = page.locator("#sg-world-page .world-stage[data-state=ready]");
      await stage.waitFor({ timeout: 120_000 });
      assert.equal(await page.locator(".tunnel-stage").count(), 0, "the ordinary player and world launched");
      const initial = await inspect(stage);
      assert.ok(Math.hypot(initial.x - initial.start.x, initial.z - initial.start.z) < 4 && initial.groundedWheels === 4,
        "the ordinary Bayfront start is usable before moving to the passage");
      assert.equal(await page.evaluate(() => matchMedia("(pointer: coarse)").matches), mobile);
      const press = locator => mobile ? locator.tap() : locator.click();
      const before = await parkAtApproach(page, stage);
      let surfaces, graphEdges, laneSurfaces;
      if (!expectWall) {
        const portalStations = [entry - 4, entry + 4, exit - 4, exit + 4];
        surfaces = await Promise.all(portalStations.map(station => roadAt(stage, sample(station))));
        assert.deepEqual(surfaces.map(({ edgeId }) => edgeId), portalStations.map(station => ids.find(id => station < stations.get(id).end)),
          "both portals connect the loaded surface and covered road edges");
        const graphProbes = await Promise.all(ids.map(id => roadAt(stage, midpoint(id))));
        graphEdges = graphProbes.map(({ edgeId }) => edgeId);
        assert.deepEqual(graphEdges, ids, "the loaded traffic graph contains the same continuous chain");
        for (const hit of surfaces) assert.ok(Number.isFinite(hit.groundY) && Math.abs(hit.groundY) < .02, "every portal has actual ground-level support");
        const [approach, insideWest, insideEast, departure] = surfaces;
        assert.equal(approach.overheadY, null);
        assert.equal(departure.overheadY, null);
        for (const hit of [insideWest, insideEast]) {
          assert.ok(Number.isFinite(hit.overheadY) && Math.abs(hit.overheadY - roof.soffit) < .02, `both interior probes hit the simulated soffit at Y=${roof.soffit}`);
        }
        for (const hit of graphProbes.filter(({ edgeId }) => covered.includes(edgeId))) {
          assert.ok(Number.isFinite(hit.overheadY) && Math.abs(hit.overheadY - roof.soffit) < .02, `the simulated soffit covers ${hit.edgeId}`);
        }
        if (requiredLaneCount != null) {
          laneSurfaces = await Promise.all(laneCenters(middle).map(point => roadAt(stage, point)));
          for (const hit of laneSurfaces) {
            assert.ok(Number.isFinite(hit.groundY) && Math.abs(hit.groundY) < .02 && Number.isFinite(hit.overheadY) &&
              Math.abs(hit.overheadY - roof.soffit) < .02, `each through lane has a grade-level floor and the modeled soffit: ${JSON.stringify(hit)}`);
          }
        }
        for (const id of neighbors) assert.equal((await roadAt(stage, midpoint(id))).edgeId, id, `unchanged neighbor ${id} remains routable`);
        for (const id of excludedServices) assert.notEqual((await roadAt(stage, midpoint(id))).edgeId, id, `${id} stays outside the through traffic graph`);
      }
      const physical = await drive(page, stage, before, expectWall);
      const touchControls = mobile ? await stage.evaluate(element => [...new Set(element.testTouches)]) : null;
      if (mobile) assert.ok(touchControls.includes("gas") && touchControls.some(name => name === "left" || name === "right"),
        "stock screen controls received real touch accelerator and steering input");
      await press(page.locator(".drive-pause"));
      if (expectWall) {
        const portal = physical.wall === "entry" ? entry : exit;
        const side = physical.wall === "entry" ? -1 : 1;
        await photograph(stage, { eye: portal + side * 10, target: portal - side * 5, car: portal + side * 4, name: "baseline-wall.png" });
      } else {
        await photograph(stage, { eye: entry - 9, target: entry + 7, car: entry + 1, name: "entry-portal.png" });
        await photograph(stage, { eye: middle - 7, target: exit + 4, car: middle + 3, name: "under-roof.png" });
        await photograph(stage, { eye: exit + 9, target: exit - 7, car: exit + 1, name: "exit-portal.png" });
      }
      const traffic = liveTraffic && !expectWall ? await observeLiveTraffic(stage) : undefined;
      await press(page.locator("#demo-breadcrumb a"));
      await page.waitForFunction(() => !document.querySelector("#sg-world-page .world-stage > canvas"));
      assert.deepEqual(errors, []);
      return { initial: { vehicle: initial.vehicleId, wheels: initial.groundedWheels }, physical, surfaces, graphEdges, laneSurfaces, traffic,
        residentTiles: before.tiles, requestedTiles: before.requestedTiles, touchControls };
    } finally {
      await context.close();
    }
  }

  let browser, baseline;
  try {
    await mkdir(output, { recursive: true });
    verifyRenderGeometry();
    browser = await chromium.launch({ channel: "chrome", args: ["--enable-unsafe-swiftshader"] });
    if (process.env[`${env}_BASELINE_DIST`]) baseline = await serveBuild(process.env[`${env}_BASELINE_DIST`]);
    const original = baseline ? await check(browser, baseline.url, true) : null;
    const passage = await check(browser, server.url);
    console.log(JSON.stringify({ result: "PASS", profile: browserProfile, direction, original, passage, screenshots: output }));
  } finally {
    await browser?.close();
    await baseline?.close();
    await server.close();
  }
}
