import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { chromium } from "playwright";
import { launchOptions, serveBuild } from "./browser-test-utils.mjs";

const [baselineArgument, afterArgument, outputArgument, ...extra] = process.argv.slice(2);
if (!baselineArgument || !afterArgument || !outputArgument || extra.length) {
  console.error("Usage: node scripts/audit-game-paired-performance.mjs <baseline-build> <after-build> <empty-output-dir>");
  process.exit(2);
}
const builds = { baseline: path.resolve(baselineArgument), after: path.resolve(afterArgument) };
const outputDir = path.resolve(outputArgument);
for (const buildDir of Object.values(builds)) {
  assert.ok(outputDir !== buildDir && !outputDir.startsWith(`${buildDir}${path.sep}`), "Output must be outside both build directories");
  await fs.access(path.join(buildDir, "index.html"));
}
const buildInfo = {};
for (const [name, buildDir] of Object.entries(builds)) {
  const bytes = await fs.readFile(path.join(buildDir, "build-info.json"));
  buildInfo[name] = { path: buildDir, identity: JSON.parse(bytes), sha256: crypto.createHash("sha256").update(bytes).digest("hex") };
}
await fs.mkdir(outputDir, { recursive: true });
assert.equal((await fs.readdir(outputDir)).length, 0, "Output directory must be empty");
const order = ["baseline", "after", "baseline", "after", "baseline", "after"];
const report = {
  methodology: {
    execution: "One headless Chromium process. One fresh context per run. Baseline and after alternate sequentially three times each; no samples overlap.",
    warmup: "One fresh-context warmup per build in baseline/after order, with one real shot observed for 800ms; warmups are recorded separately and excluded from the six measured samples.",
    conditions: "1440x900 CSS pixels, DPR 1, no CPU or network throttle, loopback production builds, identical browser launch flags and SwiftShader software WebGL.",
    shot: "Rack seed 42, default cue placement, aim 0 degrees, power 75%; real UI controls and game simulation. Six seconds of requestAnimationFrame intervals start after moving is observed and are classified by game phase at each callback.",
    comparison: "Moving and settled summaries are separate. Intervals crossing a phase transition are assigned to the phase seen at the callback. Three paired samples are descriptive and do not establish statistical significance.",
    limitations: [
      "SwiftShader, headless Chromium, OS file cache and loopback are not physical GPU, real mobile device or real-world network performance.",
      "Frame intervals are not GPU timers. Other host workload, scheduling and thermal conditions can affect results.",
      "This benchmark does not measure memory leaks or justify changing model appearance.",
    ],
    betweenContextsMs: 300,
    measuredOrder: order,
  },
  environment: {
    node: process.version, platform: process.platform, architecture: process.arch,
    osRelease: os.release(), cpu: os.cpus()[0]?.model || "unknown",
    logicalCpuCount: os.cpus().length, launchOptions, buildInfo,
    measuredAt: new Date().toISOString(),
  },
  warmups: [], samples: [], errors: [],
};
const contextOptions = { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, hasTouch: false, isMobile: false };
const servers = {};
let browser;
let rackSignature;

function captureErrors(page, label) {
  page.on("pageerror", (error) => report.errors.push({ label, type: "pageerror", message: error.message }));
  page.on("console", (message) => {
    if (message.type() === "error") report.errors.push({ label, type: "console", message: message.text() });
  });
}
async function ready(page, url) {
  const start = performance.now();
  await page.goto(`${url}?page=game`);
  await page.waitForFunction(() => window.render_game_to_text && JSON.parse(window.render_game_to_text()).ready, null, { timeout: 60000 });
  return performance.now() - start;
}
async function phase(page, expected) {
  await page.waitForFunction((value) => JSON.parse(window.render_game_to_text()).phase === value, expected, { timeout: 30000 });
}
async function startShot(page) {
  // The override applies only to rack creation in this disposable browser context.
  await page.evaluate(() => {
    const original = crypto.getRandomValues.bind(crypto);
    Object.defineProperty(crypto, "getRandomValues", { configurable: true, value(array) {
      if (array instanceof Uint32Array && array.length === 1) { array[0] = 42; return array; }
      return original(array);
    } });
  });
  await page.locator('[data-action="new"]:visible').click();
  await phase(page, "placing");
  await page.evaluate(() => delete crypto.getRandomValues);
  await page.locator('[data-action="place"]').click();
  await phase(page, "aiming");
  await page.locator("#shot-power").evaluate((input) => {
    input.value = "75";
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  const state = await page.evaluate(() => JSON.parse(window.render_game_to_text()));
  assert.equal(state.aim, 0);
  assert.equal(state.power, 0.75);
  assert.equal(state.balls[0].x, -0.7);
  assert.equal(state.balls[0].z, 0);
  const balls = state.balls.map(({ id, x, z, pocketed }) => ({ id, x, z, pocketed }));
  const signature = crypto.createHash("sha256").update(JSON.stringify(balls)).digest("hex");
  if (rackSignature === undefined) rackSignature = signature;
  assert.equal(signature, rackSignature, "Rack must match across builds and samples");
  const renderer = await page.evaluate(() => {
    const canvas = document.querySelector("#game-viewport canvas");
    const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
    const debug = gl?.getExtension("WEBGL_debug_renderer_info");
    return {
      userAgent: navigator.userAgent, devicePixelRatio,
      canvasPixels: [canvas.width, canvas.height], canvasCssPixels: [canvas.clientWidth, canvas.clientHeight],
      renderer: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : "unavailable",
      vendor: debug ? gl.getParameter(debug.UNMASKED_VENDOR_WEBGL) : "unavailable",
      webglVersion: gl?.getParameter(gl.VERSION),
    };
  });
  await page.locator('[data-action="shoot"]').click();
  await phase(page, "moving");
  return { signature, renderer };
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

async function runOne(build, label, warmup) {
  const context = await browser.newContext(contextOptions);
  const page = await context.newPage();
  captureErrors(page, label);
  try {
    const readyMs = await ready(page, servers[build].url);
    const { signature, renderer } = await startShot(page);
    if (warmup) {
      await page.waitForTimeout(800);
      return { build, label, readyMs, rackSignature: signature, renderer };
    }
    const intervals = await frameIntervals(page);
    assert.ok(intervals.moving.count > 0, "A measured shot must include moving frames");
    return { build, label, readyMs, rackSignature: signature, renderer, intervals };
  } finally { await context.close(); }
}

const pauseBetweenContexts = () => new Promise((resolve) => setTimeout(resolve, 300));
const median = (values) => {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted.length ? sorted[Math.floor(sorted.length / 2)] : null;
};
try {
  servers.baseline = await serveBuild(builds.baseline);
  servers.after = await serveBuild(builds.after);
  browser = await chromium.launch(launchOptions);
  report.environment.browser = browser.version();
  report.environment.serverOrigins = { baseline: servers.baseline.url, after: servers.after.url };
  for (const build of ["baseline", "after"]) {
    report.warmups.push(await runOne(build, `${build}-warmup`, true));
    await pauseBetweenContexts();
  }
  for (let i = 0; i < order.length; i++) {
    const build = order[i];
    report.samples.push(await runOne(build, `${i + 1}-${build}`, false));
    await pauseBetweenContexts();
  }
  const byBuild = (name) => report.samples.filter((sample) => sample.build === name);
  report.summary = Object.fromEntries(["baseline", "after"].map((name) => {
    const samples = byBuild(name);
    return [name, {
      count: samples.length,
      movingP95Ms: samples.map((sample) => sample.intervals.moving.p95Ms),
      medianMovingP95Ms: median(samples.map((sample) => sample.intervals.moving.p95Ms)),
      readyMs: samples.map((sample) => sample.readyMs),
    }];
  }));
  report.comparability = {
    rackSignatures: [...new Set(report.samples.map((sample) => sample.rackSignature))],
    renderers: [...new Set(report.samples.map((sample) => sample.renderer.renderer))],
    canvasPixelSizes: [...new Set(report.samples.map((sample) => sample.renderer.canvasPixels.join("x")))],
    canvasCssSizes: [...new Set(report.samples.map((sample) => sample.renderer.canvasCssPixels.join("x")))],
    note: "Different canvas sizes or renderer strings must be considered when interpreting timing differences.",
  };
  if (report.errors.length) process.exitCode = 1;
} catch (error) {
  report.failure = { message: error.message };
  process.exitCode = 1;
} finally {
  try { await browser?.close(); } catch (error) { report.errors.push({ label: "browser cleanup", message: error.message }); process.exitCode = 1; }
  for (const [name, server] of Object.entries(servers)) {
    try { await server.close(); } catch (error) { report.errors.push({ label: `${name} server cleanup`, message: error.message }); process.exitCode = 1; }
  }
  await fs.writeFile(path.join(outputDir, "results.json"), `${JSON.stringify(report, null, 2)}\n`, { flag: "wx" });
  console.log(JSON.stringify({ outputDir, summary: report.summary, comparability: report.comparability, errors: report.errors, failure: report.failure }, null, 2));
}
