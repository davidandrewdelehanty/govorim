# Montreal Forced Aligner — local alignment process (govorim)

How to force-align a Russian audiobook to its text on this machine and fold the
word timings back into the app's `public/books/audio/<book>/NN.json` files.

This is the process as it actually worked (and where it bit us) — written from the
War & Peace run. It generalizes to any book; swap the paths.

Forced alignment = you give MFA **audio + a transcript of what's spoken**, and it
returns precise per-word timestamps using a pretrained Russian acoustic model +
pronunciation dictionary. It does **not** transcribe, and it can't fix a transcript
that doesn't match the audio.

---

## 0. Which shell — read this first

Everything runs in the **WSL Ubuntu** shell, whose prompt looks like:

```
(aligner) david@Davebook:~$
```

NOT Windows PowerShell (`PS C:\Users\david>`). If you paste these commands into
PowerShell you'll get errors like `C:\dev\null` or `'||' is not a valid statement
separator`. If that happens, type `wsl` to drop into Ubuntu.

Gotchas that cost us time:

- **Env vars don't survive a new shell.** Every new terminal, re-run the `export`
  lines in Step 4. If a path echoes back empty (`echo "$REPO"` prints nothing), they
  aren't set — re-export.
- **Stuck at a `>` prompt** = the shell is waiting for a closing quote from a bad
  paste and is swallowing everything you type. Press **Ctrl+C** to bail out, then
  re-paste one line at a time.
- **Windows paths in WSL:** `C:\Users\david\...` becomes `/mnt/c/Users/david/...`,
  and any path with spaces must be quoted: `"/mnt/c/Users/david/Downloads/audiobooks/war and peace"`.

---

## 1. Install MFA (once)

conda is already installed here (v26.x). Modern conda has a fast solver built in —
no separate mamba needed:

```bash
conda create -y -n aligner -c conda-forge montreal-forced-aligner
conda activate aligner
mfa version        # expect 3.x
```

**If it dies with `CorruptedEnvironmentError`** (happens when a previous install was
interrupted), wipe the half-built env and retry — `conda env remove` alone often
can't clean a corrupted env, so force it:

```bash
conda deactivate 2>/dev/null
conda env remove -n aligner -y 2>/dev/null
rm -rf ~/miniconda3/envs/aligner
conda create -y -n aligner -c conda-forge montreal-forced-aligner
```

## 2. Download the Russian models (once)

```bash
mfa model download acoustic  russian_mfa
mfa model download dictionary russian_mfa
mfa model download g2p        russian_mfa
```

They cache under `~/Documents/MFA/pretrained_models/`. "Local version already
exists" on a re-run is fine. Confirm:

```bash
mfa model inspect acoustic russian_mfa >/dev/null && echo "MODEL OK"
```

## 3. Install ffmpeg (once)

Needed to convert MP3 → 16 kHz mono WAV (MFA's required input format):

```bash
sudo apt-get update && sudo apt-get install -y ffmpeg
ffmpeg -version | head -1
```

---

## 4. Build the corpus (per book)

MFA reads a folder of **matched pairs with the same basename** — `NNN.wav` (16 kHz
mono) + `NNN.lab` (the transcript for that audio). Set your paths:

```bash
export REPO=/mnt/c/Users/david/projects/govorim-app
export AUDIO_DIR="/mnt/c/Users/david/Downloads/audiobooks/<book folder>"
export WP=~/<book>_align
mkdir -p "$WP"/{corpus,out}
```

Use the repo script `scripts/mfa/build_corpus.py`. It pairs each local MP3 with the
matching app transcript, converts to WAV, and writes the `.lab`:

```bash
python "$REPO/scripts/mfa/build_corpus.py"          # DRY RUN — prints the pairing
python "$REPO/scripts/mfa/build_corpus.py" --build  # converts all files
```

**Always eyeball the dry-run pairing first.** For War & Peace the local files were
named by the audiobook's own scheme (`...tom-1-chast-1-glava-1.mp3`, the deti-online
recording), not `002.mp3`, so the script sorts them into reading order
(intro → том/часть/глава → epilogue) and pairs positionally with the numbered
transcript JSONs. The dry run is self-checking: the chapter numbers in the filenames
should line up with the "Глава N" in the paired transcript. A mis-pairing here
produces silently wrong timings, so it's the one thing to verify by eye.

> The `build_corpus.py` in the repo is currently written for the War & Peace layout
> (`tom/chast/glava` names → `audio/vim/NNN.json`). For a different book, adjust the
> `sortkey()` / transcript glob at the top of the script.

---

## 5. Handle out-of-vocabulary (OOV) words — don't skip for real books

Any book with proper names or foreign passages will have OOV words the base
dictionary doesn't cover. War & Peace had **85 OOV types / 204k tokens**: character
names in every case (Пьеру, Болконского, Наташе…), **French** (de, vous, c'est…),
and **years** (1812, 1805). Those names recur constantly, so leaving them OOV
strips the alignment of its most frequent anchors and wrecks quality.

Fix: g2p those words and merge them into the dictionary. MFA writes the OOV list to
disk during any corpus load, so point g2p straight at it:

```bash
# the OOV list MFA generated (path is printed in the load output):
#   ~/Documents/MFA/corpus/oovs_found_russian_mfa.txt

mfa g2p ~/Documents/MFA/corpus/oovs_found_russian_mfa.txt russian_mfa "$WP/oov.dict"
cat ~/Documents/MFA/pretrained_models/dictionary/russian_mfa.dict "$WP/oov.dict" > "$WP/wp.dict"
```

`$WP/wp.dict` is now the base Russian dictionary plus pronunciations for every name /
French word / year in this book.

> If you haven't loaded the corpus yet and don't have `oovs_found_...txt`, run one
> quick corpus load to produce it (e.g. `mfa g2p "$WP/corpus" russian_mfa "$WP/oov.dict" --dictionary_path russian_mfa`,
> which extracts and pronounces the corpus's OOVs directly).

---

## 6. Align — and DO NOT run `mfa validate`

**Skip `mfa validate`.** It trains a fresh monophone model *from scratch* on the
whole corpus as a "check" (26 minutes per iteration on 76 hours) and on this build it
crashes with `ZeroDivisionError: division by zero` in the training accumulator. It is
optional and unrelated to real alignment.

Alignment itself uses the **pretrained** acoustic model — a single pass, no training,
a completely different code path that doesn't hit that bug:

```bash
mfa align "$WP/corpus" "$WP/wp.dict" russian_mfa "$WP/out" \
    --single_speaker \
    --output_format json \
    --num_jobs 4 \
    --clean
```

- `--single_speaker` — an audiobook is one narrator; faster and more accurate.
- `--output_format json` — writes `$WP/out/NNN.json` with word intervals (easier to
  parse than TextGrids).
- Output lands per-file keyed by the same `NNN` basename as the corpus, so it maps
  straight back to `audio/<book>/NNN.json`.

Watch-outs:

- **Out-of-memory:** drop to `--num_jobs 2` (or `1`).
- **Long utterances:** each chapter is one ~12-minute utterance — the heaviest case
  for MFA. It handles it, but if it specifically chokes on long files, add a
  segmentation pass (`mfa segment`) before aligning.
- A few chapters failing with `beam` errors → re-run just those with
  `--beam 100 --retry_beam 400`.

---

## 7. Fold the timings back into the app JSONs (per book)

MFA's JSON gives word start/end times in order. `scripts/mfa/apply_timings.py` maps
them positionally onto each chapter's existing `fragments[].words[]`:

```bash
# BACK UP FIRST — this rewrites files in place
cp -r "$REPO/public/books/audio/<book>"{,.bak}

python "$REPO/scripts/mfa/apply_timings.py"          # dry run: per-chapter word counts + DRIFT flags
python "$REPO/scripts/mfa/apply_timings.py" --write  # apply
```

The dry run flags any chapter where MFA's word count and the app's word-slot count
differ by more than a few (`DRIFT`) — spot-check those before trusting them. Then
open a chapter in the reader, play the narrator, and confirm the highlight tracks.

> `apply_timings.py` is written for the War & Peace `vim` folder — change the output
> path glob for another book.

---

## Cheat-sheet — the whole run, once everything's installed

```bash
# in WSL Ubuntu, in the aligner env
conda activate aligner
export REPO=/mnt/c/Users/david/projects/govorim-app
export AUDIO_DIR="/mnt/c/Users/david/Downloads/audiobooks/war and peace"
export WP=~/wp_align
mkdir -p "$WP"/{corpus,out}

python "$REPO/scripts/mfa/build_corpus.py"            # check pairing
python "$REPO/scripts/mfa/build_corpus.py" --build    # build corpus

mfa g2p ~/Documents/MFA/corpus/oovs_found_russian_mfa.txt russian_mfa "$WP/oov.dict"
cat ~/Documents/MFA/pretrained_models/dictionary/russian_mfa.dict "$WP/oov.dict" > "$WP/wp.dict"

mfa align "$WP/corpus" "$WP/wp.dict" russian_mfa "$WP/out" \
    --single_speaker --output_format json --num_jobs 4 --clean

cp -r "$REPO/public/books/audio/vim"{,.bak}
python "$REPO/scripts/mfa/apply_timings.py"           # dry run
python "$REPO/scripts/mfa/apply_timings.py" --write   # apply
```

Key rules learned the hard way: run in WSL not PowerShell, re-export env vars in every
new shell, verify the build-corpus pairing by eye, g2p the OOV names/French, and never
run `mfa validate` — go straight to `mfa align`.
