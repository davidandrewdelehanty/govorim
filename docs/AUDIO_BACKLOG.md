# Audio backlog — where we left off

Snapshot: 19 Aug 2026. Companion to `CHAPTER_SPLITTING.md`.

## Done

- Read-along highlighting stripped from `src/App.jsx` (word-level, sentence-level,
  TTS tint, audiobook-driven auto page-flip). Alignment JSONs kept — they now
  only feed seeking and the Sentence N/M readout.
- Every book in the catalogue is one audio file per chapter or act. The five
  shared recordings (Дядя Ваня, Вишнёвый сад, Палата № 6 ×2, Чайка) were cut with
  `tools/chop_aligned.py` and uploaded to `<folder>-split/` on R2.

## Uploaded, not yet aligned

422 files (~5 GB) uploaded from `C:\Users\david\Downloads\audiobooks` on 19 Aug
via `tools/stage_audio_upload.py`. The audio is on R2; nothing is aligned and
nothing is in `index.json` yet, so none of it is visible in the reader.

| R2 slug | Book | Files | Renamed staging copy |
|---|---|---|---|
| `karamazovy` | Братья Карамазовы — Достоевский | 104 | `~/upload-staging/karamazovy` |
| `tikhy-don` | Тихий Дон — Шолохов | 232 | `~/upload-staging/tikhy-don` |
| `zhivago` | Доктор Живаго — Пастернак | 17 | `~/upload-staging/zhivago` |
| `ottsy-i-deti` | Отцы и дети — Тургенев | 28 | `~/upload-staging/ottsy-i-deti` |
| `smert-ivana-ilicha` | Смерть Ивана Ильича — Толстой | 12 | `~/upload-staging/smert-ivana-ilicha` |
| `mertvye-dushi` | Мёртвые души — Гоголь | 11 | `~/upload-staging/mertvye-dushi` |
| `kapitanskaya-dochka` | Капитанская дочка — Пушкин | 14 | `~/upload-staging/kapitanskaya-dochka` |
| `gore-ot-uma` | Горе от ума — Грибоедов | 4 acts | `~/upload-staging/gore-ot-uma` |

Each staging folder holds the renamed audio (`001.mp3`, `002.mp3`, …) plus a
`manifest.tsv` mapping every new name back to its original filename. Those
folders are what Auto-MFA should point at — drop the book's FB2 in beside the
audio and they are ready to align. Note `~` here is the WSL home
(`/home/david`), not the Windows one.

Two notes on that set:

- The `mertviye dushi` staging folder held **two** books. Untitled `glava-N.mp3`
  files are Мёртвые души (11); the ones with a title slug after the number
  (`glava-1-serzhant-gvardii`) are Капитанская дочка (14) — whose own folder has
  the FB2 and no audio. They were separated on upload.
- Доктор Живаго's audio is by **часть**, not chapter — 17 files against a book
  with far more chapters. The FB2 has to be split to match before aligning.

## Next

**Alignment is no longer required.** A chapter JSON needs only `audio_url`.
`tools/add_plain_book.py` puts a book in the catalogue in one command — no MFA,
no GPU. It verifies the audio file count against the FB2 chapter count using
Auto-MFA's `app/fb2.py`, which is the splitter `src/App.jsx` mirrors; counting
with anything else checks the wrong thing (the two disagree on Горе от ума by
more than twofold).

### Live (8 books added 19 Aug)

| Book | Chapters | Notes |
|---|---|---|
| Тихий Дон — Шолохов | 232 | |
| Братья Карамазовы — Достоевский | — | *pending: audio merge, see below* |
| Доктор Живаго — Пастернак | 17 | FB2 flattened to части; the 1988 `К ЧИТАТЕЛЮ` foreword dropped |
| Отцы и дети — Тургенев | 28 | |
| Капитанская дочка — Пушкин | 15 | ch15 `ПРОПУЩЕННАЯ ГЛАВА` is text-only — audio wanted |
| Смерть Ивана Ильича — Толстой | 12 | |
| Мёртвые души — Гоголь | 11 | |
| Горе от ума — Грибоедов | 5 | ch1 `Действующие лица` text-only by choice; acts 1–4 carry the audio |

Живаго's 17 pairings were checked by title, not just by count — the audio
filenames carry часть names (`kniga-2-chast-9-varykino` ↔ `ЧАСТЬ девятая.
ВАРЫКИНО`) and all 17 line up.

### Still to do

1. ~~**Братья Карамазовы**~~ — done, and it needed no audio work. The recording
   is *finer* than the markup: Book 6 chapters 2–3 are read as 9 lettered files,
   and those sections are in the FB2 as ordinary paragraphs ("а) О юноше брате
   старца Зосимы"). `regroup_fb2.py --split` promotes them to chapter breaks,
   giving 104 to match the 104 recordings. Chapters take their lettered heading
   as their title.
2. **Капитанская дочка ch15** — `ПРИЛОЖЕНИЕ. ПРОПУЩЕННАЯ ГЛАВА`, ~19k chars
   (20–25 min read). Real Pushkin, opens "Мы приближались к берегам Волги…".
   Text-only until a recording turns up.
3. **Лошадиная фамилия** — already aligned, audio not uploaded. Quickest win left.
4. **Eight single-file recordings** need cutting before they can be added:
   Ревизор, Три сестры, Женитьба, Гроза, Горе от ума (radio), Лес,
   Бесприданница, Дети подземелья. `chop_aligned.py` can't help — they have no
   alignment JSONs to read boundaries from.
5. **Blocked.** `finist` — audio, no FB2. `cement gadkov` — three files that
   don't add up; needs a listen.
6. **Optional upgrades**: Онегин has a 33-file reading against the 8 chapters in
   use; Война и мир 723 against 361; Чайка a 10-file version against 5.

### Fixed along the way

- **Notes sections misparsed as chapters.** `_NOTES_TITLE_RE` was anchored at the
  start of the title, so Тихий Дон's `*\u00a0ПРИМЕЧАНИЯ\u00a0*` (77 editorial
  footnotes) became chapter 233 and looked like a chapter with missing audio.
  Leading/trailing decoration is now matched explicitly — not with `\W`, which in
  JS also matches Cyrillic and would have let "ЛОЖНЫЕ ПРИМЕЧАНИЯ" through. Fixed
  in `src/App.jsx` and Auto-MFA `app/fb2.py`, which are meant to stay identical.
  Across every FB2 in the library it changes exactly that one title.
- **Definitions were calling a retired Gemini model.** `GEMINI_MODEL` was pinned
  to `gemini-2.0-flash`. Default is now `gemini-3.6-flash`, the thinking-disabled
  guard covers 2.5–2.9 and any major version from 3 up, and a 404 about a model
  now names the env var to change.

### Война и мир was paired against the wrong recording (fixed)

Chapter 1 played "Глава вторая". Two rips of the book exist in
`Downloads/audiobooks/war and peace/`: a 361-file set at the top level, and
`old with narrator comments/` with 362. The alignment JSONs were transcribed
from the **old** set (spoken title cards, chapter announcements, translator's
footnotes read aloud); the **new** set is what sits on R2, where `NNN.mp3` is
simply chapter NNN. The index had been built for the old numbering, so every
chapter played the next one's audio.

Confirmed by duration, not guesswork: new `002.mp3` is 510.59s — the 8:30 that
was heard — and new *N* tracks old *N+1* across the whole book (sampled at
chapters 1–12, 180, 300, 361), with the old always longer by the narrator
comments.

Fix: chapter list is now `001.json`–`361.json`, and those JSONs were rewritten
as plain `audio_url` records. Stripping the old transcripts mattered beyond
tidiness — `word_timings` still feed the exercise-clip 🔊 button, and timings
from a different recording would have sought to the wrong passage. The folder
went from ~100 MB to 1.5 MB. `362.json` is now an unreferenced orphan.

### Library-wide pairing audit

Every book's stored transcript was fuzzy-matched against the FB2 chapter it is
paired with. All clean except the cases below, which are now fixed:

- **Записки из подполья** — 68 FB2 chapters against 18 recordings. The FB2 is a
  *collection*: chapters 1–22 are the novel, 23–68 are Петербургские сновидения,
  Крокодил and others. And the recording is a LibriVox reading split by session,
  not by chapter — one file covers I+II, the next III+IV, and Part II chapter 1
  runs across two files ("Глава 1. Продолжение"). Decoded from the "End of
  chapter N" markers in the transcripts, then rebuilt with `tools/regroup_fb2.py`
  into `underground-grouped.fb2`: 18 chapters, exactly matching the 18
  recordings. Verified by content — 16 of 18 recordings open on their chapter's
  first words, and the other two are Whisper mis-hearings ("накончалась" for
  "но кончалась") that a second method placed correctly.
- **Анна на шее** — FB2 split into 2 chapters against 1 recording; regrouped into
  one.
- **Евгений Онегин** — a false alarm. Pairing is correct; the recordings just
  open a couple of lines into each chapter, from the LibriVox preamble trims.
- **Студент**, **Братья и сёстры!**, **Радиоспектакль «Чайка»** — low scores from
  spoken intros and dramatised dialogue, not mispairing.

- **Библия** — 1952 FB2 chapters against 1189 recordings; everything after
  Genesis 3 was mispaired. The FB2 nests as Testament > group > book > chapter >
  heading-section, and the reader's splitter descends to the heading sections, so
  "Каин и Авель" and "Потомки Каина" became two chapters when both are Genesis 4.
  The book level carries the truth: each book section has exactly as many child
  sections as the book has chapters. `tools/regroup_bible.py` rebuilds at that
  level, giving 1189 — with two structural exceptions, Псалмы (subdivided into
  the Psalter's five books, so its chapters sit one level deeper) and Откровение
  (whose chapters are promoted to the book level). Verified against the
  recordings: 95% of chapters open on the same words, and every straggler is the
  same chapter with the reading announcing "Псалтырь, книга первая, псалом
  первый" first. Chapters are now titled "Бытие 1", "От Луки 13" and so on.

  This also repairs the **dual-language English text**, which is keyed off the
  audio path — with 1952 chapters against 1189 audio entries, most chapters were
  showing the wrong English verses or none.

**Paragraphs.** The first `regroup_fb2.py` rebuilt chapters from
Auto-MFA's `extract_chapters`, whose text has paragraph breaks already collapsed
— fine for aligning audio, destructive for rebuilding a document. It turned each
chapter into one giant paragraph. The tool now copies the original XML elements,
like `flatten_fb2.py` and `regroup_bible.py` always did, and refuses to run when
the leaf-section count and the reader's chapter count disagree (the case where
group numbers would not mean what you think). Подполье, Анна на шее and
Карамазовы were regenerated: 490, 73 and 5041 paragraphs respectively.

**Orphan FB2s.** `scripts/generate-books-manifest.js` runs on every Vercel build
and auto-adds any book file under `public/books/` (it skips only dot-prefixed
names). Every FB2 replaced by a regrouped version would therefore have come back
as a duplicate book. Superseded originals now live in `_superseded-fb2/` outside
`public/`, and `_pending-fb2/` holds the Karamazov FB2 until its audio is merged.
That also cleared a pre-existing duplicate: `Ф Достоевский - Идиот.fb2` sat
beside the `idiot.fb2` actually in use.

### Pre-existing pairing gaps (not from this work)

`Анна на шее` (FB2 2 chapters / 1 audio), `Записки из подполья` (68 / 18) and
`Библия` (1952 / 1189) have more FB2 chapters than audio entries, so their later
chapters silently have no audio. Longstanding; untouched here.

## Loose ends in the repo

- `index.json` has a literal `null` chapter entry for **Вишнёвый сад** and
  **Герой нашего времени** — chapter 1 of each has no audio JSON.
- Three orphan JSONs no longer referenced by `index.json`, still pointing at the
  pre-split whole-file MP3s: `audio/vishnevy-sad-full/vishnevy-sad-full.json`,
  `audio/palata-nomera-6/palata-nomera-6-ch01.json`, `…-ch02.json`.
- The pre-split source MP3s are still on R2 (`dv-good/full.mp3`,
  `chaika-good/01.mp3`, `vishnevy-sad-full/…`, `palata-nomera-6/…-ch01,02.mp3`).
  Safe to delete once the new cuts have been listened to.
- Палата № 6 ch02: the first 6:04 belonged to no section and was dropped in the
  cut. Worth confirming that was dead air.
