#!/usr/bin/env python3
"""
split_corpus.py — cut each chapter WAV into short, fragment-aligned segments.

WHY THIS EXISTS
---------------
MFA's peak memory is dominated by the alignment lattice of the LONGEST single
utterance, not by how many files are in the corpus. Each chapter here is one
~12-minute utterance — the worst case for MFA, and what has been OOM-killing
the run. Batching chapters into groups does not help, because every group still
contains 12-minute utterances.

Cutting each chapter into ~30 s pieces at EXISTING fragment boundaries makes
every utterance small, so peak RAM drops by orders of magnitude and alignment
also gets more accurate (no long-range drift).

This is safe because the app's vim/NNN.json files already carry per-fragment
begin/end times. We only cut in the silence BETWEEN fragments (at the midpoint
of the gap, with padding), never inside speech.

INPUTS
  $WP/corpus/NNN.wav          16 kHz mono WAV, produced by build_corpus.py
  <json-dir>/NNN.json         app transcript: fragments[].begin/.end/.text/.words

OUTPUTS
  $WP/seg/bNNN/NNN_pMMM.wav   short audio segments, grouped into align batches
  $WP/seg/bNNN/NNN_pMMM.lab   the exact transcript text for that segment
  $WP/segmap.json             manifest consumed by apply_timings.py

USAGE
  python split_corpus.py                            # dry run — prints the plan
  python split_corpus.py --build                    # actually cut
  python split_corpus.py --build --drop-source      # delete each chapter wav
                                                    #   right after cutting it,
                                                    #   so disk stays flat
  python split_corpus.py --build --target=20 --max=30   # even smaller pieces

ENV: REPO, WP   (optional: AUDIO_JSON_DIR)
"""
import json
import glob
import os
import re
import shutil
import sys
import wave

REPO = os.environ.get("REPO", "")
WP = os.environ.get("WP", "")
if not REPO or not WP:
    sys.exit("ERROR: export REPO and WP first (see docs/mfa_alignment_guide.md)")

JSON_DIR = os.environ.get("AUDIO_JSON_DIR", f"{REPO}/public/books/audio/vim")
CORPUS = f"{WP}/corpus"
SEGROOT = f"{WP}/seg"
SEGMAP = f"{WP}/segmap.json"

# ---- options ---------------------------------------------------------------
BUILD = "--build" in sys.argv
DROP_SOURCE = "--drop-source" in sys.argv
FORCE = "--force" in sys.argv


def opt(name, default):
    for a in sys.argv[1:]:
        if a.startswith(f"--{name}="):
            return a.split("=", 1)[1]
    return default


TARGET_SEC = float(opt("target", 30))      # aim for segments about this long
MAX_SEC = float(opt("max", 45))            # hard cap before we force a cut
BATCH_CHAPTERS = int(opt("batch-chapters", 25))   # chapters per align batch
PAD = float(opt("pad", 0.25))              # padding added around each cut
ONLY = opt("only", "")                     # e.g. --only=001,002,003

only_set = {x.strip() for x in ONLY.split(",") if x.strip()} if ONLY else None


# ---- helpers ---------------------------------------------------------------
def windows_for(fragments):
    """Group consecutive fragments into windows of <= MAX_SEC, aiming at TARGET_SEC.

    Never splits a fragment. A single fragment longer than MAX_SEC becomes its
    own window (nothing we can do without word-level cutting, and those are rare).
    """
    out = []
    cur = []
    cur_start = None
    for i, f in enumerate(fragments):
        b, e = f.get("begin"), f.get("end")
        if b is None or e is None:
            continue
        if not cur:
            cur, cur_start = [i], b
            continue
        span = e - cur_start
        if span > MAX_SEC or (span >= TARGET_SEC):
            out.append(cur)
            cur, cur_start = [i], b
        else:
            cur.append(i)
    if cur:
        out.append(cur)
    return out


def cut_points(fragments, idxs, duration):
    """Start/end seconds for a window, cut at the midpoint of the surrounding gaps."""
    first, last = idxs[0], idxs[-1]
    b = fragments[first]["begin"]
    e = fragments[last]["end"]

    prev_end = fragments[first - 1].get("end") if first > 0 else None
    next_beg = fragments[last + 1].get("begin") if last + 1 < len(fragments) else None

    start = (prev_end + b) / 2.0 if prev_end is not None and prev_end < b else b - PAD
    end = (e + next_beg) / 2.0 if next_beg is not None and next_beg > e else e + PAD

    return max(0.0, start), min(duration, end)


def seg_text(fragments, idxs):
    return " ".join((fragments[i].get("text") or "").strip() for i in idxs).strip()


def nwords(fragments, idxs):
    return sum(len(fragments[i].get("words") or []) for i in idxs)


# ---- main ------------------------------------------------------------------
wavs = sorted(glob.glob(f"{CORPUS}/*.wav"))
if not wavs:
    sys.exit(f"ERROR: no WAVs in {CORPUS} — run build_corpus.py --build first")

if only_set:
    wavs = [w for w in wavs if os.path.splitext(os.path.basename(w))[0] in only_set]

print(f"corpus: {len(wavs)} chapter WAVs in {CORPUS}")
print(f"transcripts: {JSON_DIR}")
print(f"target={TARGET_SEC}s  max={MAX_SEC}s  pad={PAD}s  batch-chapters={BATCH_CHAPTERS}")
print()

plan = []       # (base, wav_path, duration, windows, fragments)
total_segs = 0
total_secs = 0.0
skipped = []

for w in wavs:
    base = os.path.splitext(os.path.basename(w))[0]
    jp = f"{JSON_DIR}/{base}.json"
    if not os.path.exists(jp):
        skipped.append((base, "no transcript json"))
        continue
    try:
        with wave.open(w, "rb") as wf:
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                skipped.append((base, f"not 16-bit mono ({wf.getnchannels()}ch/{wf.getsampwidth()*8}bit)"))
                continue
            sr = wf.getframerate()
            duration = wf.getnframes() / float(sr)
    except Exception as ex:
        skipped.append((base, f"unreadable wav: {ex}"))
        continue

    d = json.load(open(jp, encoding="utf-8"))
    frs = [f for f in d.get("fragments", []) if (f.get("text") or "").strip()]
    if not frs:
        skipped.append((base, "empty transcript"))
        continue

    wins = windows_for(frs)
    plan.append((base, w, duration, sr, wins, frs))
    total_segs += len(wins)
    total_secs += duration

print(f"planned: {len(plan)} chapters -> {total_segs} segments "
      f"({total_secs/3600:.1f}h audio, avg {total_secs/max(1,total_segs):.1f}s/segment)")

if skipped:
    print(f"\nskipped {len(skipped)}:")
    for b, why in skipped[:10]:
        print(f"  {b}: {why}")
    if len(skipped) > 10:
        print(f"  ... and {len(skipped)-10} more")

# longest surviving utterance is what decides peak memory — report it
longest = 0.0
longest_where = ""
for base, w, duration, sr, wins, frs in plan:
    for idxs in wins:
        s, e = cut_points(frs, idxs, duration)
        if e - s > longest:
            longest, longest_where = e - s, f"{base}_p{wins.index(idxs)+1:03d}"
print(f"\nlongest single utterance after splitting: {longest:.1f}s ({longest_where})")
print("  (this is the number that drives MFA's peak RAM — before splitting it was ~700s)")

nbatches = (len(plan) + BATCH_CHAPTERS - 1) // max(1, BATCH_CHAPTERS)
print(f"align batches: {nbatches} (~{BATCH_CHAPTERS} chapters each)")

# disk guard
need = sum(os.path.getsize(w) for _, w, _, _, _, _ in plan)
free = shutil.disk_usage(WP).free
print(f"\ndisk: segments need ~{need/1e9:.1f} GB, free {free/1e9:.1f} GB"
      f"{'  (--drop-source keeps this flat)' if not DROP_SOURCE else '  (--drop-source ON)'}")
if not DROP_SOURCE and free < need * 1.1 and not FORCE:
    print("  !! not enough headroom. Re-run with --drop-source (recommended) or --force.")
    if BUILD:
        sys.exit(1)

if not BUILD:
    print("\nDry run only. If the plan looks right:")
    print("  python split_corpus.py --build --drop-source")
    sys.exit(0)

# ---- do the cutting --------------------------------------------------------
if os.path.exists(SEGROOT):
    shutil.rmtree(SEGROOT)
os.makedirs(SEGROOT, exist_ok=True)

segmap = {"chapters": {}, "params": {
    "target": TARGET_SEC, "max": MAX_SEC, "pad": PAD,
    "batch_chapters": BATCH_CHAPTERS, "json_dir": JSON_DIR,
}}

print("\ncutting...")
made = 0
for ci, (base, w, duration, sr, wins, frs) in enumerate(plan):
    batch = f"b{ci // BATCH_CHAPTERS + 1:03d}"
    bdir = f"{SEGROOT}/{batch}"
    os.makedirs(bdir, exist_ok=True)

    with wave.open(w, "rb") as wf:
        frames = wf.readframes(wf.getnframes())
    sw = 2  # verified 16-bit above

    entries = []
    for si, idxs in enumerate(wins, start=1):
        s, e = cut_points(frs, idxs, duration)
        a = int(round(s * sr)) * sw
        b_ = int(round(e * sr)) * sw
        chunk = frames[a:b_]
        if not chunk:
            continue
        sid = f"{base}_p{si:03d}"
        with wave.open(f"{bdir}/{sid}.wav", "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(sw)
            out.setframerate(sr)
            out.writeframes(chunk)
        with open(f"{bdir}/{sid}.lab", "w", encoding="utf-8") as fh:
            fh.write(seg_text(frs, idxs))
        entries.append({
            "id": sid,
            "batch": batch,
            "offset": round(s, 3),
            "frag_start": idxs[0],
            "frag_end": idxs[-1],
            "app_words": nwords(frs, idxs),
        })
        made += 1

    segmap["chapters"][base] = {"batch": batch, "duration": round(duration, 3),
                                "segments": entries}

    if DROP_SOURCE:
        os.remove(w)

    if (ci + 1) % 20 == 0:
        print(f"  ...{ci+1}/{len(plan)} chapters, {made} segments")

with open(SEGMAP, "w", encoding="utf-8") as fh:
    json.dump(segmap, fh, ensure_ascii=False)

print(f"\nbuilt {made} segments across {nbatches} batches -> {SEGROOT}")
print(f"manifest -> {SEGMAP}")
print("\nNext:  python align_segments.py")
