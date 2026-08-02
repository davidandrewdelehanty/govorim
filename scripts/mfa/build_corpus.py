#!/usr/bin/env python3
"""
Build an MFA corpus for War & Peace from local deti-online MP3s + the app's
per-chapter transcripts.

  Dry run (just show the pairing, convert nothing):
      python build_corpus.py
  Build for real (convert MP3->WAV 16k mono, write .lab transcripts):
      python build_corpus.py --build

Reads env vars: REPO, WP, AUDIO_DIR
"""
import json, glob, os, re, subprocess, sys

REPO = os.environ["REPO"]; WP = os.environ["WP"]; AUD = os.environ["AUDIO_DIR"]
BUILD = "--build" in sys.argv

def sortkey(path):
    b = os.path.basename(path).lower()
    if "avtora" in b or "neskolko-slov" in b:      # author's note = very first
        return (0, 0, 0)
    m = re.search(r"epilog-chast-(\d+)-glava-(\d+)", b)   # epilogue = after all toms
    if m:
        return (5, int(m.group(1)), int(m.group(2)))
    m = re.search(r"tom-(\d+)-chast-(\d+)-glava-(\d+)", b)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return (99, 99, 99)   # unknown -> sorts last so it's obvious

mp3s = sorted(glob.glob(f"{AUD}/**/*.mp3", recursive=True), key=sortkey)
jsons = sorted(glob.glob(f"{REPO}/public/books/audio/vim/*.json"),
               key=lambda p: int(re.sub(r"\D", "", os.path.basename(p)) or 0))

print(f"local mp3s: {len(mp3s)}  |  transcripts: {len(jsons)}")
unknown = [os.path.basename(m) for m in mp3s if sortkey(m) == (99, 99, 99)]
if unknown:
    print("!! filenames I couldn't parse (fix before building):", unknown[:10])

def firstwords(jp, n=9):
    d = json.load(open(jp))
    for fr in d.get("fragments", []):
        t = (fr.get("text") or "").strip()
        if t:
            return " ".join(t.split()[:n])
    return "(empty transcript)"

pairs = list(zip(mp3s, jsons))
print("\n--- spot-check: first 3, middle 2, last 3 pairings ---")
mid = len(pairs) // 2
for mp3, jp in pairs[:3] + pairs[mid:mid+2] + pairs[-3:]:
    print(f"{os.path.basename(mp3)[:46]:46} -> {os.path.basename(jp):9} : {firstwords(jp)}")

if len(mp3s) != len(jsons) or unknown:
    print("\nCounts don't match (or unparsed names) — NOT building. Fix first.")
    sys.exit(1)

if not BUILD:
    print("\nDry run only. If the pairings above look right, re-run with:  python build_corpus.py --build")
    sys.exit(0)

os.makedirs(f"{WP}/corpus", exist_ok=True)
built = 0
for mp3, jp in pairs:
    base = os.path.splitext(os.path.basename(jp))[0]        # 001..362
    wav = f"{WP}/corpus/{base}.wav"; lab = f"{WP}/corpus/{base}.lab"
    d = json.load(open(jp))
    text = " ".join((fr.get("text") or "") for fr in d.get("fragments", [])).strip()
    if not text:
        print("skip (empty transcript):", base); continue
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3,
                    "-ac", "1", "-ar", "16000", wav], check=True)
    open(lab, "w", encoding="utf-8").write(text)
    built += 1
    if built % 25 == 0:
        print(f"  ...{built}/{len(pairs)}")
print(f"\nbuilt {built} wav/lab pairs -> {WP}/corpus")
