# Chapter-split audio (replaces read-along highlighting)

Highlighting is gone. Instead, every book's audio should be **one file per
chapter — or per act, for a play** — so the recording and the page stay in step
without any word-level sync.

---

## 1. Where the library stands

### Already one file per chapter — nothing to do (18 books)

| Book | Chapters |
|---|---|
| Библия. Новый русский перевод | 1189 |
| Война и мир | 361 |
| Анна Каренина | 239 |
| Денискины рассказы | 60 |
| Идиот | 50 |
| Москва — Петушки | 44 |
| Преступление и наказание | 41 |
| Мастер и Маргарита | 33 |
| Лето в пионерском галстуке | 21 |
| Записки из подполья | 18 |
| Патриот | 18 |
| Моя любимая страна | 14 |
| Собачье сердце | 10 |
| Евгений Онегин | 8 |
| Герой нашего времени | 6 |
| Дама с собачкой | 4 |
| Радиоспектакль «Дядя Ваня» | 4 acts |
| Радиоспектакль «Чайка» | 4 acts |

### Single-chapter works — one chapter, one file, nothing to do (11)

Анна на шее · Брак по расчёту · Смерть чиновника · Спать хочется · Студент ·
Тоска · Человек в футляре · Тёмные аллеи · Братья и сёстры! ·
Речь к юбилею Дня Победы (1975) · Речь к 60-летию Октябрьской революции (1977)

### Needs chopping (4 books, 5 source files)

| Book | Source on R2 | Now (length to last aligned word) | Should be | Notes |
|---|---|---|---|---|
| **Дядя Ваня** | `dv-good/full.mp3` | 1 file, ≥2:00 | 5 files | cast list + 4 acts |
| **Вишнёвый сад** | `vishnevy-sad-full/vishnevy-sad-full.mp3` | 1 file, ≥2:20 | 4 files | 4 acts |
| **Палата № 6** | `palata-nomera-6/…-ch01.mp3` | 1 file, ≥2:00 | 16 files | sections 1–16 |
| **Палата № 6** | `palata-nomera-6/…-ch02.mp3` | 1 file, ≥0:23 | 3 files | sections 17–19 |
| **Чайка** | `chaika-good/01.mp3` | 1 file, ≥0:37 | 2 files | cast list + Act 1; acts 2–4 are already separate files |

**The cut points already exist.** Every one of these chapters has an alignment
JSON whose `word_timings` are in the long file's timeline, so chapter N ends at
its last word and N+1 starts at its first. Nothing needs re-transcribing — see
`tools/chop_aligned.py` below. Whisper is only needed for *new* recordings that
have never been aligned (`tools/chop_by_transcript.py`).

### Two loose ends worth fixing while you're in here

- `index.json` has a literal `null` in the chapters array for **Вишнёвый сад**
  and **Герой нашего времени** — a chapter with no audio JSON. Harmless today,
  but it means chapter 1 of each silently has no audio.
- **Палата № 6 ch02**: sections 17–19 don't start until **6:04** into the file.
  Whatever is in those first six minutes belongs to no section (most likely a
  re-read of the end of ch01). `chop_aligned.py` will drop it. Give it a listen
  before you upload if that matters.

---

## 2. Chopping a recording that already has alignment JSONs

`tools/chop_aligned.py` reads the boundaries straight out of the chapter JSONs,
cuts with ffmpeg, and rewrites each JSON in place with times rebased to its new
file. `index.json` never changes, because the chapter JSON paths don't.

Configure the rclone remote once (nothing in the scripts holds credentials):

```bash
# WSL — one time only
rclone config create r2 s3 provider=Cloudflare \
  access_key_id=YOUR_KEY secret_access_key=YOUR_SECRET \
  endpoint=https://YOUR_ACCOUNT.r2.cloudflarestorage.com region=auto
```

Then, per book:

```bash
# WSL
cd /mnt/c/Users/david/projects/govorim-app

# 1. dry run — prints the cut table, touches nothing
python3 tools/chop_aligned.py --repo . --title "Дядя Ваня"

# 2. cut for real (downloads the source, writes MP3s, rewrites the JSONs)
python3 tools/chop_aligned.py --repo . --title "Дядя Ваня" --apply --work ~/chop

# 3. listen to the first and last 10 seconds of each piece, then upload
python3 tools/chop_aligned.py --repo . --title "Дядя Ваня" --apply --upload --work ~/chop
```

`--all` does every book that still shares a file. Do them one at a time the
first couple of times so you can hear the seams.

**What it does to each chapter JSON:** `audio_url` points at the new per-chapter
MP3, every `begin`/`end` in `fragments` (including the nested `words`) and in
`word_timings` is shifted so the file starts at 0, and `stopAtEnd` is dropped —
it existed only to stop a slice bleeding into the next one.

**Where it cuts:** exactly halfway through the gap between one chapter's last
word and the next chapter's first. The first chapter starts 1s before its first
word (so a LibriVox-style preamble is dropped); the last runs to the end of the
file. Originals on R2 are left alone — new pieces go to `<folder>-split/`, so a
bad run costs nothing.

---

## 3. Chopping a recording that has *no* alignment (new material)

`tools/chop_by_transcript.py`. Transcribe once, match the FB2's chapter/act
openings into the transcript, review, then cut.

```bash
# WSL, GPU box — the transcribe step wants CUDA
pip install faster-whisper

python3 tools/chop_by_transcript.py \
  --audio ~/new/full.mp3 --fb2 public/books/novel/some-book.fb2 --out ~/new/cuts

# -> ~/new/cuts/cuts.tsv, one row per chapter with a match score and the
#    transcript text found at that timestamp. Read it.
#    Anything marked "<-- CHECK" is a bad match: fix the start column by hand.

python3 tools/chop_by_transcript.py --audio ~/new/full.mp3 --out ~/new/cuts --cut
```

It stops in the middle on purpose. A wrong cut point that nobody looked at is
far more expensive than thirty seconds of reading the table. The transcript is
cached as `<audio>.words.json`, so re-running the matcher after an edit is free.

On CPU only, pass `--device cpu --compute-type int8 --model medium`. It works,
it's just slow — roughly real-time for `medium`.

### Rules of thumb for plays

- Acts announce themselves ("Действие первое") and match at high confidence.
- The cast list (`Действующие лица`) is its own chapter — it reads as one short
  segment before Act 1.
- Applause, music stings, and an announcer's intro sit between acts. The
  midpoint rule puts them at the *end* of the preceding act, which is usually
  what you want. Move the boundary by hand in `cuts.tsv` if you'd rather they
  led the next one.

---

## 4. After any split

Give each new piece a 10-second listen at both ends — that catches a
clipped first word or a chapter that starts mid-sentence faster than any
automated check. Then commit the rewritten JSONs and push; the MP3s live on R2,
not in the repo.
