# Pre-loaded books library

Files in this folder are served at `/books/`. The app shows them as a dropdown
("Or pick from the library") on the Read mode picker screen.

## How to add a book

1. **Drop the file into this folder.** Supported: `.epub`, `.fb2`, `.fb2.zip`, `.txt`, `.html`.
2. **Commit and push to GitHub** — that's it.

When Vercel builds, the `prebuild` script (`scripts/generate-books-manifest.js`)
scans this folder and rebuilds `index.json` automatically. The new book appears
in the dropdown with a title derived from its filename
(`dostoevsky-idiot.epub` → "Dostoevsky Idiot").

To get nicer titles, see "Customizing entries" below.

### Run locally

If you want to test before pushing:

```bash
npm run books
```

This regenerates `index.json` from whatever's currently in the folder.

## Customizing entries

`index.json` is the source of truth for what shows in the dropdown.
The auto-generator preserves any fields you've added by hand — it only
fills in missing entries and removes deleted-file entries.

So you can edit `index.json` after running the script to set author,
description, etc. Those edits stick on the next run.

### Schema

| Field | Required | What it does |
|-------|----------|--------------|
| `filename` | yes | Filename in this folder (e.g. `tsoi-songs.epub`) |
| `title` | yes (auto-filled) | Display title |
| `author` | no | Author byline shown under the title |
| `description` | no | One-line note shown in small text |
| `splitByNumberedSections` | no | If `true`, re-split chapters using digits-on-own-line as boundaries (for song collections like Tsoi) |

### Example

```json
[
  {
    "filename": "tolstoy-anna.epub",
    "title": "Анна Каренина",
    "author": "Лев Толстой"
  },
  {
    "filename": "tsoi-songs.epub",
    "title": "Песни Виктора Цоя",
    "author": "Виктор Цой",
    "description": "Lyrics — each song is a chapter",
    "splitByNumberedSections": true
  }
]
```

## File size limits

- Each file: 100MB max (Vercel limit)
- Total across all files: counts against your monthly bandwidth (100GB on Hobby, 1TB on Pro)

## Where to find Russian EPUBs

- [Project Gutenberg Russian](https://www.gutenberg.org/browse/languages/ru) — public domain classics, free, no copyright issues
- Librusec / Flibusta — large catalogs but check copyright status
- Litres — paid catalog with DRM-free options
