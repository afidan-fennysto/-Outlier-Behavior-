// Minimal service worker so the dashboard is an installable PWA.
// It caches the app shell so the "web app" can open from a phone home-screen icon,
// which is our prototype answer to reaching app-based shoppers without a browser extension.
const CACHE = "de-influence-v1";
const SHELL = ["/", "/static/manifest.webmanifest", "/static/icon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)));
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
  // Never cache API calls - always hit the network for fresh analysis.
  if (new URL(request.url).pathname.startsWith("/api/")) return;
  event.respondWith(
    caches.match(request).then((hit) => hit || fetch(request))
  );
});
