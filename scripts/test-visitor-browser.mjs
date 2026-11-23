import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { chromium } from "playwright";
import { launchOptions, serveBuild } from "./browser-test-utils.mjs";

const variants = [
  {
    id: "gjh-mall-visitor-v2",
    file: "../models/gjh-mall-visitor-v2/exports/gjh-mall-visitor-v2.glb",
    viewport: { width: 1280, height: 900 },
    options: {
      hair: ["swept", "short"], hairColor: ["brown", "black"], outfit: ["polo", "hoodie"],
      skin: ["light", "medium", "dark"], glasses: ["on", "off"], backpack: ["on", "off"],
      watch: ["on", "off"],
      animation: ["idle", "walk", "sprint", "sit", "stand", "pickup", "place", "push", "elevator"],
    },
    loop: "sprint",
    once: "sit",
  },
  {
    id: "gjh-visitor-v3",
    file: "../models/gjh-visitor-v3/exports/gjh-visitor-v3.glb",
    viewport: { width: 390, height: 844 },
    options: {
      hair: ["wavy", "short"], hairColor: ["black", "brown"], outfit: ["hoodie", "tee"],
      skin: ["light", "medium", "dark"], backpack: ["on", "off"], badge: ["on", "off"],
      watch: ["on", "off"],
      animation: ["idle", "walk", "run", "turn_left", "turn_right", "sit_down", "stand_up", "pick_up", "carry", "wave", "point", "push_cart"],
    },
    loop: "carry",
    once: "wave",
  },
];
const hash = bytes => createHash("sha256").update(bytes).digest("hex");
const server = await serveBuild();
let browser;

function currentChoices(fields) {
  return fields.evaluateAll(selects => Object.fromEntries(selects.map(select => [select.dataset.visitorControl, select.value])));
}

function waitForFrames(page, before) {
  return page.waitForFunction(count => window.visitorDraws > count + 2, before, { timeout: 10000 });
}

async function waitForStill(page) {
  await page.evaluate(() => { window.visitorStill = { previous: -1, frames: 0 }; });
  return page.waitForFunction(() => {
    const state = window.visitorStill;
    if (state.previous === window.visitorDraws) state.frames++;
    else { state.previous = window.visitorDraws; state.frames = 0; }
    return state.frames >= 8;
  }, null, { timeout: 15000 });
}

function withoutIdleClip(bytes) {
  const jsonLength = bytes.readUInt32LE(12);
  const json = bytes.toString("utf8", 20, 20 + jsonLength);
  assert.ok(JSON.parse(json).animations.some(animation => animation.name === "idle"));
  const matches = [...json.matchAll(/"name"\s*:\s*"idle"/g)];
  assert.equal(matches.length, 1);
  const [match] = matches;
  const offset = 20 + Buffer.byteLength(json.slice(0, match.index));
  const changed = Buffer.from(bytes);
  changed.write(match[0].replace('"idle"', '"test"'), offset);
  return changed;
}

try {
  browser = await chromium.launch(launchOptions);
  for (const variant of variants) {
    const context = await browser.newContext({
      viewport: variant.viewport, reducedMotion: "reduce", serviceWorkers: "block",
      isMobile: variant.viewport.width < 600, hasTouch: variant.viewport.width < 600,
    });
    try {
      await context.addInitScript(() => {
        window.visitorDraws = 0;
        let counted = false;
        for (const prototype of [WebGLRenderingContext.prototype, WebGL2RenderingContext.prototype]) {
          for (const method of ["drawElements", "drawArrays", "drawElementsInstanced", "drawArraysInstanced"]) {
            const draw = prototype[method];
            if (typeof draw !== "function") continue;
            prototype[method] = function (...args) {
              if (!counted) {
                window.visitorDraws++;
                counted = true;
                requestAnimationFrame(() => { counted = false; });
              }
              return draw.apply(this, args);
            };
          }
        }
      });
      const page = await context.newPage();
      const errors = [];
      page.on("pageerror", error => errors.push(error.message));
      page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });

      const glb = page.waitForResponse(response => new URL(response.url()).pathname.endsWith(".glb"));
      await page.goto(server.url + "?model=" + variant.id, { waitUntil: "domcontentloaded" });
      const response = await glb;
      assert.equal(response.status(), 200);
      assert.equal(hash(await response.body()), hash(await readFile(new URL(variant.file, import.meta.url))));
      const fields = page.locator(".visitor-v2-controls [data-visitor-control]");
      const canvas = page.locator("#viewport canvas");
      const select = key => page.locator(`[data-visitor-control="${key}"]`);
      const ready = () => page.waitForFunction(() => !document.querySelector("#reset-view").disabled && window.visitorDraws > 0);
      await ready();
      const defaults = Object.fromEntries(Object.entries(variant.options).map(([key, values]) => [key, values[0]]));
      assert.deepEqual(await fields.evaluateAll(selects => selects.map(select => (
        [select.dataset.visitorControl, Array.from(select.options, option => option.value)]
      ))), Object.entries(variant.options));
      assert.deepEqual(await currentChoices(fields), defaults);
      await waitForStill(page);
      const original = hash(await canvas.screenshot());

      for (const [key, values] of Object.entries(variant.options))
        if (key !== "animation") await select(key).selectOption(values.at(-1));
      await waitForStill(page);
      assert.notEqual(hash(await canvas.screenshot()), original, "cosmetic choices change the rendered GLB");
      await select("animation").selectOption(variant.loop);
      await waitForStill(page);
      await page.locator("#reset-view").click();
      assert.deepEqual(await currentChoices(fields), defaults);
      await waitForStill(page);
      assert.equal(hash(await canvas.screenshot()), original, "reset recovers the default appearance and pose");

      await page.emulateMedia({ reducedMotion: "no-preference" });
      let before = await page.evaluate(() => window.visitorDraws);
      await select("animation").selectOption(variant.loop);
      await waitForFrames(page, before);
      before = await page.evaluate(() => window.visitorDraws);
      await select("animation").selectOption(variant.once);
      await waitForFrames(page, before);
      await waitForStill(page);

      await page.locator("#close-viewer").click();
      assert.equal(await fields.count(), 0);
      assert.equal(await canvas.count(), 0);
      await page.emulateMedia({ reducedMotion: "reduce" });
      await page.locator(`#catalog a[data-asset-id="${variant.id}"]`).first().click();
      await ready();
      assert.deepEqual(await currentChoices(fields), defaults);
      await page.locator("#close-viewer").click();
      assert.deepEqual(errors, []);
      console.log(`PASS ${variant.id}: exact GLB, controls, appearance, motion, reset, close and reopen`);
    } finally {
      await context.close();
    }
  }

  const context = await browser.newContext({ serviceWorkers: "block" });
  try {
    const page = await context.newPage();
    await page.route("**/*.glb", async route => {
      const response = await route.fetch();
      await route.fulfill({ response, body: withoutIdleClip(await response.body()) });
    });
    await page.goto(server.url + "?model=" + variants[0].id, { waitUntil: "domcontentloaded" });
    await page.locator("#retry-view").waitFor({ state: "visible" });
    assert.equal(await page.locator(".visitor-v2-controls").count(), 0, "failed initialization cannot leave controls attached");
    assert.equal(await page.locator("#viewport canvas").count(), 0);
    await page.unroute("**/*.glb");
    await page.locator("#retry-view").click();
    await page.locator(".visitor-v2-controls").waitFor({ state: "visible" });
    assert.equal(await page.locator(".visitor-v2-controls").count(), 1);
    console.log("PASS missing idle clip leaves no controls or canvas behind and can retry");
  } finally {
    await context.close();
  }
} finally {
  await browser?.close();
  await server.close();
}
