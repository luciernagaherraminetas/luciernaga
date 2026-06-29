const CACHE_NAME = "luciernaga-v2";

const urlsToCache = [
  "/",
  "/static/manifest.json"
];

self.addEventListener("install", event => {
  self.skipWaiting();

  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(urlsToCache);
    })
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );

  self.clients.claim();
});

self.addEventListener("fetch", event => {
  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match(event.request);
    })
  );
});

// 🔔 PUSH NOTIFICATIONS
self.addEventListener("push", function(event) {

  let data = {};

  if (event.data) {
    data = event.data.json();
  }

  const title = data.title || "Luciérnaga";
  const options = {
    body: data.body || "Nuevo evento disponible",
    icon: "/static/icons/icon-512.png",
    badge: "/static/icons/icon-192.png",
    data: data.url || "/"
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// 📲 CLICK NOTIFICATION
self.addEventListener("notificationclick", function(event) {

  event.notification.close();

  fetch("/api/notificacion-abierta", {
    method: "POST"
  });

  event.waitUntil(
    clients.openWindow(event.notification.data)
  );

});
