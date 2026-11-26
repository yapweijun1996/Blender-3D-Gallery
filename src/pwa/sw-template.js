const BUILD = __BUILD__,
  SHELL = __SHELL__,
  PACK = __PACK__;
const SCOPE = self.registration.scope,
  PREFIX = "b3g-" + new URL(SCOPE).pathname.replace(/[^a-z0-9]/gi, "_") + "-",
  SHELL_CACHE = PREFIX + "shell-" + BUILD,
  PACK_CACHE = PREFIX + "game-" + BUILD;
const absolute = (url) => new URL(url, SCOPE).href;
const CARD_SCOPE = absolute("christmas-card/"),
  CARD_RECOVERY_QUERY = "__gallery_card_recovery=" + BUILD,
  GALLERY_STATE_CACHE = PREFIX + "state",
  CARD_AWARE = absolute("__gallery-card-aware__");
const shellEntries = new Map(SHELL.map((entry) => [absolute(entry.url), entry]));
const marker = absolute("__game-pack-ready__");
const packFiles = PACK.build === BUILD && Array.isArray(PACK.files) ? PACK.files : [];
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

        // An active card-aware worker may still be recording its marker.
        const active = self.registration.active;
        if (active?.state === "activating")
          await new Promise((resolve) =>
            active.addEventListener("statechange", resolve, { once: true }),
          );
        if (
          self.registration.active &&
          !(await caches.match(CARD_AWARE, { cacheName: GALLERY_STATE_CACHE }))
        )
          return self.skipWaiting();
      } catch (e) {
        await caches.delete(SHELL_CACHE);
        throw e;
      }
    })(),
  ),
);
self.addEventListener("activate", (event) =>
  event.waitUntil((async () => {
    const state = await caches.open(GALLERY_STATE_CACHE);
    if (await state.match(CARD_AWARE)) return;
    // Record activation so a superseded install cannot suppress the migration.
    await state.put(CARD_AWARE, new Response());
    // Only this gallery registration's clients take over. Leave card-controlled tabs alone.
    for (const client of await self.clients.matchAll({ type: "window" })) {
      if (!client.url.startsWith(CARD_SCOPE)) continue;
      const url = new URL(client.url);
      // Force a document load even when the original URL has a fragment.
      url.search += (url.search ? "&" : "?") + CARD_RECOVERY_QUERY;
      // The navigation's fetch waits for activation to finish.
      void client.navigate(url.href).catch(() => {});
    }
  })()),
);
// Retention exception: an old/suspended tab can still request its hashed modules,
// and the last complete pack may belong to an older build after a failed update.
// CacheStorage has no durable proof that either is unused. Retain complete scoped
// builds rather than deleting by cache count; only each preparation job deletes
// its own temporary candidate. Users may clear site storage explicitly.
async function packReady(name = PACK_CACHE) {
  if (packFiles.length === 0) return false;
  const cache = await caches.open(name);
  if (!(await cache.match(marker))) return false;
  for (const entry of packFiles)
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
      if (packFiles.length === 0) throw new Error("Incomplete pack");
      const cache = await caches.open(candidate);
      let count = 0,
        index = 0;
      const results = await Promise.allSettled(
        Array.from({ length: 3 }, async () => {
          while (index < packFiles.length) {
            const entry = packFiles[index++];
            await cache.put(absolute(entry.url), await verified(entry));
            progress({ progress: ++count, total: packFiles.length });
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
      for (const entry of packFiles)
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
  if (event.data?.type === "BUILD_INFO") {
    reply({ ok: true, build: BUILD });
    return;
  }
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
          ).filter((client) => client.url.startsWith(SCOPE) && !client.url.startsWith(CARD_SCOPE));
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
const unavailable = () =>
  new Response("Resource is not available offline", {
    status: 503,
    headers: { "Content-Type": "text/plain" },
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
  if (request.mode === "navigate" && url.href.startsWith(CARD_SCOPE)) {
    if (url.search === "?" + CARD_RECOVERY_QUERY || url.search.endsWith("&" + CARD_RECOVERY_QUERY)) {
      url.search = url.search.slice(0, -CARD_RECOVERY_QUERY.length - 1);
      // Redirects inherit the navigation's fragment if Location omits it.
      event.respondWith(Response.redirect(url.href));
    }
    return;
  }
  event.respondWith(
    (async () => {
      const key = request.mode === "navigate" ? absolute("index.html") : url.origin + url.pathname;
      const isAsset = key.startsWith(absolute("assets/"));
      const isCriticalAsset = isAsset && /\.(glb|js|css)$/.test(url.pathname);
      let response;
      try {
        const entry = shellEntries.get(key);
        if (entry) {
          const cached = await (await caches.open(SHELL_CACHE)).match(key);
          // An evicted shell entry can only be repaired with bytes for this worker.
          return cached ?? await verified(entry);
        }
        // Older live documents can still request their immutable Vite URLs.
        if (isAsset) {
          for (const name of [PACK_CACHE, ...(await caches.keys()).filter((name) =>
            name !== SHELL_CACHE && name !== PACK_CACHE &&
            (name.startsWith(PREFIX + "shell-") || name.startsWith(PREFIX + "game-")) &&
            !name.includes("-candidate-"),
          )]) {
            const hit = await (await caches.open(name)).match(key);
            if (hit) return hit;
          }
        }
        response = await fetch(request);
        if (isCriticalAsset && response.ok &&
            response.headers.get("Content-Type")?.startsWith("text/html"))
          response = unavailable();
      } catch {
        response = unavailable();
      }
      if (!response.ok && isCriticalAsset && event.clientId) {
        const client = await self.clients.get(event.clientId);
        client?.postMessage({ type: "RESOURCE_LOAD_FAILED" });
      }
      return response;
    })(),
  );
});
