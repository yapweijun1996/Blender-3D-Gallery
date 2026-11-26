const VERSION = __VERSION__;
const FILES = __FILES__;
const ROOT = new URL('../', self.registration.scope);
const CACHE = 'christmas-card-' + new URL(self.registration.scope).pathname.replace(/[^a-z0-9]/gi, '_') + VERSION;
let allowUpdate;
let approved = false;
self.addEventListener('message', event => {
  if (event.data?.type === 'ACTIVATE') { approved = true; allowUpdate?.(); }
});
self.addEventListener('install', event => event.waitUntil((async () => {
  const cache = await caches.open(CACHE);
  try {
    for (const file of FILES) {
      const url = new URL(file, ROOT);
      const response = await fetch(url, {cache:'reload'});
      if (!response.ok) throw new Error('Offline resource unavailable: ' + file);
      await cache.put(url, response);
    }
  } catch (error) { await caches.delete(CACHE); throw error; }
  // Do not complete an upgrade installation without an explicit page action,
  // even if all old tabs close. First installation needs no approval.
  if (self.registration.active) {
    if (!approved) await new Promise(resolve => { allowUpdate = resolve; });
    await self.skipWaiting();
  }
})()));
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  const key = event.request.mode === 'navigate' ? new URL('christmas-card/index.html', ROOT) : new URL(url.pathname, url.origin);
  event.respondWith((async () => (await caches.open(CACHE)).match(key) || fetch(event.request))());
});
