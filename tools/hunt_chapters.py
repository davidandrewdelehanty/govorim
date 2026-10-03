#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find a reading that was uploaded chapter by chapter.

hunt_audio.py looks for one video holding a whole book, and its length check
is what tells a reading from an excerpt. That check is also why it finds
nothing for the longest books in the library: nobody uploads Воскресение as a
single twenty-hour file. 66 multi-chapter books have no recording, and the big
ones among them — Воскресение, Идиот, Подросток, Униженные и оскорблённые —
are read on YouTube one chapter at a time.

The thing to find is the SERIES, not the chapters. Searching for each chapter
on its own would mean 129 searches for Воскресение, each free to wander off to
a different reader, and a book stitched from four voices with three chapters
missing. A reader who posted chapter one posted the rest, in one playlist or
on one channel, so this finds that series once and then maps the chapters onto
it in order.

    python3 tools/hunt_chapters.py --slug voskresenie --dry-run
    python3 tools/hunt_chapters.py --slug voskresenie
    python3 tools/hunt_chapters.py --slug idiot --playlist <url>   # found by hand

Needs the network (yt-dlp). What it writes is verified the same way
place_picks.py verifies its own: a chapter is attached only when that
chapter's opening words are in THAT video's transcript. A chapter whose video
cannot be checked is left without one rather than attached on trust.
"""
import argparse
import io
import json
import os
import re
import sys

sys.path.insert(0, "tools")
import hunt_audio as ha
import place_picks as pp
from scan_alignment import chapters as fb2_chapters
import xml.etree.ElementTree as ET


def section_titles(path):
    root = ET.parse(path).getroot()
    out = []
    for el in root.iter():
        if el.tag.split("}")[-1] != "title":
            continue
        t = " ".join("".join(x.itertext()).strip() for x in el
                     if x.tag.split("}")[-1] in ("p", "v"))
        if t.strip():
            out.append(t.strip())
    return out

MANIFEST = "private/books/index.json"
VTT_DIR = "tools/vtt"

# Per chapter the band can be looser than per book: a ten-minute chapter
# often carries the reader's own introduction and a sign-off, which is a
# large fraction of a short chapter and a rounding error on a whole novel.
RATE_LO, RATE_HI = 0.34, 1.10
MIN_PROBE_HIT = 0.65      # of a probe's words, in one window
MIN_VERIFIED = 0.5        # of the chapters matched, or nothing is written
CHANNEL_CAP = 400

# «Глава 5», «Часть 2. Глава 5», «05 Воскресение», «Лев Толстой - 12»
NUM_PATTERNS = [
    re.compile(r"глава\s*[№\s]*(\d{1,3})", re.I),
    re.compile(r"час(?:ть|ти)\s*\d{1,2}[^\d]{0,12}глава\s*(\d{1,3})", re.I),
    re.compile(r"\bчасть\s*[№\s]*(\d{1,3})", re.I),
    re.compile(r"(?:^|[\s\[(#])(\d{1,3})\s*(?:глава|часть)", re.I),
    re.compile(r"(?:^|[\s\[(#])(\d{1,3})(?:\s*[-–—.)\]]|\s*$)"),
]


def chapter_no(title):
    """Which chapter a video claims to be. None when it does not claim one."""
    for rx in NUM_PATTERNS:
        m = rx.search(title or "")
        if m:
            try:
                n = int(m.group(1))
            except ValueError:
                continue
            if 1 <= n <= 999:
                return n
    return None


ORDINALS = ["первая", "вторая", "третья", "четвертая", "четвёртая", "пятая",
            "шестая", "седьмая", "восьмая", "девятая", "десятая"]
ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}


def from_roman(s):
    s = (s or "").strip().lower().replace("\u0445", "x").replace("\u0441", "c") \
                 .replace("\u0456", "i").replace("\u04cf", "i")
    if not s or any(c not in ROMAN for c in s):
        return None
    total, prev = 0, 0
    for c in reversed(s):
        v = ROMAN[c]
        total += v if v >= prev else -v
        prev = max(prev, v)
    return total or None


def part_no(text):
    """«Часть первая» -> 1, «Часть 2» -> 2, «Часть II» -> 2."""
    m = re.search(r"час(?:ть|ти)\s+([^\s,.—–-]+)", text or "", re.I)
    if not m:
        return None
    word = m.group(1).lower()
    if word.isdigit():
        return int(word)
    for i, o in enumerate(ORDINALS):
        if word.startswith(o[:5]):
            return (i + 1) if i < 4 else (i if i >= 5 else i + 1)
    return from_roman(word)


def book_numbering(headings):
    """{(part, chapter): flat index} from the book's own section titles.

    Воскресение is numbered part by part — «Часть первая — Глава I» through
    «Часть третья — Глава XXVIII», 59 + 42 + 28 — and the readers who upload
    it number their videos the same way, «Часть 01, глава 01». Treating either
    side as one flat run of 129 is what made the first attempt match nothing:
    there are three chapters called 1 and none called 60. The counts are taken
    from the file rather than written down here, so a book divided some other
    way needs no special case.
    """
    out, flat_only = {}, True
    for i, h in enumerate(headings):
        pno = part_no(h)
        m = re.search(r"глав[аыу]\s+([IVXLCivxlc\u0445\u0441\u0456]+|\d{1,3})", h or "", re.I)
        cno = None
        if m:
            g = m.group(1)
            cno = int(g) if g.isdigit() else from_roman(g)
        if pno and cno:
            out[(pno, cno)] = i
            flat_only = False
    return (out if not flat_only else {})


def video_numbering(title):
    """(part, chapter) as the uploader wrote it, or (None, chapter)."""
    return part_no(title), chapter_no(title)


def claims_book(title, book_title, surname):
    """Does the video name the book or its author? Cheap, and it is the only
    thing standing between a chapter map and somebody else's novel."""
    t = " ".join(ha.norm_t(title))
    if surname and ha.norm_t(surname) and ha.norm_t(surname)[0] in t:
        return True
    bits = ha.norm_t(book_title)
    if not bits:
        return False
    hit = sum(1 for w in bits if w in t)
    return hit >= max(1, int(len(bits) * 0.6))


def flat(url, cap=CHANNEL_CAP):
    out = ha.yt(["--skip-download", "--flat-playlist", "-J",
                 "--playlist-end", str(cap), url], timeout=180)
    try:
        d = json.loads(out)
    except Exception:
        return []
    if not isinstance(d, dict):
        return []               # yt-dlp prints "null" when it cannot extract
    return [e for e in (d.get("entries") or []) if e and e.get("id")]


def full(vid):
    out = ha.yt(["--skip-download", "-J",
                 "https://www.youtube.com/watch?v=" + vid], timeout=120)
    try:
        j = json.loads(out)
    except Exception:
        return None
    return j if isinstance(j, dict) else None


def captions(vid):
    dest = os.path.join(VTT_DIR, vid + ".ru.vtt")
    if os.path.exists(dest):
        return dest
    os.makedirs(VTT_DIR, exist_ok=True)
    ha.yt(["--write-auto-sub", "--sub-lang", "ru", "--skip-download", "--quiet",
           "-o", os.path.join(VTT_DIR, "%(id)s"),
           "https://youtu.be/" + vid], timeout=180)
    return dest if os.path.exists(dest) else None


def transcript_words(path):
    words = []
    for line in io.open(path, encoding="utf-8", errors="replace"):
        if "-->" in line or line.startswith(("WEBVTT", "Kind:", "Language:")):
            continue
        for w in re.sub(r"<[^>]+>", " ", line).split():
            n = pp.norm(w)
            if n:
                words.append(n)
    return words


def opening_is_there(chapter, words):
    """Is this chapter's opening in this transcript?

    place_picks.locate searches one transcript for every chapter in order,
    which is the right test when one video holds the book and the wrong one
    here: each chapter has a transcript of its own and order across them means
    nothing. What matters per video is only that its own chapter's first
    spoken words are in it.
    """
    index = {}
    for i, w in enumerate(words):
        index.setdefault(w, []).append(i)
    best = 0.0
    for probe in pp.probes(chapter):
        if not probe:
            continue
        for start in index.get(probe[0], [])[:400]:
            window = words[start:start + len(probe) + 6]
            hit = sum(1 for w in probe if w in window) / float(len(probe))
            best = max(best, hit)
            if best >= MIN_PROBE_HIT:
                return best
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--playlist", help="skip the search; use this playlist or "
                                       "channel URL as the series")
    ap.add_argument("--manifest", default=MANIFEST)
    ap.add_argument("--max-chapters", type=int, default=0,
                    help="try only the first N chapters, to see if it works")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show-series", action="store_true",
                    help="print the series listing and what this makes of it")
    a = ap.parse_args()

    idx = json.load(io.open(a.manifest, encoding="utf-8"))
    book = next((b for b in idx if b.get("slug") == a.slug), None)
    if not book:
        sys.exit("no such book: %s" % a.slug)
    chs = fb2_chapters("public/books/" + book["filename"])
    title = book.get("title") or ""
    surname = str(book.get("author") or "").split()[0].rstrip(",.")
    counts = [sum(len(p.split()) for p in c if isinstance(p, str)) for c in chs]
    n_want = a.max_chapters or len(chs)
    print("%s — %s, %d chapters, %s words"
          % (title, surname, len(chs), format(sum(counts), ",")))

    # ── find the series ───────────────────────────────────────────────────
    entries, source = [], a.playlist
    if a.playlist:
        entries = flat(a.playlist)
        print("series given: %d videos" % len(entries))
    else:
        seeds = []
        for q in ("%s %s глава 1" % (surname, title),
                  "%s %s аудиокнига глава 1" % (surname, title),
                  "%s %s часть 1" % (surname, title)):
            for e in ha.search(q, 20):
                t = e.get("title") or ""
                if claims_book(t, title, surname) and chapter_no(t) == 1:
                    seeds.append(e)
        seen = set()
        seeds = [e for e in seeds if not (e["id"] in seen or seen.add(e["id"]))]
        print("seed candidates for chapter 1: %d" % len(seeds))
        for e in seeds[:4]:
            j = full(e["id"])
            if not j:
                continue
            dur = j.get("duration") or 0
            rate = dur / float(max(counts[0], 1))
            ok = RATE_LO <= rate <= RATE_HI
            print("   %-12s %4dm  %.2f s/w %-10s %s"
                  % (e["id"], dur // 60, rate, "in band" if ok else "out of band",
                     (j.get("title") or "")[:46]))
            if not ok:
                continue
            pl, ch = j.get("playlist_id"), j.get("channel_id")
            url = ("https://www.youtube.com/playlist?list=" + pl) if pl else \
                  ("https://www.youtube.com/channel/%s/videos" % ch if ch else None)
            if not url:
                continue
            got = flat(url)
            if len(got) >= 2:
                entries, source = got, url
                print("   series: %s (%d videos)" % (url, len(got)))
                break

    if not entries:
        print("\nno chaptered series found.")
        return 1

    # ── map chapters onto it ──────────────────────────────────────────────
    heads = section_titles("public/books/" + book["filename"])
    plan = book_numbering(heads[1:] if len(heads) > len(chs) else heads)
    if plan:
        print("the book numbers its chapters by part: %d parts, %d chapters"
              % (len({k[0] for k in plan}), len(plan)))

    if a.show_series:
        print("\nwhat the series listing holds (first 25):")
        for e in entries[:25]:
            t = e.get("title") or ""
            pno, cno = video_numbering(t)
            print("   %-12s part %-4s ch %-4s claims=%-5s %s"
                  % (e.get("id"), pno, cno, claims_book(t, title, surname), t[:48]))

    by_idx = {}
    for e in entries:
        t = e.get("title") or ""
        if not claims_book(t, title, surname):
            continue
        pno, cno = video_numbering(t)
        if cno is None:
            continue
        if plan:
            ci = plan.get((pno or 1, cno))
        else:
            ci = cno - 1
        if ci is None or not (0 <= ci < len(chs)):
            continue
        by_idx.setdefault(ci, e)
    matched = sorted((ci, e) for ci, e in by_idx.items() if ci < n_want)
    print("\nchapters claimed by the series: %d of %d" % (len(matched), n_want))
    if not matched:
        print("the series' titles carry no chapter numbers this can read. "
              "Run again with --show-series to see what they do carry.")
        return 1

    # ── verify each against its own transcript ────────────────────────────
    placed, refused = {}, []
    for ci, e in matched:
        vid = e["id"]
        j = full(vid)
        dur = (j or {}).get("duration") or 0
        rate = dur / float(max(counts[ci], 1))
        if not (RATE_LO <= rate <= RATE_HI):
            refused.append((ci, vid, "%.2f s/w out of band" % rate))
            continue
        path = captions(vid)
        if not path:
            refused.append((ci, vid, "no transcript"))
            continue
        hit = opening_is_there(chs[ci], transcript_words(path))
        if hit < MIN_PROBE_HIT:
            refused.append((ci, vid, "opening not in the transcript (%.2f)" % hit))
            continue
        placed[str(ci)] = {"youtube": vid, "heading": "Глава %d" % (ci + 1),
                           "start": 0}
        print("   ch %-3d %-12s %4dm  %.2f s/w  opening %.2f  %s"
              % (ci + 1, vid, dur // 60, rate, hit, (e.get("title") or "")[:40]))

    frac = len(placed) / float(len(matched))
    print("\nverified %d of %d matched chapters (%.0f%%)"
          % (len(placed), len(matched), 100 * frac))
    for ci, vid, why in refused[:20]:
        print("   refused ch %-3d %-12s %s" % (ci + 1, vid, why))

    if frac < MIN_VERIFIED:
        print("\n!! too few verified — writing nothing. A series this patchy is "
              "more likely the wrong reading than a bad transcript.")
        return 1
    if a.dry_run:
        print("\n(dry run)")
        return 0
    book["videos"] = dict(book.get("videos") or {}, **placed)
    book["videoSeries"] = source
    io.open(a.manifest, "w", encoding="utf-8", newline="\n").write(
        json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
    print("\nwrote %d chapter(s) to %s" % (len(placed), a.slug))
    print("next:  python3 tools/sync_new.py 0 40")
    return 0


if __name__ == "__main__":
    sys.exit(main())
