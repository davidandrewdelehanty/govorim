# Audio backlog — where we left off

Snapshot: 19 Aug 2026. Companion to `CHAPTER_SPLITTING.md`.

## Done

- Read-along highlighting stripped from `src/App.jsx` (word-level, sentence-level,
  TTS tint, audiobook-driven auto page-flip). Alignment JSONs kept — they now
  only feed seeking and the Sentence N/M readout.
- Every book in the catalogue is one audio file per chapter or act. The five
  shared recordings (Дядя Ваня, Вишнёвый сад, Палата № 6 ×2, Чайка) were cut with
  `tools/chop_aligned.py` and uploaded to `<folder>-split/` on R2.

## In flight

Uploading 8 books' worth of already-per-chapter audio from
`C:\Users\david\Downloads\audiobooks` via `tools/stage_audio_upload.py`
(422 files, ~5 GB). Nothing is aligned or in `index.json` yet.

| R2 slug | Book | Files |
|---|---|---|
| `karamazovy` | Братья Карамазовы — Достоевский | 104 |
| `tikhy-don` | Тихий Дон — Шолохов | 232 |
| `zhivago` | Доктор Живаго — Пастернак | 17 |
| `ottsy-i-deti` | Отцы и дети — Тургенев | 28 |
| `smert-ivana-ilicha` | Смерть Ивана Ильича — Толстой | 12 |
| `mertvye-dushi` | Мёртвые души — Гоголь | 11 |
| `kapitanskaya-dochka` | Капитанская дочка — Пушкин | 14 |
| `gore-ot-uma` | Горе от ума — Грибоедов | 4 acts |

Two notes on that set:

- The `mertviye dushi` staging folder holds **two** books. Untitled `glava-N.mp3`
  files are Мёртвые души (11); the ones with a title slug after the number
  (`glava-1-serzhant-gvardii`) are Капитанская дочка (14) — whose own folder has
  the FB2 and no audio. `stage_audio_upload.py` separates them.
- Доктор Живаго's audio is by **часть**, not chapter — 17 files against a book
  with far more chapters. The FB2 has to be split to match before aligning.

## Next

1. **Align the 8 uploaded books**, one at a time (concurrent MFA runs get
   OOM-killed). Each needs its FB2 and audio in one folder; Капитанская дочка's
   FB2 is in the `captains daughter` folder.
2. **Лошадиная фамилия — quickest win.** Already aligned (`book-ch001.json` is in
   its folder). Needs only an audio upload and an `index.json` entry.
3. **Eight single-file recordings**: align, then `chop_aligned.py`. Ревизор,
   Три сестры, Женитьба, Гроза, Горе от ума (radio), Лес, Бесприданница,
   Дети подземелья.
4. **Blocked.** `finist` — 126 MB of audio, no FB2, nothing to align against.
   `cement gadkov` — three files (one 61-min, plus a 2-part set totalling 68 min);
   different lengths, and both far too short for the novel. Needs a listen.
5. **Optional upgrades** to books already live: Онегин has a 33-file reading
   staged against the 8 chapters in use; Война и мир 723 files against 361;
   Чайка a 10-file version against the 5-chapter cut.

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
