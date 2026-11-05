import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs/promises";
import http from "node:http";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { chromium } from "playwright";
import { fileURLToPath } from "node:url";
import { serveBuild } from "./browser-test-utils.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const [buildArg, outArg, ...extra] = process.argv.slice(2);
if (!buildArg || !outArg || extra.length) {
  console.error(
    "Usage: node scripts/audit-game-loading-diagnostics.mjs <build-dist> <new-output-dir>",
  );
  process.exit(2);
}
const dist = path.resolve(buildArg),
  out = path.resolve(outArg);
assert.ok(
  out !== dist && !out.startsWith(dist + path.sep),
  "Output must be outside build",
);
await fs.access(path.join(dist, "index.html"));
await fs.mkdir(path.dirname(out), { recursive: true });
await fs.mkdir(out);
const pack = JSON.parse(
  await fs.readFile(path.join(dist, "game-pack.json"), "utf8"),
);
const table = pack.files.find((entry) => entry.id === "pool-table");
const tableBytes = await fs.readFile(path.join(dist, table.url));
const hash = (bytes) => crypto.createHash("sha256").update(bytes).digest("hex");
const expected = Object.fromEntries(
  await Promise.all(
    pack.files.map(async (entry) => [
      entry.url,
      {
        local: hash(await fs.readFile(path.join(dist, entry.url))),
        manifest: entry.sha256,
        bytes: entry.bytes,
      },
    ]),
  ),
);
for (const value of Object.values(expected))
  assert.equal(value.local, value.manifest);
const report = {
  node: process.version,
  build: dist,
  observedAt: new Date().toISOString(),
  observation:
    "Passive copy of existing GLB reader chunks or returned arrayBuffer. No Response.clone, tee, or extra reads; fixture/game cases compare observed with uninstrumented behavior.",
  profile:
    "system Chrome headless, 100ms latency, 4Mbps down, 1Mbps up, cache disabled, SW blocked",
  expectedTableHash: hash(tableBytes),
  expected,
  fixture: [],
  game: [],
  errors: [],
};
const fixtureServer = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, "http://localhost");
    if (url.pathname === "/fixture") {
      res.writeHead(200, {
        "Content-Type": "text/html",
        "Cache-Control": "no-store",
      });
      res.end(
        '<!doctype html><script type="importmap">{"imports":{"three":"/node_modules/three/build/three.module.js","three/addons/":"/node_modules/three/examples/jsm/"}}</script><script type="module">import {GLTFLoader} from "three/addons/loaders/GLTFLoader.js"; window.GLTFLoader=GLTFLoader; window.loaderReady=true;</script>',
      );
      return;
    }
    if (url.pathname.startsWith("/node_modules/three/")) {
      const threeRoot = path.join(root, "node_modules", "three"),
        file = path.resolve(root, url.pathname.slice(1));
      if (!file.startsWith(threeRoot + path.sep)) {
        res.writeHead(404);
        res.end();
        return;
      }
      const bytes = await fs.readFile(file);
      res.writeHead(200, {
        "Content-Type": "text/javascript",
        "Cache-Control": "no-store",
        "Content-Length": bytes.length,
      });
      res.end(bytes);
      return;
    }
    if (
      url.pathname === "/chunked/table.glb" ||
      url.pathname === "/length/table.glb"
    ) {
      const headers = {
        "Content-Type": "model/gltf-binary",
        "Cache-Control": "no-store",
      };
      if (url.pathname.startsWith("/length/"))
        headers["Content-Length"] = tableBytes.length;
      else headers["Transfer-Encoding"] = "chunked";
      res.writeHead(200, headers);
      res.end(tableBytes);
      return;
    }
    res.writeHead(404);
    res.end();
  } catch {
    res.writeHead(500);
    res.end("fixture failure");
  }
});
await new Promise((resolve) => fixtureServer.listen(0, "127.0.0.1", resolve));
const fixtureUrl = `http://127.0.0.1:${fixtureServer.address().port}`;
const originalServer = await serveBuild(dist);
const browser = await chromium.launch({
  channel: "chrome",
  headless: true,
  ignoreDefaultArgs: ["--enable-unsafe-swiftshader"],
});
function captureReads() {
  const chunks = {},
    bodyMap = new WeakMap(),
    readerMap = new WeakMap(),
    responseMap = new WeakMap();
  const originalFetch = window.fetch.bind(window),
    originalGetReader = ReadableStream.prototype.getReader,
    originalRead = ReadableStreamDefaultReader.prototype.read,
    originalArrayBuffer = Response.prototype.arrayBuffer;
  window.fetch = async function (...args) {
    const response = await originalFetch(...args);
    const url = new URL(response.url);
    if (url.pathname.endsWith(".glb") && response.body) {
      bodyMap.set(response.body, url.pathname);
      responseMap.set(response, url.pathname);
      chunks[url.pathname] = { parts: [], ended: false };
    }
    return response;
  };
  Response.prototype.arrayBuffer = function (...args) {
    const promise = originalArrayBuffer.apply(this, args),
      url = responseMap.get(this);
    return url
      ? promise.then((bytes) => {
          chunks[url].parts.push(new Uint8Array(bytes.slice(0)));
          chunks[url].ended = true;
          return bytes;
        })
      : promise;
  };
  ReadableStream.prototype.getReader = function (...args) {
    const reader = originalGetReader.apply(this, args),
      url = bodyMap.get(this);
    if (url) readerMap.set(reader, url);
    return reader;
  };
  ReadableStreamDefaultReader.prototype.read = function (...args) {
    const promise = originalRead.apply(this, args),
      url = readerMap.get(this);
    return url
      ? promise.then((result) => {
          if (result.done) chunks[url].ended = true;
          else if (result.value)
            chunks[url].parts.push(new Uint8Array(result.value));
          return result;
        })
      : promise;
  };
  window.__captureGlb = chunks;
  window.__readHashes = async () =>
    Object.fromEntries(
      await Promise.all(
        Object.entries(chunks).map(async ([url, item]) => {
          const total = item.parts.reduce((sum, part) => sum + part.length, 0),
            bytes = new Uint8Array(total);
          let offset = 0;
          for (const part of item.parts) {
            bytes.set(part, offset);
            offset += part.length;
          }
          const digest = await crypto.subtle.digest("SHA-256", bytes);
          return [
            url,
            {
              bytes: total,
              ended: item.ended,
              sha256: [...new Uint8Array(digest)]
                .map((b) => b.toString(16).padStart(2, "0"))
                .join(""),
            },
          ];
        }),
      ),
    );
}
async function prepare(page, context) {
  const cdp = await context.newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
  const events = [],
    ids = new Map();
  let stage = "loading";
  cdp.on("Network.requestWillBeSent", (e) => {
    if (new URL(e.request.url).pathname.endsWith(".glb")) {
      ids.set(e.requestId, e.request.url);
      events.push({
        event: "request",
        requestId: e.requestId,
        url: e.request.url,
        stage,
      });
    }
  });
  cdp.on("Network.responseReceived", (e) => {
    if (ids.has(e.requestId))
      events.push({
        event: "response",
        requestId: e.requestId,
        status: e.response.status,
        headers: e.response.headers,
        stage,
      });
  });
  cdp.on("Network.loadingFinished", (e) => {
    if (ids.has(e.requestId))
      events.push({
        event: "finished",
        requestId: e.requestId,
        encodedDataLength: e.encodedDataLength,
        stage,
      });
  });
  cdp.on("Network.loadingFailed", (e) => {
    if (ids.has(e.requestId))
      events.push({
        event: "failed",
        requestId: e.requestId,
        errorText: e.errorText,
        canceled: e.canceled,
        stage,
      });
  });
  const pw = [];
  page.on("requestfailed", (r) => {
    if (new URL(r.url()).pathname.endsWith(".glb"))
      pw.push({ url: r.url(), error: r.failure()?.errorText, stage });
  });
  const throttle = () =>
    cdp.send("Network.emulateNetworkConditions", {
      offline: false,
      latency: 100,
      downloadThroughput: 500000,
      uploadThroughput: 125000,
      connectionType: "cellular4g",
    });
  return {
    events,
    pw,
    throttle,
    setStage: (value) => {
      stage = value;
    },
  };
}
async function fixtureCase(framing, kind) {
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    serviceWorkers: "block",
  });
  if (kind === "gltf-observed") await ctx.addInitScript(captureReads);
  const page = await ctx.newPage(),
    monitor = await prepare(page, ctx);
  try {
    await page.goto(fixtureUrl + "/fixture");
    await page.waitForFunction(() => window.loaderReady);
    await monitor.throttle();
    const url = `${fixtureUrl}/${framing}/table.glb?kind=${kind}`;
    const data = await page.evaluate(
      async ({ url, kind }) => {
        if (kind === "direct") {
          const response = await fetch(url);
          const bytes = await response.arrayBuffer();
          const digest = await crypto.subtle.digest("SHA-256", bytes);
          return {
            status: response.status,
            bytes: bytes.byteLength,
            sha256: [...new Uint8Array(digest)]
              .map((b) => b.toString(16).padStart(2, "0"))
              .join(""),
          };
        }
        const gltf = await new window.GLTFLoader().loadAsync(url);
        let meshes = 0;
        gltf.scene.traverse((o) => {
          if (o.isMesh) meshes++;
        });
        return {
          scene: gltf.scene.name,
          meshes,
          hashes: window.__readHashes ? await window.__readHashes() : null,
        };
      },
      { url, kind },
    );
    await page.waitForTimeout(100);
    monitor.setStage("teardown");
    await ctx.close();
    return { framing, kind, data, events: monitor.events, pw: monitor.pw };
  } finally {
    await ctx.close().catch(() => {});
  }
}
async function gameCase(observed) {
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    serviceWorkers: "block",
  });
  if (observed) await ctx.addInitScript(captureReads);
  const page = await ctx.newPage(),
    monitor = await prepare(page, ctx);
  try {
    await monitor.throttle();
    const t = performance.now();
    await page.goto(originalServer.url + "?page=game", {
      waitUntil: "domcontentloaded",
    });
    await page.waitForFunction(
      () =>
        window.render_game_to_text &&
        JSON.parse(window.render_game_to_text()).ready,
      null,
      { timeout: 90000 },
    );
    const readyMs = performance.now() - t,
      hashes = observed
        ? await page.evaluate(() => window.__readHashes())
        : null;
    await page.waitForTimeout(200);
    monitor.setStage("teardown");
    await ctx.close();
    return {
      observed,
      readyMs,
      hashes,
      events: monitor.events,
      pw: monitor.pw,
    };
  } finally {
    await ctx.close().catch(() => {});
  }
}
try {
  report.browser = browser.version();
  for (const framing of ["chunked", "length"])
    for (const kind of ["direct", "gltf-plain", "gltf-observed"]) {
      console.log("fixture", framing, kind);
      report.fixture.push(await fixtureCase(framing, kind));
    }
  for (const observed of [false, true]) {
    console.log("game observed", observed);
    report.game.push(await gameCase(observed));
  }
  const captured = report.game.find((x) => x.observed).hashes;
  report.hashVerification = Object.entries(expected).map(([url, value]) => {
    const record = Object.entries(captured).find(([actual]) =>
      actual.endsWith("/" + url),
    );
    return {
      url,
      match:
        !!record &&
        record[1].sha256 === value.local &&
        record[1].bytes === value.bytes &&
        record[1].ended,
      captured: record?.[1] || null,
      local: value.local,
    };
  });
  assert.equal(report.hashVerification.length, 18);
  assert.ok(report.hashVerification.every((x) => x.match));
} catch (e) {
  report.errors.push(e.stack || e.message);
  process.exitCode = 1;
} finally {
  await browser.close();
  await originalServer.close();
  await new Promise((resolve) => fixtureServer.close(resolve));
  await fs.writeFile(
    path.join(out, "results.json"),
    JSON.stringify(report, null, 2) + "\n",
    { flag: "wx" },
  );
  console.log(
    JSON.stringify(
      {
        errors: report.errors,
        fixture: report.fixture.map((x) => ({
          framing: x.framing,
          kind: x.kind,
          data: x.data,
          cdp: x.events.filter((e) => ["finished", "failed"].includes(e.event)),
          pw: x.pw,
        })),
        game: report.game.map((x) => ({
          observed: x.observed,
          readyMs: x.readyMs,
          finished: x.events.filter((e) => e.event === "finished").length,
          failed: x.events.filter((e) => e.event === "failed").length,
          pw: x.pw.length,
        })),
        hashMatches: report.hashVerification?.filter((x) => x.match).length,
      },
      null,
      2,
    ),
  );
}
