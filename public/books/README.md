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
├── lyrics/
├── poetry/
├── short-stories/
└── plays/
```

## How to add a book

1. **Drop the file into the right subfolder** under `public/books/`.
   - Novels → `public/books/novel/`
   - Song lyrics → `public/books/lyrics/`
   - Poetry → `public/books/poetry/`
   - Short stories → `public/books/short-stories/`
   - Plays → `public/books/plays/`
   - Anything else / unsure → drop directly into `public/books/` (it'll go to "Other" until you move it)
2. **Commit and push to GitHub** — that's it.

The `prebuild` script (`scripts/generate-books-manifest.js`) scans every
subfolder during the Vercel build, rebuilds `index.json`, and infers the
category from the folder name. Auto-derived titles work for most files; edit
`index.json` afterward for nicer titles, author bylines, or per-song metadata.
Your manual edits are preserved across regenerations.

Supported file formats: `.epub`, `.fb2`, `.fb2.zip`, `.txt`, `.html`, `.htm`,
`.xhtml`.

### Run locally before pushing

```bash
npm run books
```

## Folder names → categories

| Folder name(s) | Becomes category |
|---|---|
| `novel`, `novels` | Novel |
| `lyrics`, `song-lyrics`, `songs` | Song Lyrics |
| `poetry`, `poems` | Poetry |
| `short-stories`, `stories` | Short Stories |
| `plays`, `play`, `drama` | Plays |
| (no subfolder, or any other folder name) | Other |

To add a new category, edit the `FOLDER_TO_CATEGORY` map at the top of
`scripts/generate-books-manifest.js` AND add the new name to the `CATEGORIES`
array in `App.jsx` (search for `Pre-loaded library`).

## Schema (index.json)

| Field | Required | What it does |
|-------|----------|--------------|
| `filename` | yes | Path within `public/books/` (e.g. `lyrics/tsoi-songs.epub`) |
| `title` | yes (auto-filled) | Display title |
| `author` | no | Author byline shown under the title |
| `description` | no | One-line note shown in small text |
| `category` | no (auto from folder) | One of `Novel`, `Song Lyrics`, `Poetry`, `Short Stories`, `Plays`. Anything missing or unknown becomes "Other". |
| `splitByNumberedSections` | no | If `true`: split chapters at numbered markers (used for song collections); the reader will then display ONE song per screen and the chapter-nav arrows become "previous/next song" |
| `songs` | no | Array of YouTube URLs indexed by song position (0-based). Used only when `splitByNumberedSections: true`. See example below |

## Example: song collection with YouTube links

```json
{
  "filename": "lyrics/tsoi-songs.epub",
  "title": "Песни Виктора Цоя",
  "author": "Виктор Цой",
  "category": "Song Lyrics",
  "splitByNumberedSections": true,
  "songs": [
    "https://www.youtube.com/watch?v=AOnZBpAQfBA",
    "https://www.youtube.com/watch?v=Imo7LWofs1U",
    null,
    "https://www.youtube.com/watch?v=ck00BFP_alM"
  ]
}
```

The `songs` array is indexed by song position — `songs[0]` is the link for the
1st song in the book, `songs[1]` is the 2nd, and so on. Use `null` (or omit
entries) when a song doesn't have a video. The reader shows a "🎵 Listen on
YouTube ↗" button next to the song title when a URL is present.

**Important**: the order in `songs` must match the order the songs appear in
the EPUB. Open the book in the reader once to see the order before pasting
URLs. (You can also use an object form: `{ "youtube": "https://..." }` per
entry, in case you want to add more metadata fields later.)

## Example: prose (novels + short stories — combined under "Works")

```json
{
  "filename": "novel/tolstoy-anna.fb2",
  "title": "Анна Каренина",
  "author": "Лев Толстой",
  "category": "Works"
}
```

## File size limits

- Each file: 100MB max (Vercel limit)
- Total across all files: counts against your monthly bandwidth (100GB on Hobby, 1TB on Pro)

## Where to find Russian texts

- [Project Gutenberg Russian](https://www.gutenberg.org/browse/languages/ru) — public domain classics, free, no copyright issues
- Librusec / Flibusta — large catalogs but check copyright status
- Litres — paid catalog with DRM-free options
