#!/usr/bin/env python3
"""
chop_by_transcript.py — split a long recording into one MP3 per chapter/act when
there is NO alignment JSON to read boundaries from (a fresh archive.org rip, a
new radio play, anything not yet run through MFA).

Method
------
  1. Transcribe the long file once with faster-whisper, word timestamps on.
  2. Pull the chapter/act list out of the FB2: heading text + the first words of
     each chapter's body. That pair is the "probe".
  3. Walk the transcript forward, chapter by chapter, and find where each probe
     matches best. The transcript is imperfect, so matching is fuzzy and always
     forward-only — a chapter can never start before the previous one.
  4. Write cuts.tsv. LOOK AT IT. Every row shows a confidence score and the
     transcript text found at that point; anything below --min-score is flagged.
  5. Re-run with --cut to produce the MP3s.

This deliberately stops in the middle for a human read. A silently wrong cut
point is much more expensive than thirty seconds of eyeballing.

Requires: ffmpeg, and `pip install faster-whisper` for the transcribe step.
The transcript is cached next to the audio as <audio>.words.json, so re-running
the matcher with different settings costs nothing.

Usage:
    python3 tools/chop_by_transcript.py --audio full.mp3 --fb2 book.fb2 --out cuts/
    # read cuts/cuts.tsv, fix any row by editing the `start` column
    python3 tools/chop_by_transcript.py --audio full.mp3 --out cuts/ --cut
"""
import argparse, difflib, json, os, re, subprocess, sys, unicodedata
import xml.etree.ElementTree as ET

PROBE_WORDS = 12          # how many words of a chapter's opening to match on
WINDOW_SLACK = 4000       # how many transcript words ahead to search


def norm(s):
    s = unicodedata.normalize("NFKC", str(s or "")).lower().replace("ё", "е")
    return re.sub(r"[^а-яa-z0-9 ]", " ", s)


def words_of(s):
    return [w for w in norm(s).split() if w]


def clock(t):
    t = max(0.0, float(t))
    return "%d:%02d:%06.3f" % (int(t // 3600), int(t % 3600 // 60), t % 60)


# ── 1. transcript ────────────────────────────────────────────────────────────
def transcribe(audio, model_name, device, compute_type):
    cache = audio + ".words.json"
    if os.path.exists(cache):
        print("using cached transcript: %s" % cache)
        return json.load(open(cache, encoding="utf-8"))
    from faster_whisper import WhisperModel
    print("transcribing with %s (%s) — this is the slow part" % (model_name, device))
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments, _ = model.transcribe(audio, language="ru", word_timestamps=True,
                                   vad_filter=True, beam_size=5)
    out = []
    for seg in segments:
        for w in (seg.words or []):
            t = norm(w.word).strip()
            if t:
                out.append({"w": t, "b": round(w.start, 3), "e": round(w.end, 3)})
        if len(out) % 2000 < 20:
            print("  … %d words, %s" % (len(out), clock(out[-1]["b"] if out else 0)))
    json.dump(out, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    print("cached %d words -> %s" % (len(out), cache))
    return out


# ── 2. chapters from the FB2 ─────────────────────────────────────────────────
def strip_ns(tag):
    return tag.split("}", 1)[-1]


def fb2_chapters(path):
    raw = open(path, "rb").read()
    m = re.match(rb"<\?xml[^>]*encoding=[\"']([\w-]+)[\"']", raw)
    enc = (m.group(1).decode() if m else "utf-8")
    text = raw.decode(enc, errors="replace")
    text = re.sub(r"^<\?xml[^>]*\?>", "", text, count=1).strip()
    root = ET.fromstring(text)

    bodies = [el for el in root.iter() if strip_ns(el.tag) == "body"
              and el.get("name") not in ("notes", "comments")]
    chapters = []

    def walk(section):
        subs = [c for c in section if strip_ns(c.tag) == "section"]
        if subs:
            for c in subs:
                walk(c)
            return
        title = " ".join(t.strip() for t in section.itertext()
                         if t.strip())[:0]  # placeholder, filled below
        title_el = next((c for c in section if strip_ns(c.tag) == "title"), None)
        title = " ".join(x.strip() for x in (title_el.itertext() if title_el is not None else []) if x.strip())
        body_words = []
        for el in section:
            if el is title_el:
                continue
            body_words += words_of(" ".join(x for x in el.itertext()))
            if len(body_words) >= PROBE_WORDS * 3:
                break
        chapters.append({"title": title or "(untitled)",
                         "probe": (words_of(title) + body_words)[:PROBE_WORDS]})

    for b in bodies:
        for sec in [c for c in b if strip_ns(c.tag) == "section"]:
            walk(sec)
    return [c for c in chapters if c["probe"]]


# ── 3. match probes into the transcript ──────────────────────────────────────
def best_match(twords, probe, lo, hi):
    """Slide `probe` over transcript[lo:hi]; return (index, score)."""
    n = len(probe)
    target = " ".join(probe)
    best_i, best_s = -1, 0.0
    sm = difflib.SequenceMatcher()
    sm.set_seq2(target)
    for i in range(lo, max(lo, min(hi, len(twords) - n))):
        cand = " ".join(w["w"] for w in twords[i:i + n])
        sm.set_seq1(cand)
        if sm.real_quick_ratio() < best_s or sm.quick_ratio() < best_s:
            continue
        s = sm.ratio()
        if s > best_s:
            best_i, best_s = i, s
            if s > 0.97:
                break
    return best_i, best_s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--fb2")
    ap.add_argument("--out", required=True, help="output dir (holds cuts.tsv + MP3s)")
    ap.add_argument("--cut", action="store_true", help="read cuts.tsv and write the MP3s")
    ap.add_argument("--slug", help="output filename stem (default: audio basename)")
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--compute-type", default="float16")
    ap.add_argument("--min-score", type=float, default=0.62)
    ap.add_argument("--lead", type=float, default=0.6, help="seconds kept before each chapter's first word")
    ap.add_argument("--quality", default="3")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    tsv = os.path.join(args.out, "cuts.tsv")
    slug = args.slug or os.path.splitext(os.path.basename(args.audio))[0]
    dur = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", args.audio]).decode().strip())

    # ── cut phase ────────────────────────────────────────────────────────────
    if args.cut:
        if not os.path.exists(tsv):
            raise SystemExit("no %s — run the match phase first" % tsv)
        rows = []
        for line in open(tsv, encoding="utf-8"):
            if line.startswith("#") or not line.strip():
                continue
            f = line.rstrip("\n").split("\t")
            rows.append({"n": int(f[0]), "start": float(f[1]), "title": f[3]})
        rows.sort(key=lambda r: r["start"])
        for i, r in enumerate(rows):
            end = rows[i + 1]["start"] if i + 1 < len(rows) else dur
            out_mp3 = os.path.join(args.out, "%s-ch%02d.mp3" % (slug, r["n"]))
            subprocess.run(["ffmpeg", "-y", "-v", "error",
                            "-ss", "%.3f" % r["start"], "-to", "%.3f" % end,
                            "-i", args.audio, "-c:a", "libmp3lame", "-q:a", args.quality,
                            "-map_metadata", "-1", out_mp3], check=True)
            print("%-28s %s .. %s  (%s)  %s" % (os.path.basename(out_mp3),
                  clock(r["start"]), clock(end), clock(end - r["start"]), r["title"][:40]))
        print("\n%d files in %s" % (len(rows), args.out))
        return

    # ── match phase ──────────────────────────────────────────────────────────
    if not args.fb2:
        ap.error("--fb2 is required for the match phase")
    twords = transcribe(args.audio, args.model, args.device, args.compute_type)
    chapters = fb2_chapters(args.fb2)
    print("%d chapters in the FB2, %d words in the transcript\n" % (len(chapters), len(twords)))

    cursor, rows, low = 0, [], 0
    for n, ch in enumerate(chapters, 1):
        i, score = best_match(twords, ch["probe"], cursor, cursor + WINDOW_SLACK)
        if i < 0:
            rows.append((n, -1.0, 0.0, ch["title"], "NOT FOUND"))
            continue
        start = max(0.0, twords[i]["b"] - args.lead) if n > 1 else 0.0
        heard = " ".join(w["w"] for w in twords[i:i + PROBE_WORDS])
        rows.append((n, round(start, 3), round(score, 3), ch["title"], heard))
        cursor = i + max(1, len(ch["probe"]))
        if score < args.min_score:
            low += 1

    with open(tsv, "w", encoding="utf-8") as fh:
        fh.write("# n\tstart_seconds\tscore\tchapter_title\ttranscript_heard_there\n")
        fh.write("# edit the start column by hand where the score looks bad, then rerun with --cut\n")
        for r in rows:
            fh.write("%d\t%.3f\t%.3f\t%s\t%s\n" % r)

    print("%-4s %-14s %-7s %s" % ("n", "start", "score", "chapter"))
    for n, start, score, title, heard in rows:
        mark = "  <-- CHECK" if score < args.min_score else ""
        print("%-4d %-14s %-7.3f %s%s" % (n, clock(start), score, title[:44], mark))
    print("\nwrote %s  (%d of %d below --min-score %.2f)" % (tsv, low, len(rows), args.min_score))
    print("Review it, fix any start times by hand, then rerun with --cut.")


if __name__ == "__main__":
    main()
