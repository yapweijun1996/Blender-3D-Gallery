import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs/promises";
import http2 from "node:http2";
import os from "node:os";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { promisify } from "node:util";
import { gzipSync } from "node:zlib";
import { chromium } from "playwright";

const [
  baselineArg,
  candidateArg,
  productionArg,
  outputArg,
  orderArg = "four-first",
  ...extra
] = process.argv.slice(2);
if (
  !baselineArg ||
  !candidateArg ||
  !productionArg ||
  !outputArg ||
  !["four-first", "six-first"].includes(orderArg) ||
  extra.length
) {
  console.error(
    "Usage: node scripts/audit-game-concurrency-http2.mjs <baseline-dist> <candidate-dist> <production-audit.json> <new-output-dir> [four-first|six-first]",
  );
  process.exit(2);
}
const builds = {
  four: path.resolve(baselineArg),
  six: path.resolve(candidateArg),
};
const out = path.resolve(outputArg);
for (const dir of Object.values(builds))
  assert.ok(
    out !== dir && !out.startsWith(dir + path.sep),
    "Output must be outside the build directories",
  );
await fs.mkdir(path.dirname(out), { recursive: true });
await fs.mkdir(out);
const production = JSON.parse(await fs.readFile(productionArg, "utf8"));
assert.ok(production.onlineBuild, "Production audit must pin its build");
const productionSample = production.samples.find(
  (sample) => sample.profile === "throttled",
);
assert.ok(productionSample, "Expected recorded production sample");
const productionGlbs = productionSample.resources.filter((r) =>
  new URL(r.url).pathname.endsWith(".glb"),
);
assert.equal(productionGlbs.length, 18);
const productionEncoded = new Map(
  productionGlbs.map((r) => [
    path.basename(new URL(r.url).pathname),
    r.encodedBytes,
  ]),
);
const report = {
  methodology: {
    source:
      "Frozen same-source builds differ only in Game worker concurrency: four vs six. Both use unchanged, identical 18 GLBs.",
    execution:
      "Five strictly alternating four/six fresh contexts in one system Chrome process, one locally generated self-signed HTTPS/HTTP2 server, gzip level 6. Browser cache disabled; service workers blocked; 100ms latency, 4Mbps down, 1Mbps up page CDP throttle; CPU not throttled.",
    ready:
      "Wall clock from page.goto start to Game ready; host CPU counters and load averages bracket this interval only, with the counters including browser plus any other host work.",
    assets:
      "File and pack hashes are verified before sampling; each sample requires 18 status-200 HTTP/2 gzip responses with matching encoded and decoded byte lengths, successful Game ready and no page/GLB failures. No response-body hashing or extra instrumentation occurs during timing.",
    limitations: [
      "This is local representative HTTPS/HTTP2 and gzip, not a production candidate deployment or a physical phone.",
      "TLS certificates are temporary self-signed test certificates, trusted only through the test context's ignoreHTTPSErrors option.",
      "Local gzip output is not guaranteed byte-identical to the CDN's gzip; encoded totals are compared against the recorded production response.",
      "Five paired observations are descriptive; host CPU counters include the browser and external host workloads may affect results.",
      "Service workers are blocked in every sample, so this does not evaluate installation contention or the offline pack.",
    ],
  },
  environment: {
    node: process.version,
    platform: process.platform,
    arch: process.arch,
    osRelease: os.release(),
    cpu: os.cpus()[0]?.model,
    timestamp: new Date().toISOString(),
    chrome: {
      channel: "chrome",
      headless: true,
      ignoreDefaultArgs: ["--enable-unsafe-swiftshader"],
    },
  },
  builds: {},
  gzipComparison: {},
  samples: [],
  errors: [],
};
const fileHash = (buffer) =>
  crypto.createHash("sha256").update(buffer).digest("hex");
const expected = {};
for (const [name, root] of Object.entries(builds)) {
  const info = JSON.parse(
    await fs.readFile(path.join(root, "build-info.json"), "utf8"),
  );
  const pack = JSON.parse(
    await fs.readFile(path.join(root, "game-pack.json"), "utf8"),
  );
  assert.equal(pack.files.length, 18);
  assert.equal(pack.build, info.build);
  expected[name] = Object.fromEntries(
    await Promise.all(
      pack.files.map(async (entry) => {
        const bytes = await fs.readFile(path.join(root, entry.url));
        assert.equal(bytes.length, entry.bytes);
        assert.equal(fileHash(bytes), entry.sha256);
        return [
          entry.id,
          {
            url: entry.url,
            bytes: entry.bytes,
            sha256: entry.sha256,
            gzipBytes: gzipSync(bytes, { level: 6 }).length,
          },
        ];
      }),
    ),
  );
  report.builds[name] = { build: info.build, root, pack: expected[name] };
}
assert.deepEqual(
  expected.four,
  expected.six,
  "All 18 original model paths, lengths, bytes and gzip lengths must match",
);
assert.equal(
  production.onlineBuild,
  report.builds.four.build,
  "Production reference and baseline build identity must match",
);
assert.equal(production.onlinePack.build, production.onlineBuild);
assert.equal(production.onlinePack.files.length, 18);
for (const item of production.onlinePack.files) {
  const local = expected.four[item.id];
  assert.ok(
    local &&
      local.url === item.url &&
      local.bytes === item.bytes &&
      local.sha256 === item.sha256,
    `Production pack entry differs from baseline: ${item.id}`,
  );
}
const comparisons = Object.values(expected.four).map((item) => ({
  path: item.url,
  localEncoded: item.gzipBytes,
  productionEncoded: productionEncoded.get(path.basename(item.url)),
}));
assert.ok(comparisons.every((item) => Number.isFinite(item.productionEncoded)));
const localTotal = comparisons.reduce(
    (sum, item) => sum + item.localEncoded,
    0,
  ),
  productionTotal = comparisons.reduce(
    (sum, item) => sum + item.productionEncoded,
    0,
  );
report.gzipComparison = {
  productionBuild: production.onlineBuild,
  localTotal,
  productionTotal,
  differenceBytes: localTotal - productionTotal,
  differencePercent: (100 * (localTotal - productionTotal)) / productionTotal,
  files: comparisons,
};
const types = {
  ".html": "text/html",
  ".js": "application/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".glb": "model/gltf-binary",
  ".webmanifest": "application/manifest+json",
  ".webp": "image/webp",
};
async function collectFiles(root, pack) {
  const gameGlbs = new Set(Object.values(pack).map((item) => item.url));
  const cache = new Map();
  async function walk(dir) {
    for (const entry of await fs.readdir(dir, { withFileTypes: true })) {
      const absolute = path.join(dir, entry.name),
        relative = path.relative(root, absolute).split(path.sep).join("/");
      if (entry.isDirectory()) await walk(absolute);
      else if (
        entry.isFile() &&
        types[path.extname(relative)] &&
        (!relative.endsWith(".glb") || gameGlbs.has(relative))
      ) {
        const source = await fs.readFile(absolute);
        cache.set(relative, {
          bytes: gzipSync(source, { level: 6 }),
          type: types[path.extname(relative)],
        });
      }
    }
  }
  await walk(root);
  return cache;
}
const files = {
  four: await collectFiles(builds.four, expected.four),
  six: await collectFiles(builds.six, expected.six),
};
const execFileAsync = promisify(execFile);
const tlsDir = await fs.mkdtemp(
  path.join(os.tmpdir(), "game-concurrency-tls-"),
);
let server, browser;
const write = () =>
  fs.writeFile(
    path.join(out, "results.json"),
    `${JSON.stringify(report, null, 2)}\n`,
  );
const cpuSnapshot = () =>
  os.cpus().reduce((sum, cpu) => {
    for (const [key, value] of Object.entries(cpu.times))
      sum[key] = (sum[key] || 0) + value;
    return sum;
  }, {});
function cpuBusy(before, after) {
  const delta = Object.fromEntries(
    Object.keys(after).map((key) => [key, after[key] - (before[key] || 0)]),
  );
  const total = Object.values(delta).reduce((sum, value) => sum + value, 0);
  return total ? (100 * (total - delta.idle)) / total : null;
}
let active = "four";
try {
  await execFileAsync(
    "openssl",
    [
      "req",
      "-x509",
      "-newkey",
      "rsa:2048",
      "-nodes",
      "-days",
      "1",
      "-subj",
      "/CN=localhost",
      "-keyout",
      path.join(tlsDir, "test.key"),
      "-out",
      path.join(tlsDir, "test.crt"),
    ],
    { maxBuffer: 1024 * 1024 },
  );
  const key = await fs.readFile(path.join(tlsDir, "test.key")),
    cert = await fs.readFile(path.join(tlsDir, "test.crt"));
  server = http2.createSecureServer({ key, cert });
  server.on("stream", (stream, headers) => {
    const url = new URL(headers[":path"], "https://localhost"),
      prefix = "/Blender-3D-Gallery/";
    if (!url.pathname.startsWith(prefix)) {
      stream.respond({ ":status": 404 });
      stream.end();
      return;
    }
    const relative =
        decodeURIComponent(url.pathname.slice(prefix.length)) || "index.html",
      file = files[active].get(relative);
    if (!file) {
      stream.respond({ ":status": 404 });
      stream.end();
      return;
    }
    stream.respond({
      ":status": 200,
      "content-type": file.type,
      "content-encoding": "gzip",
      "content-length": String(file.bytes.length),
      "cache-control": "no-store",
      vary: "Accept-Encoding",
    });
    stream.end(file.bytes);
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const url = `https://127.0.0.1:${server.address().port}/Blender-3D-Gallery/?page=game`;
  browser = await chromium.launch(report.environment.chrome);
  report.environment.browser = browser.version();
  const order = Array.from({ length: 10 }, (_, index) =>
    (index % 2 === 0) === (orderArg === "four-first") ? "four" : "six",
  );
  report.methodology.order = order;
  for (const [index, name] of order.entries()) {
    active = name;
    const sample = { index: index + 1, name, errors: [] },
      context = await browser.newContext({
        viewport: { width: 1440, height: 900 },
        deviceScaleFactor: 1,
        serviceWorkers: "block",
        ignoreHTTPSErrors: true,
      });
    const page = await context.newPage(),
      cdp = await context.newCDPSession(page),
      requests = new Map();
    page.on("pageerror", (error) =>
      sample.errors.push({ type: "pageerror", message: error.message }),
    );
    page.on("console", (message) => {
      if (message.type() === "error")
        sample.errors.push({ type: "console", message: message.text() });
    });
    page.on("requestfailed", (request) => {
      if (new URL(request.url()).pathname.endsWith(".glb"))
        sample.errors.push({
          type: "requestfailed",
          path: new URL(request.url()).pathname,
          message: request.failure()?.errorText,
        });
    });
    try {
      await cdp.send("Network.enable");
      await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
      await cdp.send("Network.emulateNetworkConditions", {
        offline: false,
        latency: 100,
        downloadThroughput: 500000,
        uploadThroughput: 125000,
        connectionType: "cellular4g",
      });
      cdp.on("Network.responseReceived", (event) => {
        if (new URL(event.response.url).pathname.endsWith(".glb"))
          requests.set(event.requestId, {
            requestId: event.requestId,
            url: event.response.url,
            status: event.response.status,
            protocol: event.response.protocol,
            headers: event.response.headers,
          });
      });
      cdp.on("Network.loadingFinished", (event) => {
        const item = requests.get(event.requestId);
        if (item) {
          item.finished = true;
          item.encodedDataLength = event.encodedDataLength;
        }
      });
      cdp.on("Network.loadingFailed", (event) => {
        const item = requests.get(event.requestId);
        if (item) item.failure = event.errorText;
      });
      const startCpu = cpuSnapshot(),
        startLoad = os.loadavg(),
        start = performance.now();
      const response = await page.goto(url, {
        waitUntil: "domcontentloaded",
        timeout: 90000,
      });
      assert.equal(response.status(), 200);
      await page.waitForFunction(
        () =>
          window.render_game_to_text &&
          JSON.parse(window.render_game_to_text()).ready,
        null,
        { timeout: 90000 },
      );
      sample.readyMs = performance.now() - start;
      const endCpu = cpuSnapshot(),
        endLoad = os.loadavg();
      sample.hostCpuBusyPercent = cpuBusy(startCpu, endCpu);
      sample.hostLoadBefore = startLoad;
      sample.hostLoadAfter = endLoad;
      await page.waitForTimeout(200);
      const observation = await page.evaluate(() => {
        const canvas = document.querySelector("#game-viewport canvas"),
          gl = canvas.getContext("webgl2"),
          debug = gl?.getExtension("WEBGL_debug_renderer_info");
        return {
          renderer: debug
            ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL)
            : null,
          canvas: [canvas.width, canvas.height],
          controller: !!navigator.serviceWorker.controller,
          resources: performance
            .getEntriesByType("resource")
            .filter((e) => new URL(e.name).pathname.endsWith(".glb"))
            .map((e) => ({
              url: e.name,
              startMs: e.startTime,
              responseEndMs: e.responseEnd,
              encodedBytes: e.encodedBodySize,
              decodedBytes: e.decodedBodySize,
              transferBytes: e.transferSize,
              protocol: e.nextHopProtocol,
            })),
        };
      });
      sample.renderer = observation.renderer;
      sample.canvas = observation.canvas;
      sample.controller = observation.controller;
      sample.resources = observation.resources;
      sample.cdpGlbs = [...requests.values()];
      const required = new Map(
        Object.values(expected[name]).map((item) => [
          path.basename(item.url),
          item,
        ]),
      );
      sample.complete =
        !observation.controller &&
        observation.resources.length === 18 &&
        sample.cdpGlbs.length === 18 &&
        new Set(
          observation.resources.map((item) =>
            path.basename(new URL(item.url).pathname),
          ),
        ).size === 18 &&
        observation.resources.every((item) => {
          const expectedItem = required.get(
            path.basename(new URL(item.url).pathname),
          );
          return (
            expectedItem &&
            item.encodedBytes === expectedItem.gzipBytes &&
            item.decodedBytes === expectedItem.bytes &&
            item.transferBytes > 0 &&
            item.protocol === "h2"
          );
        }) &&
        sample.cdpGlbs.every(
          (item) =>
            item.status === 200 &&
            item.protocol === "h2" &&
            item.finished &&
            !item.failure &&
            Object.entries(item.headers).some(
              ([key, value]) =>
                key.toLowerCase() === "content-encoding" && value === "gzip",
            ),
        );
      assert.ok(
        sample.complete,
        "All 18 GLBs must finish over HTTP/2 gzip with matching lengths",
      );
      assert.deepEqual(sample.errors, []);
    } catch (error) {
      sample.failure = error.stack || error.message;
    } finally {
      await context.close();
    }
    report.samples.push(sample);
    await write();
    console.log(
      `${sample.index}/10 ${name} ready=${sample.readyMs?.toFixed(1) || "failed"}ms complete=${!!sample.complete}`,
    );
    if (sample.failure)
      throw new Error(`Sample ${sample.index} failed: ${sample.failure}`);
  }
  const renderers = [
      ...new Set(report.samples.map((sample) => sample.renderer)),
    ],
    canvases = [
      ...new Set(report.samples.map((sample) => sample.canvas.join("x"))),
    ];
  assert.equal(renderers.length, 1);
  assert.ok(renderers[0]);
  assert.equal(canvases.length, 1);
  const byBuild = Object.fromEntries(
    ["four", "six"].map((name) => {
      const raw = report.samples
          .filter((s) => s.name === name)
          .map((s) => s.readyMs),
        sorted = [...raw].sort((a, b) => a - b);
      return [
        name,
        {
          count: raw.length,
          medianMs: sorted[2],
          minMs: sorted[0],
          maxMs: sorted.at(-1),
          valuesMs: raw,
        },
      ];
    }),
  );
  report.summary = {
    renderers,
    canvases,
    byBuild,
    pairedDeltaMs: Array.from({ length: 5 }, (_, i) => {
      const pair = report.samples.slice(2 * i, 2 * i + 2);
      return (
        pair.find((sample) => sample.name === "six").readyMs -
        pair.find((sample) => sample.name === "four").readyMs
      );
    }),
  };
} catch (error) {
  report.errors.push(error.stack || error.message);
  process.exitCode = 1;
} finally {
  await browser?.close().catch(() => {});
  await new Promise((resolve) => (server ? server.close(resolve) : resolve()));
  await fs.rm(tlsDir, { recursive: true, force: true });
  await write();
  console.log(
    JSON.stringify(
      {
        output: out,
        gzipComparison: {
          localTotal,
          productionTotal,
          differencePercent: report.gzipComparison.differencePercent,
        },
        summary: report.summary,
        errors: report.errors,
      },
      null,
      2,
    ),
  );
}
