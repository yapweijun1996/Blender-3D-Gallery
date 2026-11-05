const BUILD = __BUILD__,
  SHELL = __SHELL__,
  PACK = __PACK__;
const SCOPE = self.registration.scope,
  PREFIX = "b3g-" + new URL(SCOPE).pathname.replace(/[^a-z0-9]/gi, "_") + "-",
  SHELL_CACHE = PREFIX + "shell-" + BUILD,
  PACK_CACHE = PREFIX + "game-" + BUILD;
const absolute = (url) => new URL(url, SCOPE).href;
const marker = absolute("__game-pack-ready__");
const sha = async (buffer) =>
  [...new Uint8Array(await crypto.subtle.digest("SHA-256", buffer))]
    .map((n) => n.toString(16).padStart(2, "0"))
    .join("");
async function verified(entry) {
  const url = new URL(entry.url, SCOPE);
  url.searchParams.set("v", BUILD);
  const response = await fetch(url, { cache: "reload" });
  if (!response.ok) throw new Error("Resource unavailable");
  const bytes = await response.arrayBuffer();
  if (bytes.byteLength !== entry.bytes || (await sha(bytes)) !== entry.sha256)
    throw new Error("Resource identity mismatch");
  if (
    entry.url.endsWith(".glb") &&
    new TextDecoder().decode(bytes.slice(0, 4)) !== "glTF"
  )
    throw new Error("Invalid GLB");
  return new Response(bytes, { status: 200, headers: response.headers });
}
self.addEventListener("install", (event) =>
  event.waitUntil(
    (async () => {
      try {
        const response = await fetch(
          absolute("build-info.json") + "?v=" + BUILD,
          { cache: "reload" },
        );
        if (!response.ok || (await response.json()).build !== BUILD)
          throw new Error("Build identity mismatch");
        const cache = await caches.open(SHELL_CACHE);
        for (const entry of SHELL)
          await cache.put(absolute(entry.url), await verified(entry));
      } catch (e) {
        await caches.delete(SHELL_CACHE);
        throw e;
      }
    })(),
  ),
);
// Retention exception: an old/suspended tab can still request its hashed modules,
// and the last complete pack may belong to an older build after a failed update.
// CacheStorage has no durable proof that either is unused. Retain complete scoped
// builds rather than deleting by cache count; only each preparation job deletes
// its own temporary candidate. Users may clear site storage explicitly.
async function packReady(name = PACK_CACHE) {
  const cache = await caches.open(name);
  if (!(await cache.match(marker)) || PACK.files.length !== 18) return false;
  for (const entry of PACK.files)
    if (!(await cache.match(absolute(entry.url)))) return false;
  return true;
}
let preparing = null;
async function prepareGame(progress) {
  // An already verified pack is usable even when this request is made offline.
  if (await packReady()) return { ok: true, ready: true, build: BUILD };
  if (preparing) return preparing;
  preparing = (async () => {
    const candidate = PACK_CACHE + "-candidate-" + crypto.randomUUID();
    try {
      const cache = await caches.open(candidate);
      let count = 0,
        index = 0;
      const results = await Promise.allSettled(
        Array.from({ length: 3 }, async () => {
          while (index < PACK.files.length) {
            const entry = PACK.files[index++];
            await cache.put(absolute(entry.url), await verified(entry));
            progress({ progress: ++count, total: PACK.files.length });
          }
        }),
      );
      if (results.some((r) => r.status === "rejected"))
        throw new Error("Incomplete pack");
      await cache.put(
        marker,
        new Response(JSON.stringify({ build: BUILD, complete: true })),
      );
      if (!(await packReady(candidate))) throw new Error("Incomplete pack");
      const published = await caches.open(PACK_CACHE);
      for (const entry of PACK.files)
        await published.put(
          absolute(entry.url),
          await cache.match(absolute(entry.url)),
        );
      await published.put(marker, await cache.match(marker));
      return { ok: true, ready: await packReady(), build: BUILD };
    } catch {
      return {
        ok: false,
        error:
          "Offline preparation failed. Your previously saved pack is preserved. Reconnect and retry.",
      };
    } finally {
      await caches.delete(candidate);
      preparing = null;
    }
  })();
  return preparing;
}
const challenges = new Map(),
  activations = new Map();
self.addEventListener("message", (event) => {
  if (event.data?.type === "CANCEL_UPDATE") {
    const activation = activations.get(event.data.activationId);
    if (activation && activation.source === event.source?.id)
      activation.cancelled = true;
    return;
  }
  if (event.data?.type === "UPDATE_READY_REPLY") {
    const challenge = challenges.get(event.data.challenge);
    if (challenge && event.source?.id)
      challenge.answers.set(
        event.source.id,
        event.data.ready === true && event.data.protocol === 2,
      );
    return;
  }
  const port = event.ports[0];
  if (!port) return;
  const reply = (message) => {
    try {
      port.postMessage(message);
    } catch {
      /* Requester closed. */
    }
  };
  if (event.data?.type === "PACK_STATUS") {
    event.waitUntil(
      packReady().then((ready) => reply({ ok: true, ready, build: BUILD })),
    );
    return;
  }
  if (event.data?.type === "CACHE_GAME") {
    event.waitUntil(prepareGame(reply).then(reply));
    return;
  }
  if (event.data?.type === "ACTIVATE_UPDATE") {
    event.waitUntil(
      (async () => {
        const activationId = event.data.activationId;
        if (
          typeof activationId !== "string" ||
          !event.source?.id ||
          !Number.isFinite(event.data.expiresAt)
        ) {
          reply({
            ok: false,
            error:
              "This tab uses an older update interface. Save your turn, then close all gallery tabs and reopen the gallery.",
          });
          return;
        }
        const activation = { source: event.source.id, cancelled: false };
        activations.set(activationId, activation);
        const deadline = Math.min(event.data.expiresAt, Date.now() + 15000);
        const windows = async () =>
          (
            await self.clients.matchAll({
              type: "window",
              includeUncontrolled: true,
            })
          ).filter((client) => client.url.startsWith(SCOPE));
        let clients = [];
        const id = crypto.randomUUID(),
          answers = new Map();
        const notify = (client, message) => {
          try {
            client.postMessage(message);
          } catch {
            /* Tab closed. */
          }
        };
        challenges.set(id, { answers });
        let accepted = false;
        try {
          clients = await windows();
          for (const client of clients)
            notify(client, { type: "CAN_UPDATE", challenge: id });
          await new Promise((resolve) => setTimeout(resolve, 1200));
          const current = await windows();
          const original = new Set(clients.map((client) => client.id));
          if (
            activation.cancelled ||
            Date.now() >= deadline ||
            !current.some((client) => client.id === activation.source)
          )
            throw new Error(
              "Update request expired. Your current version is preserved. Retry.",
            );
          if (
            current.some(
              (client) =>
                !original.has(client.id) || answers.get(client.id) !== true,
            )
          )
            throw new Error(
              "Another tab is playing or is not ready. Finish or close it, then retry.",
            );
          await self.skipWaiting();
          accepted = true;
          reply({ ok: true });
        } catch (error) {
          reply({
            ok: false,
            error: error.message || "Update could not activate. Retry.",
          });
        } finally {
          for (const client of clients)
            notify(client, {
              type: "UPDATE_DECISION",
              challenge: id,
              accepted,
            });
          challenges.delete(id);
          activations.delete(activationId);
        }
      })(),
    );
  }
});
self.addEventListener("fetch", (event) => {
  const request = event.request,
    url = new URL(request.url);
  if (
    request.method !== "GET" ||
    !request.url.startsWith(SCOPE) ||
    url.origin !== self.location.origin
  )
    return;
  if (request.mode === "navigate") {
    event.respondWith(
      (async () => {
        const cache = await caches.open(SHELL_CACHE);
        return (await cache.match(absolute("index.html"))) || fetch(request);
      })(),
    );
    return;
  }
  event.respondWith(
    (async () => {
      const key = url.origin + url.pathname;
      for (const name of [SHELL_CACHE, PACK_CACHE]) {
        const hit = await (await caches.open(name)).match(key);
        if (hit) return hit;
      }
      // Hashed resources used by an older live tab may still exist in a retained scoped cache.
      if (/\.[a-z0-9]+$/i.test(url.pathname))
        for (const name of await caches.keys()) {
          if (
            !name.startsWith(PREFIX) ||
            name.includes("-candidate-") ||
            name === SHELL_CACHE ||
            name === PACK_CACHE
          )
            continue;
          const hit = await (await caches.open(name)).match(key);
          if (hit) return hit;
        }
      try {
        return await fetch(request);
      } catch {
        return new Response("Resource is not available offline", {
          status: 503,
          headers: { "Content-Type": "text/plain" },
        });
      }
    })(),
  );
});
