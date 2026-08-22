# Dual-language display (Russian text + English underneath)

How the Bible does it, and what has to change to reuse it for prose.

## The Bible mechanism

**Data.** Two static assets under `public/books/`:

- `bible-en/<NN-NN>.json` — one file per chapter (1189 of them), a flat map of
  verse number to English text:
  `{"1": "In the beginning…", "2": "The earth was formless…"}`
- `bible-headings-en.json` — one shared map for section headings,
  Russian to English: `{"Сотворение мира": "The Creation of the World", …}`

The English is the World English Bible (public domain), which is why it can be
shipped as a static asset at all.

**Loading** (`src/App.jsx`, two effects around the "Dual-language Bible" comment):

- The chapter key is derived from the audiobook path, not the book title:
  `chapters[cidx]` is matched against `/bible-nrp\/(\d+-\d+)\.json/`, and the
  captured `NN-NN` is fetched from `/books/bible-en/<key>.json` into `bibleEn`.
  State is cleared on every chapter change, so a non-Bible book shows nothing.
- The headings map loads once into `bibleHeadings` and is reused for all chapters.

**Rendering** (the paragraph renderer, `bibleEnLine` / `bibleHeadingLine`):

- Each paragraph's leading verse number is read with `/^\s*(\d+)/`.
- Strip that number; if the remainder is a key in `bibleHeadings`, the paragraph
  is a section heading and gets the heading translation.
- Otherwise, if the paragraph has a verse number present in `bibleEn`, it gets
  that verse's English.
- Dedup guard: headings get merged into a fake verse sharing the next verse's
  number, so English attaches only to the LAST paragraph carrying a given number.
- The English is emitted INSIDE the same `<p>` as the Russian, after the tokens:
  `<span className="bible-en">…</span>`.

**Styling** (`.bible-en`):
`display:block` is what puts it on its own line under the Russian; then
`font-size:0.9em`, `font-style:italic`, `margin-top:3px`, and ~50% opacity so it
reads as subordinate. `.bible-heading-en` overrides to upright + semibold.

**Invariant worth preserving:** the English is display-only. It is never
tokenized, never clickable, and never touches the aligner — audio, word-click
definitions and highlighting all stay on the Russian. That is what keeps the
feature from interfering with anything else.

## What changes for prose (Москва–Петушки)

The Bible pairs by verse number. Prose has no such key, so the join has to be
positional: Russian paragraph *n* of a chapter pairs with English paragraph *n*.

That makes paragraph counts the whole ballgame. The build step must, per chapter:

1. Split the English source into the same 44 chapters as the FB2.
2. Split each chapter into paragraphs.
3. Compare the count against the FB2 chapter's paragraph count and **report any
   chapter where they differ** rather than silently pairing off-by-one — a single
   merged or split paragraph shifts every translation after it.

Output shape can stay identical to the Bible's, keyed by paragraph index instead
of verse number: `public/books/petushki-en/<NN>.json` = `{"0": "…", "1": "…"}`.
Then the renderer needs only a second lookup path alongside `bibleEn`, reusing
`.bible-en` (or a renamed shared class) for the styling.
