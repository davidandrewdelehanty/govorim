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

**Alignment is no longer required.** A chapter JSON needs only `audio_url`; the
reader stopped using `fragments`/`word_timings` when read-along highlighting was
removed. `tools/add_plain_book.py` puts a book in the catalogue in one command —
no MFA, no GPU, no WSL.

### Live now (added 19 Aug)

| Book | Chapters |
|---|---|
| Отцы и дети — Тургенев | 28 |
| Смерть Ивана Ильича — Толстой | 12 |
| Мёртвые души — Гоголь | 11 |

### Blocked on audio↔FB2 pairing

`add_plain_book.py` refuses to write when the audio file count and the FB2
chapter count disagree, because that mismatch silently pairs every chapter with
the wrong recording. Five books are in that state:

| Book | Audio | FB2 | Why | Fix |
|---|---|---|---|---|
| Капитанская дочка | 14 | 15 | FB2's 15th is `ПРИЛОЖЕНИЕ. ПРОПУЩЕННАЯ ГЛАВА`, not in the recording | Pair the first 14 and leave the appendix text-only (a `null` chapter entry, as Вишнёвый сад already has) |
| Доктор Живаго | 17 | 232 | Audio is by **часть**; the FB2 splitter descends to leaf chapters. The two книги have 7 + 10 части = **17** | Count at nesting depth 2 instead of leaves |
| Горе от ума | 4 | 62 | Audio is by act; the FB2 splits by явление. Top level has 4 `ДЕЙСТВИЕ` sections plus an untitled preamble and `Действующие лица` | Take the 4 `ДЕЙСТВИЕ` top-level sections |
| Братья Карамазовы | 104 | 97 | Book 6 ch. 2–3 are read as 9 lettered files (а/б/в/г, д/е/ж/з/и); the FB2 has them as 2 chapters. 97 − 2 + 9 = 104 | Concat those 9 MP3s into 2, giving 97 |
| Тихий Дон | 232 | 235 | 3 chapters have no audio. Audio per часть: 23/21/24/21/31/65/29/18 | Compare against the FB2's per-часть counts to find the gaps |

The real shape of the remaining work is **pairing audio to chapters**, not
alignment. Only Карамазовы needs the audio itself touched.

### Then

1. **Лошадиная фамилия** — single story, audio not yet uploaded. One
   `stage_audio_upload.py` entry plus `add_plain_book.py` and it is live.
2. **Eight single-file recordings** still need cutting into chapters/acts before
   they can be added: Ревизор, Три сестры, Женитьба, Гроза, Горе от ума (radio),
   Лес, Бесприданница, Дети подземелья. `chop_aligned.py` cannot help — it reads
   boundaries out of alignment JSONs and these have none, so it is
   `chop_by_transcript.py` (Whisper) or cut points by ear.
3. **Blocked.** `finist` — audio, no FB2. `cement gadkov` — three files that do
   not add up; needs a listen.
4. **Optional upgrades** to books already live: Онегин has a 33-file reading
   against the 8 chapters in use; Война и мир 723 files against 361; Чайка a
   10-file version against the 5-chapter cut.

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
