import assert from "node:assert/strict";
import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { CLIPS, EXPRESSIONS, GESTURES, HANDS, STORAGE_KEY } from "../src/chibi-dressup/config.js";
import { LANGUAGE_STORAGE_KEY } from "../src/i18n/preferences.js";
import { launchOptions, serveBuild } from "./browser-test-utils.mjs";

const manifest = JSON.parse(await readFile(new URL("../models/chibi-dressup/manifest.json", import.meta.url), "utf8"));
const offline = process.env.CHIBI_DRESSUP_OFFLINE === "1";
const out = path.resolve(process.env.TEST_ARTIFACT_DIR || "models/chibi-dressup/review");
const server = offline ? null : await serveBuild();
const base = server?.url ?? "http://127.0.0.1/Blender-3D-Gallery/";
const bodyRequest = /\/base_body(?:-[\w-]+)?\.glb(?:\?|$)/;
const routeUrl = base + "?page=chibi-dressup";
const staticRoot = path.resolve("dist");
const contentTypes = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json" };
const matching = {
  L: /LeftHand(?:Thumb|Index|Middle|Ring|Pinky)[1-4]$/,
  R: /RightHand(?:Thumb|Index|Middle|Ring|Pinky)[1-4]$/,
};
const rotationChanged = (first, second) => {
  const alignment = Math.abs(first.reduce((sum, value, index) => sum + value * second[index], 0));
  return 1 - alignment > 1e-6;
};

let browser;
let stopping = false;
try {
  browser = await chromium.launch(offline ? {
    ...launchOptions,
    args: ["--single-process", "--in-process-gpu", "--disable-gpu", "--enable-unsafe-swiftshader"],
  } : launchOptions);
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 }, serviceWorkers: "block", locale: "en",
  });
  let bodyDelay, corruptBody;
  // Local build files are the sole resource origin for both modes.
  await context.route("**/*", async route => {
    const url = new URL(route.request().url());
    if (!url.href.startsWith(base)) return route.abort();
    if (bodyRequest.test(url.href)) {
      if (bodyDelay) await bodyDelay;
      if (corruptBody) {
        corruptBody = false;
        return route.fulfill({ body: "not a GLB" });
      }
    }
    if (!offline) return route.continue();
    const rootPath = new URL(base).pathname;
    const file = path.resolve(staticRoot, decodeURIComponent(url.pathname.slice(rootPath.length)) || "index.html");
    if (!file.startsWith(staticRoot + path.sep)) return route.abort();
    try {
      const body = await readFile(file);
      await route.fulfill({ body, contentType: contentTypes[path.extname(file)] ?? "application/octet-stream" });
    } catch (error) {
      if (stopping) return;
      if (error.code !== "ENOENT") throw error;
      await route.fulfill({ status: 404 });
    }
  });

  const page = await context.newPage();
  page.setDefaultTimeout(20_000);
  const requests = [];
  const errors = [];
  page.on("request", request => requests.push(request.url()));
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  const stage = page.locator(".dressup-stage");
  const play = page.locator(".dressup-play");
  const hand = side => page.locator(`[data-hand="${side}"]`);
  const clip = name => page.locator(`[data-clip="${name}"]`);
  const module = id => page.locator(`[data-module="${id}"]`);
  const verifiedModules = manifest.modules.filter(({ status }) => status === "verified");
  const pendingModules = manifest.modules.filter(({ status }) => status === "pending");
  const neutralModules = verifiedModules.filter(({ bodyIds }) => !bodyIds || bodyIds.includes(manifest.defaults.body));
  const checkPendingModulesHidden = async () => {
    for (const { id } of pendingModules) assert.equal(await module(id).count(), 0, `${id} remains hidden`);
  };
  const snapshot = () => stage.evaluate(element => element.inspectDressup());
  const ready = () => page.waitForFunction(() =>
    document.querySelector(".dressup-stage[data-state=ready]")?.inspectDressup().triangles > 0);

  await page.goto(base + "?page=demos");
  const entry = page.locator('.demo-card[data-demo-id="chibi-dressup"]');
  await entry.waitFor();
  assert.equal(requests.filter(url => /\.glb(?:\?|$)/.test(url)).length, 0);
  let releaseBody;
  bodyDelay = new Promise(resolve => { releaseBody = resolve; });
  await entry.locator(".outline-button").click();
  await stage.locator('[role="status"]').waitFor();
  assert.equal(await stage.getAttribute("aria-busy"), "true");
  assert.equal(await play.isDisabled(), true);
  releaseBody();
  bodyDelay = null;
  await ready();
  await checkPendingModulesHidden();
  const routeDownloads = requests.filter(url => /\.glb(?:\?|$)/.test(url)).length;
  // Only the worn modules download with the character; the rest wait until they are chosen.
  assert.equal(routeDownloads, 10 + 1);
  assert.equal((await snapshot()).joints.length, 65);

  await play.focus();
  await page.keyboard.press("Enter");
  assert.equal(await play.textContent(), "Play");
  assert.equal(await stage.getAttribute("aria-label"), "3D character preview");
  const moduleTriangles = {};
  for (const { id } of neutralModules) if (await module(id).getAttribute("aria-pressed") === "true") await module(id).click();
  await page.waitForFunction(() => document.querySelector(".dressup-stage").inspectDressup().triangles === 9512);
  for (const [index, { id }] of neutralModules.entries()) {
    if (index === 0) {
      await module(id).focus();
      await page.keyboard.press("Space");
    } else await module(id).click();
    await page.waitForFunction(id => {
      const state = document.querySelector(".dressup-stage").inspectDressup();
      return state.modules[id] && state.triangles > 9512;
    }, id);
    assert.equal(await module(id).getAttribute("aria-pressed"), "true");
    moduleTriangles[id] = (await snapshot()).triangles - 9512;
    await module(id).click();
    await page.waitForFunction(id => {
      const state = document.querySelector(".dressup-stage").inspectDressup();
      return !state.modules[id] && state.triangles === 9512;
    }, id);
    assert.equal(await module(id).getAttribute("aria-pressed"), "false");
  }
  assert.equal(requests.filter(url => /\.glb(?:\?|$)/.test(url)).length, neutralModules.length + 10, "each module downloads once");
  const tops = neutralModules.filter(({ slot }) => slot === "hair");
  for (const { id } of tops) {
    await module(id).click();
    assert.equal(Object.entries((await snapshot()).modules)
      .filter(([id, visible]) => visible && tops.some(top => top.id === id)).length, 1);
  }

  // A dress covers the bottoms: the jeans are hidden and disabled while it is worn, then return.
  await module("bottom-jeans").click();
  await module("top-dress").click();
  await page.waitForFunction(() => {
    const state = document.querySelector(".dressup-stage").inspectDressup();
    return state.modules["top-dress"] && !state.modules["bottom-jeans"];
  });
  assert.equal(await module("bottom-jeans").isDisabled(), true);
  await module("top-dress").click();
  await page.waitForFunction(() => document.querySelector(".dressup-stage").inspectDressup().modules["bottom-jeans"]);
  assert.equal(await module("bottom-jeans").isDisabled(), false);
  await module("bottom-jeans").click();

  await play.click();
  const clipResults = {};
  for (const name of CLIPS) {
    await clip(name).click();
    const before = await snapshot();
    await page.waitForFunction(({ name, time, mixerTime }) => {
      const state = document.querySelector(".dressup-stage").inspectDressup();
      return state.clip === name && state.time > time && state.mixerTime > mixerTime + 0.15;
    }, { name, time: before.time, mixerTime: before.mixerTime });
    const after = await snapshot();
    const bodyJoints = after.joints.filter(joint => !matching.L.test(joint.name) && !matching.R.test(joint.name));
    const rotated = bodyJoints.filter(({ rotation, rest }) => rotationChanged(rotation, rest));
    const moving = bodyJoints.filter(({ name, rotation }) =>
      rotationChanged(rotation, before.joints.find(joint => joint.name === name).rotation));
    assert.ok(rotated.length > 0 && moving.length > 0, `${name} must animate actual body joints`);
    clipResults[name] = { timeAdvanced: +(after.time - before.time).toFixed(3), rotated: rotated.length, moving: moving.length };
  }

  await play.click();
  const neutral = await snapshot();
  const gestureResults = {};
  for (const side of HANDS) {
    for (const gesture of GESTURES) {
      await hand(side).selectOption(gesture);
      const state = await snapshot();
      const changed = state.joints.filter(({ name, rotation }, index) => {
        assert.equal(name, neutral.joints[index].name);
        return rotationChanged(rotation, neutral.joints[index].rotation);
      });
      assert.ok(changed.length > 0 && changed.every(({ name }) => matching[side].test(name)), `${gesture} ${side} changed the wrong joints`);
      gestureResults[`${gesture}_${side}`] = changed.length;
      await hand(side).selectOption("");
      assert.deepEqual((await snapshot()).joints, neutral.joints, "Clearing a gesture restores the current clip pose");
    }
  }

  await hand("L").selectOption("peace");
  await hand("R").selectOption("thumbs_up");
  const overlaid = await snapshot();
  await play.click();
  await page.waitForFunction(time =>
    document.querySelector(".dressup-stage").inspectDressup().mixerTime > time + 0.15, overlaid.mixerTime);
  const movingWithGestures = await snapshot();
  assert.ok(movingWithGestures.joints.some(({ name, rotation }, index) =>
    !matching.L.test(name) && !matching.R.test(name) && rotationChanged(rotation, overlaid.joints[index].rotation)));
  assert.ok(movingWithGestures.joints.every(({ name, rotation }, index) =>
    !(matching.L.test(name) || matching.R.test(name)) || !rotationChanged(rotation, overlaid.joints[index].rotation)));

  // Expression maps load on first use; each choice shows on the face and survives a reload.
  const expressionMaps = () => requests.filter(url => /\/(?:happy|surprised|sad)(?:-[\w-]+)?\.png(?:\?|$)/.test(url)).length;
  assert.equal(expressionMaps(), 0, "expression maps must not download before they are chosen");
  for (const name of EXPRESSIONS) {
    await page.locator(`[data-expression="${name}"]`).click();
    await page.waitForFunction(name => document.querySelector(".dressup-stage").inspectDressup().expression === name, name);
    assert.equal(await page.locator(`[data-expression="${name}"]`).getAttribute("aria-pressed"), "true");
  }
  assert.equal(expressionMaps(), 3, "three expression maps are fetched once each");
  assert.equal(await page.locator('[data-expression="sad"]').getAttribute("aria-pressed"), "true");

  const selectedTop = tops.at(-1).id;
  await clip("wave").click();
  await page.reload();
  await ready();
  assert.equal(await clip("wave").getAttribute("aria-pressed"), "true");
  assert.equal(await module(selectedTop).getAttribute("aria-pressed"), "true");
  assert.equal(await hand("L").inputValue(), "peace");
  assert.equal(await hand("R").inputValue(), "thumbs_up");
  assert.equal((await snapshot()).clip, "wave");
  await page.waitForFunction(() => document.querySelector(".dressup-stage").inspectDressup().expression === "sad");
  const saved = await page.evaluate(key => JSON.parse(localStorage.getItem(key)), STORAGE_KEY);
  assert.equal(saved.modules.hair, selectedTop);

  // Each extra body: its own skeleton, clips, modules and prop sockets.
  const bodyResults = {};
  const switchTo = async id => {
    await page.locator(`[data-body="${id}"]`).click();
    await page.waitForFunction(id => {
      const state = document.querySelector(".dressup-stage").inspectDressup();
      return state.body === id && !state.switching;
    }, id);
  };
  for (const bodyId of manifest.bodies.map(({ id }) => id).filter(id => id !== manifest.defaults.body)) {
    const ownModules = verifiedModules.filter(({ bodyIds }) => bodyIds?.includes(bodyId));
    await switchTo(bodyId);
    await checkPendingModulesHidden();
    assert.equal((await snapshot()).joints.length, 65);
    assert.equal(await page.locator(`[data-body="${bodyId}"]`).getAttribute("aria-pressed"), "true");
    assert.equal(await module(selectedTop).count(), 0, "modules of another body are not offered");
    const results = {};
    for (const name of CLIPS) {
      await clip(name).click();
      const before = await snapshot();
      await page.waitForFunction(({ name, mixerTime }) => {
        const state = document.querySelector(".dressup-stage").inspectDressup();
        return state.clip === name && state.mixerTime > mixerTime + 0.15;
      }, { name, mixerTime: before.mixerTime });
      results[name] = (await snapshot()).triangles;
    }
    for (const { id } of ownModules) {
      await module(id).click();
      await page.waitForFunction(id => document.querySelector(".dressup-stage").inspectDressup().modules[id], id);
      await module(id).click();
    }
    await module(`${bodyId}-top-tshirt`).click();
    await module(`${bodyId}-bottom-jeans`).click();
    // Clear the gestures so the screenshots show the measured finger grips.
    for (const side of HANDS) await hand(side).selectOption("");
    await mkdir(out, { recursive: true });
    for (const [name, file] of [["take", "take"], ["box", "box"], ["sit", "sit"]]) {
      await clip(name).click();
      await page.waitForTimeout(1300);
      await page.screenshot({ path: path.join(out, `${bodyId}-${file}.png`), fullPage: true });
    }
    await module(`${bodyId}-top-tshirt`).click();
    await module(`${bodyId}-bottom-jeans`).click();
    bodyResults[bodyId] = results;
  }
  await switchTo(manifest.defaults.body);
  await clip("wave").click();

  await mkdir(out, { recursive: true });
  await page.waitForFunction(() => document.querySelector(".dressup-stage").inspectDressup().time > 0.7);
  await play.click();
  await page.screenshot({ path: path.join(out, "desktop.png"), fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.reload();
  await ready();
  assert.equal(await play.textContent(), "Play");
  const frozen = (await snapshot()).mixerTime;
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  assert.equal((await snapshot()).mixerTime, frozen);
  const widths = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
  assert.deepEqual(widths, { viewport: 390, document: 390 });
  await page.screenshot({ path: path.join(out, "mobile.png"), fullPage: true });

  for (const locale of ["zh-Hans", "ms"]) {
    await page.evaluate(([key, locale]) => localStorage.setItem(key, locale), [LANGUAGE_STORAGE_KEY, locale]);
    await page.reload();
    await ready();
    assert.equal(await page.locator("html").getAttribute("lang"), locale);
    assert.equal(await module("hair-bob").textContent(), manifest.modules.find(module => module.id === "hair-bob").label[locale]);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), 390);
  }
  await page.locator("#demo-breadcrumb a").click();
  await entry.waitFor();
  assert.equal(await page.locator("#chibi-dressup-page canvas").count(), 0);
  assert.deepEqual(errors, []);

  corruptBody = true;
  await page.goto(routeUrl);
  const retry = page.locator('#chibi-dressup-page [data-i18n="common.retryExperience"]');
  await retry.waitFor();
  assert.equal(errors.length, 1, "only the injected corrupt GLB should log an error");
  assert.match(errors[0], /^Experience chibi-dressup failed to start SyntaxError:.*not a GLB/);
  await retry.click();
  await ready();
  assert.equal(errors.length, 1, "retry should recover without new errors");

  console.log(JSON.stringify({
    chromium: browser.version(), glbRequests: { demos: 0, dressup: routeDownloads },
    moduleTriangles, clipResults, bodyResults, gestureResults, restored: saved, widths,
    unexpectedErrors: 0, reducedMotion: "paused", errorRecovery: "retry recovered after one injected corrupt GLB",
    screenshots: [path.join(out, "desktop.png"), path.join(out, "mobile.png")],
  }, null, 2));
} finally {
  stopping = true;
  await browser?.close();
  await server?.close();
}
