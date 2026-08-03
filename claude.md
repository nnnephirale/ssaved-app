# SSaved App - Development Log

## ✅ /cf is the live build now — UI overhaul ported, rail motion fixed (Aug 2, 2026)

**Deploy target is `cf/index.html`, not the root.** Supabase is 402 until the billing
cycle turns over, so Marilyn moved the app to a Cloudflare Worker over R2 at
https://nnnephirale.github.io/ssaved-app/cf/?c=seasontwo. The root `index.html` is the
same UI on the dead Supabase backend — keep it in step, but **/cf is what ships**.

**How the port was done, because it will need doing again.** The Cloudflare delta is
small (381 lines, 45 hunks — it swaps `db.from()` for `cloudFetch`/`saveState` and adds
the write-key row); the UI overhaul is large (1749 lines). So the merge runs the UI as
the base and replays the backend onto it:

```
git merge-file -p <new-ui> <7facf75:index.html> <cf/index.html>
```

One conflict, always the same one: `renameFolder` — take the UI's `buildFolderRail()` +
`buildFolderNav()` repaint AND the CF `saveState({ immediate: true })`. Verify after with
`grep -c "supabase\|db\.from("` = 0 and the orphan-id / handler sweeps.

Local harness for the CF build: `.claude/mkcf.py` stubs `window.fetch` for the Worker
origin (GET/PUT `/s/<id>`, PUT/GET `/s/<id>/img/<name>`) so nothing touches her real
collection. **`<img src>` never goes through `window.fetch`** — the harness has to
override `getPublicImageUrl` separately or every card shows a broken-image icon.

### The rail "snapped back to Inbox" — two separate causes

1. **The one that mattered: a 48px gap belongs to no section.** `updateFolderProgress`
   picked the active folder with a containment test (`readLine >= top && readLine < top+h`).
   `#folderWrapper` is `gap-12`, so every time the read line crossed between two folders
   the test matched nothing, `activeIdx` stayed `-1`, and the fallback `activeIdx < 0 ? 0`
   lit **Inbox**. Harmless-looking near the top; near One-off/Typography the rail then
   scrolled ~300px home and back. Now: **the last folder whose top is above the read
   line** (`if (top <= readLine) activeIdx = Math.max(activeIdx, i)`), which is monotonic
   and has no holes. Verified by walking the page in 90px steps in both directions —
   6 transitions down, 6 up, zero backtracks.
2. **A tapped jump chased every folder it passed.** The spy re-resolves on every frame of
   a 0.9s scroll, so tapping "Typography" walked the rail through Design → Art → One-off.
   `railJumpTo` now pins the destination for the flight (released on arrival, on a 1600ms
   timeout, or on the user's own touch/wheel).

**Also in that pass:** `revealRailItem` used `scrollTo({behavior:'smooth'})`, which
restarts from a standstill every time it is re-issued — replaced with a rAF lerp
(`stepRailScroll`, factor 0.12) that curves toward a target it can move mid-flight.
`smoothScrollTo` now scales duration with distance (0.55–1.35s) and uses **cubic-out, not
expo-out** — expo dumps its movement into the first third, which is what read as "snappy".
And `scrollToFolder` holds the header open for the flight (`scrollLockUntil`) and aims at
`headerFullH`: measuring `offsetHeight` while the header was tucking aimed 58px short, so
the folder you asked for landed under the rail.

### Full-bleed / safe area

`viewport-fit=cover` plus `--sat`/`--sab` (`env(safe-area-inset-*)`, 0 on desktop). The
frosted header now runs up **behind** the clock and battery rather than starting below
them, with `padding-top: calc(var(--sat) + var(--header-air))` keeping the wordmark clear
— 8px of air, which is the gap in the mockup. Everything pinned to an edge adds one of
the two: `#mainContainer`, `#toastRoot`, `#uploadTray`, `#addFab`, `#selectionToolbar`,
`.sheet-content`, `.look-bar`, `.look-tail`, `.loading-screen`, `#cmdk`. `min-height`
is `100dvh` (vh does not track Safari's collapsing toolbars). **`#mainContainer`'s
Tailwind `pt-*` had to be deleted** — the CDN injects after the inline `<style>`, so a
utility class beats the stylesheet rule at equal specificity.

### The wordmark really is the asset

Asked whether we could "just use the actual SVG in ASSETS". We do — `ASSETS/SSaved.svg`
is a `<text>` element in `QueensVar-Regular`, which is installed on the Mac and **not on
the phone**, so shipping it as-is renders a system serif on the one device the mockup is
for. The inlined paths were converted from her own `~/Library/Fonts/QueensVar.ttf` at
`wght 400, wdth 100`. Proven identical: both rendered at 760px and overlaid in
multiply blend, red vs blue — **no red-only or blue-only pixel anywhere**. The info glyph
is `ASSETS/Info.svg` byte-for-byte (path + viewBox), now 21px inside a 38px dot (0.55,
the mockup's proportion) with a 54px hit area.

## ✅ The lock — confirming a card's username/link (Aug 3, 2026)

Marilyn: "a lock icon. in unlocked state, it actually means i've not confirmed if the
username or url is correct."

**Both builds. Three changes to `#cardInfo`:**

1. **The scrim is clear, the sheet is the glass.** `#cardInfo.modal-backdrop` is
   `rgba(0,0,0,.24)` with `backdrop-filter: none` (id beats the shared `.modal-backdrop`
   class; every other sheet keeps `rgba(0,0,0,.4)` + `blur(4px)`). The frosting lives on
   `#cardInfo .modal-content`: `rgba(252,252,251,.62)` + `blur(30px) saturate(180%)`, plus
   the **same liquid-glass rim as `.shot`** on an `::after` (bright inner hairline, top
   sheen, weighted bottom edge) and matching translucent fills on `.ci-field` and the
   tiles. Blurring at the panel rather than at the scrim is what makes it read as a pane
   of glass laid on the grid instead of a fogged window. The rim layer needs
   `#cardInfo .modal-content > * { position: relative; z-index: 1 }` under it.
2. **The actions are a row of four tiles**, not a list — icon over an 11px label,
   "Open / Move / Delete / Unlocked". Scoped `#cardInfo .ci-actions { display: grid }`
   because `.ci-actions`/`.ci-action` are **shared with `#folderSheet`**, which must stay
   a vertical list — and the scoped rule also zeroes the inherited `border-top`, so there
   is no rule above the row. Labels shortened ("Open profile" → "Open") to fit 4 × ~79px
   at 375px.
   - **`#cardInfo .ci-suggest:empty { display: none }`.** The OCR chip row is empty most
     of the time, and an empty flex box still spends its `padding-top` — that 9.6px was
     most of the gap under the hint, and no amount of margin tuning on `.ci-actions`
     would have found it.
   - The grabber was landing on the username field: the markup's `-mt-2` pulls the
     handle up and its own padding was `0.6rem 0 0.1rem`, leaving ~1.6px. Scoped to
     `0.5rem 0 0.85rem`, so the air is under the notch rather than above it.
3. **The lock.** The tile is labelled by STATE, not by action — **Unlocked** (the default,
   = never checked) and **Locked**. Unlocked drops the card's info-dot glyph to
   `rgba(31,31,31,0.28)` (`.info-dot.is-unconfirmed`); tapping it locks, **closes the
   sheet**, and the glyph goes to full `#1F1F1F`. Tapping again unlocks and **stays open**,
   because unlocking is the start of an edit.
   - **Both states are full ink** — an amber "unlocked" tile was tried and dropped. The
     shackle carries the meaning and the TILE carries the state: raised glass when
     unlocked, **pressed in** when locked (`rgba(0,0,0,.075)` + an inset top shadow, and
     no bright rim), so it reads as depressed against its three raised siblings.
   - **The padlock is one inline SVG, not two Phosphor icons.** `ph-lock-simple` and
     `ph-lock-simple-open` differ by a few pixels of shackle offset, which is invisible at
     19px — and the whole point was that unlocked should be obvious. So `LOCK_GLYPH` draws
     the body as a filled `<rect>` and the shackle as its own `.lock-shackle` path, and CSS
     lifts and tilts it when unlocked.
   - **Gotcha:** lengths in a transform on an SVG child resolve in **viewBox units**
     (`transform-box: view-box` is the default), so on a 256-unit box drawn at 19px a
     `translate(-3px,-3px)` moves it about a fifth of a screen pixel. The working values
     are `translate(-26px, -30px) rotate(-18deg)`.

**Locked freezes the identity fields, and there are five ways in, not one:** `#ciInput`
(`readOnly`), `cardInfoEdit`, `toggleLinkModeSeamless` (it blanks username AND link),
`applySuggestion` (the OCR chips — also hidden while locked), and Look mode's pencil
(`editLookLink`, which toasts instead). Notes, move and delete stay available — the lock
is about the username/link only.

**Closing the sheet can't re-render, so the dot is repainted by hand.** `paintInfoDot(id)`
toggles the class on `#card-<id> .info-dot` directly. A `render()` here would tear the grid
down under the finger — the same constraint that `toggleLinkModeSeamless` already lives
under.

**Storage differs between the two builds, deliberately, behind one seam.** UI code only
ever calls `isConfirmed(id)` / `setConfirmed(id, on)`.
- **cf/** — `confirmed` is a field on the card in the JSON doc (`flushState`,
  `loadCollection` and `buildBackupJSON` all carry it). Syncs across devices.
- **root/** — a localStorage id-set via the existing `loadIdSet`/`saveIdSet`
  (`ssaved_confirmed_<collection>`), because the Supabase `cards` table has **no
  `confirmed` column** and adding one to the upsert payload would fail every write.
  Per-device, like reviewed/favourite. Swap those two functions if a column ever lands.
- Keeping the seam identical is what lets the `git merge-file` port keep working — the
  delta stays inside the backend block.

**Bug found on the way (root only):** `initLookState()` ran in `DOMContentLoaded` *after*
`initCollection()`, i.e. after the first `render()`. So `favouriteIds` was empty at first
paint and **favourite stars never showed until something re-rendered** — the confirmed dot
would have inherited it. Now also called at the end of `loadCollection()`, before its
`render()`.

**Verified in both harnesses** (`.claude/mkcf.py`, `.claude/mkharness.py`): lock persists
to the stub doc / localStorage, survives a `render()`, input goes read-only, username and
linkMode are unchanged after hostile `cardInfoEdit`/`toggleLinkModeSeamless`/
`applySuggestion` calls, `#folderSheet .ci-actions` still computes `flex` while
`#cardInfo` computes `grid`, and `#folderSheet` still computes `blur(4px)`.

## ⚠️ SUPABASE IS RESTRICTED (root build only) — Aug 2, 2026

Every request to `uauqqdaalnddedgjdgcg.supabase.co` returns **402**:

> `Service for this project is restricted due to the following violations:`
> `exceed_cached_egress_quota. The project owner must upgrade their plan or`
> `remove spend caps to restore service.`

Storage AND PostgREST both. So `?c=…` shows the retry screen, and no upload can land.
Nothing in the app can fix this — it's the Supabase billing dashboard (raise/remove the
spend cap, or upgrade). **Cached egress** is the meter: full-resolution screenshots are
served straight from the public bucket on every grid paint. If it keeps recurring, the
real fix is serving resized derivatives (`?width=` via the Supabase image transform, or
a thumbnail on upload) instead of the originals — `preloadImages` already caps decode at
12, but that's decode, not transfer.

Because of this the Aug 2 UI overhaul below was built and verified against a **local
Supabase stub** (`scratchpad/mkharness.py` — an in-memory `db.from()/db.storage` mock
patched over `index.html`, images served off `python3 -m http.server`). Re-verify the
upload/OCR path against the real backend once the project is unblocked.

## ✅ UI overhaul — the mockup build (Aug 2, 2026)

Marilyn supplied a 2x iPhone mockup and a written spec. `index.html` +957/−792.
**Everything below is measured off that mockup at half its pixel values** (826px export
÷ 2 = a 413pt frame; the card maths confirms it — 15 + 185 + 10 + 185 + 15 = 410). So her
"74px apart" is **37 CSS px** and "notes at 32pt" is **16px**. If a future mockup arrives
at 1x, halve nothing.

**Type: IBM Plex Mono is gone, Geist is the whole app.** `--font-ui: 'Geist'`, one
Google Fonts variable request (300..700), and `.microlabel` tracking dropped 0.16em →
0.11em because Geist caps read spaced-out at the mono's setting. Her *global* CLAUDE.md
still says Plex Mono is the house font — this project now overrides that.

**The wordmark is outlined, not live text.** `ASSETS/SSaved.svg` is a `<text>` element
in `QueensVar-Regular`; on any machine without Queens installed it silently falls back
to a system serif. Converted to paths with fontTools against
`~/Library/Fonts/QueensVar.ttf` at `wght 400, wdth 100` and inlined into the header
(also saved as `ASSETS/SSaved-outlined.svg`). **Re-do this, don't re-add the text SVG,
if the wordmark ever changes** — the script is in the session log; the tspan x-offsets
(0 / 39.53 / 81.06 / 118.14 / 157.24) and the −0.03em inside "ed" are the whole layout.

**Folder headers in the grid are gone. The rail IS the header.** `#folderRail` is a
horizontal scroller of sentence-case names in Geist Bold 22px/-0.03em, count as a
superscript, `gap: 37px`, no visible scrollbar. Active `#171717`, inactive **`#909090`
(3.06:1 — the AA floor for large text; #A3A3A3 was 2.53:1 and failed)**. Consequences,
all of them deliberate:
- `render()` emits a bare `<section id="folder-…">` + `.card-grid`. The section ids and
  `.folder-grid-area` still exist, so the pointer-drag engine and cross-folder drops are
  untouched.
- The header has two rows and **no longer slides away**: scrolling down collapses
  `#brandRow` to 0 and leaves the rail pinned. That replaced `#mobileBreadcrumb` and its
  `.fp-seg` pill row entirely — both deleted, along with `#viewTabs`/`#tabIndicator`/
  `#densityToggle` (view + columns moved into the collection sheet).
- Read-progress is now a 2px underline under the ACTIVE rail name. It needs the faint
  track (`::before` at 0.09) — a bare fill at 2% paints a 3px dash that reads as a
  rendering artefact.
- Rename/add/collapse/delete moved to a **long-press on the rail name** → `#folderSheet`.
  `setupFolderLongPress` was repointed from `#folderWrapper`/`.folder-tab` to
  `#folderRail`/`.frail-item`; the 10px slop matters more here because the host is a
  horizontal scroller. Inline rename is gone (swapping a 22px bold name for an input
  reflows the scroller) — it's a `prompt()`, and it **reverts the name on write failure**.

**Scroll-spy is computed, not observed.** `IntersectionObserver` with
`rootMargin: -20%/-70%` can never reach the last section once the page has bottomed out,
so the rail kept naming the second-to-last folder while you looked at the last one.
`updateFolderProgress` now picks the active index directly (it already had every
section's top/height) and `setActiveFolder` paints both the rail and the desktop side
nav. `initFolderObserver` is now `resetActiveFolder()` — it only clears the memo so a
fresh grid repaints.

**The card is a screenshot and a note.** No white panel, no border, no card shadow.
- `.shot` carries a Comeau shadow (one light source above, four layers on a fixed ratio,
  warm `hsl(30deg 8% 62%)` not black) plus a liquid-glass rim: `inset 0 0 0 1px
  rgba(255,255,255,.5)`, a top sheen and a weighted bottom edge.
- Aspect is **9/19.5 in the mobile 2-up** (the phone's own ratio, nothing cropped) and
  9/16 everywhere else, switched by `html[data-cols]`.
- **Tapping the image opens the link.** The hover-revealed arrow and the `⋯` menu are
  both gone. Side-effect worth knowing: `ocrCard` used to write
  `https://instagram.com/` + `''` on an empty read, which now sent a tap to Instagram's
  home page — it writes `'#'` instead.
- Username/link and every action live behind the italic-i **info dot** (30px frosted,
  46px hit area via `::before`) → `#cardInfo`.
- Notes: 16px Geist Medium in a `#EDECE8` bubble, collapse at **2 lines** (`MAX_LINES`
  2, `max-height: 2.6em` — keep those two in step), dwell auto-expand unchanged.
- `.card` is transparent, so **every elevation had to move onto `.shot`**:
  `.card-lifted`, `.drag-ghost-live`, `.card-flash`, `.is-selected`, `.is-restored`. A
  shadow left on `.card` draws a rectangle around nothing.

**The double-tap requirement, precisely.** In `#cardInfo`, double-tapping the @ swaps to
the link glyph with **no render at all** — `toggleLinkModeSeamless` mutates the card,
crossfades the glyph and repaints only the input. Verified: the `#ciInput` node and the
first `.card` node are `===` the same objects afterwards. This is only possible *because*
the grid no longer shows the username, so there is nothing to repaint; `closeCardInfo`
just `flushCardSaves()`. Don't reintroduce a `transitionRender()` here.

**Desktop.** Side nav + running vertical rail kept as asked. The size lever now drives
`--card-min` on an `auto-fill` grid — it changes card size AND column count, which is
what "control the image size" means to the eye. **New storage key `ssaved_cardw`**: the
old `ssaved_width` held 600–2400 (a container width), and feeding one of those to
`--card-min` gives a single 1390px column. A shared `.shell` class caps the content
column at `min(1390px, 100vw - 260px)` on desktop so the fixed side nav stops sitting on
top of the last card.

**Deferred at Marilyn's request:** search / Look / column toggle / Latest have no place
in the mobile header yet ("future consideration, i want to get the base of the UI design
right first"). They're all in the collection sheet (tap the pill), plus ⌘K. Look mode,
Latest and the 1-column view are otherwise untouched.

**Sweep after all this:** the orphan-id check from Jul 31 was re-run — `saveIndicator`
is still the only one, and still deliberately null-guarded. A second pass checks every
`on*="fn("` handler against the declared functions: zero missing. Deleted as dead:
`showTagOverview` (the rail does that in one tap; the shell it borrowed is now only
"Move to folder"), `handleImageClick`, `handleTagTap`, `toggleLinkMode`, `triggerTooltip`,
`closeAllTooltips`, `expandLinkField`, `collapseLinkField`, `copyCardLink`,
`openCardMenu`/`closeCardMenu`/`cardMenuAction`, `editFolderName`/`cancelEditFolderName`/
`saveFolderName`, `positionTabIndicator`, `folderObserver`, `activeFolderName`, and the
CSS for the tooltip, card menu, folder pill, tab indicator and density toggle.

## ✅ "Failed" uploads that weren't, and dead OCR — one null deref (Jul 31, 2026)

Marilyn: "when i upload an image it often says failed and retry, but the truth is the image
actually gets uploaded. however, i havent had the OCR working in a long while."

**Both symptoms, one line.** `#saveIndicator` was deleted from the markup in **1526564**
("Streamline the mobile UI: 18 persistent controls down to 9") — toasts had replaced it and a
successful save is deliberately silent. But **five call sites survived**, and `showSaved()`
dereferenced the result without a guard:

```js
const el = document.getElementById('saveIndicator');
el.classList.remove('opacity-0');   // TypeError: el is null
```

`saveCardToDB()` calls `showSaved()` on its way out, **after** the upsert. So every completed
write threw. Callers `await saveCardToDB(...)`, so in `processUploadEntry` the rejection was
caught by the upload's own `catch` and the entry went to **`failed`** — with the image already
in Storage and the row already in Postgres. And because the throw jumped over
`appData.cards.unshift(card)` … `setState('reading')` … `ocrCard(...)`, **OCR was never
invoked at all.** Not broken — unreachable, since 1526564.

**Reproduced and verified against real Supabase** (throwaway collection `zz-diag-0731`, deleted
afterwards — cards/folders/collections/storage all confirmed `[]`). Before: tray `failed`,
`error: "Cannot read properties of null (reading 'classList')"`, `appData.cards.length === 0`,
yet the row and a 70,544-byte object were both present, `username: ""`. After: tray `done`,
`username: "marilynmakerlab"`, link built, textarea populated live, 5s end to end.

**Not the schema.** Asked directly, so it was checked directly: `cards` has all 12 columns the
code writes (`id, collection_id, username, notes, link, image_path, folder_id, order,
suggestions, created_at, deleted_at, tags`); `folders` and `collections` likewise. **No SQL
migration is outstanding.** (Doc nit: `collections` is `id, created_at, slug` — no `name`
column, contra the schema section below. `createCollection()` only inserts `{ id }`, so this is
harmless.) Tesseract v5 was also cleared as a suspect — a probe against the pinned CDN build
confirms `data.words` is still present and the app's filter/sort picks the username correctly.

**Fixes:**
1. `showSaved()` null-guarded, kept as the one seam if a "saved" affordance ever returns.
2. `flashBackupStatus()` borrowed the same dead element — routed to `toast()` under one id.
3. **Structural:** `processUploadEntry` now closes its `try` right after the two writes. Past
   that point the upload *has* succeeded, so `render`/`preloadImages`/`ocrCard` each get their
   own guard and **cannot re-report a committed card as "Failed"**. Display must never
   re-judge a write that already landed — that inversion is what made a cosmetic null deref
   look like data loss.

**Sweep:** every literal `getElementById('x')` / `querySelector('#x')` in the file was diffed
against every `id="…"` in the markup. `saveIndicator` was the **only** orphan. Worth re-running
after any pass that strips UI (`python3` one-liner in the session log) — deleting an element is
routine, and the call sites are what get left behind.

## ✅ Reliability audit — 17 bugs fixed, 404 KB dropped (Jul 29, 2026)

Marilyn: "it's pretty broken. i sometimes run into errors while using it on my phone."
Two parallel audits (mobile-runtime reliability + dead-weight), every finding re-verified
against the code before any edit. `index.html` +348/−146.

**The three that explain "errors on my phone":**

1. **`alert()` on every failed card save** (`saveCardToDB`) — and notes were a **full-row
   upsert per keystroke**, no debounce. One cellular blip mid-typing = a native modal that
   dismisses the keyboard and steals focus, one per failed character; inside the upload and
   folder-delete `await` loops it froze the whole batch until tapped. Now a toast with Retry,
   and `updateCard` coalesces per card at 600ms (**measured: 12 keystrokes → 1 write, was
   12**), flushed on `pagehide` + `visibilitychange`.
2. **A dropped request on load painted an empty app over real data.** `loadCollection`
   destructured only `data`. supabase-js does NOT throw on network failure — it resolves
   `{data: null, error}` — so a blip was indistinguishable from "collection doesn't exist",
   and `initCollection` fell through to `createCollection()`, resetting `appData` to a bare
   Inbox and rendering "Nothing saved yet". **This is the exact shape of the historical
   "notes are gone" scare below.** Now returns `'loaded' | 'absent' | 'failed'`; only
   PGRST116 (genuinely 0 rows) creates. Verified by stubbing all four read paths: network
   errors → retry screen, **0 rows written**; PGRST116 → still creates.
3. **One unreadable image wedged the upload queue forever.** `simpleCrop` re-fetched the
   just-uploaded image from Supabase with `crossOrigin='anonymous'` *after* the grid had
   loaded the same URL without it — WebKit reuses the cached non-CORS response and fails the
   check. With **no `onerror` and no timeout** the promise never settled → `ocrCard` never
   returned → `uploadRunning` latched `true` and every later file sat at "Queued" until a
   reload. Now crops the **local File** (no network, no CORS), plus `onerror`, a 10s timeout,
   a null-blob guard, a 45s race around OCR, and `try/finally` on the queue flag.
   **Verified with a corrupt file placed FIRST: the two valid files behind it still
   processed and OCR'd.**

**Also fixed:** undo-delete didn't check its write, so a failed restore left `deleted_at` set
and the *next* page load hard-deleted the row **and its image** — undo appeared to work and
the card was destroyed (now reverts state, re-arms the timer, says so) · `getInboxId()`
matched on the folder **name**, so renaming "Inbox" sent every upload into a phantom folder
(id now resolved once at load; `inboxId`) · `preloadImages` decoded **every** full-res
screenshot (~14 MB each — the iOS "problem repeatedly occurred" reload); capped at 12,
skipped entirely under 768px · ⌘K "Add screenshot" was a silent no-op on iOS (`fileInput
.click()` from a rAF loses the user-gesture grant; now synchronous) · same for the palette's
keyboard (`input.focus()` deferred) · a **second finger** overwrote `pressInfo` while the
first long-press timer was armed, firing `pickUp()` on the wrong card (`isPrimary` +
`clearTimeout`) · Look mode: an under-threshold swipe starting on the image **navigated to
Instagram** (added `lookJustDragged`, the guard the grid engine already had) · long notes were
unscrollable on touch (`.look-card{touch-action:none}` covers the subtree → `pan-y` on the
note) · undo discarded a note being typed (Safari fires no `blur` when a focused element is
removed from the DOM) · a stale Look session resumed **days later** (30-min TTL) ·
`restoreLookSession()` ran before `initSmoothScroll()`, so its `lenis?.stop()` was a no-op ·
`reindexCards` fired N unawaited parallel upserts including soft-deleted cards (now one
batched call, `!deletedAt`) · `handleFolderDropMultiple` didn't check its write · unescaped
`${c.notes}` / `${c.username}` in textareas (RCDATA: a note containing `</textarea` destroyed
the card, and `&amp;` was entity-decoded on re-render then **persisted mutated**) and
`${folder.name}` in three attributes — a folder named `Mum's "stuff"` broke out and killed the
header's buttons. `confirmDeleteFolder` now takes only an id.

**Payload: −404 KB.** `unpkg.com/@phosphor-icons/web` is a *loader shim* that appends
`<link>`s for **all six weights**; the app uses three (`ph`, `ph-bold`, `ph-fill` — zero uses
of thin/light/duotone). Replaced with three pinned links. **If you ever re-add that bare
shim, you re-add the 404 KB.** Tesseract (67 KB) is now lazy via `ensureTesseract()`.
Verified all three weights still render real glyphs (a bogus icon class gives
`content: none` — use that as the control).

**Deleted as dead:** `deleteCardFromDB` (superseded by `permanentlyDeleteCard`), `showStatus`,
`undoTimeout`, `inSelectableFolder`, `.focus-ring`, `.tray-item.is-leaving`, the
`tailwind.config` `warm` palette (15 lines, zero uses), 6 debug `console.log`s.

**Corrections to the notes below — the docs were staler than the code.** Every "removed
feature" vestige this file warns about is **already gone** (grep = 0 for `deletedCardsStack`,
the old HTML5 DnD handlers, `dragSrcId`, `INBOX_ID`, `tags`, `toggleAddMenu`, …).
`handleImageClick` is **no longer a no-op** (it drives `toggleCardSelection`) — do not delete
it. `saveCardToDB` omitting `deleted_at` is **harmless**: PostgREST's `ON CONFLICT DO UPDATE`
only sets columns present in the payload. **`debug.html` does not exist** despite being cited
three times below as a recovery tool. The 8 empty `catch {}` blocks are deliberate
(`setPointerCapture` throws on synthetic pointers; `localStorage` throws on quota).

**Still open, deliberately not done:** ~995 KB of 28 old backup `.html` files (including
`personal.html` and `restore.html`) are tracked on `main` and therefore **publicly served
from GitHub Pages** — referenced by nothing but prose, git history is the backup, but
deleting them is Marilyn's call. `setupFeedFilterLongPress` / `setupFolderLongPress` are
~81 lines of near-identical scaffolding on the same `#folderWrapper` node (~40 lines
recoverable) — left alone because it's the most fragile code in the app and consolidating it
risks the very reliability this pass was about.

**Testing note (cost me time):** the Browser pane cannot open `file://` here and
`launch.json` servers can't read `~/Documents` (sandbox). Working loop: `python3 -m
http.server` from **Bash** in background, then `navigate` to `127.0.0.1`. See the
`claude-preview-panel-debugging` skill. Both test collections (`zz-selftest-0729`,
`zz-selftest2-0729`) and all 8 uploaded images were deleted from Supabase afterwards —
verified 0 rows remaining.

## ✅ "Look at this" — swipe-to-triage review mode (Jul 26, 2026)

Commit e3b0bd3. Full-screen, one card at a time, for working through the backlog.

**Behaviour:** swipe **right** = solved, clears from the pile · **left** = keep, stays for
next session · **up** = favourite (also clears). Tapping the image opens the profile.
Existing notes render readably (0.8125rem/1.6, not the grid's tiny text); empty ones show
a big "Add a thought" button. The link is editable via a pencil. Undo in the top bar,
arrow keys mirror the swipes, Esc closes.

**No action buttons** — Marilyn: "i dont think i need the three icons: swipe left, right and
top is understood by the sole user (me)." This deliberately overrides the design-DNA rule
that hidden gestures get a visible twin; she's the only user. Already-favourited state
still shows as a star (information, not chrome).

**Storage — deliberately NOT a migration.** `reviewedIds` / `favouriteIds` are localStorage
Sets behind a four-function adapter (`isReviewed` / `setReviewed` / `isFavourite` /
`setFavourite` + `loadIdSet`/`saveIdSet`). Nothing else touches storage, so swapping to
Supabase columns later is confined to that block. Chosen over columns because this project's
worst outage came from code shipping ahead of the schema. **Consequence: "solved" is
per-device.** Note and link edits still go to Supabase, so actual content syncs.

**Surfacing:** star on the card in the grid, plus a "Favourites" filter chip in Latest
(`feedFavouritesOnly`, independent of the folder `feedFilter`). Entry = header button
(`ph-cards`) + ⌘K action; the mobile control row was left untouched.

**Two layout bugs found in testing, both worth remembering:**
1. `.look-image-wrap img { height: 100% }` rendered **49px taller than its wrapper** and
   covered the username row. A percentage height resolves unreliably against a
   flex-grow-derived height. Fix: `position: absolute; inset: 0` + `overflow: hidden` on
   the wrap. **`getBoundingClientRect()` on the WRAPPER hid this** — the wrapper measured
   correctly while its child overflowed; always measure the child too.
2. Fixing that collapsed the image area to zero, because an absolutely-positioned child
   gives its parent no height and `flex: 1` has nothing to distribute inside an
   **auto-height** parent. Fix: `height: 100%` on `.look-card`.

**Testing note:** the first symptom looked exactly like the known stale-compositor
preview bug, and hit-testing (`elementFromPoint`) said the username was visible and
topmost — because it *was* in the layout tree, just painted under the overflowing image.
A fresh tab reproduced it, which is what proved it real. Hit-testing can't see paint order.

## ✅ improved2 promoted to the root app (Jul 26, 2026)

Commit 7877832. `improved2/index.html` copied over `index.html`, so
https://nnnephirale.github.io/ssaved-app/?c=... now serves the bold build.

**Pre-flight checks that made this safe (repeat them before any future promotion):**
- `git log 431fb3f..HEAD -- index.html` was EMPTY — the root hadn't diverged since the
  fork, so nothing was silently dropped. If it ever has commits, reconcile them first.
- Function-inventory diff (`grep -oE '^\s*(async )?function \w+'`, sorted, `comm -23`)
  showed **zero** root functions missing from improved2 — a clean superset, 116 → 146.

The old root remains in history at **2c55039**.

**`improved2/` was deleted right after** (commit b588c82) — once promoted it was
byte-identical to `index.html`, and two copies of a 3,872-line file invite silent drift.
Git history is the backup. It's still recoverable: `git checkout 7877832 -- improved2/`.

**Current published surfaces: just two** — `/` (bold build) and `/improved/` (the
restrained polish variant, kept as the alternative).

Same Supabase backend throughout, so every existing `?c=` collection was unaffected by
the swap.

## ✅ improved2 round 2 — serif out, menu in, Lenis, merged mobile row (Jul 26, 2026)

Commit ab5dc9c. Five asks from Marilyn, all in `improved2/` only.

1. **Instrument Serif removed.** `.font-display` is now the same IBM Plex Mono at weight 500 / `-0.03em` — one typeface, two registers. Display sizes dropped (`text-2xl` → `text-base`/`text-lg`) because mono at 2xl reads chunky where serif read elegant.
2. **Bloom-style card menu.** The card's delete-× became a `⋯` that opens `#cardMenu`: Open profile / Copy link / **Move to folder** / Delete. ONE shared menu element, not per-card DOM (cards re-render constantly). Positioned against the trigger rect with edge-flipping, and `transform-origin` set per-open so it grows out of the button corner. Move-to-folder reuses the `#tagOverview` shell — so `showTagOverview()` must reset the `<h2>` back to "Jump to folder".
3. **Lenis smooth scroll** (what tyronec.com uses — confirmed via `html.lenis`). `smoothWheel: true`, **`syncTouch: false`** deliberately: iOS momentum is already good and hijacking touch both feels laggy and would fight the pointer-drag engine. `lenis.stop()` in `beginDrag` / `.start()` in `endDrag` so autoScroll's `scrollBy` doesn't fight the rAF lerp. Inner scrollables need `data-lenis-prevent` (palette results, tray list, both modal lists). All smooth scrolling goes through `smoothScrollTo()`, which falls back to native if the CDN is blocked.
4. **Tab underline lag fixed — two causes, both real:**
   - `#tabIndicator` transitioned `left`/`width`, which relayouts every frame on the main thread. Now a fixed 100px base animated with `translate3d + scaleX` — compositor-only. `positionTabIndicator()` suppresses the transition on first placement (`tabIndicatorReady`) so it doesn't animate in from zero width.
   - `setLayoutMode` called `render()` synchronously, so the heavy grid rebuild blocked the frame the transition needed to start. Now it paints tab state first and defers `render()` by two rAFs. Measured: the synchronous part went to **0.5ms**.
5. **Merged mobile control row** (designed with an Opus product-designer subagent; I implemented as design engineer). `#viewTabs` is now `justify-between`: `.tab-group` (labeled tabs, on the hairline, stretching underline) on the left, `#densityToggle` (enclosed icon-only pill, sliding white thumb) on the right. Different *form* per category, so no divider is needed to separate them. Fits 375px with 40px to spare.
   - **Icon off-by-one fixed:** the two real *layout* glyphs had been assigned to the two *view modes*. Folders `ph-squares-four` → `ph-folders`; Latest `ph-rows` → `ph-clock-counter-clockwise`; 1-col `ph-rectangle` → `ph-rows`; 2-col `ph-columns` → `ph-squares-four` (`ph-columns` reads as a split pane, not a 2-across grid). Also updated the ⌘K "Switch to…" action icons.
   - **Gotcha:** `#tabIndicator` MUST live inside `.tab-group` — `positionTabIndicator()` reads `offsetLeft`, which needs that wrapper as the `position:relative` offsetParent; and `justify-between` on the bare `#viewTabs` would throw the two tabs to opposite ends.
   - The header's second row is now empty on mobile → `hidden md:flex`, header 116px → **61px**, `main` `pt-36` → `pt-24`. `#fileInput` stays in that hidden container; `.click()` works fine on a `display:none` input (verified).

## ✅ "improved2" — the bold variant (Jul 25, 2026)

**What:** `improved2/index.html` → https://nnnephirale.github.io/ssaved-app/improved2/?c=... — third parallel build (root = original, `/improved/` = restrained polish, `/improved2/` = bold). Same Supabase backend, so every existing `?c=` collection works in all three.

**Brief:** Marilyn explicitly invoked the design-preferences wildcard escape hatch — "go bolder, true to your intent, because my restrained DNA was mapped on their taste anyway." So this build makes structural bets, not just polish.

**The four bold moves:**
1. **Real typography.** The app never used her stated signature fonts. Now: **IBM Plex Mono** (300/400/500) for all UI, **Instrument Serif** for the wordmark, modal titles, and empty state. `.microlabel` (0.625rem / 500 / uppercase / 0.16em tracking) is the workhorse for every structural label — folder names, view tabs, filter chips, tray states.
   - **Gotcha:** had to remove `font-sans` from `<body>` — Tailwind's class (specificity 0,1,0) beats `body { font-family }` (0,0,1).
2. **⌘K command palette** (`openCmdk`/`renderCmdk`/`buildCmdkItems`). Searches usernames + notes + folders, plus 5 actions. Sigil scoping from moumenlab's argument chips: `@` = usernames, `#` = folders, `>` = actions — promoted to a chip, Backspace drops it. Arrow/Enter/Esc nav, `<mark>` match highlighting, thumbnails in results, recents on empty query. `/` also opens it when not typing. `jumpToCard()` expands a collapsed folder, scrolls, and flashes a blue ring.
3. **Upload staging tray** (moumenlab file-upload staging). `handleFiles` was a blocking serial loop that called `alert()` on failure and lost the batch. Now each file is an entry with its own visible state machine: queued → uploading → reading text → done | **failed + Retry**. Cards appear one-by-one as they land (uses plain `render([id])`, NOT `transitionRender`, to avoid stacking view transitions per file). Kept serial (proven-reliable on mobile per the old upload-hang bug); progress bars are indeterminate travelling bars, never fake percentages.
4. **Flat folder headers.** Dropped the `clip-path: polygon()` skeuomorphic tab for a mono-caps label + chevron + count on a hairline. Kept `.folder-tab` / `.folder-header[data-folder-id]` classes intact — the drag engine and folder long-press depend on them.

**Also:** skeleton card grid (shimmer) replaces the bare spinner on load; frosted gradient scroll edge (`#scrollEdge`) rides under the header; inherits everything from `/improved/` (toasts, bottom sheets, fluid tab indicator, press feedback, icon morphs).

**Gotcha:** `.cmdk-foot span { display: inline-flex }` (0,1,1) beat Tailwind's `.hidden` (0,1,0), so mobile-hidden footer hints still showed — added an explicit `.cmdk-foot span.hidden { display: none }` plus an `md:` restore.

## ✅ "Improved" UI Variant at /improved/ (Jul 25, 2026)

**What:** A parallel UI-polish build at `improved/index.html` → https://nnnephirale.github.io/ssaved-app/improved/?c=... — same Supabase backend, so any existing `?c=` collection works in both versions. Original at the root URL is untouched. (Commit 431fb3f)

**Reference sites distilled** (Josh Puckett pasito/bloom, Emil Kowalski's 7 animation tips + vaul + sonner, lab.moumen.dev, amicro):
- **Sonner-style toasts** replace the status bar AND the header Undo button: stacked dark pills bottom-center (`#toastRoot`, `toast()/dismissToast()`), spinner toast for uploads, rose "Undo" action toast after deletes (15s, matches old timing). `showStatus()`/`updateUndoUI()` now route into toasts.
- **Vaul-style bottom sheets on mobile:** shareModal, tagOverview, folderVisibilityModal slide up (`sheetIn`), have a drag handle (`.sheet-handle`), and drag-down-past-110px dismisses (`setupSheetDrag`). Desktop keeps centered modals with scale-from-0.95 + blur entrance.
- **Emil's tips:** global `button:active { scale(0.97) !important }`, entrances from scale ≥0.93 (never 0), origin-aware suggestions tooltip (`transform-origin: bottom left` + blur-in), spinners sped to 0.7s (`!important` needed — Tailwind CDN injects styles after inline `<style>`).
- **Pasito-style fluid tab indicator:** `#tabIndicator` slides+stretches under Folders/Latest tabs (transitions `left` and `width`; positioned in `updateLayoutToggleUI`/`render`/resize).
- **Micro:** copy-link icon morphs to checkmark (`.icon-pop`), share Copy button morphs to "Copied ✓", per-file upload progress ("Uploading 2 of 5…"), OCR progress ("Reading usernames… 1 of 3").

**Gotcha:** In-app Browser pane serves *stale snapshots* of `file://` pages — after editing, `navigate` (even with force) re-serves the old snapshot; open a NEW tab to test fresh file content.

## ✅ Pointer-Based Drag & Drop Rewrite (Jul 20, 2026)

**Problem:** Reordering was glitchy — it used native HTML5 drag-and-drop, which (a) doesn't fire at all on mobile touch, and (b) only showed a fixed ±24px shift of in-between cards, never the actual landing position.

**Solution:** Replaced native DnD with a unified pointer-event drag engine (`setupLongPress` / `beginDrag` / `reorderPreview` / `endDrag`):
- **Mouse:** press + move ~6px starts a drag immediately.
- **Touch:** long-press 450ms (haptic tick) "picks up" the card; moving then drags it. Moving before pickup = normal scroll.
- **Live ghost:** a floating clone follows the pointer (scaled to ≤220px wide so the grid stays visible), while the real card becomes an invisible placeholder that FLIP-animates to the exact landing slot — the grid always previews the true final arrangement before release.
- **Multi-select preserved:** long-press pickup enters selection mode; releasing without moving parks there, tapping other cards adds them; dragging a selected card moves the whole group (count badge on ghost, folder highlight as drop target).
- **Cross-folder:** dropping into another folder's section commits `folderId`; hovering a collapsed folder auto-expands it.
- Drop commits order from live DOM positions (`saveCardToDB` per card + `reindexCards` for source folder on cross-folder moves).

**Hard-won gotchas (relevant for future edits):**
1. `::view-transition { pointer-events: none }` is REQUIRED — during a View Transition (0.35s) the transition overlay intercepts hit-testing, so `document.elementFromPoint` returns nothing useful and any drag started mid-transition silently fails to find drop targets.
2. `e.preventDefault()` on `pointermove` does NOT stop touch scrolling — a non-passive `touchmove` listener that preventDefaults while a card is picked up is required, otherwise the browser starts panning and kills the drag with `pointercancel`.
3. `setPointerCapture` wrapped in try/catch (synthetic/test pointers throw).
4. In 1-column grids, before/after is decided by vertical halves; in multi-column by horizontal halves (`computeInsertRef`).

Also fixed: folder-header add-screenshot vs delete-x button misalignment (delete button was `display:block` with line-height inflating it to 35px; both are now flex, `py-1.5`/`p-1.5`, icon centers pixel-identical).

**Removed:** old `handleDragStart`/`handleCardDragOver`/`handleCardDrop`/`handleDragEnd`/`handleFolderDragOver/Leave/Drop` (single-card path), `dragSrcId`/`dragSrcFolderId`, `.card-shift-forward/backward` CSS, old `enterSelectionMode` (replaced by `enterSelectionInPlace` which doesn't re-render mid-gesture). `handleFolderDropMultiple` is retained for multi-drops.

## ✅ CRITICAL ISSUES RESOLVED (Jan 16, 2026)

### Issue 1: Missing Database Columns
**Problem:** Uploaded images disappeared on page refresh. New sessions couldn't save data.

**Root Cause:** Database schema out of sync with code. The code evolved with new features (tags, soft-delete) but the Supabase database was never migrated to include the required columns.

**Solution:** Added missing database columns:
1. `deleted_at` - TIMESTAMP WITH TIME ZONE DEFAULT NULL (for soft-delete feature)
2. `tags` - JSONB DEFAULT '["inbox"]'::jsonb (for multi-folder tagging)

### Issue 2: Global Inbox ID Causing Duplicate Key Errors
**Problem:** Creating new collections failed with error: "duplicate key value violates unique constraint 'folders_pkey'"

**Root Cause:** All collections used the same global `INBOX_ID = "inbox"` for their inbox folder. Since folder IDs are globally unique (primary key), the second collection couldn't create its inbox.

**Why It Happened:**
- First collection creates folder with `id: "inbox"` ✓
- Second collection tries to create folder with `id: "inbox"` ✗ (duplicate key error)
- Images uploaded successfully but folder creation failed, breaking the app

**Solution (Commits 9c3c3b3, 6e8ddb8, 9bfb470):**
1. **Collection-specific folder IDs:** Inbox ID now = `{collectionId}_inbox` instead of global `"inbox"`
   - Example: `onkncluf07jh_inbox` instead of `inbox`
2. **Check before create:** `createCollection()` checks if collection exists before trying to create it
3. **Backwards compatibility:** Maps old `"inbox"` tags to actual inbox folder ID when loading cards
4. **Removed localStorage auto-load:** Opening URL with no `?c=` parameter always creates new collection

**Code Changes:**
- `createCollection()` - creates inbox with collection-specific ID (line 690)
- `loadCollection()` - maps old "inbox" tags to actual inbox ID (line 750-773)
- `handleUpload()` - gets actual inbox folder ID from appData.folders (line 1370-1371)
- `initCollection()` - removed localStorage fallback, always creates new on no `?c=` (line 641-642)

**Critical Lesson Learned:**
> **ALWAYS ENSURE DATABASE CONSTRAINTS MATCH CODE LOGIC**
>
> 1. Primary keys must be globally unique, not just unique within a collection
> 2. Test creating MULTIPLE collections, not just one
> 3. When adding features that require new database fields, run SQL migrations immediately
> 4. Code and database schema must stay in sync
>
> Old collections worked because they existed before these features. New collections failed because:
> - Missing columns: code tried to save fields that didn't exist
> - Duplicate folder IDs: all collections tried to use the same inbox ID

**How to Prevent Future Issues:**
1. Document all database schema changes in this file
2. Run SQL migrations immediately after code changes
3. Test new collections after every feature addition
4. Test creating MULTIPLE new collections to catch uniqueness issues
5. Keep a migration log (see "Database Migrations" section below)
6. Understand database constraints (primary keys, foreign keys, unique constraints)

---

## Overview
SSaved is an Instagram profile screenshot organizer with OCR, tags/folders, and drag-and-drop functionality. Uses Supabase (cloud storage + Postgres) for backend.

**Repository:** https://github.com/nnnephirale/ssaved-app.git
**Supabase URL:** https://uauqqdaalnddedgjdgcg.supabase.co
**Main File:** `/Users/imac/Documents/2026/01_VIBECODED/03_SSAVED/index.html`

## Recent Features Added

### 1. Split Add Buttons + Edit Folder Names (Feb 9, 2026)
**Features:** Replaced dropdown menu with two icon buttons, added inline folder name editing

**Implementation (Commit 2d18dcd):**
- Replaced "Add New" dropdown with two separate buttons:
  - Plus + Image icon = Add Screenshot
  - Plus + Folder icon = New Folder
- Button styling matches folder tab aesthetic (grey, muted)
- Double-click folder names to edit inline
- Enter to save, Escape to cancel
- Updates Supabase folders table immediately

**Code Cleanup:**
- Removed dropdown menu styles (`#addMenuMobile`, `#addMenuDesktop`)
- Removed `toggleAddMenu()` and `closeAddMenus()` JavaScript functions
- Removed dropdown click-outside event listener

**Code Locations:**
- Button HTML: lines 379-387 (mobile), 418-426 (desktop)
- Edit functions: `editFolderName()`, `cancelEditFolderName()`, `saveFolderName()` (lines ~1158-1200)

### 2. One-Time Auto-Sort by Upload Date (Feb 9, 2026)
**Feature:** Cards automatically sort by upload date (newest first), then allow manual reordering

**Implementation:**
- New cards assigned `order: -id` (negative ID, so newer = first)
- Added `created_at` timestamp field to track upload time
- Removed `reindexCards()` call after upload to preserve timestamp-based order
- Manual drag-and-drop still works - updates `order` field as before

**Database Migration Required:**
```sql
ALTER TABLE cards
ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
```

**Code Changes:**
- `handleFiles()` - sets `order: -id` and `createdAt` on new cards (line ~1256)
- `saveCardToDB()` - saves `created_at` to database (line ~706)
- `loadCollection()` - loads `created_at` from database (line ~646)
- Removed `reindexCards(INBOX_ID)` after upload

**Behavior:**
- Upload 3 images → they appear in upload order (newest first)
- Drag to reorder → manual order persists
- Upload another image → appears at top, but manually ordered cards stay in place

### 3. Mobile Drag-and-Drop Rounded Corners Fix
**Issue:** Long-pressing cards on mobile to drag them caused black borders to appear instead of maintaining rounded crop.

**Solution (Commit 1d00f08):**
- Uses actual card element as drag image instead of cloning DOM
- Temporarily hides buttons during drag preview
- Cleaner implementation without glitches

**Code Location:** `handleDragStart()` function around line 200-220

### 2. Tags System Implementation
**Feature:** Cards can now appear in multiple folders using tags while retaining folder UI visuals.

**Changes (Commit 4049536):**
- Changed data model from single `folderId` to `tags` array (JSONB in Supabase)
- Dragging card to folder ADDS tag (doesn't replace existing tags)
- Cards can appear in multiple folders simultaneously
- Delete folder removes that tag but keeps others
- Changed "Add New" button to "Add" with dropdown (Add Screenshot + Add Folder)
- Backwards compatible: supports both old `folder_id` and new `tags` fields

**Code Locations:**
- `saveCardToDB()` - saves both `folder_id` (backwards compat) and `tags` array
- `handleFolderDrop()` - adds tag instead of replacing
- Card rendering logic filters by tags: `appData.cards.filter(c => c.tags && c.tags.includes(folder.id))`

### 3. Soft-Delete with 15-Minute Grace Period
**Feature:** Deleted screenshots have a 15-minute grace period before permanent deletion from Supabase.

**Implementation (Commit b6a5daf):**
- Added `deleted_at` timestamp field to cards table
- Soft-delete sets timestamp, hides card from UI
- Timer-based permanent deletion after 15 minutes
- Undo mechanism clears timestamp and cancels deletion timer
- Cleanup on page load removes cards past grace period
- Permanently deletes both DB record AND Supabase Storage image

**Code Locations:**
- `DELETION_GRACE_PERIOD = 15 * 60 * 1000` (line ~500)
- `deleteCard()` - sets `deleted_at` timestamp
- `schedulePermamentDeletion()` - timer management
- `permanentlyDeleteCard()` - removes from storage and DB
- `cleanupOldDeletedCards()` - runs on page load
- `deletionTimers` Map tracks active timers

### 4. Human-Readable Collection IDs
**Feature:** Collection URLs now use word-based IDs like "dazzling-payne" instead of random alphanumeric strings.

**Implementation (Commit 43b37dd):**
- 70 adjectives + 70 nouns = ~5,000 unique combinations
- Word lists include nature words and CS pioneers (Lovelace, Hopper, Turing, etc.)
- `generateCollectionId()` creates adjective-noun combinations
- Rename functionality via clicking header title or pencil icon
- `collectionName` field stored in database
- Fully backwards compatible - old alphanumeric IDs still work

**Code Locations:**
- `ADJECTIVES` array (line ~510)
- `NOUNS` array (line ~526)
- `generateCollectionId()` function (line ~679)
- `renameCollection()` function (line ~775)

### 5. Recent Collections Tracking
**Feature:** Tracks last 10 accessed collections in localStorage for easy re-access.

**Implementation (Commit f597d9b):**
- `ssaved_recent_collections` localStorage key
- Saves collection ID, name, and lastAccessed timestamp
- "View recent collections" button on empty state
- Shows list with names and IDs
- Backwards compatible - starts tracking after deployment

**Code Locations:**
- `saveToRecentCollections()` - saves to localStorage (line ~790)
- `showRecentCollections()` - displays list or prompts for ID entry (line ~805)
- `navigateToCollection()` - navigates to collection by ID (line ~824)

### 6. URL Slug Renaming
**Feature:** Customize collection URLs with human-readable slugs (e.g., `?c=my-vacation-photos` instead of `?c=zeb0w7ban3l3`).

**Implementation (Commits dd06d5e, 70a231f):**
- Pencil icon next to "SSaved" header for easy renaming
- `slug` column in collections table (TEXT UNIQUE constraint)
- Validates slug format: lowercase letters, numbers, hyphens only
- URL updates without page reload using `history.replaceState()`
- Fully backwards compatible - old ID-based URLs still work
- Slug resolution: tries slug lookup first, falls back to ID

**Database Migration:**
```sql
ALTER TABLE collections ADD COLUMN slug TEXT UNIQUE;
```

**Code Locations:**
- `renameCollection()` - prompts for slug, validates, updates DB and URL (line 771-810)
- `initCollection()` - resolves slug to ID via database lookup (line 619-639)
- `loadCollection()` - loads slug from database (line 708)
- `updateUrl()` - prefers slug over ID in URL (line 812-816)

## Known Issues

### 1. **CRITICAL: Data Loss for Old Collections**
**Collections Affected:**
- `ge1tkzo1hsgv` (old alphanumeric ID)
- `enon7u070sr8` (old alphanumeric ID)
- Also tested: `frosty-pine` (renamed to `shy-wood`) - same issue

**Current Status:** User urgently needs to recover notes associated with screenshots. Images are visible in Supabase Storage but notes are gone.

**Symptoms:**
- Collections load but show "No screenshots yet" (empty state)
- Images still exist in Supabase Storage bucket at paths like `{collection_id}/{filename}`
- Card records appear to be missing from database `cards` table
- Notes were stored in `notes` column of `cards` table - currently inaccessible
- User has confirmed they can see images in Supabase dashboard

**Potential Causes:**
1. `deleted_at` timestamps set incorrectly causing permanent deletion via `cleanupOldDeletedCards()`
2. Soft-delete cleanup ran on page load and removed card records
3. `collection_id` mismatch in cards table (cards exist but with wrong collection_id)
4. Manual deletion or database migration issue
5. Bug in recent code changes that affected existing data

**Investigation Steps (NOT YET DONE):**
1. Check Supabase `cards` table directly via Table Editor:
   - https://supabase.com/dashboard → project → Table Editor → cards
   - Look for ANY rows with `collection_id` = `ge1tkzo1hsgv` or `enon7u070sr8`
   - Check if cards exist with different `collection_id` values
   - Look for cards with `deleted_at` timestamps set

2. Check Supabase point-in-time recovery:
   - See if database backups exist
   - Check retention policy settings

3. Use debug tool:
   - Open `/Users/imac/Documents/2026/01_VIBECODED/03_SSAVED/debug.html`
   - Enter collection ID and click "Load Data"
   - Will show exact state of collections, folders, cards, and storage

**What User Needs:**
- Access to notes written for each screenshot (stored in `cards.notes` column)
- Simple solution without extensive coding
- User plans to migrate all content to new collection after recovery

**Debug Tool Created:**
- `/Users/imac/Documents/2026/01_VIBECODED/03_SSAVED/debug.html`
- Shows collections, folders, cards, and storage images
- Can query by collection ID to see what's actually in database
- Includes Supabase credentials for direct access

### 2. Recent Collections Alert on Page Load
**Symptom:** When accessing collection URLs (e.g., `?c=frosty-pine` or `?c=shy-wood`), user reports seeing alert: "Recent Collections: 1. shy-wood (frosty-pine)"

**Status:** Unclear if this is user clicking button or automatic trigger. Code review shows `showRecentCollections()` only called via button onclick, not on page load.

## Architecture Notes

### Database Schema
**Tables:**
- `collections` - id (text/PK), name (text)
- `folders` - id (text/PK), collection_id (text/FK), name (text), order (int), is_collapsed (bool)
- `cards` - id (text/PK), collection_id (text/FK), username (text), notes (text), link (text), image_path (text), folder_id (text, deprecated), tags (jsonb array), order (int), suggestions (jsonb), deleted_at (timestamp)

**Storage:**
- Bucket: `images`
- Path structure: `{collection_id}/{image_filename}`
- Public URL: `https://uauqqdaalnddedgjdgcg.supabase.co/storage/v1/object/public/images/{image_path}`

### Security Model
- **Current:** Security via unguessable collection IDs (no Row Level Security)
- **Supabase RLS:** All tables use `USING (true)` policy (unrestricted)
- **Risk Level:** Low (non-sensitive data, ~5,000 ID combinations)
- **Recommendation:** Consider implementing RLS if scaling or adding sensitive data

### Backwards Compatibility Strategy
- Old alphanumeric collection IDs still functional
- Database supports both `folder_id` (old) and `tags` (new) fields
- Load logic: `tags: c.tags || (c.folder_id ? [c.folder_id] : [INBOX_ID])`
- Recent collections tracking doesn't affect old collections until accessed

## Backup Files History
1. `Ssaved Supabase (3).html` - Before mobile drag fix
2. `Ssaved Supabase (4).html` - After first drag attempt (glitchy)
3. `Ssaved Supabase (5).html` - Before tags feature
4. `Ssaved Supabase (6).html` - Before soft-delete
5. `Ssaved Supabase (7).html` - Before word-based IDs
6. `Ssaved Supabase (8).html` - Before recent collections
7. `Ssaved Supabase (9).html` - Before manual collection ID entry
8. `Ssaved Supabase (10).html` - Current backup (latest version)

## ✅ Fixes Applied (Feb 14, 2026)

### Fix: Stale INBOX_ID constant (Commit 6276826)
**Problem:** `const INBOX_ID = 'inbox'` was never updated to match actual inbox IDs (`{collectionId}_inbox`). Deleting a folder moved cards to non-existent `'inbox'` folder (cards vanished), and the Inbox folder itself could be deleted.

**Solution:** Replaced with `getInboxId()` function that dynamically looks up the actual inbox folder from `appData.folders`. Updated all 4 references: render delete-button check, deleteFolder guard, card-move-to-inbox, reindex-after-delete.

### Fix: External file drop onto cards froze the app (Commit 071500c)
**Problem:** Dropping an external image file onto an existing card caused `handleCardDrop` to call `stopPropagation()` before checking if it was a card drag. The file drop event was swallowed, the drag overlay counter got stuck, and the app froze requiring a page refresh.

**Solution:** Added early `if (!dragSrcId) return` guard in both `handleCardDragOver` and `handleCardDrop` so external file drags bubble up to the global file drop handler.

### Cleanup: Removed dead `deletedCardsStack` variable
Was declared but never used — leftover from previous undo implementation replaced by `deletedAt` timestamps.

---

## Known Minor Issues (Not Yet Fixed)

### 1. `saveCardToDB` doesn't save `deleted_at`
**Impact:** Low. If a full card upsert is triggered on a soft-deleted card (e.g., via `clearRestoreStatus`), the upsert omits `deleted_at`, potentially stripping the deletion timestamp. Currently unlikely to cause visible issues.

### 2. `clearRestoreStatus` triggers unnecessary DB write
**Impact:** Low. Sets UI-only `isRestored` property then calls `saveCardToDB()`, causing a wasted Supabase request on hover. No visible effect to user.

### 3. `handleImageClick` is a no-op
**Impact:** None. Function exists and is called on every card image click but does nothing. Dead code adding unnecessary event handling.

### 4. `order: 0` has dual meaning
**Impact:** Edge case. `order: 0` means both "new card, use timestamp sort" and "just moved to a folder." Could cause unexpected sort order if two cards in the same folder both have `order: 0` with different timestamps.

### 5. Missing features documented but not in code
- `saveToRecentCollections()` / `showRecentCollections()` — Recent collections tracking feature is absent
- `renameCollection()` / slug feature — URL slug renaming with pencil icon is absent
- These were either removed or lost during edits. The CLAUDE.md documentation describes them but the code doesn't contain them.

---

## Git Commits Referenced
- `23e0a82` - Button improvements
- `16ccb7d` - Integrating Supabase for unique URLs
- `2633451` - Claude improvements (smoother, prettier)
- `7779dcf` - v6.31 reinstate
- `7522036` - Fix mobile upload hang
- `6169d4f` - First mobile drag fix attempt (glitchy)
- `1d00f08` - Cleaner mobile drag fix
- `4049536` - Tags feature implementation
- `b6a5daf` - Soft-delete with grace period
- `43b37dd` - Human-readable collection IDs
- `f597d9b` - Recent collections tracking
- `dd06d5e` - Add URL slug renaming feature
- `70a231f` - Fix: Use correct showSaved() function name
- `9c3c3b3` - Fix: Always create new collection when no ?c= parameter
- `6e8ddb8` - Fix: Check if collection exists before creating
- `9bfb470` - Fix: Use collection-specific folder IDs to prevent conflicts

## Stack & Dependencies
- **Frontend:** Single HTML file, Tailwind CSS, vanilla JavaScript
- **OCR:** Tesseract.js v5
- **Backend:** Supabase (Storage + Postgres)
- **Icons:** Phosphor Icons
- **View Transitions:** CSS View Transitions API for smooth animations

## Next Steps / TODO
1. **URGENT:** Investigate missing card data for `ge1tkzo1hsgv` and `enon7u070sr8`
   - Check Supabase dashboard cards table
   - Look for database backups or point-in-time recovery
   - Verify Supabase retention policies

2. **Data Recovery:**
   - If cards exist with wrong collection_id, update them
   - If permanently deleted, check if Supabase has backups
   - Consider exporting data regularly going forward

3. **Future Improvements:**
   - Add export functionality (CSV/JSON) for backup purposes
   - Consider implementing proper RLS if needed
   - Add manual "Add old collection" feature to recent collections
   - Improve error handling and user feedback for missing data

## User Context
- Has 2 old collections they want to access for notes
- Images still visible in Supabase Storage
- Plans to move all screenshots to new session going forward
- Needs simple solutions, not complex implementations
- Testing frequently on mobile
- Values backwards compatibility

## Database Migrations Log

### Migration 1: Tags Feature (Jan 16, 2026)
**Purpose:** Enable cards to appear in multiple folders simultaneously

**SQL:**
```sql
ALTER TABLE cards
ADD COLUMN tags JSONB DEFAULT '["inbox"]'::jsonb;
```

**Impact:**
- New field: `tags` (JSONB array)
- Default value: `["inbox"]` for backwards compatibility
- Code supports both old `folder_id` and new `tags` fields

### Migration 2: Soft-Delete Feature (Jan 16, 2026)
**Purpose:** 15-minute grace period before permanent deletion

**SQL:**
```sql
ALTER TABLE cards
ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;
```

**Impact:**
- New field: `deleted_at` (nullable timestamp)
- Cards with `deleted_at` timestamp are hidden from UI
- Permanent deletion happens 15 minutes after soft-delete

### Migration 3: One-Time Auto-Sort by Upload Date (Feb 9, 2026)
**Purpose:** Cards automatically sort by upload date (newest first) on creation, then allow manual reordering

**SQL:**
```sql
ALTER TABLE cards
ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
```

**Impact:**
- New field: `created_at` (timestamp with automatic NOW() default for existing rows)
- New cards use negative ID as initial `order` value (-id) so newer cards (larger IDs) appear first
- Manual drag-and-drop reordering still works via `order` field
- Removed `reindexCards()` call after upload to preserve timestamp-based order
- One-time auto-sort: cards get initial position from upload time, then manual drag takes over

**Code Changes:**
- `handleFiles()` - sets `order: -id` and `createdAt` on new cards
- `saveCardToDB()` - saves `created_at` to database
- `loadCollection()` - loads `created_at` from database
- Removed `reindexCards(INBOX_ID)` call after upload (line ~1286)

---

## Complete Database Schema (Current)

### Table: `collections`
```sql
CREATE TABLE collections (
  id TEXT PRIMARY KEY,
  name TEXT
);
```

### Table: `folders`
```sql
CREATE TABLE folders (
  id TEXT PRIMARY KEY,
  collection_id TEXT REFERENCES collections(id),
  name TEXT NOT NULL,
  "order" INTEGER DEFAULT 0,
  is_collapsed BOOLEAN DEFAULT false
);
```

### Table: `cards`
```sql
CREATE TABLE cards (
  id BIGINT PRIMARY KEY,
  collection_id TEXT REFERENCES collections(id),
  username TEXT,
  notes TEXT,
  link TEXT,
  image_path TEXT,
  folder_id TEXT,              -- DEPRECATED: kept for backwards compatibility
  tags JSONB DEFAULT '["inbox"]'::jsonb,  -- DEPRECATED: reverted to single-folder model
  "order" INTEGER DEFAULT 0,   -- Manual drag-and-drop order (negative IDs for auto-sort)
  suggestions JSONB,
  deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Storage Bucket: `images`
- Path structure: `{collection_id}/{timestamp}.png`
- Public access enabled
- No RLS policies (security via unguessable collection IDs)

---

## Important File Paths
- Main app: `/Users/imac/Documents/2026/01_VIBECODED/03_SSAVED/index.html`
- Debug tool: `/Users/imac/Documents/2026/01_VIBECODED/03_SSAVED/debug.html`
- Handover docs:
  - `SSaved App - Handover Document 01.md`
  - `SSaved App - Handover Document 02.md`
  - `Handover Document 03.md`
- Git worktree: `/Users/imac/.claude-worktrees/03_SSAVED/dazzling-payne`
- Main repo: Connected to GitHub (https://github.com/nnnephirale/ssaved-app.git)
