#!/usr/bin/env python3
"""Build scratchpad/test.html from index.html with an in-memory Supabase stub.

The real project is 402 (exceed_cached_egress_quota), so every read/write is
faked locally. Images are served from this same directory by the python http
server, so getPublicImageUrl is patched to return a relative path.
"""
import re, pathlib, shutil

SRC = pathlib.Path('/Users/imac/Documents/2026/01_VIBECODED/03_SSAVED/index.html')
OUT = pathlib.Path(__file__).parent / 'test.html'

html = SRC.read_text()

# Drop the real supabase CDN script; the stub takes its place.
html = html.replace(
    '<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>',
    '<script>%s</script>' % '__STUB__')

NOTES = [
  "explainer is 32pt Geist Medium -10px",
  "",
  "Malaysian travel guides, mostly Sabah and Johor. Good reference for how they stack the caption over a full-bleed photo — the type is always bottom-left and never centred, which is why it reads as editorial rather than as a poster. Worth stealing for the next deck.",
  "brazilian editorial, strong afro hair styling",
  "two lines exactly here so nothing collapses at all",
  "ceramics + raw plaster",
  "Screenshotted for the grid rhythm: three portrait, one landscape, repeat. Never breaks.",
  "",
  "muted palette, lots of paper texture",
  "The bio line does a lot of work here — four short clauses separated by slashes, then a star. Compact and legible even at thumbnail size.",
  "one-off",
  "type specimen account, weekly posts",
  "interiors, warm neutrals, no people in frame ever",
  "colour study — six posts, one hue each",
  "very short",
]

FOLDERS = ["Inbox", "Design", "Art", "One-off", "Typography", "Interiors"]
USERS = ["kiakia.places", "antulimaa", "studio.mono", "form.and.field",
         "noon.archive", "paper.pulp", "atlas.of.rooms", "slow.press",
         "grain.and.grid", "the.plaster.works", "second.season", "field.notes",
         "long.username.that.wraps.around", "m", "quiet.objects"]

cards = []
cid = 1
counts = [5, 4, 2, 1, 2, 1]
for fi, n in enumerate(counts):
    for k in range(n):
        cards.append(dict(
            id=1000 + cid,
            collection_id='demo',
            username=USERS[(cid - 1) % len(USERS)],
            notes=NOTES[(cid - 1) % len(NOTES)],
            link='https://instagram.com/' + USERS[(cid - 1) % len(USERS)],
            image_path='shot%d.png' % (((cid - 1) % 6) + 1),
            folder_id='demo_f%d' % fi,
            order=-(1000 + cid),
            suggestions=[],
            deleted_at=None,
            created_at='2026-07-%02dT10:00:00Z' % (28 - (cid % 20)),
        ))
        cid += 1

import json
DATA = dict(
    collections=[{'id': 'demo'}],
    folders=[{'id': 'demo_f%d' % i, 'collection_id': 'demo', 'name': n,
              'order': i, 'is_collapsed': False} for i, n in enumerate(FOLDERS)],
    cards=cards,
)
# folder 0 must be the inbox id the app expects
DATA['folders'][0]['id'] = 'demo_inbox'
for c in DATA['cards']:
    if c['folder_id'] == 'demo_f0':
        c['folder_id'] = 'demo_inbox'

STUB = """
window.__DB__ = %s;
window.__BLOBS__ = {};
(function(){
  const D = window.__DB__;
  function match(row, filters){
    return filters.every(([k,op,v]) => {
      if (op==='eq') return String(row[k]) === String(v);
      if (op==='in') return v.map(String).includes(String(row[k]));
      if (op==='notnull') return row[k] != null;
      if (op==='lt') return row[k] != null && row[k] < v;
      return true;
    });
  }
  function run(s){
    const rows = D[s.table] || (D[s.table] = []);
    if (s.op === 'select'){
      let out = rows.filter(r => match(r, s.filters)).map(r => JSON.parse(JSON.stringify(r)));
      if (s.single){
        if (out.length !== 1) return { data:null, error:{ code:'PGRST116', message:'no rows' } };
        return { data: out[0], error:null };
      }
      return { data: out, error:null };
    }
    const vals = Array.isArray(s.val) ? s.val : [s.val];
    if (s.op === 'insert'){ vals.forEach(v => rows.push(JSON.parse(JSON.stringify(v)))); return { data:vals, error:null }; }
    if (s.op === 'upsert'){
      vals.forEach(v => { const i = rows.findIndex(r => String(r.id)===String(v.id));
        if (i>=0) rows[i] = Object.assign({}, rows[i], v); else rows.push(JSON.parse(JSON.stringify(v))); });
      return { data:vals, error:null };
    }
    if (s.op === 'update'){
      rows.filter(r => match(r, s.filters)).forEach(r => Object.assign(r, s.val));
      return { data:null, error:null };
    }
    if (s.op === 'delete'){
      for (let i = rows.length-1; i>=0; i--) if (match(rows[i], s.filters)) rows.splice(i,1);
      return { data:null, error:null };
    }
    return { data:null, error:null };
  }
  function table(name){
    const s = { table:name, filters:[], op:'select', single:false, val:null };
    const api = {
      select(){ s.op='select'; return api; },
      insert(v){ s.op='insert'; s.val=v; return api; },
      upsert(v){ s.op='upsert'; s.val=v; return api; },
      update(v){ s.op='update'; s.val=v; return api; },
      delete(){ s.op='delete'; return api; },
      eq(k,v){ s.filters.push([k,'eq',v]); return api; },
      in(k,v){ s.filters.push([k,'in',v]); return api; },
      not(k,_o,_v){ s.filters.push([k,'notnull']); return api; },
      lt(k,v){ s.filters.push([k,'lt',v]); return api; },
      order(){ return api; },
      limit(){ return api; },
      single(){ s.single=true; return api; },
      then(res, rej){ return new Promise(r => setTimeout(() => r(run(s)), 40)).then(res, rej); }
    };
    return api;
  }
  const storage = { from(){ return {
      upload(path, file){ window.__BLOBS__[path] = URL.createObjectURL(file);
        return new Promise(r => setTimeout(() => r({ data:{ path }, error:null }), 300)); },
      remove(){ return Promise.resolve({ data:null, error:null }); }
    }; } };
  window.supabase = { createClient(){ return { from: table, storage }; } };
})();
""" % json.dumps(DATA)

html = html.replace('__STUB__', STUB)

# Patch getPublicImageUrl AFTER the app script so images resolve locally.
html = html.replace('</body>', """<script>
window.getPublicImageUrl = function(p){
  if (!p) return '';
  return window.__BLOBS__[p] || p;
};
</script>
</body>""")

OUT.write_text(html)
for i in range(1, 7):
    pass
print('wrote', OUT, len(html), 'bytes')
