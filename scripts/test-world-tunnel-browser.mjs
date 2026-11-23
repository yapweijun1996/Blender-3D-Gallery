import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, mkdtemp, readdir, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { chromium } from "playwright";
import { serveBuild } from "./browser-test-utils.mjs";

const tunnel = JSON.parse(await readFile(new URL("./world/fort-canning-tunnel.json", import.meta.url), "utf8"));
const course = [tunnel.approaches.entry, ...tunnel.fragments.map(({ points }) => points), tunnel.approaches.exit]
  .flat().filter((point, index, points) => index === 0 || point.s > points[index - 1].s);
const route = "?page=sg-world&tunnel=fort-canning";
const output = process.env.TUNNEL_SHOTS ?? await mkdtemp(join(tmpdir(), "gallery-tunnel-browser-"));
const dist = process.env.TUNNEL_DIST ?? "dist";
const selectedProfile = process.env.TUNNEL_PROFILE;
const keys = { gas: "ArrowUp", brake: "ArrowDown", left: "ArrowLeft", right: "ArrowRight" };
const launchOptions = { channel: "chrome", headless: true, args: ["--enable-unsafe-swiftshader"] };
const profiles = [
  { label: "desktop", viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, isMobile: false, hasTouch: false },
  { label: "mobile-touch", viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
];
if (selectedProfile) assert.ok(selectedProfile === "retry" || profiles.some(({ label }) => label === selectedProfile), "unknown TUNNEL_PROFILE");

const angleDifference = (a, b) => Math.atan2(Math.sin(a - b), Math.cos(a - b));

function pointAt(distance) {
  const next = course.findIndex(({ s }) => s >= distance);
  if (next < 0) return course.at(-1);
  if (next === 0) return course[0];
  const a = course[next - 1], b = course[next];
  const fraction = (distance - a.s) / (b.s - a.s);
  return { x: a.x + fraction * (b.x - a.x), z: a.z + fraction * (b.z - a.z) };
}

function readState(page) {
  return page.evaluate(() => JSON.parse(window.render_game_to_text()));
}

function button(page, name) {
  return page.locator(`.tunnel-stage [data-key="${name}"]`);
}

async function controller(page, context, touch) {
  const active = new Map();
  const device = touch ? await context.newCDPSession(page) : null;
  const touchEvent = (type, points) => device.send("Input.dispatchTouchEvent", { type, touchPoints: points });
  let points;
  return {
    async layout() {
      if (!touch) return;
      points = await page.locator(".tunnel-stage [data-key]").evaluateAll(buttons => Object.fromEntries(buttons.map(element => {
        const { x, y, width, height } = element.getBoundingClientRect();
        return [element.dataset.key, { x: x + width / 2, y: y + height / 2 }];
      })));
      const size = page.viewportSize();
      for (const [index, name] of Object.keys(keys).entries()) {
        const point = points[name];
        assert.ok(point && point.x >= 0 && point.x < size.width && point.y >= 0 && point.y < size.height, `${name} touch centre is in the viewport`);
        point.id = index + 1;
      }
    },
    async set(names) {
      const released = [];
      for (const [name, point] of active) {
        if (names.includes(name)) continue;
        if (touch) released.push(point);
        else await page.keyboard.up(keys[name]);
        active.delete(name);
      }
      if (released.length) await touchEvent("touchEnd", released);
      let added = false;
      for (const name of names) {
        if (active.has(name)) continue;
        if (touch) active.set(name, points[name]);
        else {
          await page.keyboard.down(keys[name]);
          active.set(name, null);
        }
        added = true;
      }
      if (touch && added) await touchEvent("touchStart", [...active.values()]);
    },
    async cancel() {
      assert.ok(touch && active.size, "there is a touch to cancel");
      await touchEvent("touchCancel", []);
      active.clear();
    },
    async close() {
      if (touch && active.size) await this.cancel();
      if (!touch) await this.set([]);
      await device?.detach();
    },
  };
}

async function waitForReady(page) {
  await page.locator(".tunnel-stage[data-state=ready] canvas").waitFor();
  await page.waitForFunction(() => window.tunnelFrames > 1, undefined, { polling: 100 });
  return readState(page);
}

async function reset(page, tap, origin) {
  await tap(page.locator(".tunnel-reset"));
  await page.waitForFunction(along => {
    const state = JSON.parse(window.render_game_to_text());
    return state.phase === "approach" && Math.abs(state.along - along) < 0.25 && state.speed < 0.25;
  }, origin.along, { polling: 100 });
}

async function photograph(page, name) {
  await page.locator(".tunnel-stage canvas").screenshot({ path: join(output, `${name}.png`), timeout: 20_000 });
}

async function prototypeChunk() {
  const directory = join(dist, "assets");
  const scripts = (await readdir(directory)).filter(file => file.endsWith(".js"));
  const matches = [];
  for (const file of scripts) {
    const text = await readFile(join(directory, file), "utf8");
    if (text.includes("tunnel-preview") && text.includes("tunnel-reset")) matches.push(file);
  }
  assert.equal(matches.length, 1, "the production tunnel has one independently detectable entry chunk");
  return matches[0];
}

async function checkRetry(browser, url) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, serviceWorkers: "block", locale: "en" });
  try {
    const page = await context.newPage();
    const pageErrors = [];
    page.on("pageerror", error => pageErrors.push(error.message));
    const carPattern = /\/car_saga(?:-[\w-]+)?\.glb$/;
    let blocked = 0;
    await page.route(carPattern, request => {
      blocked++;
      return request.fulfill({ status: 503, body: "Injected car model failure" });
    });
    await page.goto(url + route, { waitUntil: "domcontentloaded" });
    const retry = page.getByRole("button", { name: "Retry experience" });
    await retry.waitFor({ timeout: 45_000 });
    assert.equal(blocked, 1, "the real car request failed as intended");
    assert.equal(await page.locator("#sg-world-page canvas").count(), 0, "startup failure leaves no renderer");
    assert.equal(await page.evaluate(() => typeof window.render_game_to_text), "undefined", "startup failure leaves no state callback");
    await page.unroute(carPattern);
    const response = page.waitForResponse(result => carPattern.test(new URL(result.url()).pathname), { timeout: 45_000 });
    await retry.click();
    const model = await response;
    assert.equal(model.status(), 200, "the real car loads when retried");
    const hash = data => createHash("sha256").update(data).digest("hex");
    assert.equal(hash(await model.body()), hash(await readFile(new URL("../models/drive/kit/car_saga.glb", import.meta.url))));
    await page.locator(".tunnel-stage[data-state=ready] canvas").waitFor({ timeout: 45_000 });
    assert.equal(await page.locator("#sg-world-page canvas").count(), 1, "retry mounts one renderer");
    assert.deepEqual(pageErrors, []);
    console.log(JSON.stringify({ result: "PASS", label: "local car 503 and retry", blocked, car: new URL(model.url()).pathname }));
  } finally {
    await context.close();
  }
}

async function drive(page, input, tap, origin, label) {
  const started = performance.now();
  let lastAdvance = started, farthest = origin.along, minimumY = origin.position.y;
  let maxLateral = 0;
  const phases = new Set([origin.phase]);
  const recent = [];
  const touch = label === "mobile-touch";
  let captured = false;
  while (performance.now() - started < 120_000) {
    const state = await readState(page);
    assert.ok([state.along, state.speed, state.position.y, state.heading, state.lateral].every(Number.isFinite), "tunnel state is finite");
    minimumY = Math.min(minimumY, state.position.y);
    maxLateral = Math.max(maxLateral, Math.abs(state.lateral));
    assert.ok(farthest - state.along < 25, `vehicle went back to the approach after ${farthest.toFixed(1)} m: ${JSON.stringify(recent)}`);
    phases.add(state.phase);
    if (state.along > farthest + 0.7) {
      lastAdvance = performance.now();
      farthest = state.along;
    }
    assert.ok(performance.now() - lastAdvance < 15_000, `vehicle stopped advancing: ${JSON.stringify(state)}`);
    if (state.complete) {
      await input.set([]);
      assert.ok(captured, "the vehicle reached the covered bore");
      for (const phase of ["approach", "descent", "covered", "ascent", "surface"])
        assert.ok(phases.has(phase), `${label} used real controls through ${phase}`);
      assert.ok(state.along >= tunnel.length, "vehicle cleared the exit portal");
      assert.ok(minimumY < origin.position.y - 4, "vehicle dropped into the bore");
      assert.ok(state.position.y > origin.position.y - 0.5, "vehicle climbed back to surface level");
      assert.ok(maxLateral < tunnel.width / 2, "vehicle stayed within the road corridor");
      await photograph(page, `${label}-exit`);
      return { phases: [...phases], minimumY, maxLateral, exit: state.along, seconds: Math.round((performance.now() - started) / 1000) };
    }
    if (!captured && state.phase === "covered" && state.along > tunnel.length * 0.4) {
      await input.set([]);
      const pause = page.locator(".tunnel-pause");
      await tap(pause);
      const stopped = await readState(page);
      await photograph(page, `${label}-interior`);
      assert.ok(Math.abs((await readState(page)).along - stopped.along) < 0.05, "pause holds the vehicle at the screenshot location");
      await tap(pause);
      if (touch) {
        await button(page, "gas").scrollIntoViewIfNeeded();
        await input.layout();
      }
      captured = true;
      lastAdvance = performance.now();
    }
    // Use bounded look-ahead to press the same digital controls as a player. Scene state is read-only.
    const lookAhead = (touch ? 11 : 8) + state.speed * 0.65;
    const target = pointAt(state.along + lookAhead);
    const wanted = Math.atan2(target.x - state.position.x, target.z - state.position.z);
    const error = angleDifference(wanted, state.heading);
    const directions = [];
    if (state.speed < (touch ? 7 : 10)) directions.push("gas");
    if (state.speed > (touch ? 8 : 11) && (touch || Math.abs(error) > 0.14)) directions.push("brake");
    const turn = error > 0.05 ? "left" : error < -0.05 ? "right" : null;
    recent.push([state.along.toFixed(1), state.lateral.toFixed(1), state.position.y.toFixed(2), state.speed.toFixed(1), [...directions, turn].filter(Boolean).join("+")]);
    if (recent.length > 18) recent.shift();
    await input.set(turn ? [...directions, turn] : directions);
    if (touch && turn) {
      // Release the turn before any potentially slow screenshot, state read or layout command.
      await page.waitForTimeout(Math.min(100, 40 + 150 * Math.abs(error)));
      await input.set(directions);
    }
    await page.waitForTimeout(touch ? 45 : 65);
  }
  assert.fail(`did not finish ${label} route within 120 seconds: ${JSON.stringify(await readState(page))}`);
}

await mkdir(output, { recursive: true });
const tunnelChunk = process.env.TUNNEL_SITE || selectedProfile === "retry" ? null : await prototypeChunk();
const server = process.env.TUNNEL_SITE ? { url: new URL("./", process.env.TUNNEL_SITE).href, close() {} }
  : await serveBuild(dist);
let browser;
try {
  browser = await chromium.launch(launchOptions);
  for (const { label, hasTouch, ...device } of profiles) {
    if (selectedProfile && selectedProfile !== label) continue;
    const context = await browser.newContext({ ...device, hasTouch, serviceWorkers: "block", locale: "en" });
    const errors = [];
    let input, page;
    try {
      await context.addInitScript(() => {
        window.tunnelFrames = 0;
        window.tunnelPointerEvents = [];
        for (const type of ["pointerdown", "pointerup", "pointercancel", "lostpointercapture"]) {
          document.addEventListener(type, event => {
            const label = event.target.closest?.(".tunnel-preview [data-key], .tunnel-pause, .tunnel-reset");
            if (!label || event.pointerType !== "touch") return;
            window.tunnelPointerEvents.push([type, label.dataset.key ?? label.className, event.pointerId]);
            if (window.tunnelPointerEvents.length > 30) window.tunnelPointerEvents.shift();
          }, true);
        }
        const tunnelCanvases = new WeakSet();
        let counted = false;
        for (const prototype of [WebGLRenderingContext.prototype, WebGL2RenderingContext.prototype]) {
          for (const method of ["drawElements", "drawArrays", "drawElementsInstanced", "drawArraysInstanced"]) {
            const original = prototype[method];
            if (typeof original !== "function") continue;
            prototype[method] = function (...args) {
              if (!tunnelCanvases.has(this.canvas) && this.canvas.closest?.(".tunnel-stage")) tunnelCanvases.add(this.canvas);
              if (!counted && tunnelCanvases.has(this.canvas)) {
                window.tunnelFrames++;
                counted = true;
                requestAnimationFrame(() => { counted = false; });
              }
              return original.apply(this, args);
            };
          }
        }
      });
      page = await context.newPage();
      page.setDefaultTimeout(45_000);
      page.on("pageerror", error => errors.push(error.message));
      page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
      const requested = new Set();
      page.on("request", request => requested.add(new URL(request.url()).pathname.split("/").at(-1)));
      const tap = element => hasTouch ? element.tap() : element.click();
      const checkNormal = !hasTouch && process.env.TUNNEL_CHECK_NORMAL !== "0";
      if (checkNormal) {
        await page.goto(server.url + "?page=sg-world", { waitUntil: "domcontentloaded" });
        await page.locator("#sg-world-page .drive-stage[data-state=ready]").waitFor({ timeout: 120_000 });
        assert.equal(await page.locator(".tunnel-stage").count(), 0);
        if (tunnelChunk) assert.ok(!requested.has(tunnelChunk), "a fresh normal world did not fetch the tunnel chunk");
        await page.locator(`#sg-world-page a[href="${route}"]`).click();
      } else await page.goto(server.url + route, { waitUntil: "domcontentloaded" });
      const origin = await waitForReady(page);
      if (tunnelChunk) assert.ok(requested.has(tunnelChunk), "the opt-in world fetched the tunnel entry chunk");
      assert.equal(await page.locator(".tunnel-preview h1").textContent(), "Fort Canning Link tunnel");
      assert.match(await page.title(), /Fort Canning Link tunnel/);
      assert.ok(origin.ready && origin.along < 0 && origin.phase === "approach", "starts on the surface approach");
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), "no horizontal overflow");
      await photograph(page, `${label}-entrance`);
      if (hasTouch) await button(page, "gas").scrollIntoViewIfNeeded();
      input = await controller(page, context, hasTouch);
      if (hasTouch) {
        await input.layout();
        await input.set(["gas"]);
        await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).speed > 1.5, undefined, { polling: 100 });
        await input.cancel();
        const before = await readState(page);
        const frames = await page.evaluate(() => window.tunnelFrames);
        await page.waitForFunction(count => window.tunnelFrames >= count + 25, frames, { polling: 100 });
        assert.ok((await readState(page)).speed <= before.speed + 0.25, "pointercancel releases the accelerator");
        await reset(page, tap, origin);
        await button(page, "gas").scrollIntoViewIfNeeded();
        await input.layout();
      }
      const result = await drive(page, input, tap, origin, label);
      await reset(page, tap, origin);
      await tap(page.locator("#demo-breadcrumb a"));
      await page.waitForFunction(() => !document.querySelector(".tunnel-stage canvas") && typeof window.render_game_to_text === "undefined");
      const disposedFrame = await page.evaluate(() => window.tunnelFrames);
      await page.waitForTimeout(250);
      assert.equal(await page.evaluate(() => window.tunnelFrames), disposedFrame, "navigation stops the tunnel renderer");
      assert.ok(!new URL(page.url()).searchParams.has("tunnel"), "the normal Demos navigation drops the opt-in query");
      await page.goBack();
      assert.ok((await waitForReady(page)).along < 0, "browser Back remounts at the initial approach");
      if (checkNormal) {
        await page.locator('.tunnel-preview a[data-page="sg-world"]').click();
        await page.locator("#sg-world-page .drive-stage[data-state=ready]").waitFor({ timeout: 120_000 });
        assert.ok(!new URL(page.url()).searchParams.has("tunnel"), "the same-page return restores the normal world route");
        assert.equal(await page.locator(".tunnel-stage").count(), 0);
        assert.equal(await page.evaluate(() => typeof window.render_game_to_text), "undefined");
        assert.doesNotMatch(await page.title(), /Fort Canning Link tunnel/);
      } else await tap(page.locator("#demo-breadcrumb a"));
      assert.deepEqual(errors, []);
      console.log(JSON.stringify({ result: "PASS", label, ...result, tunnelChunk, screenshots: output }));
    } catch (error) {
      const pointers = await page?.evaluate(() => window.tunnelPointerEvents).catch(() => null);
      console.error(JSON.stringify({ result: "FAIL", label, url: page?.url(), message: error.message, errors, pointers }));
      throw error;
    } finally {
      await input?.close();
      await context.close();
    }
  }
  if ((!selectedProfile && !process.env.TUNNEL_SITE) || selectedProfile === "retry") await checkRetry(browser, server.url);
} finally {
  await browser?.close();
  await server.close();
}
