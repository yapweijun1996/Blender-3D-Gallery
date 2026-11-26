const BUILD = __BUILD__;
const FILES = __FILES__;
const SCOPE = self.registration.scope;
const ROOT = new URL('../', SCOPE);
const SHELL = 'christmas-card/index.html';
const CACHE_PREFIX = 'christmas-card:' + encodeURIComponent(new URL(SCOPE).pathname) + ':';
const CACHE = CACHE_PREFIX + BUILD;
const LEGACY_PREFIX = 'christmas-card-' + new URL(SCOPE).pathname.replace(/[^a-z0-9]/gi, '_');
const isLegacyCache = name => name.startsWith(LEGACY_PREFIX) && /^[a-f0-9]{12}$/.test(name.slice(LEGACY_PREFIX.length));
const INSTALL_STATE = new URL('.install-state', SCOPE);
const MIGRATION_QUERY = 'christmas-card-reload=' + BUILD;

self.addEventListener('message', event => {
  if (event.data?.type === 'CARD_BUILD') event.source?.postMessage({type:'CARD_BUILD', build:BUILD});
});
self.addEventListener('install', event => event.waitUntil((async () => {
  // An install can start while its predecessor is still activating.
  const previous = (await caches.keys()).filter(name => name !== CACHE &&
    (name.startsWith(CACHE_PREFIX) || isLegacyCache(name)));
  const migrateLegacy = Boolean(self.registration.active && previous.some(isLegacyCache));
  const cache = await caches.open(CACHE);
  try {
    for (const file of FILES) {
      const url = new URL(file, ROOT);
      const response = await fetch(url, {cache:'reload'});
      if (!response.ok) throw new Error('Offline resource unavailable: ' + file);
      if (file === SHELL && !(await response.clone().text()).includes('data-build="' + BUILD + '"')) {
        throw new Error('Christmas card shell changed during installation');
      }
      await cache.put(url, response);
    }
    await cache.put(INSTALL_STATE, new Response(JSON.stringify({previous, migrateLegacy})));
  } catch (error) { await caches.delete(CACHE); throw error; }
  await self.skipWaiting();
})()));
self.addEventListener('activate', event => event.waitUntil((async () => {
  const cache = await caches.open(CACHE);
  const state = await cache.match(INSTALL_STATE);
  const {previous = [], migrateLegacy} = state ? await state.json() : {};
  await cache.delete(INSTALL_STATE);
  await Promise.all(previous.map(name => caches.delete(name)));
  await self.clients.claim();
  if (migrateLegacy) {
    // A legacy page may still be waiting for register() and miss controllerchange.
    for (const client of await self.clients.matchAll({type:'window'})) {
      if (!client.url.startsWith(SCOPE)) continue;
      const url = new URL(client.url);
      url.search += (url.search ? '&' : '?') + MIGRATION_QUERY;
      // A query change forces a document load even when the URL has a fragment.
      // The navigation's fetch must wait for activation, so don't await it here.
      void client.navigate(url.href).catch(() => {});
    }
  }
})()));
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  if (event.request.mode === 'navigate' && url.href.startsWith(SCOPE) &&
      (url.search === '?' + MIGRATION_QUERY || url.search.endsWith('&' + MIGRATION_QUERY))) {
    url.search = url.search.slice(0, -MIGRATION_QUERY.length - 1);
    event.respondWith(Response.redirect(url.href));
    return;
  }
  const key = event.request.mode === 'navigate' ? new URL(SHELL, ROOT) : new URL(url.pathname, url.origin);
  event.respondWith((async () => (await caches.match(key, {cacheName:CACHE})) || fetch(event.request))());
});
