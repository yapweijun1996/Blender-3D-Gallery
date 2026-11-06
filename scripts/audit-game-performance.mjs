import { pullShot, chargePull, releasePull, setPullRatio } from "./browser-test-utils.mjs";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { chromium } from "playwright";
import { launchOptions, serveBuild } from "./browser-test-utils.mjs";

// The build is never changed; an empty output directory avoids overwrites.
const [buildArgument, outputArgument, mode, ...extra] = process.argv.slice(2);
if (!buildArgument || !outputArgument || extra.length || (mode && !["performance-quality", "lifecycle-long"].includes(mode))) {
  console.error("Usage: node scripts/audit-game-performance.mjs <build-dir> <empty-output-dir> [performance-quality|lifecycle-long]");
  process.exit(2);
}
const performanceQuality = mode === "performance-quality";
const lifecycleLong = mode === "lifecycle-long";
const buildDir = path.resolve(buildArgument), outputDir = path.resolve(outputArgument);
assert.ok(outputDir !== buildDir && !outputDir.startsWith(`${buildDir}${path.sep}`), "Output must be outside the build directory");
await fs.access(path.join(buildDir, "index.html"));
await fs.mkdir(outputDir, { recursive: true });
assert.equal((await fs.readdir(outputDir)).length, 0, "Output directory must be empty");
const buildInfoBytes = await fs.readFile(path.join(buildDir, "build-info.json"));
const report = {
  methodology: {
    description: "Chromium headless, software WebGL and loopback production build; mobile is viewport/touch emulation, not a physical device.",
    ready: "Wall time from navigation to the game ready signal in a fresh browser context; no network or CPU throttling.",
    shot: "Rack seed 42, default cue placement and aim 0 degrees, power 75%; actual game controls and simulation. Six-second requestAnimationFrame intervals are classified by game phase at each callback.",
    frameSampling: "An interval on a phase transition can partly belong to the previous phase. Frame pacing is not GPU time; the game renders only when needed.",
    drawCalls: "Separate instrumented contexts count native WebGL2 submissions during one synchronous advanceTime(0) render. Draw instrumentation is absent from frame samples.",
    lifecycle: "Six Game-to-Gallery cycles in one page, with forced-GC snapshots immediately and 300ms after returning to Gallery.",
    limitations: [
      "SwiftShader, headless execution, OS file cache and unthrottled loopback are not a hardware GPU or realistic mobile network.",
      "Emulation does not establish physical iOS/Android performance, browser chrome, battery or thermal behavior.",
      "Draw counts and frame intervals do not measure GPU time, shader stalls, texture allocation or total device memory.",
      "Six lifecycle cycles and JS heap/DOM/listener snapshots do not prove the absence of sustained leaks, including GPU leaks.",
    ],
  },
  environment: {
    node: process.version, platform: process.platform, architecture: process.arch,
    osRelease: os.release(), cpu: os.cpus()[0]?.model || "unknown",
    logicalCpuCount: os.cpus().length, launchOptions, buildDir,
    buildInfo: JSON.parse(buildInfoBytes),
    buildInfoSha256: crypto.createHash("sha256").update(buildInfoBytes).digest("hex"),
    measuredAt: new Date().toISOString(),
  },
  viewports: [], lifecycle: null, errors: [],
};
const server = await serveBuild(buildDir);
let browser;
const defaultSizes = [
  { width: 1440, height: 900, deviceScaleFactor: 1, isMobile: false, hasTouch: false, samples: 3 },
  { width: 390, height: 844, deviceScaleFactor: 1, isMobile: true, hasTouch: true, samples: 3 },
  { width: 390, height: 844, deviceScaleFactor: 3, isMobile: true, hasTouch: true, samples: 2 },
];
const sizes = performanceQuality ? [defaultSizes[2]] : lifecycleLong ? [] : defaultSizes;
if (performanceQuality) {
  report.methodology.quality = "Open App options, select Graphics quality: Performance, close the dialog, then measure a real shot at 390x844 / DPR 3.";
  report.methodology.drawCalls = "Not sampled in this quality-only mode.";
  report.methodology.lifecycle = "Not sampled in this quality-only mode.";
}
if (lifecycleLong) {
  report.methodology.ready = "Not sampled in this lifecycle-only mode.";
  report.methodology.shot = "Not sampled in this lifecycle-only mode.";
  report.methodology.frameSampling = "Not sampled in this lifecycle-only mode.";
  report.methodology.drawCalls = "Not sampled in this lifecycle-only mode.";
  report.methodology.lifecycle = "Thirty Game-to-Gallery cycles in one Chromium page, with forced-GC heap/DOM/listener and owner-lock snapshots immediately and 300ms after each return.";
  report.methodology.limitations[3] = "Thirty lifecycle cycles and JS heap/DOM/listener snapshots do not prove the absence of sustained leaks, including GPU leaks.";
}
const optionsFor = ({ width, height, deviceScaleFactor, isMobile, hasTouch }) => ({
  viewport: { width, height }, deviceScaleFactor, isMobile, hasTouch,
});
function captureErrors(page, label) {
  page.on("pageerror", (error) => report.errors.push({ label, type: "pageerror", message: error.message }));
  page.on("console", (message) => {
    if (message.type() === "error") report.errors.push({ label, type: "console", message: message.text() });
  });
}
async function ready(page) {
  const start = performance.now();
  await page.goto(`${server.url}?page=game`);
  await page.waitForFunction(() => window.render_game_to_text && JSON.parse(window.render_game_to_text()).ready, null, { timeout: 60000 });
  return performance.now() - start;
}
async function waitForPhase(page, phase) {
  await page.waitForFunction((expected) => JSON.parse(window.render_game_to_text()).phase === expected, phase, { timeout: 30000 });
}
async function selectPerformanceQuality(page, screenshotPath) {
  const options = page.locator('[data-action="options"]');
  if (await options.count() !== 1 || !(await options.isEnabled())) {
    throw new Error("Performance quality mode requires an enabled App options control");
  }
  await options.click();
  const dialog = page.locator("#game-options");
  const quality = dialog.locator("#graphics-quality");
  if (!(await dialog.isVisible()) || await quality.count() !== 1 || !(await quality.isEnabled()) ||
      await quality.locator('option[value="performance"]').count() !== 1) {
    throw new Error("Performance quality mode requires an enabled Graphics quality select with a Performance option");
  }
  await quality.selectOption("performance");
  if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true });
  await dialog.locator('[data-action="close-options"]').click();
  await dialog.waitFor({ state: "hidden" });
  assert.equal(await quality.inputValue(), "performance", "Graphics quality must stay on Performance after closing options");
}
async function startFixedMatch(page) {
  // The only test override is scoped to rack creation in this isolated context.
  await page.evaluate(() => {
    const original = crypto.getRandomValues.bind(crypto);
    Object.defineProperty(crypto, "getRandomValues", { configurable: true, value(array) {
      if (array instanceof Uint32Array && array.length === 1) { array[0] = 42; return array; }
      return original(array);
    } });
  });
  await page.locator('[data-action="new"]:visible').click();
  await waitForPhase(page, "placing");
  await page.evaluate(() => delete crypto.getRandomValues);
  await page.locator('[data-action="place"]').click();
  await waitForPhase(page, "aiming");
  setPullRatio(page, Math.pow(0.75, 2 / 3));
}
async function rendererInfo(page) {
  return page.evaluate(() => {
    const canvas = document.querySelector("#game-viewport canvas");
    const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
    const debug = gl?.getExtension("WEBGL_debug_renderer_info");
    return {
      userAgent: navigator.userAgent, devicePixelRatio,
      hardwareConcurrency: navigator.hardwareConcurrency, canvasPixels: [canvas.width, canvas.height],
      renderer: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : "unavailable",
      vendor: debug ? gl.getParameter(debug.UNMASKED_VENDOR_WEBGL) : "unavailable",
      webglVersion: gl?.getParameter(gl.VERSION), maxTextureSize: gl?.getParameter(gl.MAX_TEXTURE_SIZE),
    };
  });
}

async function frameIntervals(page) {
  return page.evaluate(() => new Promise((resolve) => {
    const phases = { moving: [], settled: [], other: [] };
    let start, previous;
    const tick = (now) => {
      if (start === undefined) start = now;
      const phase = document.querySelector(".game-shell")?.dataset.phase;
      const category = phase === "moving" ? "moving" : ["aiming", "placing", "finished"].includes(phase) ? "settled" : "other";
      if (previous !== undefined) phases[category].push(now - previous);
      previous = now;
      if (now - start < 6000) requestAnimationFrame(tick);
      else {
        const summarize = (values) => {
          if (!values.length) return { count: 0, meanMs: null, p50Ms: null, p95Ms: null, maxMs: null };
          values.sort((a, b) => a - b);
          return {
            count: values.length, meanMs: values.reduce((sum, value) => sum + value, 0) / values.length,
            p50Ms: values[Math.floor((values.length - 1) * 0.5)],
            p95Ms: values[Math.ceil(values.length * 0.95) - 1], maxMs: values.at(-1),
          };
        };
        resolve(Object.fromEntries(Object.entries(phases).map(([key, values]) => [key, summarize(values)])));
      }
    };
    requestAnimationFrame(tick);
  }));
}

async function measureDrawCalls(size) {
  const context = await browser.newContext(optionsFor(size));
  await context.addInitScript(() => {
    window.__drawAudit = { active: false, calls: 0, triangles: 0, lines: 0 };
    for (const name of ["drawElements", "drawArrays", "drawElementsInstanced", "drawArraysInstanced"]) {
      const original = WebGL2RenderingContext.prototype[name];
      WebGL2RenderingContext.prototype[name] = function (...args) {
        if (window.__drawAudit.active) {
          const mode = args[0], count = name.startsWith("drawElements") ? args[1] : args[2];
          const instances = name.endsWith("Instanced") ? args.at(-1) : 1;
          window.__drawAudit.calls++;
          if (mode === this.TRIANGLES) window.__drawAudit.triangles += count / 3 * instances;
          else if (mode === this.TRIANGLE_STRIP || mode === this.TRIANGLE_FAN) window.__drawAudit.triangles += Math.max(0, count - 2) * instances;
          else if (mode === this.LINES) window.__drawAudit.lines += count / 2 * instances;
          else if (mode === this.LINE_STRIP) window.__drawAudit.lines += Math.max(0, count - 1) * instances;
          else if (mode === this.LINE_LOOP) window.__drawAudit.lines += count * instances;
        }
        return original.apply(this, args);
      };
    }
  });
  const page = await context.newPage();
  captureErrors(page, `${size.width} DPR ${size.deviceScaleFactor} draw-count`);
  try {
    await ready(page);
    const sample = () => page.evaluate(() => {
      if (typeof window.advanceTime !== "function") throw new Error("Game observation hook unavailable");
      window.__drawAudit = { active: true, calls: 0, triangles: 0, lines: 0 };
      window.advanceTime(0);
      window.__drawAudit.active = false;
      return { ...window.__drawAudit };
    });
    const setup = await sample();
    await startFixedMatch(page);
    const aiming = await sample();
    return { setup, aiming };
  } finally { await context.close(); }
}

async function measureLifecycle({ cycles = 6, recordLocks = false } = {}) {
  const context = await browser.newContext(optionsFor(defaultSizes[0]));
  const page = await context.newPage();
  const errorOffset = report.errors.length;
  captureErrors(page, "lifecycle");
  const result = { cycles, cdpAvailable: false, snapshots: [] };
  if (recordLocks) result.completedCycles = 0;
  let currentCycle = 0;
  try {
    await page.goto(server.url);
    await page.waitForSelector("#catalog .asset-card");
    let cdp;
    try {
      cdp = await context.newCDPSession(page);
      await cdp.send("HeapProfiler.enable");
      result.cdpAvailable = true;
    } catch (error) { result.cdpError = error.message; }
    const snapshot = async (label) => {
      if (!cdp && !recordLocks) return;
      const entry = { label };
      try {
        if (cdp) {
          await cdp.send("HeapProfiler.collectGarbage");
          entry.heap = await cdp.send("Runtime.getHeapUsage");
          entry.dom = await cdp.send("Memory.getDOMCounters");
        } else {
          entry.error = "CDP forced-GC metrics are unavailable";
        }
      } catch (error) { entry.error = error.message; }
      if (recordLocks) {
        try {
          entry.locks = await page.evaluate(async () => {
            if (!navigator.locks?.query) return { available: false };
            const state = await navigator.locks.query();
            const owner = (locks) => locks.filter((lock) => lock.name === "blender-gallery-game-owner").map(({ name, mode }) => ({ name, mode }));
            return { available: true, held: owner(state.held), pending: owner(state.pending) };
          });
        } catch (error) { entry.locks = { available: false, error: error.message }; }
        entry.errorsSoFar = report.errors.slice(errorOffset);
      }
      result.snapshots.push(entry);
    };
    await snapshot("initial-gallery");
    for (let i = 1; i <= result.cycles; i++) {
      currentCycle = i;
      await page.locator('[data-page="game"]').click();
      await page.waitForFunction(() => window.render_game_to_text && JSON.parse(window.render_game_to_text()).ready, null, { timeout: 60000 });
      assert.equal(await page.locator("#game-page canvas").count(), 1);
      await page.getByRole("link", { name: "Gallery", exact: true }).click();
      await page.waitForFunction(() => !window.render_game_to_text && document.querySelector("#game-page").hidden);
      assert.equal(await page.locator("#game-page canvas").count(), 0);
      await snapshot(`gallery-after-cycle-${i}-immediate`);
      await page.waitForTimeout(300);
      await snapshot(`gallery-after-cycle-${i}-settled-300ms`);
      if (await page.evaluate(() => !!navigator.locks?.query)) {
        await page.waitForFunction(async () => !(await navigator.locks.query()).held.some((lock) => lock.name === "blender-gallery-game-owner"), null, { timeout: 10000 });
      }
      if (recordLocks) result.completedCycles = i;
    }
  } catch (error) {
    if (!recordLocks) throw error;
    result.error = error.message;
    result.failedCycle = currentCycle;
  } finally {
    if (recordLocks) result.errors = report.errors.slice(errorOffset);
    await context.close();
  }
  return result;
}

try {
  browser = await chromium.launch(launchOptions);
  report.environment.browser = browser.version();
  let fixedRackSignature;
  for (const size of sizes) {
    const measurements = [];
    for (let sample = 1; sample <= size.samples; sample++) {
      const context = await browser.newContext(optionsFor(size));
      const page = await context.newPage();
      captureErrors(page, `${size.width} DPR ${size.deviceScaleFactor} sample ${sample}`);
      try {
        const readyMs = await ready(page);
        const prefix = `${size.width}x${size.height}-dpr${size.deviceScaleFactor}${performanceQuality ? "-performance" : ""}`;
        if (sample === 1) await page.screenshot({ path: path.join(outputDir, `setup-${prefix}.png`), fullPage: true });
        if (performanceQuality) {
          await selectPerformanceQuality(page, sample === 1 ? path.join(outputDir, `options-${prefix}.png`) : null);
        }
        await startFixedMatch(page);
        if (performanceQuality) {
          try {
            await page.waitForFunction(() => {
              const canvas = document.querySelector("#game-viewport canvas");
              return canvas && canvas.width === canvas.clientWidth && canvas.height === canvas.clientHeight;
            }, null, { timeout: 5000 });
          } catch {
            throw new Error("Performance quality was selected, but the canvas did not reach 1x CSS resolution");
          }
        }
        const renderer = await rendererInfo(page);
        const quality = performanceQuality ? await page.evaluate(() => {
          const canvas = document.querySelector("#game-viewport canvas");
          return { selected: document.querySelector("#graphics-quality").value, canvasCssPixels: [canvas.clientWidth, canvas.clientHeight] };
        }) : undefined;
        const beforeShot = await page.evaluate(() => JSON.parse(window.render_game_to_text()));
        assert.equal(beforeShot.phase, "aiming");
        assert.equal(beforeShot.aim, 0);
        assert.equal(beforeShot.power, 0.75);
        assert.equal(beforeShot.balls[0].x, -0.7);
        assert.equal(beforeShot.balls[0].z, 0);
        const rackSignature = crypto.createHash("sha256").update(JSON.stringify(beforeShot.balls)).digest("hex");
        if (fixedRackSignature === undefined) fixedRackSignature = rackSignature;
        assert.equal(rackSignature, fixedRackSignature, "Rack must be identical across samples");
        if (sample === 1) await page.screenshot({ path: path.join(outputDir, `aiming-${prefix}.png`), fullPage: true });
        await pullShot(page);
        await waitForPhase(page, "moving");
        assert.ok(Math.abs(await page.evaluate(() => JSON.parse(window.render_game_to_text()).power) - .75) < 1e-5, "benchmark preserves75% physical strength");
        measurements.push({ sample, readyMs, renderer, rackSignature, intervals: await frameIntervals(page), ...(quality ? { quality } : {}) });
      } finally { await context.close(); }
    }
    report.viewports.push({ ...size, measurements, drawCalls: performanceQuality ? null : await measureDrawCalls(size) });
  }
  if (!performanceQuality) {
    try {
      report.lifecycle = await measureLifecycle(lifecycleLong ? { cycles: 30, recordLocks: true } : undefined);
      if (lifecycleLong && (report.lifecycle.error || report.lifecycle.completedCycles !== 30 ||
          !report.lifecycle.cdpAvailable || report.lifecycle.snapshots.length !== 61 || report.lifecycle.errors.length ||
          report.lifecycle.snapshots.some((entry) => entry.error || !entry.locks?.available))) {
        process.exitCode = 1;
      }
    } catch (error) {
      report.lifecycle = { error: error.message };
      process.exitCode = 1;
    }
  } else {
    report.lifecycle = { skipped: true, reason: "Performance-quality mode measures the selected mobile setting only." };
  }
  await fs.writeFile(path.join(outputDir, "results.json"), `${JSON.stringify(report, null, 2)}\n`, { flag: "wx" });
  console.log(JSON.stringify({ outputDir, browser: report.environment.browser, errors: report.errors, viewports: report.viewports, lifecycle: report.lifecycle }, null, 2));
} finally {
  await browser?.close();
  await server.close();
}
