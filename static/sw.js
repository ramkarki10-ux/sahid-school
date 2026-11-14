// Service Worker for Shahid Smriti Residential Secondary School PWA (Mobile & Desktop)
const CACHE_NAME = 'sahid-smriti-cache-v2';
const STATIC_PRECACHE = [
  '/',
  '/static/css/custom.css',
  '/static/images/logo_header.png',
  '/static/images/default_avatar.png',
  '/static/js/main.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_PRECACHE).catch(() => {});
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Only handle GET requests
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);

  // Bypass API endpoints and auth calls so dynamic data is always fresh
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/admin/api/')) {
    return;
  }

  // Cache-first runtime caching for images and static assets (instant mobile loading)
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then((cachedResponse) => {
        if (cachedResponse) {
          // Return cached asset immediately, optionally revalidate in background
          return cachedResponse;
        }
        return fetch(event.request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return networkResponse;
        }).catch(() => {
          if (event.request.destination === 'image' || url.pathname.match(/\.(jpg|jpeg|png|webp|svg)$/i)) {
            return caches.match('/static/images/default_avatar.png');
          }
        });
      })
    );
    return;
  }

  // Network-first with cache fallback for HTML pages
  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        return networkResponse;
      })
      .catch(() => {
        return caches.match(event.request);
      })
  );
});
