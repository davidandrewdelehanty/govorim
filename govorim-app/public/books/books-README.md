# Pre-loaded books library

Books in this folder are served at `/books/` and appear in the "Or pick from
the library" dropdown on the Read mode picker. Organize them into category
subfolders — the dropdown groups them automatically.

## Folder structure

```
public/books/
├── README.md
├── index.json              ← auto-generated, but your edits are preserved
├── novel/
│   ├── tolstoy-anna.epub
│   └── dostoevsky-idiot.epub
├── lyrics/
│   └── tsoi-songs.epub
├── poetry/
│   └── akhmatova-poems.epub
└── short-stories/
    └── chekhov-stories.epub
```

## How to add a book

1. **Drop the file into the right subfolder** under `public/books/`.
   - Novels → `public/books/novel/`
   - Song lyrics → `public/books/lyrics/`
   - Poetry → `public/books/poetry/`
   - Short stories → `public/books/short-stories/`
   - Anything else / unsure → drop directly into `public/books/` (it'll go to "Other" until you move it)
2. **Commit and push to GitHub** — that's it.

When Vercel builds, the `prebuild` script (`scripts/generate-books-manifest.js`)
scans every subfolder, rebuilds `index.json`, and infers the category from the
folder name. The book appears in the dropdown with an auto-derived title (e.g.
`dostoevsky-idiot.epub` → "Dostoevsky Idiot"). To get a nicer title, edit
`index.json` after the script has run (your edits will be preserved on the
next build).

Supported file formats: `.epub`, `.fb2`, `.fb2.zip`, `.txt`, `.html`, `.htm`,
`.xhtml`.

### Run locally before pushing

```bash
npm run books
```

This regenerates `index.json` from whatever's currently in the folder tree.

## Folder names → categories

The script reads the immediate subfolder name and maps it to a category like
this (case-insensitive, multiple aliases supported):

| Folder name(s) | Becomes category |
|---|---|
| `novel`, `novels` | Novel |
| `lyrics`, `song-lyrics`, `songs` | Song Lyrics |
| `poetry`, `poems` | Poetry |
| `short-stories`, `stories` | Short Stories |
| (no subfolder, or any other folder name) | Other |

To add a new category, edit the `FOLDER_TO_CATEGORY` map at the top of
`scripts/generate-books-manifest.js` and also add the new name to the
`CATEGORIES` array in `App.jsx` (search for `Pre-loaded library`).

## Customizing entries

`index.json` is the source of truth for what shows in the dropdown.
The auto-generator preserves any fields you've added by hand — it only
fills in missing entries and removes deleted-file entries.

So you can edit `index.json` after running the script to set author,
description, etc. Those edits stick on the next run.

### Schema

| Field | Required | What it does |
|-------|----------|--------------|
| `filename` | yes | Path within `public/books/` (e.g. `lyrics/tsoi-songs.epub`) |
| `title` | yes (auto-filled) | Display title |
| `author` | no | Author byline shown under the title |
| `description` | no | One-line note shown in small text |
| `category` | no (auto-filled from folder) | One of `Novel`, `Song Lyrics`, `Poetry`, `Short Stories`. Anything else (or missing) goes in an "Other" group at the bottom. Set manually in JSON if you want to override the folder-derived value. |
| `splitByNumberedSections` | no | If `true`, re-split chapters using digits-on-own-line as boundaries (for song collections like Tsoi) |

### Example

```json
[
  {
    "filename": "novel/tolstoy-anna.epub",
    "title": "Анна Каренина",
    "author": "Лев Толстой",
    "category": "Novel"
  },
  {
    "filename": "lyrics/tsoi-songs.epub",
    "title": "Песни Виктора Цоя",
    "author": "Виктор Цой",
    "description": "Lyrics — each song is a chapter",
    "category": "Song Lyrics",
    "splitByNumberedSections": true
  }
]
```

## File size limits

- Each file: 100MB max (Vercel limit)
- Total across all files: counts against your monthly bandwidth (100GB on Hobby, 1TB on Pro)

## Where to find Russian texts

- [Project Gutenberg Russian](https://www.gutenberg.org/browse/languages/ru) — public domain classics, free, no copyright issues
- Librusec / Flibusta — large catalogs but check copyright status
- Litres — paid catalog with DRM-free options
