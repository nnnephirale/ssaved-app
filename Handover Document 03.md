# SSaved App – Comprehensive Handover Document

**Current Version:** v5.0 (Supabase Cloud Integration)
**Project Type:** Cloud-first, Single-file HTML/JS Web Application
**Core Stack:** Tailwind CSS (CDN), Tesseract.js (OCR), Supabase (Storage + Postgres), Phosphor Icons

---

## 1. Executive Summary & Core Philosophy

**SSaved** is a minimalist tool designed to organize Instagram profile screenshots. It scans images for usernames using OCR, allows for fluid reordering, and now persists data in the cloud via Supabase, enabling access from any device via shareable URLs.

**Design Philosophy:** "Linear-adjacent." The UI prioritizes:
* **Minimalism:** Warm off-white palette (`#FAFAF8`), subtle borders, high whitespace.
* **Optimistic UI:** No "Are you sure?" delete popups. Actions are instant, with a non-intrusive "Undo" mechanism.
* **Fluidity:** Items do not snap into place; they slide. Restored items fade in. The interface feels "alive."
* **Invisible Interface:** Controls (like Delete, External Link, or Drag handles) only appear on hover.

---

## 2. Technical Evolution (The "Why" behind the Code)

### Phase 1: Core Mechanics (v1 - v2.6)
* **OCR:** Implemented Tesseract.js to read usernames from cropped headers (top 20% of image).
* **Persistence:** Moved from `localStorage` to **IndexedDB** to handle binary image data (blobs) without hitting quota limits.
* **Ghost Inputs:** Created inputs that blend into the background (`text-neutral-400`) until interacted with (`text-neutral-900`), mimicking the `@` symbol style.

### Phase 2: Interaction Design (v3.0 - v3.5)
* **View Transitions:** Integrated the browser `View Transition API` to animate DOM changes (sorting, deleting, restoring) automatically.
* **Undo Stack:** Implemented a `deletedCardsStack` array. This allows infinite undo. When an item is restored, it remembers its original `order` index and slides back into the exact position it left.
* **Visual Feedback:** Restored items receive a temporary "Rose" shadow/glow to indicate their return. This glow is programmatically removed (`onmouseenter`) once the user acknowledges the item.

### Phase 3: The Drag & Layout Overhaul (v3.6 - v4.8)
* **Aspect Ratio:** Switched from `4:5` to `9:16` to better accommodate mobile screenshots.
* **Fluid Reorder:** Instead of standard drag-and-drop swapping, we implemented a **Neighbor Shift** logic. When dragging Card A over Card B, Card B slides (via CSS transform) to visually make room, rather than shrinking or snapping.
* **Cursor Wars:** We struggled with browser native drag overriding CSS cursors.
    * *Solution (v4.8):* We apply a `.global-dragging` class to the `<body>` on `dragstart`. This class uses `* { cursor: grabbing !important }` to force the "Closed Hand" cursor globally, ensuring consistent feedback.

### Phase 4: Visual Refresh (v4.9)
* **Moodboard-Driven Redesign:** Inspired by design engineer portfolios with depth-of-field effects, warm tones, and floating elements.
* **Color Temperature Shift:** Moved from cool `slate-*` palette to warmer `neutral-*` colors.
* **Background:** Changed from flat white to subtle warm gradient (`#FAFAF8` → `#F7F6F3`).
* **Card Styling:** Increased border-radius to 20px, added layered diffused shadows, cards lift on hover (`translateY(-3px)`).
* **Header:** Frosted glass effect with `backdrop-filter: blur(20px)`.
* **Image Hover:** Subtle scale effect (`scale(1.02)`) on desktop only, disabled on touch devices.
* **External Link Button:** Added ↗ button (top-left of card) that appears on hover, replacing implicit image-click behavior.

### Phase 5: Mobile Notes Collapse (v4.9.1)
* **Problem:** Long notes waste vertical space on mobile, pushing content down.
* **Solution:** Hybrid collapse system for mobile only (<768px):
    * Notes with 3+ lines are collapsed by default with fade gradient
    * Chevron toggle (▼/▲) for manual expand/collapse
    * Dwell expansion: auto-expands if card is 60%+ visible in viewport center for 1.5 seconds
* **Desktop:** Notes always fully expanded, no collapse behavior.

### Phase 6: Supabase Cloud Integration (v5.0)
* **Motivation:** Enable access from any device via shareable URLs, eliminate device-locked data.
* **Storage Migration:** Moved from IndexedDB to Supabase Storage (images) + Supabase Postgres (metadata).
* **Authentication Model:** Secret URL only (zero friction, security via unguessable 12-character collection ID).
* **Removed:** JSZip, FileSaver.js, local import/export functionality (replaced by cloud persistence).

---

## 3. Current Feature Set & Implementation Details

### A. Cloud Storage Architecture

**Supabase Configuration:**
* **Project URL:** `https://uauqqdaalnddedgjdgcg.supabase.co`
* **Storage Bucket:** `images` (public, 10MB limit, `image/*` MIME types)

**Database Tables:**

```sql
-- collections: Each unique URL gets one collection
CREATE TABLE collections (
    id TEXT PRIMARY KEY,  -- 12-character random alphanumeric
    created_at TIMESTAMPTZ DEFAULT now()
);

-- cards: Screenshot metadata
CREATE TABLE cards (
    id INT8 PRIMARY KEY,  -- Timestamp-based ID
    collection_id TEXT REFERENCES collections(id),
    username TEXT,
    notes TEXT,
    link TEXT,
    image_path TEXT,      -- Path in storage bucket
    folder_id TEXT,
    "order" INT4,
    suggestions JSONB,    -- OCR word guesses
    created_at TIMESTAMPTZ DEFAULT now()
);

-- folders: Organizational containers
CREATE TABLE folders (
    id TEXT PRIMARY KEY,
    collection_id TEXT REFERENCES collections(id),
    name TEXT,
    "order" INT4,
    is_collapsed BOOL DEFAULT false
);
```

**RLS Policies:** All tables have `USING (true)` policy for all operations (security via unguessable URL).

**Storage Policy:**
```sql
CREATE POLICY "Allow all storage operations" 
ON storage.objects 
FOR ALL 
TO public 
USING (bucket_id = 'images')
WITH CHECK (bucket_id = 'images');
```

### B. URL-Based Collection System

**URL Structure:** `yoursite.com?c=abc123xyz456`

**Collection ID Generation:**
```javascript
function generateCollectionId() {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    let id = '';
    for (let i = 0; i < 12; i++) {
        id += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return id;
}
```

**Initialization Flow:**
1. Check URL for `?c=` parameter
2. If found, load that collection from Supabase
3. If not, check localStorage for saved collection ID
4. If neither exists, generate new collection
5. Update URL with `?c=` parameter (without page reload)

### C. Hybrid Responsive Layout
1. **Mobile (< 768px):** Uses a **Segmented Toggle** in the header (1 | 2 Columns). This forces CSS classes (`grid-cols-1`, `grid-cols-2`).
2. **Desktop (≥ 768px):** Uses a **Width Slider**. This adjusts the `max-width` pixel value of the main container. The grid columns respond automatically (`md:grid-cols-2 lg:grid-cols-3`) based on available space.

### D. Drag & Drop Logic
Located in `handleDragStart`, `handleCardDragOver`, `handleCardDrop`, and folder equivalents.
* **Card Reordering:** Neighbor shift animation within same folder.
* **Folder Transfer:** Drag card to folder tab to move between folders.
* **Global Overlay:** "Drop images here" overlay appears only when dragging external files into the window.

### E. Mobile Notes Collapse System

**CSS Classes:**
* `.notes-wrapper` — Container for notes textarea
* `.notes-wrapper.is-collapsible` — Applied when notes exceed 3 lines
* `.notes-wrapper.is-expanded` — Applied when manually or dwell-expanded
* `.notes-fade` — Gradient overlay at bottom of collapsed notes
* `.notes-toggle` — Chevron button (hidden unless `.is-collapsible`)

**JavaScript Constants:**
```javascript
const LINE_HEIGHT = 18;   // ~1.5em at text-xs
const MAX_LINES = 3;
const DWELL_DELAY = 1500; // ms before auto-expand
```

**IntersectionObserver Configuration:**
```javascript
new IntersectionObserver(callback, {
    threshold: [0, 0.6],
    rootMargin: '-20% 0px -20% 0px'  // Center bias
});
```

### F. Data Structure

**In-Memory State:**
```javascript
let appData = { cards: [], folders: [] };
let collectionId = null;

// Card object (in memory)
{
    id: 1709...,           // Timestamp-based ID
    username: "name",
    notes: "...",
    link: "https://instagram.com/name",
    imageUrl: "https://...",  // Public Supabase URL
    imagePath: "abc123/1709.png",  // Storage path
    folderId: "inbox",
    order: 0,
    suggestions: [],       // OCR word guesses
    isScanning: false,
    isRestored: false
}

// Folder object
{
    id: "inbox",
    name: "Inbox",
    order: 0,
    isCollapsed: false
}
```

---

## 4. Visual Design System

### Color Palette
* **Background:** Gradient `#FAFAF8` → `#F7F6F3`
* **Cards:** Pure white with `rgba(0,0,0,0.04)` border
* **Text:** `neutral-900` (primary), `neutral-400` (secondary), `neutral-300` (placeholder)
* **Accent:** Rose (`rose-50`, `rose-100`, `rose-400`, `rose-600`) for undo, restore states

### Card Styling
```css
.card {
    background: white;
    border-radius: 1.25rem;  /* 20px */
    border: 1px solid rgba(0, 0, 0, 0.04);
    overflow: hidden;  /* Critical for hover scale clipping */
    box-shadow: 
        0 2px 4px -1px rgba(0, 0, 0, 0.02),
        0 8px 24px -4px rgba(0, 0, 0, 0.06);
    transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), 
                box-shadow 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.card:hover {
    transform: translateY(-3px);
    box-shadow: 
        0 4px 8px -2px rgba(0, 0, 0, 0.03),
        0 16px 40px -8px rgba(0, 0, 0, 0.1);
}
```

### Header (Frosted Glass)
```css
.header-glass {
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}
```

### Image Hover Scale (Desktop Only)
```css
@media (hover: hover) and (pointer: fine) {
    .group\/image:hover .img-hover-scale {
        transform: scale(1.02);
    }
}
```

---

## 5. Key Functions Reference

### Supabase Operations
```javascript
// Save card to database
async function saveCardToDB(card) {
    const dbCard = {
        id: card.id,
        collection_id: collectionId,
        username: card.username,
        notes: card.notes,
        link: card.link,
        image_path: card.imagePath,
        folder_id: card.folderId,
        order: card.order,
        suggestions: card.suggestions
    };
    const { error } = await db.from('cards').upsert(dbCard);
    return { error };
}

// Upload image to storage
const { error } = await db.storage
    .from('images')
    .upload(imagePath, file, { contentType: file.type });

// Get public URL
function getPublicImageUrl(path) {
    return `${SUPABASE_URL}/storage/v1/object/public/images/${path}`;
}

// Delete card (with image cleanup)
async function deleteCardFromDB(id) {
    const card = appData.cards.find(c => c.id === id);
    if (card?.imagePath) {
        await db.storage.from('images').remove([card.imagePath]);
    }
    await db.from('cards').delete().eq('id', id);
}
```

### Mobile Notes Collapse
```javascript
function checkNotesCollapsible(id) {
    if (window.innerWidth >= 768) return;  // Desktop: skip
    
    const wrapper = document.getElementById(`notes-wrapper-${id}`);
    const textarea = wrapper?.querySelector('.notes-textarea');
    
    const fullHeight = textarea.scrollHeight;
    const threshold = LINE_HEIGHT * MAX_LINES;
    
    if (fullHeight > threshold) {
        wrapper.classList.add('is-collapsible');
    }
}

function initNotesObserver() {
    notesObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            const id = parseInt(entry.target.id.replace('card-', ''));
            
            if (entry.isIntersecting && entry.intersectionRatio >= 0.6) {
                // Start dwell timer
                dwellTimers.set(id, setTimeout(() => {
                    expandNotes(id);
                    dwellTimers.delete(id);
                }, DWELL_DELAY));
            } else {
                // Cancel timer
                clearTimeout(dwellTimers.get(id));
                dwellTimers.delete(id);
            }
        });
    }, {
        threshold: [0, 0.6],
        rootMargin: '-20% 0px -20% 0px'
    });
}
```

---

## 6. Known Issues & Quirks

### Image Hover Scale + Rounded Corners
The card must have `overflow: hidden` for the `border-radius` to properly clip the scaled image during CSS transforms. Without this, the image corners become square on hover.

### Cursor "Crosshair" vs "Grabbing"
The user originally requested a "Crosshair" cursor for dragging. Due to browser inconsistencies, we forced "Grabbing" (Closed Hand) in v4.8 as it is more reliable. **Do not revert to 'move' or 'crosshair' without testing across different browsers.**

### Monolithic Render
The `render()` function rebuilds the entire DOM string on every change (drag, edit, delete). As the library grows past 100+ cards, this may cause performance issues.
* **Potential Fix:** Implement keyed DOM diffing or use `content-visibility: auto` CSS property.

### Undo Stack Not Persisted
The Undo stack (`deletedCardsStack`) is in memory only. If the user refreshes, undo history is lost. Additionally, deleted images are removed from Supabase Storage immediately, so undo after refresh would fail anyway.
* **Potential Fix:** Implement soft-delete with TTL, persist undo stack to database.

### OCR CORS Requirement
The `simpleCrop()` function requires `img.crossOrigin = 'anonymous'` for Supabase-hosted images to work with canvas operations (OCR cropping).

---

## 7. Roadmap: Future Features

### Tags Instead of Folders
**Status:** Planned
**Goal:** Allow cards to belong to multiple categories.
**Approach:** Add `tags` array to card schema, render filter/toggle UI for tags.

### Search
**Status:** Planned
**Goal:** Filter cards by username and notes content.
**Approach:** Add search input in header, filter `appData.cards` on input.

### Batch Operations
**Status:** Planned
**Goal:** Select multiple cards for bulk move/delete.
**Approach:** Add selection mode toggle, shift-click for range select, floating action bar.

### Dark Mode
**Status:** Planned
**Goal:** Alternative color scheme matching moodboard's moody warm-dark aesthetic.
**Approach:** CSS custom properties for colors, toggle in header, persist preference.

### Render Performance
**Status:** Monitor
**Trigger:** If lag observed at 100+ cards.
**Options:**
1. `content-visibility: auto` (CSS, free win)
2. Keyed DOM diffing (manual implementation)
3. Pagination/infinite scroll (changes UX)
4. Lightweight virtual DOM library (adds dependency)

---

## 8. File Reference

**Current Production File:** `ssaved-supabase.html`

**Dependencies (CDN):**
* Tailwind CSS
* Tesseract.js v5
* Supabase JS v2
* Phosphor Icons

**Removed Dependencies:**
* JSZip (was for local export)
* FileSaver.js (was for local export)

---

## 9. Decisions Log

| Decision | Chosen | Reason | Rejected Alternative |
|----------|--------|--------|---------------------|
| Storage | Supabase Cloud | Cross-device access, shareable URLs | IndexedDB (device-locked) |
| Auth | Secret URL | Zero friction, matches philosophy | PIN, magic link (too much friction) |
| Offline | Cloud-only | Hybrid sync too complex | Offline-first with sync |
| Colors | Warm `neutral-*` | Moodboard direction, softer feel | Cool `slate-*` |
| Card radius | 20px | Matches moodboard aesthetic | 12px (too sharp) |
| Profile link | Explicit ↗ button | More discoverable | Image click (hidden affordance) |
| Notes collapse | Hybrid (tap + dwell) | Best of both approaches | Tap-only or dwell-only |
| Collapse scope | Mobile only | Desktop has space | Both viewports |
| Image hover | Desktop only | Touch triggers glitchy on mobile | All devices |
