// The shell is cached so the app opens instantly and the list is readable with
// no signal. Playback is not cached and never could be — every episode streams
// from YouTube, so offline here means "browse what you have", not "listen".
//
// Bumping CACHE is how a deploy takes effect: an old worker serves its own
// copies until its name stops matching.
const CACHE = "podtv-v20";
const SHELL = [
  "./", "./index.html", "./manifest.webmanifest",
  "./icons/icon-192.png", "./icons/icon-512.png", "./icons/apple-touch-icon.png",
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;

  // The playlist AND the page itself are network-first.
  //
  // The page was cache-first at first, which meant a fix reached the phone only
  // on the SECOND reload — the new worker installs while the old one is still
  // answering, so the reload that fetches the fix still renders the old page.
  // That is a miserable way to ship anything, and it is indistinguishable from
  // the fix not working.
  if (url.pathname.endsWith("/playlist.json")
      || url.pathname.endsWith("/audio.json")
      || e.request.mode === "navigate"
      || url.pathname.endsWith("/index.html")
      || url.pathname.endsWith("/")) {
    e.respondWith(
      fetch(e.request)
        .then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r; })
        .catch(() => caches.match(e.request))
    );
    return;
  }

  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request)));
});
