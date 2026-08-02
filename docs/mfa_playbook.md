# Forced alignment playbook — engineering notes

**Audience: whoever (human or Claude) picks this up next.** `mfa_alignment_guide.md`
is the *how-to* — the commands to run. This file is the *why*: the failure modes we
actually hit, the reasoning that resolved them, and the constraints any future
rewrite (including the planned Windows app) has to respect.

Written after aligning War & Peace: 362 chapters, 76.5 hours, on WSL with ~7.8 GB RAM.

---

## 1. The one thing to know

> **MFA's peak memory is set by the length of the LONGEST SINGLE UTTERANCE, not by
> how many files are in the corpus.**

Everything else in this document follows from that sentence. We lost roughly a day
of wall-clock to not knowing it.

An audiobook chapter is ~12 minutes. Handed to MFA as one utterance, its alignment
lattice is enormous, and the process gets OOM-killed on a 7.8 GB box. Splitting the
same audio into ~30-second utterances drops peak RAM by more than an order of
magnitude — and *improves* accuracy, because there's no long-range drift.

Numbers from the real run: longest utterance went from **~700 s → 40 s**. 362
chapters became 10,614 segments averaging 26 s. Fifteen batches, 6–8 minutes each,
~100 minutes total, zero OOM.

---

## 2. Mistakes we made, in order

Recorded so nobody re-derives them. Several of these are mistakes *I* made and then
repeated in a slightly different costume — #3 and #4 especially.

### 2.1 Running `mfa validate`

It looked like the responsible pre-flight check. It is not: it trains a fresh
monophone model **from scratch** on the whole corpus (26 minutes *per iteration* on
76 hours) and on this build dies with `ZeroDivisionError` in the training
accumulator.

**Never run it.** `mfa align` uses the *pretrained* acoustic model — single pass, no
training, completely different code path, doesn't hit the bug.

### 2.2 Aligning whole chapters

All 362 chapters aligned successfully, then the kernel OOM-killed the process during
the final **"Analyzing alignment quality"** step. The alignment work was done and the
outputs were never exported. Hours of compute, nothing on disk.

Note the shape of this failure: *success followed by a crash in a post-processing
step you didn't ask for*. It reads like "the alignment is too big to work", which
sends you down the wrong path — see next.

### 2.3 Chunking the corpus into 4 groups — WRONG AXIS

The obvious response to OOM is "process less at a time", so we split 362 chapters
into 4 groups of ~90 and aligned each. **It crashed the same way.**

It had to. Every group still contained 12-minute utterances. We reduced a dimension
that wasn't the problem. Corpus size affects total runtime; utterance length affects
peak memory.

### 2.4 Proposing the same fix again, smaller

Faced with "the chunking crashed", the next suggestion was `mfa_chunk_align.py`:
14 chunks of 25 files instead of 4 chunks of 90, with `--num_jobs` lowered. Same
wrong axis, more ceremony. It would have failed identically.

**The lesson worth keeping:** when a fix fails, re-check whether the *diagnosis* was
right before making the same fix more aggressive. "Smaller batches" and "shorter
utterances" sound like the same idea and are not.

The user's instinct — *"can we chunk down the fragments even smaller?"* — was the
correct diagnosis, and it was voiced before I got there.

### 2.5 Delivering scripts to chat instead of to disk

`python: can't open file '/home/david/mfa_chunk_align.py'`. The script had been sent
as a chat attachment and never written to the machine.

**Rule: anything the user is meant to execute goes into the repo** (`SendUserFile`
→ `device_commit_files`), and every command in instructions references it by
`"$REPO/scripts/mfa/..."`. Never hand over a bare filename.

### 2.6 Assuming the intermediate corpus still existed

Between sessions `$WP/corpus` was wiped, so `split_corpus.py` had nothing to read.
The fix was better than rebuilding it: **read the MP3s directly**, decoding one
chapter at a time to a temp file and deleting it after slicing. That removed an
8.8 GB intermediate from the pipeline permanently.

Generalisable: if a large intermediate can be streamed instead of materialised,
stream it. Fewer states to get out of sync between sessions.

### 2.7 Positional word mapping (silent, ugly)

The original `apply_timings.py` walked MFA's word list and the app's word slots in
lockstep. But the app stores punctuation "words" — a leading em-dash `—` is its own
token with its own timing — and **MFA emits no interval for those**. One dash meant
every subsequent word in the chapter took the previous word's timing. Highlighting
drifts by one, forever, and nothing errors.

Fix: normalise both token streams (lowercase, ё→е, strip punctuation) and line them
up with `difflib.SequenceMatcher`. Tokens with no MFA counterpart get interpolated
from their neighbours instead of consuming a slot.

### 2.8 Interpolating from stale timestamps

Subtle, and caught only by testing. For a segment-leading `—` there's no matched
token to its left, so the code fell back to the fragment's *existing* `begin` — a
pre-alignment value. When the new alignment moved that fragment earlier, the dash
landed **after** the word it precedes. Three non-monotonic words in chapter 002.

Fix: when a real anchor and a stale bound disagree, trust the anchor and clamp the
stale one. Direction matters — clamp `left` to `right` when there's a right anchor,
extend `right` to `left` when there isn't (trailing run).

### 2.9 Treating normal partial batches as failures

MFA leaves ~0.5% of segments unaligned (beam failures where audio and transcript
diverge — 991/995, 941/944). The script counted "outputs < inputs" as *pending*, so
the next invocation would re-align all 15 batches — ~100 minutes — to chase ~50
segments that would fail again for exactly the same reason.

Fix: a batch is done at ≥98% (`--complete-at=`), plus a `.complete` marker, plus the
unaligned IDs written to `$WP/logs/<batch>.missing.txt`. `--retry-partial` forces the
chase if you really want it.

**Design principle:** if a tool has a normal, non-zero failure rate, encode that
tolerance or your resume logic will thrash.

### 2.10 Environment and shell papercuts

Individually trivial, collectively hours:

- **PowerShell vs WSL.** These commands only run in WSL Ubuntu
  (`david@Davebook:~$`). In PowerShell they produce `C:\dev\null` and
  `'||' is not a valid statement separator`. Type `wsl` to switch.
- **Env vars die with the shell.** Every new tab needs `REPO`/`WP`/`AUDIO_DIR`
  re-exported. `echo "$WP"` printing empty is the tell.
- **A bare `>` prompt** means a paste broke mid-quote and the shell is swallowing
  input. `Ctrl+C`, then paste one line at a time.
- **No cursor / no prompt is normal** while a foreground job runs. It is *not*
  frozen. Do not `Ctrl+C` it; open a second window instead.
- **Closing the window kills the run.** Use `screen -S mfa`, detach with `Ctrl+A`
  then `D`, return with `screen -r mfa`.
- **Never run two aligners at once.** MFA 3 keeps a shared database under
  `~/Documents/MFA`, and each batch runs with `--clean`. `--status` is read-only and
  safe in a second window.

---

## 3. Why cutting on fragment boundaries is safe

This is the load-bearing assumption of the whole approach, so verify it per book
before trusting it.

The app's `public/books/audio/<book>/NNN.json` files **already contain timings**:

```json
{"audio_url": "...", "narrator": "...", "word_timings": ...,
 "fragments": [{"text": "Лев Николаевич Толстой.", "begin": 1.052, "end": 5.055,
                "words": [{"word": "Лев", "begin": 1.052, "end": 1.412}, ...]}]}
```

So an MFA run here is a **refinement pass**, not a cold start. We can cut audio at
existing fragment boundaries — specifically at the *midpoint of the silence between*
fragments, with 0.25 s padding — so no cut ever lands inside speech.

Verified before building, across chapters 002/092/182/272/362: zero non-monotonic
fragments, zero missing timings, median inter-fragment gap 0.06 s, max 23 s. Clean
enough to cut on.

**If a future book has no prior timings or bad ones, this shortcut is invalid.**
Fall back to `mfa segment`, or generate a rough pass first. Check before splitting.

---

## 4. The pipeline as it now stands

```
MP3s ──┐
       ├─> split_corpus.py ──> $WP/seg/bNNN/*.wav|.lab  +  $WP/segmap.json
JSONs ─┘                              │
                                      ├─> align_segments.py ──> $WP/segout/bNNN/*.json
                                      │                          $WP/logs/*.missing.txt
                                      └─> apply_timings.py ────> public/books/audio/<book>/*.json
                                                                 (+ .bak on first write)
```

**`split_corpus.py`** — groups fragments into ≤45 s windows targeting 30 s, never
splitting a fragment; cuts at gap midpoints; auto-detects MP3 vs existing-WAV source;
writes a manifest recording each segment's `offset`, `frag_start`, `frag_end`,
`app_words`.

**`align_segments.py`** — one `mfa align` per batch of ~25 chapters' segments.
Resumable via markers + the 98% rule. Per-batch logs. `--status`, `--mark-done`,
`--retry-partial`, `--only`, `--jobs`, `--beam`.

**`apply_timings.py`** — per-segment anchoring (add `offset` back, map onto that
segment's own fragment range, so a bad 30 s piece cannot drift the chapter) plus
text-aware token matching. Auto-backs up on first `--write`. Reports per-chapter
match rate; flags `LOW MATCH` (<90%) and unaligned segments.

`segmap.json` is the contract between stages. **Don't delete it** — without it
`apply_timings.py` silently falls back to FLAT mode and finds nothing.

---

## 5. How to test this without burning six hours

This caught bug 2.8 *before* an overnight run, and it's the technique to reuse.

You do not need MFA, or real audio, to test the plumbing:

1. **Synthesise audio** at the right duration from the transcript itself —
   `fragments[-1].end + 1`. For WAV, write PCM with the `wave` module; for MP3,
   `ffmpeg -f lavfi -i sine=...`. Name the files to match the real audiobook's
   scheme so the pairing/`sortkey()` logic is exercised too.
2. **Fake MFA's output** from each `.lab`: tokens spread evenly across the segment,
   and — crucially — **drop punctuation-only tokens**, because that's the real
   behaviour that breaks positional mapping.
3. **Delete one segment's output** to exercise the not-aligned path.
4. **Assert on invariants**, not on eyeballing: word begins monotonic, no negative
   spans, no nulls, fragment bounds re-synced to their words, and MP3-mode offsets
   byte-identical to WAV-mode offsets.

Monotonicity is the assertion that earns its keep — it's what surfaced the stale
interpolation bug, which no amount of reading the diff would have shown.

---

## 6. Reference numbers (War & Peace, for sanity-checking a future run)

| | |
|---|---|
| Chapters / audio | 362 / 76.5 h |
| Segments produced | 10,614, avg 26 s, longest 40 s |
| Batches | 15 (~25 chapters each) |
| Time per batch | 6–8 min → ~100 min total |
| Unaligned segments | ~0.5% per batch (normal) |
| Disk for segments | ~8.8 GB |
| OOV before g2p | 85 types / 204k tokens — character names in every case, French, years |

OOV matters more than it looks: character names recur constantly, so leaving them
out of the dictionary strips the alignment of its most frequent anchors. Always g2p
them and concatenate onto the base dictionary.

---

## 7. Notes toward the Windows app

The stated goal is an executable where you load files and it does this. Notes for
whoever builds it.

**The UI is the easy part. The dependency is the hard part.** MFA means conda +
Kaldi binaries — hundreds of MB, a conda environment that has already corrupted
itself once here (`CorruptedEnvironmentError`, needing a forced `rm -rf` of the env),
and no clean story for double-click installation on Windows. Three honest options:

1. **Bundle a conda environment.** Works, enormous, brittle to ship and update.
2. **Require WSL and drive it from the GUI.** Keeps today's pipeline exactly, but
   the user still has to install and maintain WSL — most of the pain, less of the
   control.
3. **Replace the aligner** with something pip-installable — torchaudio's forced
   alignment, CTC-segmentation, or WhisperX. Drops conda entirely and is the only
   route to a genuine double-click app. Costs a quality re-validation against the
   MFA output we now have as a baseline.

Option 3 is probably right, and the good news is **most of this pipeline is
aligner-agnostic.** These survive an aligner swap unchanged:

- splitting on existing fragment boundaries (§3)
- the `segmap.json` offset/range manifest
- text-aware token remapping (§2.7, §2.8)
- resumable batches with a tolerated failure rate (§2.9)
- backup-then-write with a match-rate report

What's MFA-specific and would be rewritten: the dictionary/g2p step, the
`mfa align` invocation, and the `tiers.words.entries` output parsing in
`apply_timings.py`.

**Keep the pairing confirmation in the UI.** Audio↔transcript pairing is positional,
and a mis-pairing produces *silently wrong timings* — the single worst failure mode
here, because nothing errors and the app just highlights the wrong words. The CLI
prints a spot-check table (first 3, middle 2, last 3) for a human to eyeball. The GUI
must do the equivalent and require confirmation. Do not automate this away.

**Other things the GUI needs, learned from the CLI:**

- A visible peak-utterance-length number after planning — that's the memory predictor
  (§1), and it's the number that tells you in advance whether the run will survive.
- Per-batch progress with resume, not a single opaque bar over hours of work.
- The post-run match-rate report, with low-match chapters clickable into the reader.
  Alignment quality is not binary and the report is how you find the bad 2%.
- Never write in place without a backup. `apply_timings.py --write` creates
  `<dir>.bak` on first run; keep that behaviour.

---

## 8. Repo map for this work

```
scripts/mfa/
  build_corpus.py     optional — full-book WAV corpus (superseded by MP3 mode)
  split_corpus.py     cut into ~30 s fragment-aligned segments  [START HERE]
  align_segments.py   batched, resumable mfa align
  apply_timings.py    fold timings back, text-aware, auto-backup
docs/
  mfa_alignment_guide.md   the runbook — commands, in order
  mfa_playbook.md          this file — why, and what not to repeat
  mfa_war_and_peace.md     the W&P-specific run notes
```

Per-book portability: `AUDIO_JSON_DIR` overrides the transcript folder
(default `public/books/audio/vim`). `build_corpus.py`'s `sortkey()` and
`split_corpus.py`'s copy of it encode the deti-online `tom/chast/glava` filename
scheme — a different audiobook needs that function adjusted, and that's the main
per-book edit.
