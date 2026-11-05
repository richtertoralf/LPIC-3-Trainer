/* Service worker: static assets cache-first, visited pages network-first with cache fallback. */
var VERSION = "lpic3-v4";
var STATIC = ["/static/app.css", "/static/app.js", "/static/icon.svg", "/static/icon-192.png", "/offline", "/manifest.webmanifest"];

self.addEventListener("install", function (event) {
  event.waitUntil(caches.open(VERSION).then(function (cache) { return cache.addAll(STATIC); }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (event) {
  event.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== VERSION; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener("fetch", function (event) {
  var req = event.request;
  if (req.method !== "GET") { return; }
  var url = new URL(req.url);
  if (url.origin !== self.location.origin) { return; }
  if (url.pathname.startsWith("/api/") || url.pathname === "/health" || url.pathname.startsWith("/admin")) { return; }

  if (url.pathname.startsWith("/static/")) {
    event.respondWith(caches.match(req).then(function (hit) {
      return hit || fetch(req).then(function (res) {
        var copy = res.clone();
        caches.open(VERSION).then(function (c) { c.put(req, copy); });
        return res;
      });
    }));
    return;
  }

  event.respondWith(fetch(req).then(function (res) {
    if (res.ok && res.type === "basic") {
      var copy = res.clone();
      caches.open(VERSION).then(function (c) { c.put(req, copy); });
    }
    return res;
  }).catch(function () {
    return caches.match(req).then(function (hit) { return hit || caches.match("/offline"); });
  }));
});
