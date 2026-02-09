# SSaved App - Development Log

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
