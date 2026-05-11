# Pre-loaded books library

Files in this folder are served directly by Vercel at `/books/`.
The app shows them as a clickable list on the EPUB picker screen.

## How to add a book

1. Drop the `.epub` file into this folder. Example: `dostoevsky-idiot.epub`
2. Edit `index.json` and add an entry for it.
3. Commit and push to GitHub. Vercel auto-deploys.

## index.json schema

Each entry is an object with these fields:

| Field | Required | What it does |
|-------|----------|--------------|
| `filename` | yes | Filename in this folder (e.g. `tsoi-songs.epub`) |
| `title` | recommended | Display title shown in the picker |
| `author` | optional | Author byline shown under the title |
| `description` | optional | One-line note shown in small text |
| `splitByNumberedSections` | optional | If `true`, re-split chapters using digits-on-own-line as boundaries (for song collections like Tsoi) |

## Example

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
- Total across all files: counts against your monthly bandwidth
  (100GB on Hobby tier, 1TB on Pro)

## Where to find Russian EPUBs

- [Project Gutenberg Russian](https://www.gutenberg.org/browse/languages/ru)
  — public domain classics, free, no copyright issues
- [Librusec / Flibusta] — large catalogs but check copyright status
- Litres — paid catalog with DRM-free options
