import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import { runInNewContext } from "node:vm";

const template = await readFile(new URL("../src/pwa/sw-template.js", import.meta.url), "utf8");
const scope = "https://gallery.test/Blender-3D-Gallery/";
const build = "old";
const shellCache = "b3g-_Blender_3D_Gallery_-shell-old";
const packCache = "b3g-_Blender_3D_Gallery_-game-old";
const marker = "__game-pack-ready__";
const stateCache = "b3g-_Blender_3D_Gallery_-state";
const cardAware = "__gallery-card-aware__";
const card = "christmas-card/index.html?test=a%20b#to=Riley&msg=Happy+holidays";
const entries = { "index.html": "<title>Old</title>", "assets/page-OldHash1.js": "export const build = 'old';" };
const shell = await Promise.all(Object.entries(entries).map(async ([url, body]) => {
  const bytes = new TextEncoder().encode(body);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return { url, bytes: bytes.length, sha256: Buffer.from(hash).toString("hex") };
}));

function worker(pack = { build, files: [] }, { active, windows = [], storage = new Map() } = {}) {
  const handlers = new Map(), messages = [], requests = [];
  const skips = [], navigations = [];
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
    async match(url, { cacheName } = {}) {
      if (cacheName) return storage.get(cacheName)?.get(url)?.clone();
      return [...storage.values()].find(cache => cache.has(url))?.get(url).clone();
    },
    async keys() { return [...storage.keys()]; },
    async delete(name) { return storage.delete(name); },
  };
  runInNewContext(template
    .replace("__BUILD__", JSON.stringify(build))
    .replace("__SHELL__", JSON.stringify(shell))
    .replace("__PACK__", JSON.stringify(pack)), {
    URL, TextDecoder, Uint8Array, Response, crypto, caches,
    self: {
      registration: { scope, active },
      location: new URL(scope),
      addEventListener(type, handler) {
        if (type === "activate") assert.ok(!handlers.has(type), "Only one activate listener");
        handlers.set(type, handler);
      },
      clients: {
        async get() { return { postMessage: (message) => messages.push(message.type) }; },
        async matchAll({ includeUncontrolled }) {
          return windows.filter(window => includeUncontrolled || window.galleryControlled)
            .map(({ url }) => ({ url: key(url), async navigate(target) { navigations.push(target); } }));
        },
      },
      async skipWaiting() { skips.push([...storage.get(shellCache).keys()]); },
    },
    async fetch(input) {
      const url = new URL(input.url ?? input);
      requests.push(url.href);
      const file = url.pathname.slice(new URL(scope).pathname.length);
      return network.get(file)?.clone() ?? new Response("Not found", { status: 404 });
    },
  });
  const lifecycle = (type) => {
    let result;
    handlers.get(type)({ waitUntil: (promise) => { result = promise; } });
    return result;
  };
  return {
    key, network, storage, messages, requests, skips, navigations,
    install: () => lifecycle("install"),
    activate: () => lifecycle("activate"),
    async message(type) {
      let result;
      const replies = [];
      handlers.get("message")({
        data: { type },
        ports: [{ postMessage: (reply) => replies.push(reply) }],
        waitUntil: (promise) => { result = promise; },
      });
      await result;
      return replies;
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
  const sw = worker(undefined, { active: {} });
  sw.storage.set("b3g-_Blender_3D_Gallery_-shell-retained", new Map());
  sw.network.set("build-info.json", Response.json({ build: "new" }));
  await assert.rejects(sw.install(), /Build identity mismatch/);
  sw.network.set("build-info.json", Response.json({ build }));
  sw.network.set("index.html", new Response("<title>Mixed</title>"));
  await assert.rejects(sw.install(), /Resource identity mismatch/);
  assert.deepEqual(sw.skips, []);
  assert.deepEqual([...sw.storage.keys()], ["b3g-_Blender_3D_Gallery_-shell-retained"]);
});

test("a legacy upgrade skips waiting after verification even without a card window", async () => {
  const sw = worker(undefined, { active: {}, windows: [{ url: "index.html", galleryControlled: true }] });
  sw.storage.set("card-cache", new Map([
    [sw.key("christmas-card/version.json"), Response.json({ build: "card" })],
  ]));
  sw.storage.set("sibling-gallery-state", new Map([[sw.key(cardAware), new Response()]]));
  const previousShell = new Map([[sw.key("index.html"), new Response("Legacy shell")]]);
  const previousPack = new Map([[sw.key(marker), new Response("Legacy pack")]]);
  sw.storage.set("b3g-_Blender_3D_Gallery_-shell-legacy", previousShell);
  sw.storage.set("b3g-_Blender_3D_Gallery_-game-legacy", previousPack);

  await sw.install();
  assert.deepEqual(sw.skips, [Object.keys(entries).map(sw.key)]);
  assert.ok(!sw.storage.has(stateCache), "Installation alone leaves the migration pending");
  await sw.activate();
  assert.ok(sw.storage.get(stateCache).has(sw.key(cardAware)));
  assert.deepEqual(sw.navigations, []);
  assert.equal(await previousShell.get(sw.key("index.html")).text(), "Legacy shell");
  assert.equal(await previousPack.get(sw.key(marker)).text(), "Legacy pack");
  assert.equal(sw.storage.get("b3g-_Blender_3D_Gallery_-shell-legacy"), previousShell);
  assert.equal(sw.storage.get("b3g-_Blender_3D_Gallery_-game-legacy"), previousPack);
});

test("first install activates normally and a later candidate leaves user approval in place", async () => {
  const sw = worker(undefined, { windows: [{ url: card }] });
  await sw.install();
  assert.deepEqual(sw.skips, []);
  await sw.activate();
  assert.deepEqual(sw.navigations, []);

  const next = worker(undefined, {
    active: {},
    storage: sw.storage,
    windows: [{ url: card, galleryControlled: true }],
  });
  await next.install();
  assert.deepEqual(next.skips, []);
  await next.activate();
  assert.deepEqual(next.navigations, []);
});

test("an install waits for an activating predecessor to record card awareness", async () => {
  let observeActivation, finishActivation;
  const observed = new Promise(resolve => { observeActivation = resolve; });
  const active = {
    state: "activating",
    addEventListener(type, listener) {
      assert.equal(type, "statechange");
      finishActivation = listener;
      observeActivation();
    },
  };
  const previous = worker();
  await previous.install();
  const next = worker(undefined, { active, storage: previous.storage });
  const installation = next.install();
  await observed;
  await previous.activate();
  active.state = "activated";
  finishActivation();
  await installation;
  assert.deepEqual(next.skips, []);
});

test("activation only navigates gallery-controlled card windows and removes the recovery query", async () => {
  const sw = worker(undefined, { active: {}, windows: [
    { url: card, galleryControlled: true },
    { url: "christmas-card/#healthy" },
    { url: "index.html", galleryControlled: true },
  ] });
  await sw.install();
  assert.deepEqual(sw.skips, [Object.keys(entries).map(sw.key)]);
  await sw.activate();
  const recovery = card.replace("#", "&__gallery_card_recovery=old#");
  assert.deepEqual(sw.navigations, [sw.key(recovery)]);
  const redirect = await sw.fetch(recovery.split("#")[0], "navigate");
  assert.equal(redirect.status, 302);
  assert.equal(redirect.headers.get("Location"), sw.key(card.split("#")[0]));
  assert.equal(sw.fetch(card, "navigate"), undefined);
  await sw.activate();
  assert.deepEqual(sw.navigations, [sw.key(recovery)]);
});

test("a two-file pack needs its completion marker and both files", async () => {
  const assets = { "assets/cue.glb": "glTFcue", "assets/table.glb": "glTFtable" };
  const files = await Promise.all(Object.entries(assets).map(async ([url, body]) => {
    const bytes = new TextEncoder().encode(body);
    const sha256 = Buffer.from(await crypto.subtle.digest("SHA-256", bytes)).toString("hex");
    return { id: url.split("/").at(-1).replace(".glb", ""), url, bytes: bytes.length, sha256 };
  }));
  const sw = worker({ build, files });
  for (const [file, body] of Object.entries(assets)) sw.network.set(file, new Response(body));
  const replies = await sw.message("CACHE_GAME");
  assert.deepEqual(replies.slice(0, -1).map(reply => [reply.progress, reply.total]), [[1, 2], [2, 2]]);
  assert.equal(replies.at(-1).ready, true);
  const cache = sw.storage.get(packCache);
  const savedMarker = cache.get(sw.key(marker));
  assert.deepEqual(await savedMarker.clone().json(), { build, complete: true });
  cache.delete(sw.key(marker));
  assert.equal((await sw.message("PACK_STATUS")).at(-1).ready, false);
  cache.set(sw.key(marker), savedMarker);
  cache.delete(sw.key(files[0].url));
  assert.equal((await sw.message("PACK_STATUS")).at(-1).ready, false);
});

test("an empty manifest or a manifest for another build cannot become ready", async () => {
  const gameFile = "assets/table.glb";
  for (const pack of [{ build, files: [] }, { build: "different", files: [{ id: "table", url: gameFile }] }]) {
    const sw = worker(pack);
    sw.storage.set(packCache, new Map([
      [sw.key(marker), Response.json({ build, complete: true })],
      [sw.key(gameFile), new Response("glTFtable")],
    ]));
    assert.equal((await sw.message("PACK_STATUS")).at(-1).ready, false);
    assert.equal((await sw.message("CACHE_GAME")).at(-1).ok, false);
    assert.deepEqual(sw.requests, []);
    assert.deepEqual([...sw.storage.keys()], [packCache]);
  }
});
