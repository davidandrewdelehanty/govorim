#!/usr/bin/env python3
"""Decide which books should stop pretending their rows line up.

Some translations cannot be paired row by row. Garnett gives Мёртвые души 70
paragraphs where the Russian has 112; a translator who folds three paragraphs
into one is not making a mistake. Pinning that to rows produces confident
nonsense, and the wrong English beside a paragraph reads as a translation of
it — worse than no English at all.

So a book that does not clear the bar gets flowEn in the catalogue, and the
reader runs the two texts as separate columns, each at its own length.

The score is the median, over a book's files, of how often a proper noun in
the Russian turns up in the English on its own row. Files with fewer than six
names to judge by are not counted, and a book with nothing judgeable is left
alone rather than guessed at.

    python3 tools/set_flow_mode.py --at 0.90
    python3 tools/set_flow_mode.py --at 0.90 --apply
"""
import argparse, glob, io, json, os, re, statistics, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import BOOKS, INDEX, chapters, score_file

MIN_NAMES = 6
# Verse is left paired, whatever the score. Its English is written one cell per
# STANZA and keyed to the stanza's first line, so the row locking is the point
# and it works: Onegin scores 69% on names only because the same three names
# recur in every stanza, and the shape measure says all eight cantos sit
# exactly where they should. Flowing a poem would also throw away the line-by-
# line work just done on the four Pushkin poems.
VERSE = "Poetry"
# And a book whose English is deliberately sparse - far fewer entries than the
# Russian has paragraphs - is using the reader's spanning cell on purpose.
MIN_DENSITY = 0.5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", type=float, default=0.90, help="the bar, 0..1")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    cat = json.load(io.open(INDEX, encoding="utf-8"))
    print("%-32s %6s %6s  %s" % ("folder", "score", "files", "title"))
    on = off = quiet = 0
    for b in cat:
        d = b.get("parallelEn")
        if not d or d == "bible-kjv":
            continue
        p = os.path.join(BOOKS, b["filename"])
        if not os.path.exists(p):
            continue
        chs = chapters(p)
        if not chs:
            continue
        if str(b.get("category", "")) == VERSE:
            b.pop("flowEn", None)
            continue
        sc, keys, paras = [], 0, 0
        for f in sorted(glob.glob(os.path.join(BOOKS, d, "[0-9]*.json"))):
            n = int(re.match(r"(\d+)", os.path.basename(f)).group(1))
            if not (1 <= n <= len(chs)):
                continue
            m = json.load(io.open(f, encoding="utf-8"))
            if not [k for k in m if k != "_note" and str(k).lstrip("-").isdigit()]:
                continue
            keys += len([k for k in m if k != "_note" and str(k).lstrip("-").isdigit()])
            paras += len(chs[n - 1])
            r = score_file(chs[n - 1], m)
            if r.get("onrow") is not None and r.get("placed", 0) >= MIN_NAMES:
                sc.append(r["onrow"])
        if not sc:
            # Nothing to judge by. Leaving a working alignment alone beats
            # taking it apart on no evidence.
            quiet += 1
            b.pop("flowEn", None)
            continue
        med = statistics.median(sc)
        dense = (keys / float(paras)) if paras else 1.0
        if med < a.at and dense >= MIN_DENSITY:
            b["flowEn"] = True
            on += 1
            print("%-32s %5.0f%% %6d  %s" % (d, 100 * med, len(sc), b.get("title", "")))
        else:
            b.pop("flowEn", None)
            off += 1
    print()
    print("%d book(s) flow, %d stay paired, %d had nothing to judge by"
          % (on, off, quiet))
    if a.apply:
        with io.open(INDEX, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(cat, ensure_ascii=False, indent=2) + "\n")
        print("catalogue written")
    else:
        print("nothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
