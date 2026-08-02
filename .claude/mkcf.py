#!/usr/bin/env python3
"""Build cftest.html from the merged cf build with the Worker stubbed in-memory.

The real Worker is live, but writing to Marilyn's collection to test a UI change
is not on. This intercepts window.fetch for the WORKER_URL origin and serves the
same contract: GET/PUT /s/<id> for the document, PUT/GET /s/<id>/img/<name>.
"""
import json, pathlib, re

SRC = pathlib.Path(__file__).parent / 'merged.html'
OUT = pathlib.Path(__file__).parent / 'cftest.html'

html = SRC.read_text()

NOTES = [
  "explainer is 32pt Geist Medium -10px", "",
  "Malaysian travel guides, mostly Sabah and Johor. Good reference for how they stack the "
  "caption over a full-bleed photo — the type is always bottom-left and never centred, which "
  "is why it reads as editorial rather than as a poster. Worth stealing for the next deck.",
  "brazilian editorial, strong afro hair styling",
  "two lines exactly here so nothing collapses at all",
  "ceramics + raw plaster",
  "Screenshotted for the grid rhythm: three portrait, one landscape, repeat. Never breaks.",
  "", "muted palette, lots of paper texture",
  "The bio line does a lot of work here — four short clauses separated by slashes, then a "
  "star. Compact and legible even at thumbnail size.",
  "one-off", "type specimen account, weekly posts",
  "interiors, warm neutrals, no people in frame ever",
  "colour study — six posts, one hue each", "very short",
]
FOLDERS = ["Inbox", "Design", "Art", "One-off", "Typography", "Interiors"]
USERS = ["kiakia.places", "antulimaa", "studio.mono", "form.and.field", "noon.archive",
         "paper.pulp", "atlas.of.rooms", "slow.press", "grain.and.grid", "the.plaster.works",
         "second.season", "field.notes", "long.username.that.wraps.around", "m", "quiet.objects"]

folders = [{'id': ('demo_inbox' if i == 0 else f'demo_f{i}'), 'name': n, 'order': i,
            'isCollapsed': False} for i, n in enumerate(FOLDERS)]
cards, cid = [], 1
for fi, n in enumerate([5, 4, 2, 1, 2, 1]):
    for _ in range(n):
        cards.append({
            'id': 1000 + cid,
            'username': USERS[(cid - 1) % len(USERS)],
            'notes': NOTES[(cid - 1) % len(NOTES)],
            'link': 'https://instagram.com/' + USERS[(cid - 1) % len(USERS)],
            'imagePath': 'demo/shot%d.png' % (((cid - 1) % 6) + 1),
            'folderId': folders[fi]['id'],
            'order': -(1000 + cid),
            'createdAt': '2026-07-%02dT10:00:00Z' % (28 - (cid % 20)),
            'suggestions': [], 'deletedAt': None,
        })
        cid += 1

DOC = {'folders': folders, 'cards': cards, 'etag': 'w/"stub-1"'}

STUB = """
<script>
// --- WORKER STUB (local only) -------------------------------------------------
(function () {
  const ORIGIN = 'https://deposits.nnnephirale.workers.dev';
  let doc = %s;
  let etagN = 1;
  const blobs = {};                       // imagePath -> object URL
  const J = (o, status = 200, headers = {}) =>
      new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json', ...headers } });
  const real = window.fetch.bind(window);

  window.fetch = async function (input, init = {}) {
    const url = typeof input === 'string' ? input : input.url;
    if (!url.startsWith(ORIGIN)) return real(input, init);
    await new Promise(r => setTimeout(r, 60));            // a little latency, like the real thing
    const path = decodeURI(url.slice(ORIGIN.length));
    const method = (init.method || 'GET').toUpperCase();
    const img = path.match(/^\\/s\\/([^/]+)\\/img\\/(.+)$/);

    if (img) {
      const key = decodeURIComponent(img[1]) + '/' + decodeURIComponent(img[2]);
      if (method === 'PUT') {
        blobs[key] = URL.createObjectURL(init.body);
        return J({ ok: true, path: key });
      }
      const local = blobs[key] || ('/' + key.split('/').pop());
      return real(local);
    }
    if (path.startsWith('/s/')) {
      if (method === 'GET') return J({ ...doc, etag: doc.etag });
      if (method === 'PUT') {
        const ifMatch = (init.headers || {})['if-match'];
        if (ifMatch && ifMatch !== doc.etag) return J({ error: 'conflict' }, 412);
        const body = JSON.parse(init.body);
        doc = { ...body, etag: 'w/"stub-' + (++etagN) + '"' };
        window.__DOC__ = doc;
        return J({ etag: doc.etag });
      }
    }
    return J({ error: 'not found' }, 404);
  };
  window.__DOC__ = doc;
  window.__BLOBS__ = blobs;
  try { localStorage.setItem('ssaved_worker_secret', 'stub-key'); } catch (e) {}
})();
</script>
""" % json.dumps(DOC)

# Inject before the app's own <script> so the stub is installed first.
marker = '    <script>\n        // --- CLOUD CONFIG'
assert marker in html, 'app script marker not found'
html = html.replace(marker, STUB + marker, 1)


# <img src> goes straight to the network — window.fetch never sees it — so the
# stub also has to redirect image URLs to the local files.
html = html.replace('</body>', """<script>
window.getPublicImageUrl = function (path) {
  if (!path) return '';
  return window.__BLOBS__[path] || ('/' + String(path).split('/').pop());
};
</script>
</body>""")

OUT.write_text(html)
print('wrote', OUT, len(html), 'bytes')
