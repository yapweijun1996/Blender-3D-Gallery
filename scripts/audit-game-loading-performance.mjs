import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { chromium } from "playwright";
import { serveBuild } from "./browser-test-utils.mjs";

const [baselineArg, candidateArg, outputArg, mode = "paired", ...extra] =
  process.argv.slice(2);
if (
  !baselineArg ||
  !candidateArg ||
  !outputArg ||
  extra.length ||
  !["paired", "profile"].includes(mode)
) {
  console.error(
    "Usage: node scripts/audit-game-loading-performance.mjs <baseline-dist> <candidate-dist> <new-output-dir> [paired|profile]",
  );
  process.exit(2);
}
const builds = {
  baseline: path.resolve(baselineArg),
  candidate: path.resolve(candidateArg),
};
const out = path.resolve(outputArg);
for (const dir of Object.values(builds)) {
  assert.ok(
    out !== dir && !out.startsWith(`${dir}${path.sep}`),
    "Output must be outside both builds",
  );
  await fs.access(path.join(dir, "index.html"));
}
const buildInfo = {},
  packs = {};
for (const [name, dir] of Object.entries(builds)) {
  const info = await fs.readFile(path.join(dir, "build-info.json"));
  buildInfo[name] = {
    path: dir,
    identity: JSON.parse(info),
    sha256: crypto.createHash("sha256").update(info).digest("hex"),
  };
  const pack = JSON.parse(
    await fs.readFile(path.join(dir, "game-pack.json"), "utf8"),
  );
  assert.equal(pack.files.length, 18);
  packs[name] = Object.fromEntries(
    await Promise.all(
      pack.files.map(async (entry) => {
        const bytes = await fs.readFile(path.join(dir, entry.url));
        const sha256 = crypto.createHash("sha256").update(bytes).digest("hex");
        assert.equal(bytes.length, entry.bytes);
        assert.equal(sha256, entry.sha256);
        return [entry.id, { url: entry.url, bytes: entry.bytes, sha256 }];
      }),
    ),
  );
}
assert.deepEqual(
  Object.fromEntries(
    Object.entries(packs.baseline).map(([id, item]) => [
      id,
      { bytes: item.bytes, sha256: item.sha256 },
    ]),
  ),
  Object.fromEntries(
    Object.entries(packs.candidate).map(([id, item]) => [
      id,
      { bytes: item.bytes, sha256: item.sha256 },
    ]),
  ),
  "The actual 18 GLB assets must be byte-identical across builds",
);
await fs.mkdir(path.dirname(out), { recursive: true });
await fs.mkdir(out);
const order =
  mode === "paired"
    ? Array.from({ length: 10 }, (_, index) =>
        index % 2 ? "candidate" : "baseline",
      )
    : ["baseline", "candidate"];
const report = {
  methodology: {
    mode,
    order,
    execution:
      "One system Chrome process and one loopback server, switched between frozen builds only after each fresh context closes.",
    cold: "Fresh context per sample; service workers blocked; browser cache disabled; CDP emulates 100ms latency, 4Mbps down and 1Mbps up. CPU is not throttled.",
    ready:
      "Wall time from navigation start to the game's ready signal. Each sample verifies 18 Resource Timing entries with nonzero transfer and manifest-matching byte lengths.",
    profile:
      mode === "profile"
        ? "Diagnostic only: instrument the final 18/18 progress update, first following WebGL draw and first requestAnimationFrame observing ready. Do not combine these timings with formal paired samples."
        : "No parse/draw instrumentation during formal samples.",
    bandwidthFloor:
      "3,697,784 GLB bytes at 4,000,000 bit/s require about 7.4 seconds of ideal serial transfer, before protocol and processing overhead.",
    limitations: [
      "Loopback CDP throttling is a controlled simulation, not a physical phone or real network.",
      "Resource Timing byte counts and a ready signal do not prove byte-identical responses; separate passive-stream hash diagnostics cover that claim.",
      "Five samples per side are descriptive, not a statistical guarantee; other host work can affect results.",
      "The frozen baseline precedes the final UX CSS commit; any difference is not automatically attributable only to the loader.",
      "Host CPU counters include the browser and all other processes; they do not isolate unrelated work.",
    ],
  },
  environment: {
    node: process.version,
    platform: process.platform,
    architecture: process.arch,
    osRelease: os.release(),
    cpu: os.cpus()[0]?.model || "unknown",
    launchOptions: {
      channel: "chrome",
      headless: true,
      ignoreDefaultArgs: ["--enable-unsafe-swiftshader"],
    },
    buildInfo,
    measuredAt: new Date().toISOString(),
  },
  packIdentity: packs,
  samples: [],
  errors: [],
};

function profileInit() {
  window.__gameLoadProfile = {
    allParsedMs: null,
    firstCompleteDrawMs: null,
    readyObservedMs: null,
  };
  const descriptor = Object.getOwnPropertyDescriptor(
    Node.prototype,
    "textContent",
  );
  Object.defineProperty(Node.prototype, "textContent", {
    ...descriptor,
    set(value) {
      descriptor.set.call(this, value);
      if (this.id === "game-loading" && /18\/18/.test(String(value)))
        window.__gameLoadProfile.allParsedMs = performance.now();
    },
  });
  for (const name of [
    "drawElements",
    "drawArrays",
    "drawElementsInstanced",
    "drawArraysInstanced",
  ]) {
    const original = WebGL2RenderingContext.prototype[name];
    WebGL2RenderingContext.prototype[name] = function (...args) {
      if (
        window.__gameLoadProfile.allParsedMs !== null &&
        window.__gameLoadProfile.firstCompleteDrawMs === null
      )
        window.__gameLoadProfile.firstCompleteDrawMs = performance.now();
      return original.apply(this, args);
    };
  }
  const check = () => {
    if (
      window.render_game_to_text &&
      JSON.parse(window.render_game_to_text()).ready
    )
      window.__gameLoadProfile.readyObservedMs = performance.now();
    else requestAnimationFrame(check);
  };
  requestAnimationFrame(check);
}

const cpuSnapshot = () =>
  os.cpus().reduce((sum, cpu) => {
    for (const [key, value] of Object.entries(cpu.times))
      sum[key] = (sum[key] || 0) + value;
    return sum;
  }, {});
function hostCpuBusy(before, after) {
  const delta = Object.fromEntries(
    Object.keys(after).map((key) => [key, after[key] - (before[key] || 0)]),
  );
  const total = Object.values(delta).reduce((sum, value) => sum + value, 0);
  return total > 0 ? ((total - delta.idle) / total) * 100 : null;
}

async function sample(browser, server, name, index) {
  server.setRoot(builds[name]);
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
    serviceWorkers: "block",
  });
  if (mode === "profile") await context.addInitScript(profileInit);
  const page = await context.newPage(),
    errors = [];
  let stage = "active";
  page.on("pageerror", (error) =>
    errors.push({ stage, type: "pageerror", message: error.message }),
  );
  page.on("console", (message) => {
    if (message.type() === "error")
      errors.push({ stage, type: "console", message: message.text() });
  });
  page.on("requestfailed", (request) => {
    if (new URL(request.url()).pathname.endsWith(".glb"))
      errors.push({
        stage,
        type: "requestfailed",
        path: new URL(request.url()).pathname,
        message: request.failure()?.errorText,
      });
  });
  try {
    const cdp = await context.newCDPSession(page);
    await cdp.send("Network.enable");
    await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
    await cdp.send("Network.emulateNetworkConditions", {
      offline: false,
      latency: 100,
      downloadThroughput: 500000,
      uploadThroughput: 125000,
      connectionType: "cellular4g",
    });
    const cpuBefore = cpuSnapshot(),
      loadBefore = os.loadavg(),
      started = performance.now();
    await page.goto(`${server.url}?page=game`, {
      waitUntil: "domcontentloaded",
      timeout: 90000,
    });
    const handle = await page.waitForFunction(
      () => {
        if (
          window.render_game_to_text &&
          JSON.parse(window.render_game_to_text()).ready
        )
          return { ready: true };
        const error = document.querySelector("#game-load-error:not([hidden])");
        return error ? { ready: false, message: error.innerText } : null;
      },
      null,
      { timeout: 90000 },
    );
    const outcome = await handle.jsonValue(),
      readyMs = performance.now() - started;
    if (!outcome.ready)
      throw new Error(`Game initialization failed: ${outcome.message}`);
    if (mode === "profile")
      await page.waitForFunction(
        () => window.__gameLoadProfile?.readyObservedMs !== null,
        null,
        { timeout: 5000 },
      );
    const observation = await page.evaluate(() => {
      const canvas = document.querySelector("#game-viewport canvas"),
        gl = canvas.getContext("webgl2");
      const debug = gl?.getExtension("WEBGL_debug_renderer_info");
      return {
        serviceWorkerControlled: !!navigator.serviceWorker?.controller,
        renderer: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : null,
        canvasPixels: [canvas.width, canvas.height],
        canvasCssPixels: [canvas.clientWidth, canvas.clientHeight],
        profile: window.__gameLoadProfile || null,
        resources: performance
          .getEntriesByType("resource")
          .filter((entry) => new URL(entry.name).pathname.endsWith(".glb"))
          .map((entry) => ({
            path: new URL(entry.name).pathname,
            startMs: entry.startTime,
            responseEndMs: entry.responseEnd,
            durationMs: entry.duration,
            transferBytes: entry.transferSize,
            encodedBytes: entry.encodedBodySize,
          })),
        allResources: window.__gameLoadProfile
          ? performance.getEntriesByType("resource").map((entry) => ({
              path: new URL(entry.name).pathname,
              initiatorType: entry.initiatorType,
              startMs: entry.startTime,
              responseEndMs: entry.responseEnd,
              transferBytes: entry.transferSize,
              encodedBytes: entry.encodedBodySize,
            }))
          : null,
      };
    });
    const cpuAfter = cpuSnapshot(),
      loadAfter = os.loadavg();
    const expected = new Map(
      Object.values(packs[name]).map((entry) => [
        path.basename(entry.url),
        entry.bytes,
      ]),
    );
    const observed = observation.resources.map((entry) => ({
      ...entry,
      file: path.basename(entry.path),
    }));
    const complete =
      !observation.serviceWorkerControlled &&
      observed.length === 18 &&
      new Set(observed.map((entry) => entry.file)).size === 18 &&
      observed.every(
        (entry) =>
          entry.transferBytes > 0 &&
          expected.get(entry.file) === entry.encodedBytes,
      );
    return {
      name,
      index,
      readyMs,
      complete,
      browser: browser.version(),
      renderer: observation.renderer,
      canvasPixels: observation.canvasPixels,
      canvasCssPixels: observation.canvasCssPixels,
      serviceWorkerControlled: observation.serviceWorkerControlled,
      firstGlbStartMs: Math.min(...observed.map((entry) => entry.startMs)),
      lastGlbResponseEndMs: Math.max(
        ...observed.map((entry) => entry.responseEndMs),
      ),
      profile: observation.profile,
      resources: observed,
      allResources: observation.allResources,
      errors,
      hostLoadBefore: loadBefore,
      hostLoadAfter: loadAfter,
      hostCpuBusyPercent: hostCpuBusy(cpuBefore, cpuAfter),
    };
  } finally {
    stage = "teardown";
    await context.close();
  }
}

const median = (values) => {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)];
};
let browser, server;
try {
  server = await serveBuild(builds.baseline);
  browser = await chromium.launch(report.environment.launchOptions);
  report.environment.browser = browser.version();
  report.environment.serverOrigin = server.url;
  for (let i = 0; i < order.length; i++) {
    const result = await sample(browser, server, order[i], i + 1);
    report.samples.push(result);
    console.log(
      `${i + 1}/${order.length} ${result.name} ready=${result.readyMs.toFixed(1)}ms complete=${result.complete}`,
    );
    if (!result.complete)
      throw new Error(`Incomplete cold-load evidence in sample ${i + 1}`);
    if (
      result.name === "candidate" &&
      result.errors.some((error) => error.stage === "active")
    )
      throw new Error(
        `Candidate reported an active loading error in sample ${i + 1}`,
      );
  }
  const renderers = [...new Set(report.samples.map((item) => item.renderer))];
  report.summary = {
    renderers,
    canvasPixels: [
      ...new Set(report.samples.map((item) => item.canvasPixels.join("x"))),
    ],
    byBuild: Object.fromEntries(
      ["baseline", "candidate"].map((name) => {
        const values = report.samples
          .filter((item) => item.name === name)
          .map((item) => item.readyMs);
        return [
          name,
          {
            count: values.length,
            medianMs: median(values),
            minMs: Math.min(...values),
            maxMs: Math.max(...values),
            valuesMs: values,
          },
        ];
      }),
    ),
  };
  if (renderers.length !== 1 || !renderers[0])
    throw new Error("Renderer differed or could not be identified");
} catch (error) {
  report.errors.push(error.message);
  process.exitCode = 1;
} finally {
  await browser?.close().catch(() => {});
  await server?.close().catch(() => {});
  await fs.writeFile(
    path.join(out, "results.json"),
    `${JSON.stringify(report, null, 2)}\n`,
    { flag: "wx" },
  );
  console.log(
    JSON.stringify(
      { output: out, summary: report.summary, errors: report.errors },
      null,
      2,
    ),
  );
}
