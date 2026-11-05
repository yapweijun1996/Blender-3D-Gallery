import fs from "node:fs/promises";
import http from "node:http";
import path from "node:path";
import crypto from "node:crypto";
import { chromium } from "playwright";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const [buildArg, outArg, ...extra] = process.argv.slice(2);
if (!buildArg || !outArg || extra.length) {
  console.error(
    "Usage: node scripts/audit-game-loading-mechanism.mjs <build-dist> <new-output-dir>",
  );
  process.exit(2);
}
const build = path.resolve(buildArg),
  out = path.resolve(outArg);
assert.ok(
  out !== build && !out.startsWith(build + path.sep),
  "Output must be outside build",
);
await fs.access(path.join(build, "index.html"));
await fs.mkdir(path.dirname(out), { recursive: true });
await fs.mkdir(out);
const pack = JSON.parse(
    await fs.readFile(path.join(build, "game-pack.json"), "utf8"),
  ),
  table = pack.files.find((x) => x.id === "pool-table"),
  bytes = await fs.readFile(path.join(build, table.url)),
  expected = crypto.createHash("sha256").update(bytes).digest("hex");
const server = http.createServer(async (req, res) => {
  try {
    const u = new URL(req.url, "http://localhost");
    if (u.pathname === "/fixture") {
      res.writeHead(200, {
        "Content-Type": "text/html",
        "Cache-Control": "no-store",
      });
      res.end(
        '<script type="importmap">{"imports":{"three":"/node_modules/three/build/three.module.js","three/addons/":"/node_modules/three/examples/jsm/"}}</script><script type="module">import {FileLoader} from "three";import {GLTFLoader} from "three/addons/loaders/GLTFLoader.js";window.FileLoader=FileLoader;window.GLTFLoader=GLTFLoader;window.ready=true;</script>',
      );
      return;
    }
    if (u.pathname.startsWith("/node_modules/three/")) {
      const f = path.resolve(root, u.pathname.slice(1)),
        allowed = path.join(root, "node_modules", "three");
      if (!f.startsWith(allowed + path.sep)) throw Error("bad path");
      const b = await fs.readFile(f);
      res.writeHead(200, {
        "Content-Type": "text/javascript",
        "Content-Length": b.length,
      });
      res.end(b);
      return;
    }
    if (u.pathname === "/table.glb") {
      res.writeHead(200, {
        "Content-Type": "model/gltf-binary",
        "Content-Length": bytes.length,
        "Cache-Control": "no-store",
      });
      res.end(bytes);
      return;
    }
    res.writeHead(404);
    res.end();
  } catch {
    res.writeHead(500);
    res.end();
  }
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}`,
  browser = await chromium.launch({
    channel: "chrome",
    headless: true,
    ignoreDefaultArgs: ["--enable-unsafe-swiftshader"],
  }),
  cases = [];
try {
  for (const name of [
    "fetch-direct",
    "fetch-request-signal",
    "wrapped-no-signal",
    "wrapped-request-signal",
    "fileloader",
    "gltfloader",
  ]) {
    console.log(name);
    const ctx = await browser.newContext({ serviceWorkers: "block" }),
      page = await ctx.newPage(),
      cdp = await ctx.newCDPSession(page),
      events = [],
      ids = new Set();
    await cdp.send("Network.enable");
    await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
    cdp.on("Network.requestWillBeSent", (e) => {
      if (new URL(e.request.url).pathname === "/table.glb")
        ids.add(e.requestId);
    });
    cdp.on("Network.loadingFailed", (e) => {
      if (ids.has(e.requestId))
        events.push({
          event: "failed",
          id: e.requestId,
          error: e.errorText,
          canceled: e.canceled,
        });
    });
    cdp.on("Network.loadingFinished", (e) => {
      if (ids.has(e.requestId))
        events.push({
          event: "finished",
          id: e.requestId,
          encodedDataLength: e.encodedDataLength,
        });
    });
    try {
      await page.goto(base + "/fixture");
      await page.waitForFunction(() => window.ready);
      await cdp.send("Network.emulateNetworkConditions", {
        offline: false,
        latency: 100,
        downloadThroughput: 500000,
        uploadThroughput: 125000,
        connectionType: "cellular4g",
      });
      const result = await page.evaluate(
        async ({ url, name }) => {
          let output,
            meshes = 0;
          const needsSignal = name.includes("request-signal");
          const request = needsSignal
            ? new Request(url, {
                headers: new Headers(),
                credentials: "same-origin",
                signal: AbortSignal.any([
                  new AbortController().signal,
                  new AbortController().signal,
                ]),
              })
            : url;
          if (name === "fileloader")
            output = await new window.FileLoader()
              .setResponseType("arraybuffer")
              .loadAsync(url);
          else if (name === "gltfloader") {
            const g = await new window.GLTFLoader().loadAsync(url);
            g.scene.traverse((o) => {
              if (o.isMesh) meshes++;
            });
          } else {
            const response = await fetch(request);
            if (name.startsWith("wrapped")) {
              const reader = response.body.getReader(),
                stream = new ReadableStream({
                  start(controller) {
                    function readData() {
                      reader.read().then(
                        ({ done, value }) => {
                          if (done) controller.close();
                          else {
                            controller.enqueue(value);
                            readData();
                          }
                        },
                        (e) => controller.error(e),
                      );
                    }
                    readData();
                  },
                });
              output = await new Response(stream).arrayBuffer();
            } else output = await response.arrayBuffer();
          }
          const hash = output
            ? [...new Uint8Array(await crypto.subtle.digest("SHA-256", output))]
                .map((b) => b.toString(16).padStart(2, "0"))
                .join("")
            : null;
          return { bytes: output?.byteLength || null, sha256: hash, meshes };
        },
        { url: base + "/table.glb?mode=" + name, name },
      );
      await page.waitForTimeout(100);
      cases.push({ name, result, events });
    } finally {
      await ctx.close();
    }
  }
} finally {
  await browser.close();
  await new Promise((r) => server.close(r));
  await fs.writeFile(
    path.join(out, "results.json"),
    JSON.stringify(
      {
        node: process.version,
        browser: browser.version(),
        build,
        expected,
        cases,
      },
      null,
      2,
    ) + "\n",
    { flag: "wx" },
  );
  console.log(
    JSON.stringify(
      {
        node: process.version,
        browser: browser.version(),
        build,
        expected,
        cases,
      },
      null,
      2,
    ),
  );
}
