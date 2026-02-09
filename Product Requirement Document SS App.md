# Product Requirement Document (PRD): Instagram Profile Organizer

## 1. Product Overview
**App Name:** InstaGrid (Working Title)
**Description:** A lightweight, responsive web application serving as a "Visual CRM" for Instagram profiles. Users can batch-upload screenshots of Instagram profiles, automatically extract usernames via OCR, and organize them into a grid view with sorting, tagging, and annotation capabilities.
**Core Value Proposition:** Removes the friction of manually typing usernames from screenshots and organizing visual inspiration.

---

## 2. Technical Philosophy
* **Client-Side First:** All processing (OCR) and storage happen in the browser to ensure privacy and speed.
* **Lightweight Persistence:** Uses **IndexedDB** instead of LocalStorage to handle heavy image data without server costs.
* **Portable:** Uses a **ZIP-based Export/Import** system to move data between devices.

---

## 3. User Flow
1.  **Landing:** User opens the app (clean, empty state or loads previously saved data from IndexedDB).
2.  **Organization:** User creates a new Folder (e.g., "Competitors," "Design Inspo").
3.  **Input:** User clicks a sticky "Upload Screenshot" button.
4.  **Processing:** User selects multiple images. The app displays loading skeletons while it processes text locally.
5.  **Output:** Images appear in a 3-column grid. The Username is auto-filled, and the URL is generated.
6.  **Refinement:** User hovers over an image to delete, add notes, or drag-and-drop to reorder.
7.  **Data Safety:** Data is auto-saved. User can "Export" to download a backup `.zip` file.

---

## 4. Functional Requirements

### A. Upload & OCR Engine
* **Input:** File input accepting `.jpg`, `.png`, `.heic` (if supported). Must allow `multiple` attribute for batch uploading.
* **OCR Logic (Tesseract.js):**
    * **Cropping:** Pre-process image to scan only the top 15-20% (Header area) to improve speed and accuracy.
    * **Cleaning:** Regex filter to strip whitespace, emojis, and non-standard characters from the result.
    * **Result:** Populates the `username` field. If OCR fails, field is left empty for manual entry.

### B. The "Card" Component (UI)
Each screenshot is treated as a "Card" within the grid.
* **Visual:** Full width of the column, maintaining aspect ratio.
* **Fields:**
    * **Username:** Editable text input.
    * **Link:** Clickable anchor: `instagram.com/[username]`.
    * **Notes:** A text area (collapsible).
* **Hover Actions (Overlay):**
    * **Trigger:** On mouse enter, an overlay appears (70% Opacity Black).
    * **Button 1 (Move):** Crosshair icon. Handle for drag-and-drop reordering.
    * **Button 2 (Notes):** Pencil icon. Toggles visibility of the notes input field below the link.
    * **Button 3 (Delete):** Red trash bin icon. Prompts confirmation, then removes card.

### C. Grid & Layout (Auto Layout)
* **Library:** `dnd-kit` (recommended) or `react-beautiful-dnd`.
* **Structure:** CSS Grid with 3 columns (`grid-cols-3`) on desktop.
* **Responsiveness:**
    * Desktop: 3 Columns.
    * Tablet: 2 Columns.
    * Mobile: 1 Column.
* **Behavior:** "Auto Layout" style. If Card 1 is dragged to position 3, Card 2 shifts to position 1 automatically.

### D. Folders (Collapsible Tables)
* **Structure:** A parent container holding a specific array of Cards.
* **Header:**
    * **Title:** Editable Folder Name.
    * **Toggle:** Chevron icon to Collapse/Expand the section.
    * **Count:** Displays number of images in folder (e.g., "12 items").
* **Default:** New uploads route to the currently active folder.

---

## 5. Data Architecture (Persistence)

To maintain a "lightweight" feel while storing images, we use a decoupled IndexedDB approach.

### A. Database Schema (IndexedDB)
We use two object stores to separate heavy blobs from lightweight metadata.

**Store 1: `metadata`**
* **Purpose:** Fast loading of the UI structure.
* **Data:**
    ```json
    {
      "id": "uuid_1",
      "folderId": "folder_A",
      "username": "simon_sinek",
      "notes": "Good bio structure",
      "imageId": "img_ref_1",
      "order": 0
    }
    ```

**Store 2: `images`**
* **Purpose:** Storage of raw binary data.
* **Key:** `img_ref_1`
* **Value:** `Blob` (The raw PNG/JPG file).
* **Loading Strategy:** Images are lazy-loaded. We generate a `URL.createObjectURL(blob)` only when the specific card is mounted in the viewport.

### B. Export / Import System (ZIP)
Since JSON cannot efficiently handle megabytes of image data, we use a ZIP archive strategy.

* **Export Flow:**
    1.  Fetch all metadata + all image blobs from IndexedDB.
    2.  Generate `data.json` containing the metadata.
    3.  Generate an `images/` folder containing the blobs.
    4.  Zip them using `JSZip` and trigger download of `backup.zip`.
* **Import Flow:**
    1.  User uploads `.zip`.
    2.  App extracts `data.json` to rebuild state.
    3.  App extracts images and populates `images` store in IndexedDB.
    4.  Page reloads to reflect state.

---

## 6. Technical Stack

* **Framework:** Next.js (App Router) or Vite + React (TypeScript).
* **UI Library:** `shadcn/ui` (Components: Card, Button, Input, Dialog, Collapsible).
* **Styling:** Tailwind CSS.
* **Icons:** Lucide React (Trash, Pencil, Move/Crosshair).
* **State Management:** `zustand`.
* **OCR:** `tesseract.js`.
* **Drag & Drop:** `dnd-kit`.
* **Storage Utils:** `idb` (IndexedDB wrapper), `jszip`, `file-saver`.

## 7. Future Roadmap (Post-MVP)
* **Tagging System:** Add a `tags` array to the metadata schema to allow filtering across folders.
* **Global Search:** Search bar to filter cards by username, notes, or tags.
* **Dark Mode:** Toggle (standard with shadcn).