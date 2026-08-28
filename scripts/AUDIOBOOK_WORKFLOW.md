# Adding an audiobook with sentence-level highlighting

The reader supports two playback modes for any book:

- **🤖 TTS** — Azure Dmitry reads the text. Always available. Works on any book.
- **🎧 Audiobook** — a real human narrator (typically a Soviet-era recording from archive.org) streams in sync with sentence highlighting. Has to be set up per book.

This doc walks through setting up audiobook mode for a single book.

---

## Prerequisites (one-time setup)

You need **Python with aeneas** for the alignment. Install instructions are at the top of `scripts/align-audiobook.py`. tl;dr:

```bash
# macOS
brew install espeak ffmpeg
pip install numpy aeneas

# Ubuntu / Debian
sudo apt install espeak espeak-data ffmpeg python3-pip python3-dev
pip install numpy aeneas
```

Test it works:
```bash
python scripts/align-audiobook.py --help
```

You also need **Node** (already installed for the app).

---

## Step 1 — Find the recording

Browse [archive.org](https://archive.org) for the book. Many famous Soviet-era audiobook recordings (Гоголь, Толстой, Достоевский, Чехов, Пушкин, etc.) are hosted there free.

Search terms that work:
- `Тургенев "Записки охотника" аудиокнига`
- `Гоголь Нос Смоктуновский`
- `советская аудиокнига Пушкин`

For each audiobook chapter, get its **direct download URL** (right-click "MP3" → Copy Link). It'll look like `https://archive.org/download/<item-id>/<filename>.mp3`. Save this URL — you'll embed it in the alignment JSON.

> **Tip:** Many archive.org audiobooks come as one MP3 per chapter. If the book is a single huge file, you can use FFmpeg to split it locally before aligning, then upload each piece to your own host (or skip splitting and align the whole file against the whole book).

---

## Step 2 — Extract sentences from the book

The alignment script needs a text file with one sentence per line. If you already have the book as FB2 (e.g. `public/books/novel/gogol-nose.fb2`), run:

```bash
node scripts/extract-sentences.js public/books/novel/gogol-nose.fb2
```

This writes `gogol-nose-ch1.txt`, `gogol-nose-ch2.txt`, etc. next to the FB2 — one file per chapter, one sentence per line. The sentence parser mirrors the app's `parseSentences`, so the runtime fragment-to-sentence matching is reliable.

For other formats, you can also pass `.txt` files directly:

```bash
node scripts/extract-sentences.js my-chapter.txt --whole > sentences.txt
```

---

## Step 3 — Align each chapter

For chapter 1:

```bash
python scripts/align-audiobook.py \
  --audio   ~/Downloads/gogol-nose-ch1.mp3 \
  --text    public/books/novel/gogol-nose-ch1.txt \
  --out     public/books/audio/gogol-nose-ch1.json \
  --audio-url "https://archive.org/download/gogol-nose/ch1.mp3" \
  --narrator "Игорь Ильинский" \
  --year     1955
```

Repeat for each chapter. Each alignment takes about 1–3 seconds per minute of audio on a modern laptop — a 30-minute chapter aligns in roughly a minute.

> **Note:** `--audio-url` is what gets embedded in the JSON. The local `--audio` file is only used during alignment; once the JSON is generated, only the URL matters at runtime. **If you forget `--audio-url`**, re-run with the right URL or hand-edit the `audio_url` field in the output JSON.

The output JSON looks like:

```json
{
  "version": 1,
  "language": "rus",
  "audio_url": "https://archive.org/download/gogol-nose/ch1.mp3",
  "narrator": "Игорь Ильинский",
  "year": 1955,
  "fragments": [
    { "begin": 0.32, "end": 4.18, "text": "Марта 25 числа случилось..." },
    { "begin": 4.18, "end": 9.05, "text": "Цырюльник Иван Яковлевич..." },
    ...
  ]
}
```

---

## Step 4 — Register the audiobook in the manifest

Edit `public/books/index.json`. Find the book's entry (or add it if it doesn't exist). Add an `audiobook` field with a `chapters` array — one entry per chapter, in the **same order as the FB2's chapters**. Use `null` for chapters that have no audio:

```json
{
  "filename": "novel/gogol-nose.fb2",
  "title": "Нос",
  "author": "Николай Гоголь",
  "category": "Novels",
  "audiobook": {
    "narrator": "Игорь Ильинский",
    "year": 1955,
    "source": "https://archive.org/details/gogol-nose-iliinski",
    "chapters": [
      "audio/gogol-nose-ch1.json",
      "audio/gogol-nose-ch2.json",
      "audio/gogol-nose-ch3.json"
    ]
  }
}
```

Paths are relative to `public/books/` (so `audio/gogol-nose-ch1.json` resolves to `/books/audio/gogol-nose-ch1.json` at runtime).

---

## Step 5 — Commit and deploy

```bash
git add public/books/audio/ public/books/index.json
git commit -m "Audiobook: Гоголь — Нос (read by Игорь Ильинский, 1955)"
git push
```

Vercel auto-deploys in ~1–2 minutes.

---

## How it looks in the app

When a reader opens a chapter that has an audiobook:

1. The app fetches its alignment JSON in the background.
2. The floating audio bar gains a **🎧 / 🤖 toggle** on the right side. Defaults to 🎧 (audiobook) since it's better quality.
3. Hitting ▶ streams the audio from archive.org. The narrator name shows in the status text.
4. As playback proceeds, the sentence currently being read tints warm tan — same highlight UI as TTS mode, but driven by real per-sentence timestamps instead of heuristic.
5. ⏭ / ⏮ skip to the next/previous sentence's actual `begin` time in the recording.
6. Pause stops the stream; resume picks up where it left off.

If the user prefers the AI voice (faster, no buffering on slow connections), one tap on the 🎧 toggle switches to 🤖 (TTS mode).

---

## Troubleshooting

**The toggle doesn't appear in the audio bar.**
The alignment JSON didn't load. Check the browser console for fetch errors — usually the path is wrong in `index.json`, or the JSON is malformed. Reload after fixing.

**Audio plays but no highlight follows.**
The fragment-to-sentence matching failed. This usually means the text used during alignment doesn't quite match what the app parses at runtime. Common causes:
- The audiobook narrator added an intro or skipped sections — leaves orphan fragments. Usually self-corrects after a few sentences.
- The text file had typos different from the FB2. Re-extract sentences from the actual FB2 file with `extract-sentences.js`.

**Audio doesn't play at all — "stream error".**
Either the `audio_url` is wrong, or archive.org isn't serving CORS headers for that file. Test the URL directly in a browser tab. If it 404s, the link may have changed. If it 200s but your app can't play it, archive.org may require the file to be served under `https://archive.org/download/` rather than `archive.org/details/` (the latter is the HTML page, not the direct file).

**Alignment drifts heavily after the first few minutes.**
Re-run with `--boundary-adjust aftercurrent` or `--boundary-adjust beforenext`. Aeneas's `auto` mode usually works but occasionally produces drift on recordings with long pauses or music.

**One fragment lines up to the wrong sentence.**
The fuzzy match in the app uses the first 25 normalised characters of each sentence. If two adjacent sentences start identically (rare but possible in repetitive prose), open the alignment JSON and split / merge / re-order the fragments by hand. The format is simple JSON; edit and re-deploy.

---

## What this buys you

Instead of Azure mispronouncing 5–10% of Russian words because it can't predict stress, you get a professional Soviet voice actor whose pronunciation is perfect on every grammatical form. The sentence highlight follows along just like before — same UX, dramatically better audio quality.

For learners, hearing real Russian intonation, prosody, and emphasis is far more useful than synthetic speech. And for the classics, the Soviet recordings are often legendary — Smoktunovsky reading Hamlet, Tabakov reading Mertvye Dushi, etc.
