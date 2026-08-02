#!/usr/bin/env python3
"""
split_corpus.py — cut each chapter into short, fragment-aligned segments for MFA.

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

This is safe because the app's audio JSONs already carry per-fragment begin/end
times. We only cut in the silence BETWEEN fragments (at the midpoint of the gap,
with padding), never inside speech.

TWO SOURCE MODES (auto-detected)
  MP3   read $AUDIO_DIR/**/*.mp3 directly, decoding one chapter at a time.
        No 8.8 GB intermediate corpus. This is the default when $WP/corpus is
        empty. Requires ffmpeg. Force with --from-mp3.
  WAV   read an existing $WP/corpus/NNN.wav built by build_corpus.py.

OUTPUTS
  $WP/seg/bNNN/NNN_pMMM.wav   short audio segments, grouped into align batches
  $WP/seg/bNNN/NNN_pMMM.lab   the exact transcript text for that segment
  $WP/segmap.json             manifest consumed by apply_timings.py

USAGE
  python split_corpus.py                            # dry run — prints the plan
  python split_corpus.py --build                    # actually cut
  python split_corpus.py --build --drop-source      # WAV mode: delete each
                                                    #   chapter wav after cutting
  python split_corpus.py --build --target=20 --max=30   # even smaller pieces

ENV: REPO, WP, AUDIO_DIR (for MP3 mode)   optional: AUDIO_JSON_DIR
"""
import json
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave

REPO = os.environ.get("REPO", "")
WP = os.environ.get("WP", "")
if not REPO or not WP:
    sys.exit("ERROR: export REPO and WP first (see docs/mfa_alignment_guide.md)")

JSON_DIR = os.environ.get("AUDIO_JSON_DIR", f"{REPO}/public/books/audio/vim")
AUDIO_DIR = os.environ.get("AUDIO_DIR", "")
CORPUS = f"{WP}/corpus"
SEGROOT = f"{WP}/seg"
SEGMAP = f"{WP}/segmap.json"

# ---- options ---------------------------------------------------------------
BUILD = "--build" in sys.argv
DROP_SOURCE = "--drop-source" in sys.argv
FORCE = "--force" in sys.argv
FROM_MP3 = "--from-mp3" in sys.argv


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
SR = 16000


# ---- source pairing --------------------------------------------------------
def sortkey(path):
    """War & Peace deti-online naming -> reading order. Mirrors build_corpus.py."""
    b = os.path.basename(path).lower()
    if "avtora" in b or "neskolko-slov" in b:            # author's note = first
        return (0, 0, 0)
    m = re.search(r"epilog-chast-(\d+)-glava-(\d+)", b)   # epilogue = after toms
    if m:
        return (5, int(m.group(1)), int(m.group(2)))
    m = re.search(r"tom-(\d+)-chast-(\d+)-glava-(\d+)", b)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return (99, 99, 99)                                   # unknown -> sorts last


def transcripts():
    return sorted(glob.glob(f"{JSON_DIR}/*.json"),
                  key=lambda p: int(re.sub(r"\D", "", os.path.basename(p)) or 0))


def first_words(jp, n=9):
    d = json.load(open(jp, encoding="utf-8"))
    for fr in d.get("fragments", []):
        t = (fr.get("text") or "").strip()
        if t:
            return " ".join(t.split()[:n])
    return "(empty transcript)"


def decode_mp3(mp3, dest):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3,
                    "-ac", "1", "-ar", str(SR), dest], check=True)


# ---- windowing -------------------------------------------------------------
def windows_for(fragments):
    """Group consecutive fragments into windows of <= MAX_SEC, aiming at TARGET_SEC.

    Never splits a fragment. A single fragment longer than MAX_SEC becomes its
    own window (rare; nothing to do without cutting inside speech).
    """
    out, cur, cur_start = [], [], None
    for i, f in enumerate(fragments):
        b, e = f.get("begin"), f.get("end")
        if b is None or e is None:
            continue
        if not cur:
            cur, cur_start = [i], b
            continue
        span = e - cur_start
        if span > MAX_SEC or span >= TARGET_SEC:
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
    b, e = fragments[first]["begin"], fragments[last]["end"]
    prev_end = fragments[first - 1].get("end") if first > 0 else None
    next_beg = fragments[last + 1].get("begin") if last + 1 < len(fragments) else None
    start = (prev_end + b) / 2.0 if prev_end is not None and prev_end < b else b - PAD
    end = (e + next_beg) / 2.0 if next_beg is not None and next_beg > e else e + PAD
    return max(0.0, start), min(duration, end)


def seg_text(fragments, idxs):
    return " ".join((fragments[i].get("text") or "").strip() for i in idxs).strip()


def nwords(fragments, idxs):
    return sum(len(fragments[i].get("words") or []) for i in idxs)


# ---- decide source mode ----------------------------------------------------
corpus_wavs = sorted(glob.glob(f"{CORPUS}/*.wav"))
mp3_mode = FROM_MP3 or not corpus_wavs

if mp3_mode:
    if not AUDIO_DIR:
        sys.exit("ERROR: no WAVs in %s and AUDIO_DIR is not set.\n"
                 "  Either export AUDIO_DIR=\"/mnt/c/.../audiobooks/<book>\" to read\n"
                 "  the MP3s directly (recommended — skips the 8.8 GB intermediate),\n"
                 "  or run build_corpus.py --build first." % CORPUS)
    if not shutil.which("ffmpeg"):
        sys.exit("ERROR: ffmpeg not found — sudo apt-get install -y ffmpeg")
    mp3s = sorted(glob.glob(f"{AUDIO_DIR}/**/*.mp3", recursive=True), key=sortkey)
    jsons = transcripts()
    unknown = [os.path.basename(m) for m in mp3s if sortkey(m) == (99, 99, 99)]
    print(f"source: MP3 ({len(mp3s)} files in {AUDIO_DIR})")
    print(f"transcripts: {len(jsons)} in {JSON_DIR}")
    if unknown:
        print(f"!! filenames I couldn't parse ({len(unknown)}): {unknown[:6]}")
    if len(mp3s) != len(jsons) or unknown:
        sys.exit("Counts don't match (or unparsed names) — fix before building.\n"
                 "  This pairing is positional; a mismatch means silently wrong timings.")
    pairs = list(zip(mp3s, jsons))
    print("\n--- spot-check pairing: first 3, middle 2, last 3 ---")
    mid = len(pairs) // 2
    for mp3, jp in pairs[:3] + pairs[mid:mid + 2] + pairs[-3:]:
        print(f"{os.path.basename(mp3)[:46]:46} -> {os.path.basename(jp):9} : {first_words(jp)}")
    print("  ^ chapter numbers in the filename should match the paired text.\n")
    sources = [(os.path.splitext(os.path.basename(jp))[0], mp3, jp) for mp3, jp in pairs]
else:
    print(f"source: WAV corpus ({len(corpus_wavs)} files in {CORPUS})")
    print(f"transcripts: {JSON_DIR}")
    sources = [(os.path.splitext(os.path.basename(w))[0], w,
                f"{JSON_DIR}/{os.path.splitext(os.path.basename(w))[0]}.json")
               for w in corpus_wavs]

if only_set:
    sources = [s for s in sources if s[0] in only_set]

print(f"target={TARGET_SEC}s  max={MAX_SEC}s  pad={PAD}s  batch-chapters={BATCH_CHAPTERS}")
print()

# ---- plan ------------------------------------------------------------------
plan, skipped = [], []
total_segs = 0
total_secs = 0.0

for base, src, jp in sources:
    if not os.path.exists(jp):
        skipped.append((base, "no transcript json"))
        continue
    d = json.load(open(jp, encoding="utf-8"))
    frs = [f for f in d.get("fragments", []) if (f.get("text") or "").strip()]
    if not frs:
        skipped.append((base, "empty transcript"))
        continue

    if mp3_mode:
        # real duration comes at cut time; for planning, the transcript's own end
        # is enough (it only affects the clamp on the final segment)
        duration = (frs[-1].get("end") or 0.0) + 2.0
    else:
        try:
            with wave.open(src, "rb") as wf:
                if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                    skipped.append((base, f"not 16-bit mono ({wf.getnchannels()}ch)"))
                    continue
                duration = wf.getnframes() / float(wf.getframerate())
        except Exception as ex:
            skipped.append((base, f"unreadable wav: {ex}"))
            continue

    wins = windows_for(frs)
    plan.append((base, src, duration, wins, frs))
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

longest, longest_where = 0.0, ""
for base, src, duration, wins, frs in plan:
    for k, idxs in enumerate(wins):
        s, e = cut_points(frs, idxs, duration)
        if e - s > longest:
            longest, longest_where = e - s, f"{base}_p{k+1:03d}"
print(f"\nlongest single utterance after splitting: {longest:.1f}s ({longest_where})")
print("  (this is the number that drives MFA's peak RAM — before splitting it was ~700s)")

nbatches = (len(plan) + BATCH_CHAPTERS - 1) // max(1, BATCH_CHAPTERS)
print(f"align batches: {nbatches} (~{BATCH_CHAPTERS} chapters each)")

need = int(total_secs * SR * 2)
free = shutil.disk_usage(WP).free
print(f"\ndisk: segments need ~{need/1e9:.1f} GB, free {free/1e9:.1f} GB")
if mp3_mode:
    print("  (MP3 mode decodes one chapter at a time — no full-corpus intermediate)")
elif DROP_SOURCE:
    print("  (--drop-source ON — source wavs deleted as we go, so disk stays flat)")
if free < need * 1.1 and not FORCE:
    print("  !! not enough headroom. Free space, or use --target=20, or --force.")
    if BUILD:
        sys.exit(1)

if not BUILD:
    print("\nDry run only. If the plan looks right:")
    print("  python split_corpus.py --build" + ("" if mp3_mode else " --drop-source"))
    sys.exit(0)

# ---- cut -------------------------------------------------------------------
if os.path.exists(SEGROOT):
    shutil.rmtree(SEGROOT)
os.makedirs(SEGROOT, exist_ok=True)

segmap = {"chapters": {}, "params": {
    "target": TARGET_SEC, "max": MAX_SEC, "pad": PAD,
    "batch_chapters": BATCH_CHAPTERS, "json_dir": JSON_DIR,
    "source": "mp3" if mp3_mode else "wav",
}}

tmpdir = tempfile.mkdtemp(prefix="split_", dir=WP)
print("\ncutting...")
made = 0
try:
    for ci, (base, src, duration, wins, frs) in enumerate(plan):
        batch = f"b{ci // BATCH_CHAPTERS + 1:03d}"
        bdir = f"{SEGROOT}/{batch}"
        os.makedirs(bdir, exist_ok=True)

        if mp3_mode:
            wav_path = f"{tmpdir}/{base}.wav"
            try:
                decode_mp3(src, wav_path)
            except subprocess.CalledProcessError as ex:
                print(f"  !! ffmpeg failed on {base}: {ex}")
                continue
        else:
            wav_path = src

        with wave.open(wav_path, "rb") as wf:
            sr = wf.getframerate()
            duration = wf.getnframes() / float(sr)      # real duration now
            frames = wf.readframes(wf.getnframes())
        sw = 2

        entries = []
        for si, idxs in enumerate(wins, start=1):
            s, e = cut_points(frs, idxs, duration)
            chunk = frames[int(round(s * sr)) * sw:int(round(e * sr)) * sw]
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
                "id": sid, "batch": batch, "offset": round(s, 3),
                "frag_start": idxs[0], "frag_end": idxs[-1],
                "app_words": nwords(frs, idxs),
            })
            made += 1

        segmap["chapters"][base] = {"batch": batch, "duration": round(duration, 3),
                                    "segments": entries}
        del frames

        if mp3_mode:
            os.remove(wav_path)
        elif DROP_SOURCE:
            os.remove(src)

        if (ci + 1) % 20 == 0:
            print(f"  ...{ci+1}/{len(plan)} chapters, {made} segments")
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

with open(SEGMAP, "w", encoding="utf-8") as fh:
    json.dump(segmap, fh, ensure_ascii=False)

print(f"\nbuilt {made} segments across {nbatches} batches -> {SEGROOT}")
print(f"manifest -> {SEGMAP}")
print("\nNext:  python \"$REPO/scripts/mfa/align_segments.py\"")
