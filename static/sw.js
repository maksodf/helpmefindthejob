/* DirectJob Scout — service worker.
 *
 * Strategy by resource class:
 *   - /api/*                — never cached; always network.
 *   - app shell (HTML/JS/CSS/manifest) — **network-first**, cache fallback
 *     only when offline. So every refresh lands the latest deploy.
 *   - icons / i18n / fonts  — cache-first (small, slow-changing assets).
 *
 * The previous build used cache-first for the shell with a manual
 * ``CACHE_VERSION`` bump per deploy — a stale-version trap that left
 * users on old JS until they bumped the file. Network-first fixes that
 * by default. We still cache the shell so the app loads under flaky
 * connectivity and offline reads work.
 */
const CACHE_VERSION = "v0.15.1";
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
  // Take over on first activate; don't wait for tabs to close.
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((key) => key.startsWith("directjob-shell-") && key !== SHELL_CACHE)
          .map((key) => caches.delete(key))
      );
      await self.clients.claim();
      // Notify every open tab that a new SW activated so they can reload
      // and pick up the new HTML / JS / CSS without a manual refresh.
      const clients = await self.clients.matchAll({ includeUncontrolled: true });
      for (const client of clients) {
        try { client.postMessage({ type: "sw-updated", version: CACHE_VERSION }); }
        catch (_) { /* ignore */ }
      }
    })()
  );
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

function isShellRequest(url) {
  if (url.pathname === "/") return true;
  if (SHELL_PATHS.includes(url.pathname)) return true;
  return /\.(?:html|js|css|webmanifest)$/i.test(url.pathname);
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Never cache API calls.
  if (url.pathname.startsWith("/api/")) return;

  // App shell: network-FIRST, cache fallback only on offline.
  if (isShellRequest(url)) {
    event.respondWith(
      (async () => {
        try {
          const fresh = await fetch(request);
          if (fresh && fresh.ok) {
            const cache = await caches.open(SHELL_CACHE);
            cache.put(request, fresh.clone());
          }
          return fresh;
        } catch (_) {
          const cached = await caches.match(request);
          if (cached) return cached;
          // Last-resort offline fallback for navigation requests.
          if (request.mode === "navigate") {
            const indexFallback = await caches.match("/index.html");
            if (indexFallback) return indexFallback;
          }
          return new Response("offline", { status: 503, statusText: "Offline" });
        }
      })()
    );
    return;
  }

  // Other static assets (icons, fonts, i18n bundles): cache-first.
  event.respondWith(
    caches.open(SHELL_CACHE).then(async (cache) => {
      const cached = await cache.match(request);
      if (cached) return cached;
      try {
        const fresh = await fetch(request);
        if (fresh && fresh.ok) cache.put(request, fresh.clone());
        return fresh;
      } catch (_) {
        return new Response("offline", { status: 503, statusText: "Offline" });
      }
    })
  );
});
