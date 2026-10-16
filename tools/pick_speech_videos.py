#!/usr/bin/env python3
"""Choose each Soviet speech's YouTube video by what it SAYS, then build its
jump points. Runs in WSL (needs yt-dlp and the network); no AI involved.

For every speech in tools/soviet_speeches.json (or --only <slugs>):
  * candidates = the ids listed in the JSON + a YouTube search
    («<surname> <title>», or the entry's "query");
  * each candidate's Russian captions are fetched (cached in tools/vtt/);
  * coverage = share of the text's words (5+ letters) that the captions also
    contain; the video with the best coverage wins, if it reaches --min
    (default 0.55). A clip or a wrong video scores low and is passed over;
  * the catalogue's videos block is updated and tools/sync_all.py builds the
    jump points.
Speeches cut out of one long recording (Lenin's, with start/end) are only
scored inside their own window and keep their listed video.

    python3 tools/pick_speech_videos.py
    python3 tools/pick_speech_videos.py --only bratya-i-syostry stalin-rech-na-xix-sezde-1952
"""
import io, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import sync_all
from reader_chapters import reader_chapters

SPEC = "tools/soviet_speeches.json"
MANIFEST = "private/books/index.json"
VTT = "tools/vtt"


def words(t):
    return set(w for w in re.findall(r"[а-яё]{5,}", t.lower().replace("ё", "е")))


def captions(vid):
    path = os.path.join(VTT, vid + ".ru.vtt")
    if not os.path.exists(path):
        subprocess.call(["yt-dlp", "--write-auto-sub", "--write-sub", "--sub-lang", "ru",
                         "--skip-download", "--quiet", "--no-warnings",
                         "-o", os.path.join(VTT, "%(id)s"), "https://youtu.be/" + vid])
    return path if os.path.exists(path) else None


def info(vid):
    r = subprocess.run(["yt-dlp", "-J", "--skip-download", "--no-warnings", "https://youtu.be/" + vid],
                       capture_output=True, text=True, timeout=120)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}


def search(q, n=12):
    r = subprocess.run(["yt-dlp", "--flat-playlist", "--print", "%(id)s", "ytsearch%d:%s" % (n, q)],
                       capture_output=True, text=True, timeout=180)
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


def coverage(text_words, vid, start=0, end=0):
    if not captions(vid):
        return 0.0
    toks = sync_all.toks_for(vid) or []
    got = set()
    for tm, w in toks:
        if tm >= start and (not end or tm <= end):
            got |= words(w)
    return len(text_words & got) / max(len(text_words), 1)


def main():
    a = sys.argv[1:]
    only = set(a[a.index("--only") + 1:]) - {"--min"} if "--only" in a else None
    mn = float(a[a.index("--min") + 1]) if "--min" in a else 0.55
    spec = json.load(io.open(SPEC, encoding="utf-8"))["speeches"]
    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    by = {b.get("slug"): b for b in idx}
    os.makedirs(VTT, exist_ok=True)
    report = []
    for s in spec:
        if only and s["slug"] not in only:
            continue
        e = by.get(s["slug"])
        if not e:
            print("-- %s: not in the catalogue yet (run import_soviet_speeches.py)" % s["slug"]); continue
        chs, _ = reader_chapters("public/books/" + e["filename"])
        tw = words(" ".join(p for c in chs for p in c["paras"]))
        print("==", s["slug"], "(%d distinct words)" % len(tw))
        windowed = bool(s.get("end")) or bool(s.get("start"))
        cands = list(s.get("youtube") or [])
        if not windowed:
            surname = e["author"].split()[0]
            q = s.get("query") or "%s %s" % (surname, re.sub(r"\s*\(\d{4}\)", "", s["title"]) + " " + str(s["year"]))
            cands += [v for v in search(q) if v not in cands]
        best = (0.0, None)
        for vid in cands:
            cov = coverage(tw, vid, s.get("start") or 0, s.get("end") or 0)
            print("   %.2f  %s" % (cov, vid))
            if cov > best[0]:
                best = (cov, vid)
            if cov >= 0.9:
                break
        cov, vid = best
        if not vid or cov < mn:
            print("   !! no video covers the text (best %.2f) — left as it was" % cov)
            report.append((s["slug"], "no full recording found (best %.2f)" % cov)); continue
        if not windowed:
            j = info(vid)
            if j.get("playable_in_embed") is False:
                print("   !! %s cannot be embedded" % vid)
                report.append((s["slug"], "best video not embeddable")); continue
        seg = dict((e.get("videos") or {}).get("0") or {})
        seg.update({"youtube": vid, "heading": s["title"], "start": s.get("start") or 0})
        if s.get("end"):
            seg["end"] = s["end"]
        else:
            seg.pop("end", None)
        e["videos"] = {"0": seg}
        e.pop("audiobook", None); e.pop("publicAudio", None)
        r = sync_all.run(e, verbose=False)
        report.append((s["slug"], "%s  coverage %.2f  jump points: %s" % (vid, cov,
                       "yes (%s%% anchored)" % r.get("median_anchor") if r and r.get("chapters") else "none")))
    io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
    print("\n" + "\n".join("%-46s %s" % x for x in report))


if __name__ == "__main__":
    main()
