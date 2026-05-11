const CACHE = 'evofit-v1'
const STATIC_CACHE = 'evofit-static-v1'

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(STATIC_CACHE).then((c) => c.addAll([
      '/static/manifest.json',
      '/static/css/style.css',
      '/static/js/main.js',
    ]))
  )
  self.skipWaiting()
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((k) => k !== STATIC_CACHE).map((k) => caches.delete(k))
    ))
  )
  self.clients.claim()
})

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url)

  // Static assets: cache-first
  if (url.pathname.startsWith('/static/')) {
    e.respondWith(
      caches.match(e.request).then((r) => r || fetch(e.request))
    )
    return
  }

  // Navigation / HTML: network-first (always fresh for session)
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  )
})
