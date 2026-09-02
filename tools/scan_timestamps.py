#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan_timestamps.py — find chapter/act timestamps a human already published.

Creators put chapter marks in the description; viewers put them in comments.
Either beats anything measured from captions, so this looks for them before
any alignment is trusted. On Гроза the act times came from a comment and every
one landed on a long silence in the recording.

Needs yt-dlp metadata alongside the captions:
    yt-dlp --skip-download --write-description --write-info-json --write-comments \
           -o 'tools/captions/%(id)s' -a tools/captions/meta-videos.txt

    python3 tools/scan_timestamps.py            # every video with metadata
    python3 tools/scan_timestamps.py --slug groza-spektakl
"""
import argparse, bisect, glob, importlib.util, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CAPS = os.path.join(HERE, "captions")

TS = re.compile(r"(?<![\d:])(\d{1,2}):([0-5]\d)(?::([0-5]\d))?(?![\d:])")
# What the label beside a timestamp has to look like for this to be a chapter
# list rather than someone quoting a favourite moment.
LABEL = re.compile(
    r"(действ|акт\b|карт|глава|глвa|част|сцена|явлен|эпизод|песнь|том\b|книга|"
    r"пролог|эпилог|предислов|вступлен|послеслов|письмо|рассказ|повест|новелл|"
    r"стих|серия|chapter|part\b|act\b|scene|book\b|[ivxlIVXL]{1,6}\b|\d{1,3}\s*[.)]?)",
    re.I)

# A list of three or more timestamped lines IS a chapter list, whatever words
# sit beside them. Many descriptions label chapters only by name — "12:34
# Бэла", "38:02 Максим Максимыч" — and a keyword rule reads straight past
# them. Density is the reliable signal; the keyword rule stays for lists of
# one or two.
MIN_RUN = 3


def secs(m):
    a, b, c = m.group(1), m.group(2), m.group(3)
    return (int(a) * 3600 + int(b) * 60 + int(c)) if c else (int(a) * 60 + int(b))


def marks(text):
    """[(seconds, label)] from a published chapter list."""
    timed = []                       # every line carrying a timestamp
    for line in (text or "").splitlines():
        m = TS.search(line)
        if not m:
            continue
        label = TS.sub("", re.sub(r"https?://\S+", "", line)).strip(" \t-–—•·:[]()|»«")
        timed.append((secs(m), label[:60], bool(LABEL.search(line))))
    if not timed:
        return []
    # Structural rule first: enough timestamped lines, rising in time, is a
    # chapter list even when every label is just a name.
    rising = sum(1 for a, b in zip(timed, timed[1:]) if b[0] > a[0])
    if len(timed) >= MIN_RUN and rising >= len(timed) - 2:
        return [(t, l or "(untitled)") for t, l, _ in timed]
    return [(t, l) for t, l, kw in timed if kw and l]


def sources(vid):
    """(where, text) for every place a timestamp list could hide."""
    d = os.path.join(CAPS, vid + ".description")
    if os.path.exists(d):
        yield "description", io.open(d, encoding="utf-8", errors="replace").read()
    j = os.path.join(CAPS, vid + ".info.json")
    if os.path.exists(j):
        try:
            info = json.load(io.open(j, encoding="utf-8"))
        except Exception:
            return
        for ch in (info.get("chapters") or []):
            if ch.get("title") is not None and ch.get("start_time") is not None:
                yield "chapters", "%d:%02d:%02d %s" % (int(ch["start_time"]) // 3600,
                       int(ch["start_time"]) % 3600 // 60, int(ch["start_time"]) % 60, ch["title"])
        for c in (info.get("comments") or []):
            t = c.get("text") or ""
            if len(TS.findall(t)) >= MIN_RUN or (LABEL.search(t) and TS.search(t)):
                yield "comment by %s" % (c.get("author") or "?"), t


_av = None
def av_mod():
    global _av
    if _av is None:
        sp = importlib.util.spec_from_file_location("av", os.path.join(HERE, "align_video.py"))
        _av = importlib.util.module_from_spec(sp); sp.loader.exec_module(_av)
    return _av


def verify(ms, vid, fb2, probe_words=14):
    """Does the book's text actually begin at these timestamps?

    Spacing and entry counts cannot separate a chapter list from a tidy set of
    favourite moments. This can: take the list's k-th entry, take the k-th
    chapter's opening words out of the FB2, and look for those words in the
    captions right there. A real chapter list scores high across the board; a
    viewer's bookmarks score near zero because nothing in particular begins at
    them. Offsets are tried because a list may skip a preface.

    Returns (best mean score, offset, per-entry scores).
    """
    av = av_mod()
    cap = os.path.join(CAPS, vid + ".ru.vtt")
    if not os.path.exists(cap) or not os.path.exists(fb2):
        return None
    words = av.parse_vtt(cap)
    if not words:
        return None
    times = [w["b"] for w in words]
    chaps = av.fb2_chapters_body(fb2, probe_words)
    best = (0.0, 0, [])
    for off in (0, 1, -1, 2, -2):
        scores = []
        for i, (t, _lab) in enumerate(ms):
            ci = i + off
            if not (0 <= ci < len(chaps)):
                continue
            pr = chaps[ci]["probe"]
            if len(pr) < 6:
                continue
            lo = bisect.bisect_left(times, t - 45)
            hi = bisect.bisect_right(times, t + 90)
            _, sc = av.cbt.best_match(words, pr, lo, max(lo, hi))
            scores.append(sc)
        if scores:
            mean = sum(scores) / len(scores)
            if mean > best[0]:
                best = (mean, off, scores)
    return best


def verify_entries(ms, vid, fb2, span=4, accept=0.70):
    """Verify each timestamp on its own, and say which chapter it opens.

    Judging a list as a whole is wrong. Красный смех's description is a real
    chapter list that merges entries ("Отрывок 3-4"), so a sequential mapping
    holds for three entries and then drifts; scored as one list it looks half
    fake, entry by entry it is three solid facts and some noise. So: for each
    timestamp, try the chapters near its sequential position and keep the best
    one that actually matches the captions there.

    Returns [(seconds, label, chapter_index, score)] for entries that verify.
    """
    av = av_mod()
    cap = os.path.join(CAPS, vid + ".ru.vtt")
    if not (os.path.exists(cap) and os.path.exists(fb2)):
        return []
    words = av.parse_vtt(cap)
    if not words:
        return []
    times = [w["b"] for w in words]
    chaps = av.fb2_chapters_body(fb2, 14)
    out = []
    for i, (t, lab) in enumerate(ms):
        lo = bisect.bisect_left(times, t - 45)
        hi = bisect.bisect_right(times, t + 90)
        best = (0.0, -1)
        for ci in range(max(0, i - span), min(len(chaps), i + span + 1)):
            pr = chaps[ci]["probe"]
            if len(pr) < 6:
                continue
            _, sc = av.cbt.best_match(words, pr, lo, max(lo, hi))
            if sc > best[0]:
                best = (sc, ci)
        if best[0] >= accept:
            out.append((t, lab, best[1], round(best[0], 2)))
    return out


def judge(ms, cur):
    """How much a published list looks like this book's real chapter marks.

    Three ways a list earns trust: it has about as many entries as the book
    has chapters, its times sit close to the manifest's, and its spacing is
    irregular. That last one matters — a description listing chapters at
    0:24:35, 0:48:20, 1:12:45, 1:37:10 at a metronomic 24 minutes was written
    by something that never listened to the recording, and its times are
    fiction however confident they look.
    """
    if len(ms) < 2:
        return 0.0, "too short"
    gaps = [b[0] - a[0] for a, b in zip(ms, ms[1:])]
    mean = sum(gaps) / len(gaps)
    if mean <= 0:
        return 0.0, "not rising"
    var = (sum((g - mean) ** 2 for g in gaps) / len(gaps)) ** 0.5 / mean
    if var < 0.08:
        return 0.0, "evenly spaced — fabricated, not heard"
    if not cur:
        return 0.5, "no manifest times to compare"
    near = sorted(abs(t - min((c for _, c in cur), key=lambda c: abs(c - t))) for t, _ in ms)
    med = near[len(near) // 2]
    ratio = min(len(ms), len(cur)) / max(len(ms), len(cur))
    if med > 300:
        return 0.2, "times do not line up with the manifest (median %ds off)" % med
    score = ratio * (1.0 if med <= 30 else 0.6)
    return score, "%d entries vs %d chapters, median %ds from the manifest" % (len(ms), len(cur), med)


def clock(t):
    t = int(t); return "%d:%02d:%02d" % (t // 3600, t % 3600 // 60, t % 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug"); ap.add_argument("--min", type=int, default=2,
                    help="ignore lists shorter than this")
    args = ap.parse_args()
    man = json.load(io.open(os.path.join(ROOT, "private", "books", "index.json"), encoding="utf-8"))
    vids = {}
    for e in man:
        if args.slug and e.get("slug") != args.slug:
            continue
        for k, seg in sorted((e.get("videos") or {}).items(), key=lambda x: int(x[0])):
            y = (seg or {}).get("youtube")
            if y:
                vids.setdefault(y, (e, []))[1].append((int(k), seg))
    hits = 0
    for vid, (e, segs) in vids.items():
        found = []
        for where, text in sources(vid):
            ms = marks(text)
            if len(ms) >= args.min:
                found.append((where, sorted(set(ms))))
        if not found:
            continue
        hits += 1
        cur = [(ci, s.get("start")) for ci, s in segs if s.get("start") is not None]
        print("== %s  (%s)  %d timed chapters in the manifest" % (e.get("title"), vid, len(cur)))
        print("   manifest: %s" % ", ".join(clock(t) for _, t in cur[:9]))
        for where, ms in found:
            sc, why = judge(ms, cur)
            if sc < 0.35:
                print("   %-28s IGNORED — %s" % (where[:28], why)); continue
            print("   %-28s [%.2f] %s" % (where[:28], sc, why))
            print("      %s" % ", ".join("%s %s" % (clock(t), l[:24]) for t, l in ms[:10]))
        print()
    withmeta = sum(1 for v in vids if os.path.exists(os.path.join(CAPS, v + ".info.json"))
                   or os.path.exists(os.path.join(CAPS, v + ".description")))
    print("%d of %d videos WITH METADATA have a published timestamp list "
          "(%d videos in the manifest overall)" % (hits, withmeta, len(vids)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
