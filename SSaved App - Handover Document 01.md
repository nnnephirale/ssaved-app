# SSaved App – Comprehensive Handover Document

**Current Version:** v4.8 (Cursor Fix & Final Polish)
**Project Type:** Local-first, Single-file HTML/JS Web Application
**Core Stack:** Tailwind CSS (CDN), Tesseract.js (OCR), JSZip (Persistence), Phosphor Icons, IndexedDB.

---

## 1. Executive Summary & Core Philosophy
**SSaved** is a minimalist tool designed to organize Instagram profile screenshots. It scans images for usernames using OCR, allows for fluid reordering, and persists data locally.

**Design Philosophy:** "Linear-adjacent." The UI prioritizes:
* **Minimalism:** White/Slate-50 palette, subtle borders, high whitespace.
* **Optimistic UI:** No "Are you sure?" delete popups. Actions are instant, with a non-intrusive "Undo" mechanism.
* **Fluidity:** Items do not snap into place; they slide. Restored items fade in. The interface feels "alive."
* **Invisible Interface:** Controls (like Delete or Drag handles) often only appear on hover.

---

## 2. Technical Evolution (The "Why" behind the Code)

### Phase 1: Core Mechanics (v1 - v2.6)
* **OCR:** Implemented Tesseract.js to read usernames from cropped headers (top 20% of image).
* **Persistence:** Moved from `localStorage` to **IndexedDB** to handle binary image data (blobs) without hitting quota limits.
* **Ghost Inputs:** Created inputs that blend into the background (`text-slate-400`) until interacted with (`text-slate-900`), mimicking the `@` symbol style.

### Phase 2: Interaction Design (v3.0 - v3.5)
* **View Transitions:** Integrated the browser `View Transition API` to animate DOM changes (sorting, deleting, restoring) automatically.
* **Undo Stack:** Implemented a `deletedCardsStack` array. This allows infinite undo. When an item is restored, it remembers its original `order` index and slides back into the exact position it left.
* **Visual Feedback:** Restored items receive a temporary "Rose" shadow/glow (`shadow-rose-400`) to indicate their return. This glow is programmatically removed (`onmouseenter`) once the user acknowledges the item.

### Phase 3: The Drag & Layout Overhaul (v3.6 - v4.8)
* **Aspect Ratio:** Switched from `4:5` to `9:16` to better accommodate mobile screenshots.
* **Fluid Reorder:** Instead of standard drag-and-drop swapping, we implemented a **Neighbor Shift** logic. When dragging Card A over Card B, Card B slides (via CSS transform) to visually make room, rather than shrinking or snapping.
* **Cursor Wars:** We struggled with browser native drag overriding CSS cursors.
    * *Solution (v4.8):* We apply a `.global-dragging` class to the `<body>` on `dragstart`. This class uses `* { cursor: grabbing !important }` to force the "Closed Hand" cursor globally, ensuring consistent feedback.

---

## 3. Current Feature Set & Implementation Details

### A. Hybrid Responsive Layout
To satisfy the need for density on mobile vs. control on desktop, we split the logic:
1.  **Mobile (< 768px):** Uses a **Segmented Toggle** in the header (1 | 2 | 3 Columns). This forces CSS classes (`grid-cols-1`, etc.).
2.  **Desktop (≥ 768px):** Uses a **Width Slider**. This adjusts the `max-width` pixel value of the main container. The grid columns respond automatically (`md:grid-cols-2 lg:grid-cols-3`) based on available space.

### B. Drag & Drop Logic
Located in `handleDragStart`, `handleDragOver`, and `handleDropSort`.
* **Smart Click:** We differentiate between a "Click" (open link) and a "Drag" (reorder). If the mouse moves more than a threshold or the drag event fires, the click event is suppressed or ignored.
* **Global Overlay:** A "Drop images here" overlay appears *only* when dragging external files into the window (checking `e.dataTransfer.types`). It ignores internal card reordering.

### C. Data Structure
Currently a flat array stored in `appData.cards`.
```javascript
{
    id: 1709..., // Timestamp based ID
    order: 0,    // Sort index
    file: Blob,  // The image
    username: "name",
    notes: "...",
    isRestored: false, // Flag for the red glow effect
    suggestions: []    // OCR word guesses
}

## 4. Roadmap: The Folder System
**Status:** Planned / Not Started.
**Goal:** Move from a flat grid to a categorized structure.

### The Vision
Instead of "Folders" looking like OS directories, they should function as **Collapsible Sections** within the main view (similar to Notion toggles or grouped tables).

### Specifications
* **The "Inbox" Concept:**
    * The default state for new uploads is an "Inbox" or "Unsorted" section at the top.
    * Users create custom sections (e.g., "Inspo", "Recipes", "Tech").
* **Visuals:**
    * **Header:** Clean, simple text headers: `> Folder Name (3)`.
    * **No Skeuomorphism:** Avoid "tab" shapes. Stick to the "Linear" aesthetic.
* **Interaction:**
    * **Drag V2:** Users must be able to drag a card *out* of the Inbox and *into* a Folder header (which should expand or highlight on hover).
    * **Reorder:** Folders themselves should be draggable to reorder the sections.
* **Data Migration Strategy:**
    * The data structure needs to shift from a flat list to a nested structure or a tagged structure.
    * **Recommendation:** Add a `folderId` property to every card. Create a separate `folders` array in `appData`.
    * **Render Logic:** The `render()` function will need to loop through the `folders` array, rendering a container for each, then filtering the cards that belong to that folder.

---

## 5. Known Issues & Quirks

### Cursor "Crosshair" vs "Grabbing"
The user originally requested a "Crosshair" cursor for dragging. Due to browser inconsistencies, we forced "Grabbing" (Closed Hand) in v4.8 as it is more reliable. **Do not revert to 'move' or 'crosshair' without testing across different browsers.**

### Monolithic Render
The `render()` function rebuilds the entire DOM string on every change (drag, edit, delete). As the library grows, this will cause performance issues.
* **Fix:** When implementing Folders, refactor to update only specific DOM nodes or use a lightweight Virtual DOM library.

### Undo Stack Persistence
The Undo stack (`deletedCardsStack`) is currently in memory (RAM) only. If the user refreshes the page, the Undo history is lost.
* **Future Fix:** Persist the Undo stack to IndexedDB if session permanence is required.

---

## 6. Key Code Snippets for Quick Reference

**The Cursor Fix (CSS):**
/* Overrides browser native drag cursor */
body.global-dragging, body.global-dragging * {
    cursor: grabbing !important;
}


**The Neighbor Shift Logic (JS):**
function applyRangeShifts(fromIndex, toIndex) {
    // Logic to calculate which cards sit between the drag source
    // and the target, and shifting them left/right visually
    // to create the "making room" effect.
    // See: applyRangeShifts() function in code.
}

// Desktop Slider
function updateContainerWidth(val) { ... }

// Mobile Toggle
function setColumns(count) { ... } 
// Note: These two coexist. The slider sets pixel width,
// the toggle forces grid-template-columns classes.

