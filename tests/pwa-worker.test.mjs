import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import { runInNewContext } from "node:vm";

const template = await readFile(new URL("../src/pwa/sw-template.js", import.meta.url), "utf8");
const scope = "https://gallery.test/Blender-3D-Gallery/";
const build = "old";
const shellCache = "b3g-_Blender_3D_Gallery_-shell-old";
const entries = { "index.html": "<title>Old</title>", "assets/page-OldHash1.js": "export const build = 'old';" };
const shell = await Promise.all(Object.entries(entries).map(async ([url, body]) => {
  const bytes = new TextEncoder().encode(body);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return { url, bytes: bytes.length, sha256: Buffer.from(hash).toString("hex") };
}));

function worker() {
  const handlers = new Map(), storage = new Map(), messages = [], requests = [];
  const key = (file) => new URL(file, scope).href;
  const network = new Map(Object.entries(entries).map(([file, body]) => [file, new Response(body)]));
  network.set("build-info.json", Response.json({ build }));
  const caches = {
    async open(name) {
      if (!storage.has(name)) storage.set(name, new Map());
      const cache = storage.get(name);
      return {
        async put(url, response) { cache.set(url, response.clone()); },
        async match(url) { return cache.get(url)?.clone(); },
      };
    },
    async keys() { return [...storage.keys()]; },
    async delete(name) { return storage.delete(name); },
  };
  runInNewContext(template
    .replace("__BUILD__", JSON.stringify(build))
    .replace("__SHELL__", JSON.stringify(shell))
    .replace("__PACK__", '{"files":[]}'), {
    URL, TextDecoder, Uint8Array, Response, crypto, caches,
    self: {
      registration: { scope },
      location: new URL(scope),
      addEventListener: (type, handler) => handlers.set(type, handler),
      clients: { async get() { return { postMessage: (message) => messages.push(message.type) }; } },
    },
    async fetch(input) {
      const url = new URL(input.url ?? input);
      requests.push(url.href);
      const file = url.pathname.slice(new URL(scope).pathname.length);
      return network.get(file)?.clone() ?? new Response("Not found", { status: 404 });
    },
  });
  return {
    key, network, storage, messages, requests,
    install() {
      let result;
      handlers.get("install")({ waitUntil: (promise) => { result = promise; } });
      return result;
    },
    fetch(file, mode = "cors") {
      let result;
      handlers.get("fetch")({
        request: { method: "GET", url: key(file), mode },
        clientId: "returning-tab",
        respondWith: (promise) => { result = promise; },
      });
      return result;
    },
  };
}

test("stale navigation keeps its shell and tells the requesting tab about a missing motion asset", async () => {
  const sw = worker();
  await sw.install();
  sw.network.set("index.html", new Response("<title>New</title>"));
  assert.equal(await (await sw.fetch("?page=tripo-motion", "navigate")).text(), entries["index.html"]);
  assert.equal((await sw.fetch("assets/motion-OldHash1.glb")).status, 404);
  sw.network.set("assets/page-NewHash1.js", new Response("<html>Fallback</html>", {
    headers: { "Content-Type": "text/html" },
  }));
  assert.equal((await sw.fetch("assets/page-NewHash1.js")).status, 503);
  assert.deepEqual(sw.messages, ["RESOURCE_LOAD_FAILED", "RESOURCE_LOAD_FAILED"]);
});

test("evicted shell entries are fail-closed and can only recover their own bytes", async () => {
  const sw = worker();
  await sw.install();
  for (const file of Object.keys(entries)) {
    sw.storage.get(shellCache).delete(sw.key(file));
    sw.network.set(file, new Response("mixed version"));
    const url = file === "index.html" ? "?page=tripo-motion" : file;
    const mode = file === "index.html" ? "navigate" : "cors";
    assert.equal((await sw.fetch(url, mode)).status, 503);
    assert.equal(sw.requests.at(-1), sw.key(file + "?v=old"));
    sw.network.set(file, new Response(entries[file]));
    assert.equal(await (await sw.fetch(url, mode)).text(), entries[file]);
  }
});

test("install rejects wrong build metadata or wrong shell bytes and keeps other versions", async () => {
  const sw = worker();
  sw.storage.set("b3g-_Blender_3D_Gallery_-shell-retained", new Map());
  sw.network.set("build-info.json", Response.json({ build: "new" }));
  await assert.rejects(sw.install(), /Build identity mismatch/);
  sw.network.set("build-info.json", Response.json({ build }));
  sw.network.set("index.html", new Response("<title>Mixed</title>"));
  await assert.rejects(sw.install(), /Resource identity mismatch/);
  assert.deepEqual([...sw.storage.keys()], ["b3g-_Blender_3D_Gallery_-shell-retained"]);
});
