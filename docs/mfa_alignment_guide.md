# Montreal Forced Aligner — local alignment process (govorim)

How to force-align a Russian audiobook to its text on this machine and fold the
word timings back into the app's `public/books/audio/<book>/NN.json` files.

This is the process as it actually worked (and where it bit us) — written from the
War & Peace run. It generalizes to any book; swap the paths.

Forced alignment = you give MFA **audio + a transcript of what's spoken**, and it
returns precise per-word timestamps using a pretrained Russian acoustic model +
pronunciation dictionary. It does **not** transcribe, and it can't fix a transcript
that doesn't match the audio.

> **If you only read one thing:** do not feed MFA whole chapters. Split them into
> ~30-second segments first (`split_corpus.py`). Whole-chapter alignment is what
> kept getting OOM-killed. See §6.

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
- **The scripts live in the repo,** so always call them by full path:
  `python "$REPO/scripts/mfa/split_corpus.py"`. Running `python split_corpus.py`
  from your home directory gives `can't open file '/home/david/split_corpus.py'`.
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

## 4. Build the corpus (per book) — OPTIONAL now

> **You can skip this whole step.** `split_corpus.py` reads the MP3s directly and
> decodes one chapter at a time, so the full-book WAV corpus (~8.8 GB for War &
> Peace) is no longer needed as an intermediate. Jump to §6 and let it pair the
> files — it prints the same spot-check table shown below, and its pairing logic
> is identical. Build the corpus here only if you specifically want the
> intermediate WAVs on disk.

MFA reads a folder of **matched pairs with the same basename** — `NNN.wav` (16 kHz
mono) + `NNN.lab` (the transcript for that audio). Set your paths:

```bash
export REPO=/mnt/c/Users/david/projects/govorim-app
export AUDIO_DIR="/mnt/c/Users/david/Downloads/audiobooks/<book folder>"
export WP=~/<book>_align
mkdir -p "$WP"
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

> **Order note:** this step needs a corpus on disk to harvest OOVs from. If you
> skipped §4 (MP3 mode), do **§6 split first**, then come back here and point g2p
> at the segment folder — `mfa g2p "$WP/seg" russian_mfa "$WP/oov.dict" --dictionary_path russian_mfa`.
> Check whether you already have one from a previous run: `ls -la "$WP"/wp.dict`.

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

## 6. Split into segments — this is the step that fixes the crashes

### Why the first attempts died

MFA's peak memory is driven by the **length of the longest single utterance**, not
by how many files are in the corpus. Each chapter here is one ~12-minute utterance,
which is the worst case MFA has: the alignment lattice for it is enormous.

The first run aligned all 362 chapters and then got OOM-killed by the kernel during
"Analyzing alignment quality". Batching the chapters into 4 groups **did not help**,
because each group still contained 12-minute utterances. Batching the corpus was
fixing the wrong axis.

The fix is to make the utterances themselves short. `split_corpus.py` cuts every
chapter into ~30-second pieces **at existing fragment boundaries**, which is safe
because the app's `vim/NNN.json` files already carry per-fragment `begin`/`end`
times. It only ever cuts in the silence *between* fragments (at the midpoint of the
gap, with padding), never inside speech.

Peak RAM drops by more than an order of magnitude, and alignment gets *more*
accurate too — no long-range drift within a chapter.

It reads from whichever source you have, auto-detected:

- **MP3 mode** (default when `$WP/corpus` is empty): decodes each chapter from
  `$AUDIO_DIR` one at a time into a temp file, slices it, deletes the temp. No
  full-book intermediate ever exists. Needs `AUDIO_DIR` exported and ffmpeg.
  It prints the same positional pairing spot-check as `build_corpus.py` — **check
  that table**, because a mis-pairing means silently wrong timings.
- **WAV mode**: uses an existing `$WP/corpus/NNN.wav` from §4. Add `--drop-source`
  to delete each chapter WAV as it's consumed so disk stays flat.

```bash
export AUDIO_DIR="/mnt/c/Users/david/Downloads/audiobooks/war and peace"

python "$REPO/scripts/mfa/split_corpus.py"           # dry run — shows the plan
python "$REPO/scripts/mfa/split_corpus.py" --build   # cut for real
```

The dry run reports the number that actually matters:

```
longest single utterance after splitting: 34.3s
  (this is the number that drives MFA's peak RAM — before splitting it was ~700s)
```

- The dry run prints a disk estimate and refuses to build without headroom. The
  segments themselves are ~8.8 GB for the full 76 h.
- Still tight on memory? Make the pieces smaller: `--target=20 --max=30`.
- Output: `$WP/seg/bNNN/<chapter>_pMMM.wav|.lab`, plus a manifest at
  `$WP/segmap.json` that records each segment's time offset and which fragments it
  covers. **Don't delete `segmap.json`** — step 7 needs it to put the timings back.

### 6b. Align the segments

**Skip `mfa validate`.** It trains a fresh monophone model *from scratch* on the
whole corpus as a "check" (26 minutes per iteration on 76 hours) and on this build it
crashes with `ZeroDivisionError` in the training accumulator. It is optional and
unrelated to real alignment. Alignment uses the **pretrained** model — a single
pass, no training, a completely different code path.

```bash
python "$REPO/scripts/mfa/align_segments.py"           # aligns everything not yet done
python "$REPO/scripts/mfa/align_segments.py" --status  # progress only, aligns nothing
```

It runs `mfa align` one batch (~25 chapters' worth of segments) at a time and is
**resumable**: a batch whose outputs are already complete is skipped. If it dies or
you Ctrl-C it, just run it again. A crash costs one batch, not the run. Logs land in
`$WP/logs/<batch>.log`.

Expect roughly 6–8 minutes per batch (~100 minutes for the full 362 chapters).

**A batch finishing a few segments short is normal.** MFA leaves ~0.5% unaligned —
beam failures where the audio and transcript don't match well enough. A batch counts
as done once 98% of it aligned (`--complete-at=`), because re-running a whole batch
to chase four files that will fail again isn't worth it, and `apply_timings.py`
interpolates and flags them. The unaligned IDs are written to
`$WP/logs/<batch>.missing.txt`.

Watch-outs:

- **Still out-of-memory:** `--jobs=1` (default is 3).
- **A batch fails with beam errors:** re-run just that one —
  `--only=b003 --jobs=1 --beam=100 --retry-beam=400`.
- **Force a retry of the partials anyway:** `--retry-partial`.
- **Aligned by an older run and it wants to redo everything:** `--mark-done`
  backfills the completion markers and the missing-segment lists without aligning.
- Run it under `screen` / `tmux` — the full book takes hours.

---

## 7. Fold the timings back into the app JSONs

```bash
python "$REPO/scripts/mfa/apply_timings.py"          # dry run: per-chapter match rate
python "$REPO/scripts/mfa/apply_timings.py" --write  # apply
```

`--write` copies `audio/vim` to `audio/vim.bak` first if no backup exists yet, so
you can always get back.

The script auto-detects which mode to use: **segment mode** when `$WP/segmap.json`
exists (the flow above), **flat mode** when you only have `$WP/out/NNN.json`.

Two things it does that the old positional version didn't:

1. **Per-segment anchoring.** Each segment's words are mapped onto that segment's
   own fragment range, with the segment's offset added back. A bad 30-second piece
   can't drift the rest of the chapter.
2. **Text-aware matching.** App tokens and MFA tokens are normalised (lowercase,
   ё→е, punctuation stripped) and lined up with `difflib.SequenceMatcher`. MFA emits
   nothing for punctuation "words" like a leading `—`; those get interpolated from
   their neighbours instead of shifting everything after them by one slot.

Read the report before trusting it:

```
chapter     segs  gaps  matched   words    rate  flag
002           76     1     3041    3118  97.5%  1 SEGMENT(S) NOT ALIGNED
362           17     0      676     677  99.9%
```

- `gaps` > 0 means some segment produced no alignment — re-run that batch.
- `rate` below 90% is flagged `LOW MATCH`, usually a transcript/audio mismatch.

Then open a flagged chapter in the reader, play the narrator, and confirm the
highlight tracks.

> `build_corpus.py` and the default transcript folder are written for the War & Peace
> `vim` layout. For another book, set `AUDIO_JSON_DIR` (the split/apply scripts read
> it) and adjust `build_corpus.py`'s `sortkey()` / glob.

---

## Cheat-sheet — the whole run, once everything's installed

```bash
# in WSL Ubuntu, in the aligner env
conda activate aligner
export REPO=/mnt/c/Users/david/projects/govorim-app
export AUDIO_DIR="/mnt/c/Users/david/Downloads/audiobooks/war and peace"
export WP=~/wp_align
mkdir -p "$WP"

python "$REPO/scripts/mfa/split_corpus.py"            # check the pairing + plan
python "$REPO/scripts/mfa/split_corpus.py" --build    # ~30s segments, straight from MP3

# dictionary: reuse it if a previous run left one, otherwise build from the segments
ls "$WP/wp.dict" 2>/dev/null || {
  mfa g2p "$WP/seg" russian_mfa "$WP/oov.dict" --dictionary_path russian_mfa
  cat ~/Documents/MFA/pretrained_models/dictionary/russian_mfa.dict "$WP/oov.dict" > "$WP/wp.dict"
}

python "$REPO/scripts/mfa/align_segments.py"          # resumable; run under screen
python "$REPO/scripts/mfa/align_segments.py" --status # check progress anytime

python "$REPO/scripts/mfa/apply_timings.py"           # dry run
python "$REPO/scripts/mfa/apply_timings.py" --write   # apply (backs up first)
```

Key rules learned the hard way: run in WSL not PowerShell, re-export env vars in every
new shell, call the scripts by `$REPO` path, verify the build-corpus pairing by eye,
g2p the OOV names/French, never run `mfa validate` — and **never hand MFA a whole
chapter**; split it first, because utterance length, not corpus size, is what
exhausts memory.
