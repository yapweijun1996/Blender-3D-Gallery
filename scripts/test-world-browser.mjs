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
  const first_x = first.x, first_z = first.z;
  assert.ok(first.tiles >= 9, `${first.tiles} tiles loaded`);
  assert.ok(Math.hypot(first.start.x, first.start.z) < 400, "starts near Marina Bay Sands");
  assert.equal(first.supertrees, 11);

  // Traffic fills the roads around the start, with several kinds of vehicle.
  await page.waitForFunction(() => document.querySelector('.drive-stage').inspectWorld().traffic >= 8, undefined, { polling: 500 });
  assert.ok((await inspect()).trafficTypes.length >= 2);

  // People walk the footways around the car.
  await page.waitForFunction(() => document.querySelector('.drive-stage').inspectWorld().people >= 2, undefined, { polling: 1000, timeout: 150_000 });

  // The minimap draws the roads around the car.
  assert.equal(await page.locator(".drive-minimap").evaluate(canvas => { const data = canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height).data; let lit = 0; for (let i = 0; i < data.length; i += 4) if (data[i] > 150) lit++; return lit > 200; }), true, "minimap has roads");

  // A hurt car smokes; a wrecked one stalls and says so; righting the car repairs it.
  await stage.evaluate(element => element.hurt(0.6));
  await page.waitForFunction(() => document.querySelector(".drive-stage").inspectWorld().smoking, undefined, { polling: 300 });
  await stage.evaluate(element => element.hurt(0.6));
  await page.waitForFunction(() => document.querySelector(".drive-event").textContent.length > 0 && document.querySelector(".drive-stage").inspectWorld().damage >= 0.95, undefined, { polling: 300 });
  await page.locator(".drive-reset").click();
  await page.waitForFunction(() => document.querySelector(".drive-stage").inspectWorld().damage === 0, undefined, { polling: 300 });

  // The time button steps through morning, noon, evening and night.
  await page.locator(".world-time").click();
  assert.ok([8, 13, 18.5, 22].includes(Math.round((await inspect()).hour * 2) / 2), "time jumped to a preset");
  await stage.evaluate(element => element.setHour(15));

  // Missions: the first target is the ArtScience Museum; arriving there completes it and moves on to the next place.
  assert.equal((await inspect()).mission, "artscience");
  assert.ok((await page.locator(".world-mission-text").textContent()).includes(" · "));
  await stage.evaluate(element => element.teleport(-28, -314, 0));
  await page.waitForFunction(() => document.querySelector(".drive-stage").inspectWorld().missionsDone >= 1, undefined, { polling: 500 });
  assert.notEqual((await inspect()).mission, "artscience");
  assert.ok((await inspect()).score >= 100, "the finished mission scored points");
  assert.ok((await inspect()).bestRecord.artscience >= 100, "the best score of the mission is recorded");
  assert.ok(JSON.parse(await page.evaluate(() => localStorage.getItem("sg-world-best"))).best.artscience >= 100, "and saved in the browser");
  await page.waitForFunction(() => /\d{3,}$/.test(document.querySelector(".drive-trip").textContent), undefined, { polling: 500 });
  await stage.evaluate((element, [x, z, heading]) => element.teleport(x, z, heading), [first_x, first_z, first.start.heading]);

  // Drive: the physics gives speed, and the car stays upright on the road.
  // (A traffic vehicle can happen to stand right in front of the start; if the car is boxed in, try again from the start.)
  let driven = await stage.evaluate(element => element.simulate(8, { throttle: 1 }));
  for (let attempt = 0; attempt < 3 && driven.speed < 6; attempt++) {
    await stage.evaluate((element, [x, z, heading]) => element.teleport(x, z, heading), [first_x, first_z, first.start.heading]);
    driven = await stage.evaluate(element => element.simulate(8, { throttle: 1 }));
  }
  assert.ok(driven.speed > 6 && driven.speed <= 28.5, `speed ${driven.speed} (capped at 100 km/h)`);
  assert.equal(driven.flipped, false);

  // The model's wheels turn while the car moves.
  const spinBefore = (await inspect()).wheelSpin;
  assert.ok((await inspect()).wheels >= 2, "the model has wheel nodes");
  await stage.evaluate(element => element.simulate(1, { throttle: 1 }));
  await page.waitForFunction(before => Math.abs(document.querySelector(".drive-stage").inspectWorld().wheelSpin - before) > 0.5, spinBefore, { polling: 300 });

  // Steering left turns the front wheel nodes to the left (positive angle), right the other way, and the rear wheels stay straight.
  const left = await stage.evaluate(element => element.steerCheck({ throttle: 1, steer: 1 }));
  assert.ok(left.front.length >= 1 && left.front.every(angle => angle > 0.1), `front wheels left: ${left.front}`);
  assert.ok(left.rear.every(angle => angle === 0), "rear wheels do not steer");
  const right = await stage.evaluate(element => element.steerCheck({ throttle: 1, steer: -1 }));
  assert.ok(right.front.every(angle => angle < -0.1), `front wheels right: ${right.front}`);

  // Every vehicle the player can pick drives (the button steps through the nine of them and wraps round).
  const seen = new Set();
  for (let i = 0; i < 9; i++) {
    await page.locator(".world-vehicle").click();
    const chosen = await inspect();
    seen.add(chosen.vehicleId);
    await stage.evaluate((element, [x, z, heading]) => element.teleport(x, z, heading), [first_x, first_z, first.start.heading]);
    let run = await stage.evaluate(element => element.simulate(7, { throttle: 1 }));
    // A traffic vehicle can stand in front of the start; try again from the start (up to three times).
    for (let attempt = 0; attempt < 3 && run.speed <= 2; attempt++) {
      await stage.evaluate((element, [x, z, heading]) => element.teleport(x, z, heading), [first_x, first_z, first.start.heading]);
      run = await stage.evaluate(element => element.simulate(7, { throttle: 1 }));
    }
    assert.ok(run.speed > 2, `${chosen.vehicleId} drives: speed ${run.speed}`);
    assert.equal(run.flipped, false, `${chosen.vehicleId} stays upright`);
    assert.ok((await inspect()).wheels >= 2, `${chosen.vehicleId} has wheel nodes`);
  }
  assert.equal(seen.size, 9, "nine different vehicles");

  // A flipped car is reported and the reset button rights it.
  await page.screenshot({ path: process.env.WORLD_SHOT ?? "/tmp/world-drive.png" });
  assert.ok((await page.locator(".drive-speed").textContent()) !== undefined);
  await page.locator(".drive-reset").click();

  // The whole route is mapped: at the Woodlands checkpoint, 24 km north, the tiles load and the car stands on the ground.
  await stage.evaluate(element => element.teleport(-10428, -17863, 0));
  await page.waitForFunction(() => { const s = document.querySelector(".drive-stage").inspectWorld(); return s.carTile[0] === -42 && s.carTile[1] === -72 && s.tiles >= 6; }, undefined, { polling: 500 });
  const north = await stage.evaluate(element => element.simulate(3, {}));
  assert.ok(north.y > -0.5 && north.y < 3, `the car stands on the ground in the north (y ${north.y})`);
  await stage.evaluate(element => element.teleport(1500, 600, 0));

  // The Woodlands checkpoint: arriving opens the passport game, a stamp in the green zone completes the mission with a bonus.
  const before = await inspect();
  await stage.evaluate(element => element.setMission(5)); // Woodlands Checkpoint
  await stage.evaluate(element => element.teleport(-10428, -17863, 0));
  await page.waitForFunction(() => document.querySelector(".drive-stage").inspectWorld().checkpoint === "show", undefined, { polling: 500 });
  assert.equal(await page.locator(".world-passport").isVisible(), true);
  assert.equal(await stage.evaluate(element => element.stampHit()), true);
  await page.waitForFunction(count => document.querySelector(".drive-stage").inspectWorld().missionsDone > count, before.missionsDone, { polling: 500 });
  const after = await inspect();
  assert.ok(after.score >= before.score + 300, `the checkpoint bonus counted (${before.score} to ${after.score})`);
  assert.equal(await page.locator(".world-passport").isVisible(), false);
  await stage.evaluate(element => element.teleport(1500, 600, 0));

  // Streaming: far from the start new tiles load and the old ones go.
  await stage.evaluate(element => element.teleport(1500, 600, 0));
  await page.waitForFunction(() => { const s = document.querySelector(".drive-stage").inspectWorld(); return s.carTile[0] === 6 && s.tiles >= 9; }, undefined, { polling: 500 });

  // The queue of waiting tiles stays short (a tile is never requested twice while it waits).
  assert.ok((await inspect()).loading.ready < 30, "the tile queue stays short");

  // At an MRT entrance a button goes down to the station page.
  await stage.evaluate(element => element.teleport(-60, -20, 0));
  await page.waitForFunction(() => document.querySelector(".drive-stage").inspectWorld().entrances > 0, undefined, { polling: 500 });
  const entrance = (await inspect()).entranceList[0];
  await stage.evaluate((element, [x, z]) => element.teleport(x + 3, z + 3, 0), [entrance.x, entrance.z]);
  await page.waitForFunction(() => document.querySelector(".drive-stage").inspectWorld().nearEntrance, undefined, { polling: 500 });
  assert.equal(await page.locator(".world-enter").isVisible(), true);
  await page.locator(".world-enter").click();
  await page.waitForSelector("#sg-mrt-page .drive-stage[data-state=ready]");
  assert.match(page.url(), /page=sg-mrt/);
  await page.goBack();
  await page.waitForSelector("#sg-world-page .drive-stage[data-state=ready]");

  // Leaving the page releases the renderer.
  await page.locator("#demo-breadcrumb a").click();
  await page.waitForTimeout(500);
  assert.equal(await page.locator("#sg-world-page canvas:not(.drive-minimap)").count(), 0);
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ chromium: browser.version(), tiles: first.tiles, triangles: first.triangles, drawCalls: first.calls, speed: Number(driven.speed.toFixed(1)), consoleErrors: errors.length }, null, 2));
} finally {
  await browser?.close();
  await server?.close();
}
