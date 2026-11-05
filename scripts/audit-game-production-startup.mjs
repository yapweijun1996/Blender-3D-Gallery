import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { promisify } from "node:util";
import { chromium } from "playwright";

const [outputArg, ...extra] = process.argv.slice(2);
if (!outputArg || extra.length) {
  console.error(
    "Usage: node scripts/audit-game-production-startup.mjs <new-output-directory>",
  );
  process.exit(2);
}
const out = path.resolve(outputArg);
await fs.mkdir(path.dirname(out), { recursive: true });
await fs.mkdir(out);
const base = "https://yapweijun1996.github.io/Blender-3D-Gallery/";
const execFileAsync = promisify(execFile);
async function freshJson(name) {
  const url = new URL(name, base);
  url.searchParams.set("audit", `${Date.now()}-${crypto.randomUUID()}`);
  const { stdout } = await execFileAsync(
    "curl",
    [
      "-fsS",
      "--compressed",
      "--max-time",
      "25",
      "-H",
      "Cache-Control: no-cache",
      url.href,
    ],
    { maxBuffer: 1024 * 1024 },
  );
  return JSON.parse(stdout);
}
const report = {
  methodology: {
    production: base,
    order:
      "Five unthrottled and five page-CDP-throttled, service-worker-blocked fresh contexts, alternating sequentially; then an independently instrumented diagnostic, one normal worker-enabled cold visit and a warm new-page revisit in the same context.",
    pageThrottle:
      "Only service-worker-blocked profile: CDP 100 ms latency, 500000 bytes/s down, 125000 bytes/s up, no CPU throttle. The worker-enabled visit has no emulation because page CDP does not globally throttle worker requests.",
    cache:
      "Fresh browser context and CDP browser cache disabled for cold samples; service worker blocked. CDN edge cache, DNS, connection and network conditions may vary. SW-enabled cold starts with fresh context; warm replay reuses it.",
    ready:
      "Wall time from page.goto to the observed Game ready flag. Diagnostic-only progress/draw hooks and response-byte capture are excluded from these formal timings.",
    provenance:
      "Before and after each visit, a separate curl process reads cache-busted build-info.json. The Game's requested GLB paths and decoded lengths are checked against the pinned production game-pack manifest; the separate diagnostic also hashes actual consumed bytes.",
    limitations: [
      "Browser emulation and a headless desktop are not a physical mobile device.",
      "Only the worker-enabled real-network journey can observe worker requests; page-target CDP throttling is not a global worker network throttle.",
      "CDN edge caching, real network and external host workloads are not controlled.",
      "Service-worker warm replay here does not prepare the optional offline Game pack.",
      "Diagnostic hooks record the first draw call after final model progress, not GPU completion.",
      "Host CPU/load measurement includes the post-ready capture period and, for worker-cold, the wait for installation.",
    ],
  },
  environment: {
    node: process.version,
    platform: process.platform,
    arch: process.arch,
    osRelease: os.release(),
    cpu: os.cpus()[0]?.model,
    startedAt: new Date().toISOString(),
    chrome: {
      channel: "chrome",
      headless: true,
      ignoreDefaultArgs: ["--enable-unsafe-swiftshader"],
    },
  },
  onlinePack: null,
  localPackComparison: null,
  samples: [],
  errors: [],
};
const write = async () =>
  fs.writeFile(
    path.join(out, "results.json"),
    `${JSON.stringify(report, null, 2)}\n`,
  );
const cpuSnapshot = () =>
  os.cpus().reduce((sum, cpu) => {
    for (const [k, v] of Object.entries(cpu.times)) sum[k] = (sum[k] || 0) + v;
    return sum;
  }, {});
function cpuBusy(a, b) {
  const delta = Object.fromEntries(
    Object.keys(b).map((k) => [k, b[k] - (a[k] || 0)]),
  );
  const total = Object.values(delta).reduce((s, x) => s + x, 0);
  return total ? ((total - delta.idle) * 100) / total : null;
}
function diagnosticHooks() {
  window.__audit = {
    allParsed: null,
    firstDraw: null,
    ready: null,
    responses: {},
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
        window.__audit.allParsed = performance.now();
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
        window.__audit.allParsed !== null &&
        window.__audit.firstDraw === null
      )
        window.__audit.firstDraw = performance.now();
      return original.apply(this, args);
    };
  }
  const originalFetch = window.fetch.bind(window),
    originalArrayBuffer = Response.prototype.arrayBuffer,
    responsePaths = new WeakMap();
  window.fetch = async function (...args) {
    const response = await originalFetch(...args);
    const url = new URL(response.url);
    if (url.pathname.endsWith(".glb"))
      responsePaths.set(response, url.pathname);
    return response;
  };
  Response.prototype.arrayBuffer = function (...args) {
    const responsePath = responsePaths.get(this),
      result = originalArrayBuffer.apply(this, args);
    return responsePath
      ? result.then((buffer) => {
          window.__audit.responses[responsePath] = buffer.slice(0);
          return buffer;
        })
      : result;
  };
  const check = () => {
    if (
      window.render_game_to_text &&
      JSON.parse(window.render_game_to_text()).ready
    )
      window.__audit.ready = performance.now();
    else requestAnimationFrame(check);
  };
  requestAnimationFrame(check);
}
const selectedHeaders = (headers = {}) =>
  Object.fromEntries(
    Object.entries(headers).filter(([key]) =>
      [
        "content-encoding",
        "content-length",
        "content-type",
        "vary",
        "cache-control",
        "age",
        "etag",
        "last-modified",
      ].includes(key.toLowerCase()),
    ),
  );
function cdpRecorder(cdp) {
  const requests = new Map();
  let firstTimestamp = null;
  const entry = (id) => {
    if (!requests.has(id)) requests.set(id, { requestId: id });
    return requests.get(id);
  };
  cdp.on("Network.requestWillBeSent", (e) => {
    firstTimestamp ??= e.timestamp;
    Object.assign(entry(e.requestId), {
      url: e.request.url,
      method: e.request.method,
      type: e.type,
      initiator: e.initiator,
      requestTimeMs: (e.timestamp - firstTimestamp) * 1000,
    });
  });
  cdp.on("Network.responseReceived", (e) =>
    Object.assign(entry(e.requestId), {
      status: e.response.status,
      protocol: e.response.protocol,
      responseHeaders: selectedHeaders(e.response.headers),
      responseTimeMs: (e.timestamp - firstTimestamp) * 1000,
      timing: e.response.timing,
      fromDiskCache: e.response.fromDiskCache,
      fromServiceWorker: e.response.fromServiceWorker,
    }),
  );
  cdp.on("Network.responseReceivedExtraInfo", (e) =>
    Object.assign(entry(e.requestId), {
      extraStatus: e.statusCode,
      wireHeaders: selectedHeaders(e.headers),
    }),
  );
  cdp.on("Network.loadingFinished", (e) =>
    Object.assign(entry(e.requestId), {
      finishedTimeMs: (e.timestamp - firstTimestamp) * 1000,
      encodedDataLength: e.encodedDataLength,
    }),
  );
  cdp.on("Network.loadingFailed", (e) =>
    Object.assign(entry(e.requestId), {
      failedTimeMs: (e.timestamp - firstTimestamp) * 1000,
      failure: e.errorText,
      canceled: e.canceled,
    }),
  );
  cdp.on("Network.dataReceived", (e) => {
    const item = entry(e.requestId);
    item.cdpDecodedDataLength = (item.cdpDecodedDataLength || 0) + e.dataLength;
  });
  return requests;
}
function captureContextRequests(context) {
  const requests = [];
  context.on("request", (request) => {
    const worker =
      typeof request.serviceWorker === "function"
        ? request.serviceWorker()
        : null;
    requests.push({
      request,
      url: request.url(),
      method: request.method(),
      resourceType: request.resourceType(),
      serviceWorkerUrl: worker?.url() || null,
      observedAt: performance.now(),
    });
  });
  return async () =>
    Promise.all(
      requests.map(async ({ request, ...item }) => {
        const response = await request.response().catch(() => null);
        return {
          ...item,
          status: response?.status() || null,
          headers: response
            ? selectedHeaders(await response.allHeaders().catch(() => ({})))
            : {},
          fromServiceWorker: response?.fromServiceWorker() || false,
          failure: request.failure()?.errorText || null,
          sizes: await request.sizes().catch(() => null),
        };
      }),
    );
}
async function visit(browser, manifest, profile, existingContext) {
  const workerAllowed = profile === "worker-cold" || profile === "worker-warm";
  const diagnostic = profile === "diagnostic";
  const ownContext = !existingContext;
  const context =
    existingContext ||
    (await browser.newContext({
      viewport: { width: 1440, height: 900 },
      deviceScaleFactor: 1,
      serviceWorkers: workerAllowed ? "allow" : "block",
    }));
  if (diagnostic) await context.addInitScript(diagnosticHooks);
  const finishRequests = captureContextRequests(context),
    page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) =>
    errors.push({ type: "pageerror", message: e.message }),
  );
  page.on("console", (m) => {
    if (m.type() === "error")
      errors.push({ type: "console", message: m.text() });
  });
  page.on("requestfailed", (r) =>
    errors.push({
      type: "requestfailed",
      url: r.url(),
      message: r.failure()?.errorText,
    }),
  );
  const cdp = await context.newCDPSession(page);
  await cdp.send("Network.enable");
  if (!workerAllowed)
    await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
  if (profile === "throttled")
    await cdp.send("Network.emulateNetworkConditions", {
      offline: false,
      latency: 100,
      downloadThroughput: 500000,
      uploadThroughput: 125000,
      connectionType: "cellular4g",
    });
  const records = cdpRecorder(cdp);
  const startCpu = cpuSnapshot(),
    startLoad = os.loadavg(),
    begin = performance.now();
  try {
    const response = await page.goto(`${base}?page=game`, {
      waitUntil: "domcontentloaded",
      timeout: 90000,
    });
    assert.equal(response.status(), 200, "Game document must be HTTP 200");
    await page.waitForFunction(
      () =>
        window.render_game_to_text &&
        JSON.parse(window.render_game_to_text()).ready,
      null,
      { timeout: 90000 },
    );
    const readyMs = performance.now() - begin;
    if (diagnostic)
      await page.waitForFunction(() => window.__audit.ready !== null, null, {
        timeout: 10000,
      });
    if (profile === "worker-cold")
      await page.evaluate(() =>
        Promise.race([
          navigator.serviceWorker.ready.then(() => true),
          new Promise((_, reject) =>
            setTimeout(
              () => reject(new Error("Service worker installation timed out")),
              90000,
            ),
          ),
        ]),
      );
    const observation = await page.evaluate(async () => {
      const canvas = document.querySelector("#game-viewport canvas"),
        gl = canvas?.getContext("webgl2"),
        debug = gl?.getExtension("WEBGL_debug_renderer_info");
      const resources = performance
        .getEntriesByType("resource")
        .map((e) => ({
          url: e.name,
          initiatorType: e.initiatorType,
          startMs: e.startTime,
          responseEndMs: e.responseEnd,
          durationMs: e.duration,
          transferBytes: e.transferSize,
          encodedBytes: e.encodedBodySize,
          decodedBytes: e.decodedBodySize,
          protocol: e.nextHopProtocol,
        }));
      let diagnostic = null;
      if (window.__audit) {
        const hashes = Object.fromEntries(
          await Promise.all(
            Object.entries(window.__audit.responses).map(
              async ([url, data]) => [
                url,
                {
                  bytes: data.byteLength,
                  sha256: [
                    ...new Uint8Array(
                      await crypto.subtle.digest("SHA-256", data),
                    ),
                  ]
                    .map((b) => b.toString(16).padStart(2, "0"))
                    .join(""),
                },
              ],
            ),
          ),
        );
        diagnostic = {
          allParsed: window.__audit.allParsed,
          firstDraw: window.__audit.firstDraw,
          ready: window.__audit.ready,
          hashes,
        };
      }
      return {
        renderer: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : null,
        canvas: [canvas?.width, canvas?.height],
        entryScript:
          document.querySelector('script[type="module"][src]')?.src || null,
        controller: !!navigator.serviceWorker?.controller,
        resources,
        diagnostic,
      };
    });
    const glbs = observation.resources.filter((e) =>
      new URL(e.url).pathname.endsWith(".glb"),
    );
    const expected = new Map(
      manifest.files.map((e) => [new URL(e.url, base).pathname, e]),
    );
    const allExpected =
      glbs.length === 18 &&
      new Set(glbs.map((e) => new URL(e.url).pathname)).size === 18 &&
      glbs.every(
        (e) =>
          expected.has(new URL(e.url).pathname) &&
          expected.get(new URL(e.url).pathname).bytes === e.decodedBytes &&
          (workerAllowed || e.transferBytes > 0),
      );
    if (diagnostic)
      assert.ok(
        manifest.files.every((e) => {
          const actual =
            observation.diagnostic.hashes[new URL(e.url, base).pathname];
          return actual?.bytes === e.bytes && actual?.sha256 === e.sha256;
        }),
        "Consumed GLB hashes must match online pack",
      );
    assert.ok(allExpected, `Expected all 18 original GLBs in ${profile}`);
    await page.waitForTimeout(250);
    if (diagnostic)
      await page.screenshot({ path: path.join(out, "production-desktop.png") });
    const output = {
      profile,
      readyMs,
      renderer: observation.renderer,
      canvas: observation.canvas,
      entryScript: observation.entryScript,
      controller: observation.controller,
      allExpected,
      resources: observation.resources,
      diagnostic: observation.diagnostic,
      cdp: [...records.values()],
      errors,
      contextRequests: await finishRequests(),
      hostCpuBusyPercent: cpuBusy(startCpu, cpuSnapshot()),
      hostLoadBefore: startLoad,
      hostLoadAfter: os.loadavg(),
    };
    assert.ok(
      !errors.some(
        (e) =>
          e.type === "pageerror" ||
          (e.type === "requestfailed" &&
            new URL(e.url).pathname.endsWith(".glb")),
      ),
      `${profile} has a page or GLB request failure`,
    );
    return { output, context };
  } finally {
    await page.close();
    if (ownContext && profile !== "worker-cold") await context.close();
  }
}
let browser, workerContext;
try {
  const first = await freshJson("build-info.json"),
    pack = await freshJson("game-pack.json");
  assert.equal(pack.build, first.build);
  assert.equal(pack.files.length, 18);
  const local = JSON.parse(await fs.readFile("dist/game-pack.json", "utf8"));
  const localHtml = await fs.readFile("dist/index.html", "utf8");
  const localEntry = localHtml.match(
    /<script[^>]*type="module"[^>]*src="([^"]+)/,
  )?.[1];
  assert.ok(localEntry, "Local build must expose its module entry");
  report.onlinePack = pack;
  report.localPackComparison = {
    localBuild: local.build,
    localEntry: new URL(localEntry, base).href,
    sameAssets:
      local.files.length === pack.files.length &&
      local.files.every((e) =>
        pack.files.some(
          (p) =>
            p.id === e.id &&
            p.bytes === e.bytes &&
            p.sha256 === e.sha256 &&
            p.url === e.url,
        ),
      ),
  };
  report.onlineBuild = first.build;
  browser = await chromium.launch(report.environment.chrome);
  report.environment.browser = browser.version();
  async function run(profile, context) {
    const before = await freshJson("build-info.json");
    assert.equal(
      before.build,
      first.build,
      "Live build changed before sample; stop rather than mix versions",
    );
    const result = await visit(browser, pack, profile, context);
    const after = await freshJson("build-info.json");
    result.output.identityBefore = before;
    result.output.identityAfter = after;
    report.samples.push(result.output);
    await write();
    assert.equal(
      after.build,
      first.build,
      "Live build changed after sample; stop rather than mix versions",
    );
    if (first.build === local.build)
      assert.equal(
        result.output.entryScript,
        report.localPackComparison.localEntry,
        "Browser received a stale HTML entry for the observed build",
      );
    assert.equal(
      result.output.entryScript,
      report.samples[0].entryScript,
      "HTML entry changed during audit",
    );
    console.log(
      `${report.samples.length} ${profile} ready=${result.output.readyMs.toFixed(1)}ms renderer=${result.output.renderer}`,
    );
    return result.context;
  }
  for (let i = 0; i < 5; i++) {
    await run("unthrottled");
    await run("throttled");
  }
  await run("diagnostic");
  workerContext = await run("worker-cold");
  await run("worker-warm", workerContext);
  const byProfile = Object.fromEntries(
    ["unthrottled", "throttled"].map((profile) => {
      const values = report.samples
        .filter((x) => x.profile === profile)
        .map((x) => x.readyMs)
        .sort((a, b) => a - b);
      return [
        profile,
        {
          count: values.length,
          medianMs: values[Math.floor(values.length / 2)],
          minMs: values[0],
          maxMs: values.at(-1),
          valuesMs: values,
        },
      ];
    }),
  );
  report.summary = {
    byProfile,
    renderers: [...new Set(report.samples.map((x) => x.renderer))],
  };
  assert.equal(
    report.summary.renderers.length,
    1,
    "Renderer changed during production audit",
  );
} catch (error) {
  report.errors.push(error.stack || error.message);
  process.exitCode = 1;
} finally {
  await workerContext?.close().catch(() => {});
  await browser?.close().catch(() => {});
  await write();
  console.log(
    JSON.stringify(
      { output: out, summary: report.summary, errors: report.errors },
      null,
      2,
    ),
  );
}
