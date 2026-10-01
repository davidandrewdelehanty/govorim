#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Attach a recording that has no transcript behind it.

tools/place_picks.py will not place a recording it cannot check: it finds
every chapter's opening line in the transcript, in order, or it refuses. That
is the right rule, and it is why a poem by Igor Tsaryov and a daily gospel
reading were both thrown out instead of being attached to Bulgakov.

Most of what Викитека carries has no captioned reading on YouTube at all, and
for a work of one chapter there is nothing to find: the whole recording is the
whole text. So this places those — and only those — on two pieces of evidence
the hunt already gathered, the title and the length, and marks what it wrote:

    "videoUnchecked": true

Nothing in the reader looks at that field. It is there so these can be told
apart later from the recordings the transcript vouched for — to audit, to
re-check when captions appear, or to pull them all back out in one pass.

A work in several chapters is refused. Splitting a recording by word count is
a guess, and a guess that puts chapter three on chapter five reads as a fault
in the site rather than as an approximation.

    python3 tools/place_uncaptioned.py --dry-run
    python3 tools/place_uncaptioned.py
"""
import argparse
import io
import json
import os
import sys

sys.path.insert(0, "tools")
from scan_alignment import chapters as fb2_chapters

MANIFEST = "private/books/index.json"
HUNT = "tools/hunt-results.json"
VTT = "tools/vtt/%s.ru.vtt"

# Without a transcript the only evidence is the title, and a title alone is
# worth less than it looks. «Айя-София», «Чёрный камень Каабы» and «Могила
# поэта» all name a place or an object, so a Quran recitation, a news clip and
# a video about Mayakovsky's grave each match the poem's title word for word
# and are not the poem. The uploader's name for the recording is what tells
# them apart: someone reading Bunin says so.
#
# So: the author's surname in the video title, or — for a reading titled with
# nothing but the work («Гроза промчалась.») — near-exact wording and almost
# no words of its own. Anything that matches the title while talking about
# something else fails both.
import re as _re

TITLE_FLOOR = 0.8        # when the surname is absent
MAX_EXTRA = 2            # words of its own a bare title may carry

def _words(s):
    return [w for w in _re.split(r"[^\w\u0400-\u04ff]+", (s or "").lower()) if w]

def surname(author):
    a = (author or "").strip()
    return a.split()[0].rstrip(",.").lower() if a else ""

def title_ok(book_title, video_title, author):
    bt, vt = _words(book_title), _words(video_title)
    if not bt:
        return False, "no title to check"
    have = sum(1 for w in bt if w in vt)
    ratio = have / float(len(bt))
    sn = surname(author)
    if sn and sn in (video_title or "").lower():
        return (ratio >= 0.5,
                "the author is named, %d/%d title words" % (have, len(bt)))
    extra = len([w for w in vt if w not in bt])
    if ratio >= TITLE_FLOOR and extra <= MAX_EXTRA:
        return True, "titled with the work and nothing else"
    return False, ("the author is not named and the title carries %d other "
                   "word(s) (%d/%d matched)" % (extra, have, len(bt)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=MANIFEST)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="also replace a videos map that is already there")
    a = ap.parse_args()

    results = json.load(io.open(HUNT, encoding="utf-8"))
    idx = json.load(io.open(a.manifest, encoding="utf-8"))
    books = idx["books"] if isinstance(idx, dict) and "books" in idx else idx
    by_file = {b.get("filename"): b for b in books}

    placed = refused = skipped = 0
    why = {}
    for r in results:
        pick = r.get("pick")
        if not pick:
            continue
        b = by_file.get(r.get("file"))
        if not b:
            continue
        if b.get("videos") and not a.force:
            skipped += 1
            continue
        vid = pick["id"]
        if os.path.exists(VTT % vid):
            skipped += 1          # it has a transcript: place_picks.py's job
            continue
        try:
            n = len(fb2_chapters("public/books/" + b["filename"]))
        except Exception as e:
            why.setdefault("unreadable", []).append(b.get("slug"))
            refused += 1
            continue
        if n != 1:
            why.setdefault("several chapters, nothing to place them by", []).append(
                "%s (%d)" % (b.get("slug"), n))
            refused += 1
            continue
        ok, note = title_ok(b.get("title"), pick.get("title"), b.get("author"))
        if not ok:
            why.setdefault("the title does not vouch for the recording", []).append(
                "%s — %s" % (b.get("slug"), note))
            refused += 1
            continue
        print("%-38s %-12s %4dm  %.2f s/w  %-34s  %s"
              % (b.get("slug"), vid, pick["dur"] // 60,
                 pick["dur"] / max(b.get("words") or 1, 1),
                 pick["title"][:34], note))
        if not a.dry_run:
            b["videos"] = {"0": {"youtube": vid, "heading": "Глава 1"}}
            b["videoUnchecked"] = True
        placed += 1

    if not a.dry_run and placed:
        io.open(a.manifest, "w", encoding="utf-8").write(
            json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
    print("\nplaced %d%s, refused %d, left alone %d"
          % (placed, " (dry run)" if a.dry_run else "", refused, skipped))
    for reason, who in why.items():
        print("\nrefused — %s (%d):" % (reason, len(who)))
        print("   " + ", ".join(who[:40]) + (" …" if len(who) > 40 else ""))


if __name__ == "__main__":
    main()
