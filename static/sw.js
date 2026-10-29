// Service worker for De-Influence AI — installable PWA + offline support.
//
// Strategy (chosen to avoid the "blank page after an update" trap):
//   * Navigations (the HTML page) and the app code (app.js / app.css): NETWORK-FIRST.
//     When online you always get the latest code; offline you fall back to the cached copy.
//   * Read-only GET APIs (/api/products, /api/evaluation): stale-while-revalidate for offline.
//   * Other static assets (manifest, icon): cache-first.
//   * POSTs and cross-origin requests: pass straight through to the network.
//
// Bump CACHE whenever shell assets change so old caches are cleared on activate.
const CACHE = "de-influence-v10";

const PRECACHE = [
  "/",
  "/static/app.css",
  "/static/app.js",
  "/static/manifest.webmanifest",
  "/static/icon.svg",
];

// Paths served network-first so an update is picked up on the next online load.
const NETWORK_FIRST = ["/", "/static/app.js", "/static/app.css"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)).catch(() => {}));
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

async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  try {
    const res = await fetch(request);
    if (res && res.ok) cache.put(request, res.clone());
    return res;
  } catch {
    const cached = await cache.match(request);
    return cached || cache.match("/");
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  const network = fetch(request)
    .then((res) => { if (res && res.ok) cache.put(request, res.clone()); return res; })
    .catch(() => cached);
  return cached || network;
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== "GET" || url.origin !== self.location.origin) return;

  // Navigations (HTML) + app code -> network-first (always fresh when online).
  if (request.mode === "navigate" || NETWORK_FIRST.includes(url.pathname)) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Read-only APIs the dashboard needs offline -> stale-while-revalidate.
  if (url.pathname === "/api/products" || url.pathname === "/api/evaluation") {
    event.respondWith(staleWhileRevalidate(request));
    return;
  }

  // Everything else static (manifest, icon) -> cache-first.
  event.respondWith(
    caches.match(request).then((hit) => hit || fetch(request).catch(() => caches.match("/")))
  );
});
