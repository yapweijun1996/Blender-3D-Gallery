import assert from "node:assert/strict";
import { mkdir, mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { chromium } from "playwright";
import { buildTile, TILE_SIZE } from "../src/world/tile-mesh.js";
import fortCanning from "../src/world/tunnel-integration/fort-canning-runtime-overlay.json" with { type: "json" };
import { nearestTunnelSection } from "../src/world/tunnel-prototype/geometry.js";
import { serveBuild } from "./browser-test-utils.mjs";

export async function runWorldPassageBrowser({ env, tile, approach, covered, departure, neighbors, excludedServices, roof,
  direction, approachLead, requiredLaneCount, requiredWidth = 17, liveTraffic, fixedDriveClock = false,
  continuationTiles = [], runoff = 7 }) {
  const ids = [...approach, ...covered, ...departure];
  const tiles = [tile, ...continuationTiles];
  const roadIds = new Set([...ids, ...neighbors, ...excludedServices]);
  const roads = new Map();
  for (const source of tiles) {
    for (const road of source.roads.filter(({ id }) => roadIds.has(id))) {
      const fragment = road.geometry.map(([x, z]) => ({ x: x + source.x * TILE_SIZE, y: 0, z: z + source.z * TILE_SIZE }));
      const previous = roads.get(road.id);
      if (previous) {
        assert.deepEqual(fragment.shift(), previous.geometry.at(-1), `${road.id} joins at the tile seam`);
        previous.geometry.push(...fragment);
      } else roads.set(road.id, { ...road, geometry: fragment });
    }
  }
  const tileKey = `${tile.x}_${tile.z}`;
  const continuationKeys = continuationTiles.map(({ x, z }) => `${x}_${z}`);
  const stations = new Map();
  const path = [];
  for (const id of ids) {
    const points = roads.get(id).geometry.slice();
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
  const finish = exit + runoff;
  const portalDistance = Math.min(4, (exit - entry) / 3);
  assert.ok(path.at(-1).s > finish, "the mapped route covers the requested runoff beyond the second portal");
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
    return { x: (a.x + b.x) / 2, z: (a.z + b.z) / 2 };
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
    const paintIds = new Set([...ids, ...neighbors]);
    const grounds = tiles.map(source => buildTile({ x: source.x, z: source.z, roadSurfaces: source.roadSurfaces,
      roads: source.roads.filter(({ id }) => paintIds.has(id)) }).ground);
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
      const asphalt = grounds.filter(Boolean).map(geometry => geometry.getAttribute("position").array);
      const paved = (x, z) => asphalt.some(triangles => includesXZ(triangles, x, z));
      const checks = [entry - 3, ...coveredStations, exit + 3];
      if (continuationKeys.length) checks.push(finish);
      for (const station of checks) {
        for (const [lane, { x, z }] of laneCenters(station).entries()) {
          assert.ok(paved(x, z), `asphalt is drawn in lane ${lane + 1} at ${station.toFixed(2)}m`);
        }
      }
      for (const id of neighbors) {
        const point = midpoint(id);
        assert.ok(paved(point.x, point.z), `the adjoining ${id} still draws its asphalt`);
      }
    } finally {
      for (const ground of grounds) ground?.dispose();
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
    const responses = [tileKey, ...continuationKeys].map(key => page.waitForResponse(candidate => {
      const { pathname } = new URL(candidate.url());
      return pathname.match(/\/(-?\d+_-?\d+)(?:-[\w-]+)?\.json$/)?.[1] === key && candidate.ok();
    }));
    const spawn = sample(approachLead == null ? 2 : entry - approachLead);
    // Start the touch run a few degrees off heading so it must also steer.
    await teleport(stage, { ...spawn, heading: spawn.heading + (mobile ? .075 : 0) });
    await Promise.all(responses);
    await page.waitForFunction(({ x, z }) => {
      const state = document.querySelector(".world-stage")?.inspectWorld?.();
      return state?.carTile?.[0] === x && state.carTile[1] === z && state.loading.pending === 0 && state.loading.ready === 0;
    }, { x: tile.x, z: tile.z }, { polling: 100 });
    const settled = await stage.evaluate(element => element.simulate(1, { brake: 1 }));
    assert.ok(settled.groundedWheels === 4 && Math.abs(settled.y - .684) < .15, "approach supports the ordinary-world car");
    const preloadRequests = [];
    if (mobile) {
      page.off("request", recordTile);
      for (const [key, [x, z]] of requests) {
        if (Math.abs(x - tile.x) <= 1 && Math.abs(z - tile.z) <= 1) continue;
        if (settled.fortCanning !== "idle" && fortCanning.requiredTiles.includes(key)) preloadRequests.push(key);
      }
      assert.ok(requests.has(tileKey) && [...requests].every(([key, [x, z]]) =>
        preloadRequests.includes(key) || (Math.abs(x - tile.x) <= 1 && Math.abs(z - tile.z) <= 1)),
        `new approach requests stay within the mobile 3×3 ring: ${JSON.stringify([...requests.keys()])}`);
    }
    return { ...settled, requestedTiles: [...requests.keys()].filter(key => !preloadRequests.includes(key)), preloadRequests };
  }

  async function drive(page, stage, before, expectWall) {
    let farthest = 0, minimumWheels = 4, floorMin = before.y, floorMax = before.y;
    let under = 0, maxLateral = 0, elapsed = 0, clockPaused = false;
    const unsupported = [];
    const visited = new Set();
    const input = await driveControls(page, stage);
    try {
      if (fixedDriveClock) {
        await page.clock.pauseAt(await stage.evaluate(() => Date.now() + 3000));
        clockPaused = true;
      }
      const started = performance.now();
      while ((clockPaused ? elapsed : performance.now() - started) < 25_000) {
        const state = await inspect(stage);
        const on = nearestTunnelSection(path, state);
        if (continuationKeys.length) visited.add(`${Math.floor(state.x / TILE_SIZE)}_${Math.floor(state.z / TILE_SIZE)}`);
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
          if (state.groundedWheels < 4 && unsupported.length < 4) {
            unsupported.push({ station: on.s, wheels: state.groundedWheels, y: state.y, speed: state.speed, damage: state.damage });
          }
          floorMin = Math.min(floorMin, state.y);
          floorMax = Math.max(floorMax, state.y);
        }
        if (on.s > finish) {
          assert.ok(!expectWall, "the baseline should block the same center lane");
          assert.ok(under >= 8 && minimumWheels === 4,
            `all wheels remain on the floor between the two portals: ${JSON.stringify({ under, minimumWheels, unsupported })}`);
          assert.ok(Math.abs(state.y - before.y) < .12 && state.damage < .015 && maxLateral < 1.4,
            `the car exits on the same grade without damage: ${JSON.stringify({ state, maxLateral })}`);
          if (continuationKeys.length) {
            assert.ok(continuationKeys.every(key => visited.has(key)) && state.groundedWheels === 4,
              `the car reaches the supported far-side road across all tile seams: ${JSON.stringify({ visited: [...visited], state })}`);
          }
          return { farthest, minimumWheels, floorMin, floorMax, under, maxLateral, damage: state.damage,
            ...(continuationKeys.length ? { visitedTiles: [...visited], farSideWheels: state.groundedWheels } : {}) };
        }
        const aim = sample(on.s + 5);
        const delta = Math.atan2(aim.x - state.x, aim.z - state.z) - state.heading;
        const angle = Math.atan2(Math.sin(delta), Math.cos(delta));
        const controls = state.speed < 11 ? ["gas"] : [];
        if (angle > .05) controls.push("left");
        else if (angle < -.05) controls.push("right");
        await input.set(controls);
        if (clockPaused) {
          // Advance the ordinary animation loop while the actual input events remain held.
          await page.clock.runFor(60);
          elapsed += 60;
        } else await page.waitForTimeout(60);
      }
      assert.fail(`vehicle failed to ${expectWall ? "reach the old wall" : "pass both portals"} near ${farthest.toFixed(2)}m: ${
        JSON.stringify({ under, minimumWheels, unsupported, maxLateral, state: await inspect(stage) })}`);
    } finally {
      try {
        await input.close();
      } finally {
        if (clockPaused) await page.clock.resume();
      }
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
    const offsets = liveTraffic.continuation ? [-115, 95, -140] : [-85, 95, -115];
    const lookouts = offsets.map((distance, index) => {
      const station = index === 1 ? exit - .2 : entry + .2;
      const point = sample(station);
      const dx = Math.sin(point.heading), dz = Math.cos(point.heading);
      return [point.x + dx * distance + dz * 12, point.z + dz * distance - dx * 12, point.heading];
    });
    const observed = await stage.evaluate((element, { covered, departure, forbidden, continuation, step, laneCounts, lookouts }) => {
      const coveredCars = new Set(), transitions = [], continued = [];
      let maxActive = 0, coveredSamples = 0, windows = 0;
      for (const lookout of lookouts) {
        element.teleport(...lookout);
        windows++;
        let previous = new Map();
        const exited = new Set();
        for (let tick = 0; tick < Math.round(72 / step); tick++) {
          element.simulate(step, { brake: 1 });
          const cars = element.inspectTraffic();
          maxActive = Math.max(maxActive, cars.length);
          for (const car of cars) {
            if (covered.includes(car.edgeId)) {
              coveredSamples++;
              coveredCars.add(car.id);
              if (Math.abs(car.y) > .02 || car.lane < 0 || car.lane >= laneCounts[car.edgeId]) throw new Error(`An AI car is off the modeled carriageway: ${JSON.stringify(car)}`);
            }
            const prior = previous.get(car.id);
            const leftRoof = prior?.edgeId === covered.at(-1);
            const leftPortal = continuation && exited.has(car.id) && prior?.edgeId === departure[0];
            if ((!leftRoof && !leftPortal) || prior.edgeId === car.edgeId) continue;
            if (forbidden.includes(car.edgeId)) throw new Error(`An AI car left the passage for an excluded driveway: ${JSON.stringify(car)}`);
            if (leftRoof && car.edgeId === departure[0]) {
              if (prior.lane !== car.lane) throw new Error(`An AI car changed lanes at the portal: ${JSON.stringify({ prior, car })}`);
              transitions.push({ id: car.id, lane: car.lane });
              exited.add(car.id);
            }
            if (leftPortal && car.edgeId === continuation) {
              if (prior.lane !== car.lane || Math.abs(car.y) > .02) throw new Error(`An AI car changed lanes or grade after the covered passage: ${JSON.stringify({ prior, car })}`);
              continued.push({ id: car.id, lane: car.lane });
            }
          }
          previous = new Map(cars.map(car => [car.id, car]));
        }
        if (transitions.length > 0 && (!continuation || continued.length > 0)) break;
      }
      return { maxActive, coveredCars: coveredCars.size, coveredSamples, transitions, windows,
        ...(continuation ? { continued } : {}) };
    }, { covered, departure, forbidden: liveTraffic.forbidden, continuation: liveTraffic.continuation, step: liveTraffic.step ?? .2, lookouts,
      laneCounts: Object.fromEntries(covered.map(id => [id, roads.get(id).lanes])) });
    assert.ok(observed.coveredCars > 0 && observed.transitions.length > 0 && (!liveTraffic.continuation || observed.continued.length > 0),
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
      if (fixedDriveClock) await page.clock.install();
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
      let surfaces, graphEdges, laneSurfaces, farSide;
      if (!expectWall) {
        const portalStations = [entry - portalDistance, entry + portalDistance, exit - portalDistance, exit + portalDistance];
        surfaces = await Promise.all(portalStations.map(station => roadAt(stage, sample(station))));
        assert.deepEqual(surfaces.map(({ edgeId }) => edgeId), portalStations.map(station => ids.find(id => station < stations.get(id).end)),
          "both portals connect the loaded surface and covered road edges");
        const graphProbes = await Promise.all(ids.map(id => roadAt(stage, midpoint(id))));
        graphEdges = graphProbes.map(({ edgeId }) => edgeId);
        assert.deepEqual(graphEdges, ids, "the loaded traffic graph contains the same continuous chain");
        for (const hit of surfaces) assert.ok(Number.isFinite(hit.groundY) && Math.abs(hit.groundY) < .02, "every portal has actual ground-level support");
        const [outsideEntry, insideEntry, insideExit, outsideExit] = surfaces;
        assert.equal(outsideEntry.overheadY, null);
        assert.equal(outsideExit.overheadY, null);
        for (const hit of [insideEntry, insideExit]) {
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
        if (continuationKeys.length) {
          farSide = await roadAt(stage, sample(finish));
          assert.ok(farSide.edgeId === departure.at(-1) && Number.isFinite(farSide.groundY) && Math.abs(farSide.groundY) < .02,
            `the far-side continuation is present at grade: ${JSON.stringify(farSide)}`);
        }
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
        const underRoofEye = exit - entry < 14 ? entry + .6 : middle - 7;
        await photograph(stage, { eye: underRoofEye, target: exit + 4, car: middle + 3, name: "under-roof.png" });
        await photograph(stage, { eye: exit + 9, target: exit - 7, car: exit + 1, name: "exit-portal.png" });
        if (continuationKeys.length) await photograph(stage, { eye: finish - 9, target: finish + 5, car: finish, name: "far-side.png" });
      }
      const traffic = liveTraffic && !expectWall ? await observeLiveTraffic(stage) : undefined;
      await press(page.locator("#demo-breadcrumb a"));
      await page.waitForFunction(() => !document.querySelector("#sg-world-page .world-stage > canvas"));
      assert.deepEqual(errors, []);
      return { initial: { vehicle: initial.vehicleId, wheels: initial.groundedWheels }, physical, surfaces, graphEdges, laneSurfaces, traffic, farSide,
        residentTiles: before.tiles, requestedTiles: before.requestedTiles, preloadRequests: before.preloadRequests, touchControls };
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
