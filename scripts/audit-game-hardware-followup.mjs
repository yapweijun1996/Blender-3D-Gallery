import { pullShot, chargePull, releasePull, setPullRatio } from "./browser-test-utils.mjs";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { chromium } from "playwright";
import { launchOptions as softwareLaunchOptions, serveBuild } from "./browser-test-utils.mjs";

const [buildArgument, outputArgument, ...extra] = process.argv.slice(2);
if (!buildArgument || !outputArgument || extra.length) {
  console.error("Usage: node scripts/audit-game-hardware-followup.mjs <build-dir> <new-output-dir>");
  process.exit(2);
}
const buildDir = path.resolve(buildArgument), outputDir = path.resolve(outputArgument);
assert.ok(outputDir !== buildDir && !outputDir.startsWith(`${buildDir}${path.sep}`), "Output must be outside the build");
await fs.access(path.join(buildDir, "index.html"));
const buildBytes = await fs.readFile(path.join(buildDir, "build-info.json"));
await fs.mkdir(path.dirname(outputDir), { recursive: true });
try { await fs.mkdir(outputDir); }
catch (error) {
  if (error.code === "EEXIST") console.error(`Output already exists: ${outputDir}. Choose a new directory.`);
  else console.error(`Cannot create output directory: ${error.message}`);
  process.exit(1);
}

const report = {
  methodology: {
    gpuProbe: "Unforced Chromium profiles remove Playwright's default --enable-unsafe-swiftshader and pass no GPU-forcing flags. WebGL2 renderer strings, failIfMajorPerformanceCaveat and browser GPU metadata are recorded; browser-reported hardware is not a direct GPU timing measurement.",
    sampling: "At most three fresh-context samples each at 1440x900 DPR1 and touch-emulated 390x844 DPR1, only when unforced WebGL reports a hardware renderer. Rack seed 42, cue at default placement, aim 0 and a real 75% shot. Six seconds of requestAnimationFrame intervals are classified by game phase.",
    network: "Three fresh contexts with service workers blocked and browser cache disabled; Chrome DevTools Protocol network emulation applies 100ms latency, 4,000,000 bit/s down and 1,000,000 bit/s up. CPU is not throttled. Ready is measured from navigation start until the game's ready signal.",
    fallback: "If unforced browsers cannot render the game, the existing explicit SwiftShader configuration is used only for the new network-throttled loading test, not to claim hardware gameplay performance.",
    limitations: [
      "Mobile is a viewport/touch emulation on the host, not a physical Android/iOS device.",
      "Loopback CDP network throttling is a controlled simulation, not field latency or a mobile-network measurement.",
      "Frame intervals measure browser pacing, not GPU frame time, total GPU memory, battery use or sustained thermal behavior.",
      "Three samples are descriptive and cannot establish statistically reliable distributions or sustained leak freedom.",
    ],
  },
  environment: {
    node: process.version, platform: process.platform, architecture: process.arch,
    osRelease: os.release(), cpu: os.cpus()[0]?.model || "unknown", logicalCpuCount: os.cpus().length,
    buildDir, buildInfo: JSON.parse(buildBytes), buildInfoSha256: crypto.createHash("sha256").update(buildBytes).digest("hex"),
    measuredAt: new Date().toISOString(),
  },
  probes: [], hardwareSamples: [], networkSamples: [], errors: [],
};

// Playwright 1.64 adds --enable-unsafe-swiftshader by default. Remove it for
// every hardware probe so a reported hardware renderer is not forced software.
const unforced = { headless: true, ignoreDefaultArgs: ["--enable-unsafe-swiftshader"] };
const profiles = [
  { name: "playwright-chromium-headless", options: unforced },
  { name: "system-chrome-headless", options: { ...unforced, channel: "chrome" } },
];
const headedProfile = { name: "system-chrome-headed", options: { ...unforced, channel: "chrome", headless: false } };
const sizes = [
  { label: "desktop", width: 1440, height: 900, deviceScaleFactor: 1, isMobile: false, hasTouch: false },
  { label: "mobile-emulated", width: 390, height: 844, deviceScaleFactor: 1, isMobile: true, hasTouch: true },
];
const contextOptions = ({ width, height, deviceScaleFactor, isMobile, hasTouch }) => ({
  viewport: { width, height }, deviceScaleFactor, isMobile, hasTouch,
});
const softwarePattern = /swiftshader|llvmpipe|softpipe|lavapipe|software rasterizer|microsoft basic render|warp/i;
const hardwareVendorPattern = /apple|nvidia|amd|radeon|intel/i;

function classify(probe) {
  if (!probe.webgl2?.available) return "unavailable";
  const name = `${probe.webgl2.unmaskedVendor || ""} ${probe.webgl2.unmaskedRenderer || ""}`;
  if (softwarePattern.test(name)) return "software";
  if (!probe.webgl2.unmaskedRenderer || !probe.strictWebgl2?.available) return "unknown";
  if (probe.gpuFlags?.some((flag) => /--use-(angle|gl)=.*swiftshader/i.test(flag))) return "forced-software";
  return hardwareVendorPattern.test(name) ? "reported-hardware" : "unknown";
}

async function browserGpuInfo(browser) {
  const result = { gpuFlags: [], commandLineAvailable: false };
  let session;
  try {
    session = await browser.newBrowserCDPSession();
    try {
      const commandLine = await session.send("Browser.getBrowserCommandLine");
      result.commandLineAvailable = true;
      result.gpuFlags = commandLine.arguments.filter((arg) => /^--(?:use-angle|use-gl|disable-gpu|enable-gpu|enable-unsafe-swiftshader|headless)(?:=|$|-)/.test(arg));
    } catch (error) { result.commandLineError = error.message; }
    try {
      const info = await session.send("SystemInfo.getInfo");
      result.featureStatus = info.gpu?.featureStatus;
      result.devices = info.gpu?.devices?.map(({ vendorString, deviceString, driverVendor, driverVersion, active }) => ({ vendorString, deviceString, driverVendor, driverVersion, active }));
      result.auxAttributes = Object.fromEntries(Object.entries(info.gpu?.auxAttributes || {}).filter(([key]) => /glvendor|glrenderer|glversion|software|gpu/i.test(key)));
    } catch (error) { result.systemInfoError = error.message; }
  } finally { await session?.detach().catch(() => {}); }
  return result;
}

async function probeProfile(profile) {
  let browser;
  try {
    browser = await chromium.launch(profile.options);
    const context = await browser.newContext(contextOptions(sizes[0]));
    const page = await context.newPage();
    const gpu = await browserGpuInfo(browser);
    const webgl = await page.evaluate(() => {
      const inspect = (options) => {
        const canvas = document.createElement("canvas");
        const gl = canvas.getContext("webgl2", options);
        if (!gl) return { available: false };
        const debug = gl.getExtension("WEBGL_debug_renderer_info");
        const data = {
          available: true,
          vendor: gl.getParameter(gl.VENDOR), renderer: gl.getParameter(gl.RENDERER),
          unmaskedVendor: debug ? gl.getParameter(debug.UNMASKED_VENDOR_WEBGL) : null,
          unmaskedRenderer: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : null,
          webglVersion: gl.getParameter(gl.VERSION), maxTextureSize: gl.getParameter(gl.MAX_TEXTURE_SIZE),
        };
        gl.getExtension("WEBGL_lose_context")?.loseContext();
        return data;
      };
      return { webgl2: inspect({ antialias: true }), strictWebgl2: inspect({ antialias: true, failIfMajorPerformanceCaveat: true }) };
    });
    await context.close();
    const probe = { name: profile.name, launchOptions: profile.options, browser: browser.version(), ...gpu, ...webgl };
    probe.classification = classify(probe);
    return probe;
  } catch (error) {
    return { name: profile.name, launchOptions: profile.options, classification: "unavailable", error: error.message };
  } finally { await browser?.close().catch(() => {}); }
}

function captureErrors(page, label) {
  const errors = [];
  let stage = "active";
  page.on("pageerror", (error) => errors.push({ stage, type: "pageerror", message: error.message }));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push({ stage, type: "console", message: message.text() });
  });
  page.on("requestfailed", (request) => errors.push({ stage, type: "requestfailed", url: request.url(), message: request.failure()?.errorText }));
  return { label, errors, markTeardown: () => { stage = "teardown"; } };
}

async function gameReady(page, url) {
  const start = performance.now();
  await page.goto(`${url}?page=game`, { waitUntil: "domcontentloaded", timeout: 90000 });
  const handle = await page.waitForFunction(() => {
    if (window.render_game_to_text && JSON.parse(window.render_game_to_text()).ready) return { ready: true };
    const error = document.querySelector("#game-load-error:not([hidden])");
    return error ? { ready: false, message: error.innerText } : null;
  }, null, { timeout: 90000 });
  const outcome = await handle.jsonValue();
  if (!outcome.ready) throw new Error(`Game initialization failed: ${outcome.message}`);
  return performance.now() - start;
}

async function phase(page, expected) {
  await page.waitForFunction((value) => JSON.parse(window.render_game_to_text()).phase === value, expected, { timeout: 30000 });
}

async function gameRenderer(page) {
  return page.evaluate(() => {
    const canvas = document.querySelector("#game-viewport canvas");
    const gl = canvas?.getContext("webgl2");
    const debug = gl?.getExtension("WEBGL_debug_renderer_info");
    return {
      available: !!gl, userAgent: navigator.userAgent, devicePixelRatio,
      canvasPixels: canvas ? [canvas.width, canvas.height] : null,
      canvasCssPixels: canvas ? [canvas.clientWidth, canvas.clientHeight] : null,
      unmaskedVendor: debug ? gl.getParameter(debug.UNMASKED_VENDOR_WEBGL) : null,
      unmaskedRenderer: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : null,
      visibility: document.visibilityState,
    };
  });
}

async function startFixedShot(page) {
  // The seed override exists only in the disposable context during rack creation.
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
  setPullRatio(page, Math.pow(0.75, 2 / 3));
  const state = await page.evaluate(() => JSON.parse(window.render_game_to_text()));
  assert.equal(state.aim, 0);
  assert.equal(state.pullRatio, 0);
  assert.equal(state.balls[0].x, -0.7);
  assert.equal(state.balls[0].z, 0);
  const balls = state.balls.map(({ id, x, z, pocketed }) => ({ id, x, z, pocketed }));
  const rackSignature = crypto.createHash("sha256").update(JSON.stringify(balls)).digest("hex");
  const renderer = await gameRenderer(page);
  await pullShot(page);
  await phase(page, "moving");
  assert.ok(Math.abs(await page.evaluate(() => JSON.parse(window.render_game_to_text()).power) - .75) < 1e-5, "benchmark preserves75% physical strength");
  return { rackSignature, renderer };
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

async function measureHardware(browser, profile, probe, size, sample, url) {
  const context = await browser.newContext(contextOptions(size));
  const page = await context.newPage();
  const errorCapture = captureErrors(page, `${profile.name} ${size.label} sample ${sample}`);
  try {
    const readyMs = await gameReady(page, url);
    const { rackSignature, renderer } = await startFixedShot(page);
    if (!renderer.unmaskedRenderer || softwarePattern.test(renderer.unmaskedRenderer) || renderer.unmaskedRenderer !== probe.webgl2.unmaskedRenderer) {
      throw new Error("The actual game canvas did not retain the probed hardware renderer");
    }
    const intervals = await frameIntervals(page);
    assert.ok(intervals.moving.count > 0, "The sample must contain moving frames");
    if (sample === 1) {
      const screenshot = await page.screenshot({ type: "png", fullPage: true });
      await fs.writeFile(path.join(outputDir, `hardware-${size.label}.png`), screenshot, { flag: "wx" });
    }
    return { profile: profile.name, size, sample, readyMs, rackSignature, renderer, intervals, errors: errorCapture.errors };
  } finally { errorCapture.markTeardown(); await context.close(); }
}

async function measureNetwork(browser, profile, sample, url) {
  const context = await browser.newContext({ ...contextOptions(sizes[0]), serviceWorkers: "block" });
  const page = await context.newPage();
  const errorCapture = captureErrors(page, `${profile.name} throttled sample ${sample}`);
  try {
    const cdp = await context.newCDPSession(page);
    await cdp.send("Network.enable");
    await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
    await cdp.send("Network.emulateNetworkConditions", {
      offline: false, latency: 100, downloadThroughput: 500000,
      uploadThroughput: 125000, connectionType: "cellular4g",
    });
    const readyMs = await gameReady(page, url);
    const renderer = await gameRenderer(page);
    const resources = await page.evaluate(() => ({
      serviceWorkerControlled: !!navigator.serviceWorker?.controller,
      glbs: performance.getEntriesByType("resource")
        .filter((entry) => new URL(entry.name).pathname.endsWith(".glb"))
        .map((entry) => ({
          path: new URL(entry.name).pathname, durationMs: entry.duration,
          transferBytes: entry.transferSize, encodedBytes: entry.encodedBodySize,
        })),
      navigation: performance.getEntriesByType("navigation").map((entry) => ({
        responseStartMs: entry.responseStart, domContentLoadedMs: entry.domContentLoadedEventEnd,
        loadEventEndMs: entry.loadEventEnd,
      })),
    }));
    const coldEvidence = {
      serviceWorkersBlocked: true, browserCacheDisabled: true,
      serviceWorkerControlled: resources.serviceWorkerControlled,
      glbRequests: resources.glbs.length,
      glbsWithNonzeroTransfer: resources.glbs.filter((entry) => entry.transferBytes > 0).length,
      encodedGlbBytes: resources.glbs.reduce((sum, entry) => sum + entry.encodedBytes, 0),
    };
    const validColdObservation = !coldEvidence.serviceWorkerControlled &&
      coldEvidence.glbRequests === 18 && coldEvidence.glbsWithNonzeroTransfer === 18;
    return { profile: profile.name, sample, readyMs, renderer, validColdObservation, coldEvidence, resources, errors: errorCapture.errors };
  } finally { errorCapture.markTeardown(); await context.close(); }
}

let server;
let browser;
try {
  for (const profile of profiles) report.probes.push(await probeProfile(profile));
  let hardwareProfile = profiles.find((profile) => report.probes.find((probe) => probe.name === profile.name)?.classification === "reported-hardware");
  if (!hardwareProfile) {
    // A temporary headed Chrome window is tried only if headless probes did not
    // report hardware; it uses a fresh Playwright profile and closes again.
    report.probes.push(await probeProfile(headedProfile));
    if (report.probes.at(-1).classification === "reported-hardware") hardwareProfile = headedProfile;
  }
  report.hardwareStatus = hardwareProfile ? "hardware-reported" : "not-established";
  report.environment.hardwareProfile = hardwareProfile?.name || null;
  server = await serveBuild(buildDir);
  if (hardwareProfile) {
    const probe = report.probes.find((entry) => entry.name === hardwareProfile.name);
    browser = await chromium.launch(hardwareProfile.options);
    for (const size of sizes) {
      for (let sample = 1; sample <= 3; sample++) {
        try {
          report.hardwareSamples.push(await measureHardware(browser, hardwareProfile, probe, size, sample, server.url));
        } catch (error) {
          report.errors.push({ scenario: `hardware-${size.label}-${sample}`, message: error.message });
          break;
        }
      }
    }
    await browser.close();
    browser = undefined;
  }
  const availableUnforced = [...profiles, headedProfile].find((profile) =>
    report.probes.find((probe) => probe.name === profile.name)?.webgl2?.available,
  );
  const fallback = { name: "explicit-swiftshader-network-only", options: softwareLaunchOptions };
  const networkProfiles = hardwareProfile ? [hardwareProfile] : availableUnforced ? [availableUnforced, fallback] : [fallback];
  for (const networkProfile of networkProfiles) {
    report.environment.networkProfile = networkProfile.name;
    try {
      browser = await chromium.launch(networkProfile.options);
      for (let sample = 1; sample <= 3; sample++) {
        const observation = await measureNetwork(browser, networkProfile, sample, server.url);
        report.networkSamples.push(observation);
        if (!observation.validColdObservation) {
          report.errors.push({ scenario: `network-${sample}`, message: "Cold network evidence was incomplete; see coldEvidence." });
          break;
        }
      }
      await browser.close();
      browser = undefined;
      break;
    } catch (error) {
      report.errors.push({ scenario: `network-${networkProfile.name}`, message: error.message });
      await browser?.close().catch(() => {});
      browser = undefined;
      if (report.networkSamples.length) break;
    }
  }
  const signatures = [...new Set(report.hardwareSamples.map((sample) => sample.rackSignature))];
  report.summary = {
    hardwareProfile: report.environment.hardwareProfile,
    hardwareSampleCounts: Object.fromEntries(sizes.map((size) => [size.label, report.hardwareSamples.filter((sample) => sample.size.label === size.label).length])),
    rackSignatures: signatures,
    networkProfile: report.environment.networkProfile,
    validColdSamples: report.networkSamples.filter((sample) => sample.validColdObservation).length,
    hardwareErrorsDuringActive: report.hardwareSamples.flatMap((sample) => sample.errors).filter((error) => error.stage === "active").length,
    networkErrorsDuringActive: report.networkSamples.flatMap((sample) => sample.errors).filter((error) => error.stage === "active").length,
  };
  if (signatures.length > 1 || report.summary.validColdSamples !== 3 ||
      report.summary.hardwareErrorsDuringActive || report.summary.networkErrorsDuringActive ||
      (hardwareProfile && Object.values(report.summary.hardwareSampleCounts).some((count) => count !== 3))) process.exitCode = 1;
} catch (error) {
  report.failure = { message: error.message };
  process.exitCode = 1;
} finally {
  await browser?.close().catch(() => {});
  await server?.close().catch(() => {});
  await fs.writeFile(path.join(outputDir, "results.json"), `${JSON.stringify(report, null, 2)}\n`, { flag: "wx" });
  console.log(JSON.stringify({ outputDir, summary: report.summary, probes: report.probes, errors: report.errors, failure: report.failure }, null, 2));
}
