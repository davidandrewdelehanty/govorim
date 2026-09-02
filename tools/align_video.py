#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""align_video.py — find where each chapter really starts in a YouTube recording.

WHY THIS EXISTS
---------------
private/books/index.json gives every chapter a `start`/`end` in its video. When
those are wrong the reader is dropped minutes into the wrong scene. The earlier
audit could only say a segment looked wrong — it compared reading rates and
guessed. It could not say what the right number was, and once it was wrong
about Гроза and about the Synodal Bible, guessing stopped being good enough.

This does not guess. YouTube publishes word-level automatic captions; this
takes the first dozen words of a chapter out of the FB2, finds where those
words are actually spoken, and reports that timestamp. The transcript is only
ever used to locate a moment — no transcribed text is kept, shown or shipped,
so no FB2 is ever contaminated with machine-heard words.

The matcher is the one already proven in chop_by_transcript.py: forward-only,
fuzzy, with a confidence score per chapter. Nothing is applied automatically;
every row gets a score and a click-to-check URL, and --apply only ever reads
back a file a human has looked at.

USAGE
-----
  # 1. captions (needs network — run where you have it)
  yt-dlp --write-auto-sub --sub-lang ru --skip-download \
         -o 'tools/captions/%(id)s' https://youtu.be/VIDEOID

  # 2. propose
  python3 tools/align_video.py --slug besy --vtt-dir tools/captions \
         --out tools/timings-besy.csv

  # 3. read the CSV, spot-check the low scores by clicking check_url,
  #    delete or correct any row you don't believe, then
  python3 tools/align_video.py --apply tools/timings-besy.csv          # dry run
  python3 tools/align_video.py --apply tools/timings-besy.csv --write  # for real
"""
import argparse, bisect, csv, importlib.util, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MANIFEST = os.path.join(ROOT, "private", "books", "index.json")

# Reuse the matcher and the FB2 chapter probes rather than writing a second
# copy that can drift from the one already trusted for cutting audiobooks.
_spec = importlib.util.spec_from_file_location("cbt", os.path.join(HERE, "chop_by_transcript.py"))
cbt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cbt)

CUE = re.compile(r"^(\d\d):(\d\d):(\d\d\.\d\d\d) --> (\d\d):(\d\d):(\d\d\.\d\d\d)")
WORD = re.compile(r"<(\d\d):(\d\d):(\d\d\.\d\d\d)><c>\s*([^<]+)</c>")


def _secs(h, m, s):
    return int(h) * 3600 + int(m) * 60 + float(s)


def clock(t):
    t = max(0, int(round(float(t))))
    return "%d:%02d:%02d" % (t // 3600, t % 3600 // 60, t % 60)


def parse_vtt(path):
    """[{w,b}] word-level, from YouTube's automatic captions.

    Auto-captions roll up: each cue repeats the previous line as plain text and
    adds the new words carrying <c> tags. Reading only the tagged line gives
    every word exactly once, with its own timestamp.
    """
    out, cue = [], None
    for line in io.open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        m = CUE.match(line)
        if m:
            cue = _secs(*m.groups()[:3])
            continue
        if cue is None or "<c>" not in line:
            continue
        head = line.split("<", 1)[0].strip()
        if head:
            for w in cbt.words_of(head):
                out.append({"w": w, "b": cue})
        for mm in WORD.finditer(line):
            for w in cbt.words_of(mm.group(4)):
                out.append({"w": w, "b": _secs(mm.group(1), mm.group(2), mm.group(3))})
    return out


def fb2_chapters_body(path, probe_words):
    """Chapter probes taken from the BODY text only, never the heading.

    chop_by_transcript.py prefixes each probe with the chapter title, which is
    right when cutting audio — the title is spoken and belongs to the chapter.
    It is wrong here. A narrator says "белла" where the FB2 says "ЧАСТЬ ПЕРВАЯ
    I. Бэла", so the fuzzy match opens on the mismatched heading and the
    timestamp reported is the start of that mush, not the start of the prose.
    Every proposal came out seconds early as a result; Герой нашего времени
    ch1 was pulled 26s before "Я ехал на перекладных", which is exactly where
    the manifest already had it.

    Matching the body alone means the matched position IS the first word of
    the chapter, which is the number we actually want.
    """
    raw = open(path, "rb").read()
    m = re.match(rb"<\?xml[^>]*encoding=[\"']([\w-]+)[\"']", raw)
    text = raw.decode((m.group(1).decode() if m else "utf-8"), errors="replace")
    text = re.sub(r"^<\?xml[^>]*\?>", "", text, count=1).strip()
    root = __import__("xml.etree.ElementTree", fromlist=["ElementTree"]).fromstring(text)
    bodies = [el for el in root.iter() if cbt.strip_ns(el.tag) == "body"
              and el.get("name") not in ("notes", "comments")]
    chapters = []

    def walk(section):
        subs = [c for c in section if cbt.strip_ns(c.tag) == "section"]
        if subs:
            for c in subs:
                walk(c)
            return
        title_el = next((c for c in section if cbt.strip_ns(c.tag) == "title"), None)
        title = " ".join(x.strip() for x in (title_el.itertext() if title_el is not None else []) if x.strip())
        body = []
        for el in section:
            if el is title_el:
                continue
            body += cbt.words_of(" ".join(x for x in el.itertext()))
            if len(body) >= probe_words * 3:
                break
        chapters.append({"title": title or "(untitled)", "probe": body[:probe_words]})

    for b in bodies:
        for sec in [c for c in b if cbt.strip_ns(c.tag) == "section"]:
            walk(sec)
    return chapters


def find_vtt(vid, vtt_dir, explicit):
    if vid in explicit:
        return explicit[vid]
    if not vtt_dir:
        return None
    for name in sorted(os.listdir(vtt_dir)):
        if name.startswith(vid) and name.endswith(".vtt"):
            return os.path.join(vtt_dir, name)
    return None


def load_entry(manifest, slug):
    for e in manifest:
        if e.get("slug") == slug:
            return e
    for e in manifest:
        stem = os.path.basename(e.get("filename", "")).rsplit(".", 1)[0]
        if stem == slug or slug.lower() in e.get("title", "").lower():
            return e
    raise SystemExit("no book matching %r" % slug)


# ── propose ─────────────────────────────────────────────────────────────────
def propose(args):
    manifest = json.load(io.open(MANIFEST, encoding="utf-8"))
    entry = load_entry(manifest, args.slug)
    videos = entry.get("videos") or {}
    if not videos:
        raise SystemExit("%s has no videos map" % entry.get("title"))

    fb2 = args.fb2 or os.path.join(ROOT, "public", "books", entry["filename"])
    chapters = fb2_chapters_body(fb2, args.probe)
    print("%s — %d chapters in the FB2, %d entries in the videos map"
          % (entry.get("title"), len(chapters), len(videos)), file=sys.stderr)
    if len(chapters) != len(videos):
        print("  !! counts differ: chapter indices cannot be trusted to line up.\n"
              "     Fix that first (tools/flatten_fb2.py) — proposals below are "
              "indexed by the videos map and may point at the wrong text.",
              file=sys.stderr)

    explicit = dict(p.split("=", 1) for p in (args.vtt or []))

    # chapters that share a video are matched together, in order, so a match can
    # never land before the previous chapter's.
    by_video = {}
    for k in sorted(videos, key=lambda x: int(x)):
        seg = videos[k]
        if not isinstance(seg, dict) or not seg.get("youtube"):
            continue
        by_video.setdefault(seg["youtube"], []).append((int(k), seg))

    rows, missing = [], []
    for vid, items in by_video.items():
        path = find_vtt(vid, args.vtt_dir, explicit)
        if not path:
            missing.append(vid)
            continue
        words = parse_vtt(path)
        if not words:
            missing.append(vid)
            continue
        print("  %s: %d caption words, %d chapters" % (vid, len(words), len(items)), file=sys.stderr)
        times = [w["b"] for w in words]
        cursor, expect = 0, 0.0
        for ci, seg in items:
            probe = chapters[ci]["probe"] if ci < len(chapters) else []
            if not probe:
                continue
            # Search a window around where this chapter is EXPECTED to start,
            # not the whole rest of the recording. Scripture and plays repeat
            # set phrases ("и сказал господь моисею говоря") many times over;
            # an unbounded forward search locks onto a later copy, and because
            # the walk is forward-only that one bad match then drags every
            # chapter after it. The manifest's own value is the anchor when it
            # has one — the audit found only 32 bad segments in 1209, so it is
            # usually roughly right — and otherwise the previous match is.
            cur = seg.get("start")
            anchor = float(cur) if cur is not None else expect
            lo = max(cursor, bisect.bisect_left(times, anchor - args.window))
            hi = min(len(words), bisect.bisect_right(times, anchor + args.window))
            i, score = cbt.best_match(words, probe, lo, max(lo, hi))
            if i < 0:
                # Nothing in the window. Keep the walk honest by stepping the
                # expectation forward rather than letting the cursor stall.
                expect = anchor + 60.0
                continue
            t = words[i]["b"]
            rows.append({
                "slug": entry.get("slug", args.slug),
                "chapter": ci,
                "heading": seg.get("heading", ""),
                "video": vid,
                "current_start": "" if cur is None else clock(cur),
                "proposed_start": clock(max(0, t - args.lead)),
                "delta_sec": "" if cur is None else int(round(t - args.lead - cur)),
                "score": round(score, 3),
                "fb2_opening": " ".join(probe[:8]),
                "heard_at_match": " ".join(w["w"] for w in words[i:i + 8]),
                "at_window_edge": "yes" if abs(t - anchor) > args.window * 0.9 else "",
                "check_url": "https://youtu.be/%s?t=%d" % (vid, max(0, int(t - args.lead) - 3)),
                "new_start_sec": "",
            })
            # Only a confident match is allowed to move the walk forward. A
            # weak one leaves the cursor where it was, so a single unmatched
            # chapter cannot push the rest of the book out of reach.
            if score >= args.min_score:
                cursor = i + max(1, len(probe) // 2)
                expect = t + 60.0
            else:
                expect = anchor + 60.0

    if missing:
        print("\n  no captions found for %d video(s): %s" % (len(missing), " ".join(missing)), file=sys.stderr)

    rows.sort(key=lambda r: r["chapter"])
    cols = ["slug", "chapter", "heading", "video", "current_start", "proposed_start",
            "delta_sec", "score", "fb2_opening", "heard_at_match", "at_window_edge", "check_url", "new_start_sec"]
    with io.open(args.out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    good = [r for r in rows if r["score"] >= args.min_score]
    moved = [r for r in good if r["delta_sec"] != "" and abs(int(r["delta_sec"])) > args.tolerance]
    print("\n%d chapters matched — %d confident (score >= %.2f), %d of those disagree "
          "with the manifest by more than %ds"
          % (len(rows), len(good), args.min_score, len(moved), args.tolerance), file=sys.stderr)
    print("wrote %s" % args.out, file=sys.stderr)
    return 0


# ── apply ───────────────────────────────────────────────────────────────────
def apply(args):
    manifest = json.load(io.open(MANIFEST, encoding="utf-8"))
    rows = list(csv.DictReader(io.open(args.apply, encoding="utf-8-sig")))
    by_slug = {}
    for r in rows:
        # new_start_sec, if a human typed one, always wins over the proposal.
        override = (r.get("new_start_sec") or "").strip()
        if override:
            try:
                t = int(float(override))
            except ValueError:
                print("  skipping ch%s: new_start_sec=%r is not a number" % (r.get("chapter"), override))
                continue
        else:
            if float(r.get("score") or 0) < args.min_score:
                continue
            p = (r.get("proposed_start") or "").split(":")
            if len(p) != 3:
                continue
            t = int(p[0]) * 3600 + int(p[1]) * 60 + int(float(p[2]))
        by_slug.setdefault(r["slug"], {})[int(r["chapter"])] = t

    changed = 0
    for e in manifest:
        want = by_slug.get(e.get("slug"))
        if not want:
            continue
        videos = e.get("videos") or {}
        keys = sorted((int(k) for k in videos), key=int)
        for ci, t in sorted(want.items()):
            seg = videos.get(str(ci)) or videos.get(ci)
            if not isinstance(seg, dict):
                continue
            old = seg.get("start")
            if old == t:
                continue
            print("  %s ch%-4d %s -> %s" % (e.get("slug"), ci,
                  clock(old) if old is not None else "(none)", clock(t)))
            seg["start"] = t
            changed += 1
            # a chapter's end is the next chapter's start in the same video
            prev = [k for k in keys if k < ci and (videos.get(str(k)) or {}).get("youtube") == seg.get("youtube")]
            if prev:
                p = videos.get(str(prev[-1]))
                if isinstance(p, dict) and p.get("end") is not None:
                    p["end"] = t

    print("\n%d segment(s) would change." % changed)
    if not args.write:
        print("Dry run — nothing written. Re-run with --write to save.")
        return 0
    bak = MANIFEST + ".bak-prealign"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8").write(io.open(MANIFEST, encoding="utf-8").read())
        print("backup: %s" % bak)
    with io.open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    print("wrote %s" % MANIFEST)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", help="book to align")
    ap.add_argument("--fb2", help="override the FB2 path")
    ap.add_argument("--vtt-dir", help="directory of <videoid>*.vtt caption files")
    ap.add_argument("--vtt", action="append", help="VIDEOID=path/to.vtt (repeatable)")
    ap.add_argument("--out", default="timings.csv")
    ap.add_argument("--window", type=float, default=600.0,
                    help="seconds either side of the expected start to search (default 10 min)")
    ap.add_argument("--probe", type=int, default=20,
                    help="words of a chapter's opening to match on; longer resists set phrases")
    ap.add_argument("--lead", type=float, default=1.0, help="seconds kept before the first word")
    ap.add_argument("--min-score", type=float, default=0.62)
    ap.add_argument("--tolerance", type=int, default=20, help="delta below this is agreement")
    ap.add_argument("--apply", help="read a checked CSV back into the manifest")
    ap.add_argument("--write", action="store_true", help="with --apply, actually save")
    args = ap.parse_args()
    if args.apply:
        return apply(args)
    if not args.slug:
        ap.error("--slug is required to propose timings")
    return propose(args)


if __name__ == "__main__":
    sys.exit(main())
