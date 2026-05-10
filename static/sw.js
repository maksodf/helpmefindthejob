/* DirectJob Scout — service worker.
 *
 * Network-first for /api/*, cache-first for the static app shell so the
 * UI renders instantly on repeat visits and degrades to "you are offline"
 * messaging when the server is unreachable. The cache version is bumped
 * by `CACHE_VERSION` below — change it on every deploy that touches the
 * app shell so old clients pick up the new bundle.
 */
const CACHE_VERSION = "v0.12.0";
const SHELL_CACHE = `directjob-shell-${CACHE_VERSION}`;
const SHELL_PATHS = [
  "/",
  "/index.html",
  "/app.js",
  "/styles.css",
  "/manifest.webmanifest",
  "/icons/icon.svg",
  "/i18n/en.json",
  "/i18n/de.json",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_PATHS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key.startsWith("directjob-shell-") && key !== SHELL_CACHE)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("push", (event) => {
  let data = { title: "DirectJob Scout", body: "" };
  if (event.data) {
    try { data = Object.assign(data, event.data.json()); }
    catch (_) { data.body = event.data.text(); }
  }
  event.waitUntil(self.registration.showNotification(data.title, {
    body: data.body || "",
    icon: data.icon || "/icons/icon.svg",
    badge: data.icon || "/icons/icon.svg",
    data: { url: data.url || "/" },
  }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if (client.url.includes(self.location.origin) && "focus" in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      if (self.clients.openWindow) return self.clients.openWindow(url);
    })
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Always go to network for API calls; never cache them.
  if (url.pathname.startsWith("/api/")) return;

  // Cache-first for the app shell + i18n bundles.
  event.respondWith(
    caches.open(SHELL_CACHE).then(async (cache) => {
      const cached = await cache.match(request);
      if (cached) {
        // Background-revalidate so future loads get the fresh bytes.
        fetch(request).then((response) => {
          if (response && response.ok) cache.put(request, response.clone());
        }).catch(() => {});
        return cached;
      }
      try {
        const response = await fetch(request);
        if (response && response.ok) cache.put(request, response.clone());
        return response;
      } catch (error) {
        const fallback = await cache.match("/index.html");
        return fallback || new Response("offline", { status: 503, statusText: "Offline" });
      }
    })
  );
});
