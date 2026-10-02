// Santorini service worker: keeps the page and saved audio on the phone.
// The page lives in a versioned cache (build.py stamps VERSION); audio lives in its own
// unversioned cache so a page update never throws away downloaded clips.
const VERSION = '__VERSION__';
const SHELL = 'santorini-shell-' + VERSION;
const AUDIO = 'santorini-audio';
const SHELL_FILES = ['./', 'index.html', 'manifest.webmanifest', 'icon-180.png', 'icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(SHELL_FILES.map(f => new Request(f, {cache: 'reload'})))).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(k => k.startsWith('santorini-shell-') && k !== SHELL).map(k => caches.delete(k))
  )).then(() => self.clients.claim()));
});

// Safari asks for audio in byte ranges and will not play a plain 200 in reply,
// so cut the saved file to the requested range and answer 206.
async function ranged(req, res) {
  const range = req.headers.get('range');
  const blob = await res.blob();
  const type = res.headers.get('content-type') || 'audio/mpeg';
  const size = blob.size;
  if (!range) return new Response(blob, {status: 200, headers: {'Content-Type': type, 'Content-Length': String(size), 'Accept-Ranges': 'bytes'}});
  const m = /bytes=(\d*)-(\d*)/.exec(range);
  let start = m && m[1] !== '' ? parseInt(m[1], 10) : NaN;
  let end = m && m[2] !== '' ? parseInt(m[2], 10) : NaN;
  if (isNaN(start)) { start = Math.max(0, size - (isNaN(end) ? size : end)); end = size - 1; }
  if (isNaN(end) || end >= size) end = size - 1;
  if (start >= size || start > end) return new Response(null, {status: 416, headers: {'Content-Range': `bytes */${size}`}});
  return new Response(blob.slice(start, end + 1, type), {status: 206, headers: {
    'Content-Type': type, 'Content-Length': String(end - start + 1),
    'Content-Range': `bytes ${start}-${end}/${size}`, 'Accept-Ranges': 'bytes'}});
}

async function audio(req) {
  const hit = await caches.match(req.url, {cacheName: AUDIO, ignoreSearch: true});
  return hit ? ranged(req, hit) : fetch(req);
}

// The page: answer from the phone at once, refresh the copy in the background when there is signal.
async function shell(req, event) {
  const cache = await caches.open(SHELL);
  const hit = await cache.match(req, {ignoreSearch: true});
  const refresh = fetch(req).then(res => { if (res.ok) cache.put(req, res.clone()); return res; });
  if (hit) { event.waitUntil(refresh.catch(() => {})); return hit; }
  return refresh;
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url), base = new URL(self.registration.scope);
  if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname)) return;
  const rel = url.pathname.slice(base.pathname.length);
  e.respondWith(/^audio\/.+\.mp3$/.test(rel) ? audio(req) : shell(req, e));
});
