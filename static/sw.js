// Service worker for De-Influence AI — makes the dashboard installable AND offline-capable.
//
// Strategy:
//   * App shell (HTML, CSS-in-HTML, manifest, icon) is precached on install, so the app
//     opens with no network - like a downloaded app.
//   * GET /api/products and /api/evaluation use "stale-while-revalidate": serve the cached
//     copy instantly (works offline), refresh in the background when online.
//   * POST endpoints (/api/scan, /api/check-link, ...) need the server, so when offline they
//     fail gracefully and the page uses the locally stored scan history.
//
// Bump CACHE whenever shell assets change so old caches are cleared.
const CACHE = "de-influence-v6";

const SHELL = [
  "/",
  "/static/app.css",
  "/static/app.js",
  "/static/manifest.webmanifest",
  "/static/icon.svg",
  "/api/products",
  "/api/evaluation",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle same-origin GETs; let everything else (POSTs) hit the network.
  if (request.method !== "GET" || url.origin !== self.location.origin) return;

  // Read-only API: stale-while-revalidate so the dashboard works offline.
  if (url.pathname === "/api/products" || url.pathname === "/api/evaluation") {
    event.respondWith(
      caches.open(CACHE).then(async (cache) => {
        const cached = await cache.match(request);
        const network = fetch(request)
          .then((res) => {
            if (res && res.ok) cache.put(request, res.clone());
            return res;
          })
          .catch(() => cached);
        return cached || network;
      })
    );
    return;
  }

  // App shell + static assets: cache-first, fall back to network, then to the cached root.
  event.respondWith(
    caches.match(request).then(
      (hit) => hit || fetch(request).catch(() => caches.match("/"))
    )
  );
});
