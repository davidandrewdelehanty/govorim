#!/usr/bin/env python3
"""Check that the English files and the Russian chapters agree about counting.

Everything else in this repo assumes that NN.json holds the English for chapter
NN-1. Nothing enforces it. When that assumption quietly breaks — a chapter
added to an FB2, a front-matter section stripped, a folder renumbered by hand,
a file that never got written — the reader shows the wrong translation and
looks completely normal doing it.

    python3 tools/check_pairing.py            # every paired work
    python3 tools/check_pairing.py --book yama-en

ONE THING IT MUST NOT DO is confuse a broken pairing with a disagreement about
what a chapter is. This file has its own FB2 reader and it does not always
carve a book the same way the app does: it splits Onegin into its 383 stanzas
where the app has 8 cantos, and Voyna i mir into 1,389 marked sections where
the English has 361 chapters. Every file in those folders then looks wrong,
and none of them is. So a fault that affects a WHOLE folder uniformly is
reported as SPLIT — the two sides count chapters differently, go and look —
while the same fault in a few files of an otherwise healthy folder is reported
as the fault it is.

It reports these kinds of disagreement, hardest first:

  ORPHAN    a file numbered past the last chapter. Its English is unreachable
            and something else is almost certainly shifted.
  GAP       a hole in the numbering: 01, 02, 04. Either a file is missing or
            everything after the hole is off by one.
  OVERRUN   keys pointing at paragraphs the chapter does not have. The file
            belongs to a longer chapter than the one it is sitting on.
  EMPTY     a file with no entries at all.
  SHORT     fewer files than chapters, by a little. Often deliberate — a
            translation covering part of a work — so it is never fatal.
  SPLIT     the two sides do not agree on what a chapter is: every file
            overruns, or there are several times more chapters than files.
            Usually this reader's fault, not the data's. Never fatal.

Exit status is 1 if anything in the first four turned up, so it can sit in
front of a build.
"""
import argparse, glob, io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import BOOKS, INDEX, chapters


def entries(m):
    return [int(k) for k in m
            if k != "_note" and str(k).lstrip("-").isdigit()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", help="one parallelEn folder")
    ap.add_argument("--quiet", action="store_true", help="only report problems")
    a = ap.parse_args()

    cat = json.load(io.open(INDEX, encoding="utf-8"))
    works = [b for b in cat if b.get("parallelEn")
             and (not a.book or b["parallelEn"] == a.book)]

    hard = []
    soft = []
    checked = 0
    for b in works:
        d = b["parallelEn"]
        title = b.get("title", "")
        folder = os.path.join(BOOKS, d)
        fb2 = os.path.join(BOOKS, b["filename"])
        if not os.path.exists(fb2):
            hard.append((title, d, "MISSING", "the FB2 itself is not there: %s" % b["filename"]))
            continue
        chs = chapters(fb2)
        if not chs:
            hard.append((title, d, "MISSING", "the FB2 would not parse"))
            continue
        files = sorted(glob.glob(os.path.join(folder, "[0-9]*.json")))
        nums = sorted(int(re.match(r"(\d+)", os.path.basename(f)).group(1)) for f in files)
        if not nums:
            continue
        checked += 1

        # Gather the per-file faults first, then decide whether they are a
        # fault or a difference of opinion about chapters.
        overruns = []
        over = [n for n in nums if n > len(chs)]
        if over:
            hard.append((title, d, "ORPHAN",
                         "%d chapters but file(s) numbered %s — %d file(s) point past the end"
                         % (len(chs), ", ".join(str(n) for n in over[:5]), len(over))))
        missing = [n for n in range(nums[0], nums[-1] + 1) if n not in nums]
        if missing:
            hard.append((title, d, "GAP",
                         "numbering runs %d-%d with %d missing: %s"
                         % (nums[0], nums[-1], len(missing),
                            ", ".join(str(n) for n in missing[:8]))))
        for f in files:
            n = int(re.match(r"(\d+)", os.path.basename(f)).group(1))
            if n > len(chs):
                continue
            try:
                m = json.load(io.open(f, encoding="utf-8"))
            except Exception as e:
                hard.append((title, d, "UNREADABLE", "%s: %s" % (os.path.basename(f), e)))
                continue
            ks = entries(m)
            if not ks:
                hard.append((title, d, "EMPTY", "%s has no entries" % os.path.basename(f)))
                continue
            beyond = [k for k in ks if k >= len(chs[n - 1])]
            # One or two stragglers are a ragged tail; a fifth of the file
            # pointing off the end means it is on the wrong chapter.
            if len(beyond) > max(2, 0.2 * len(ks)):
                overruns.append((os.path.basename(f), len(beyond), len(ks), n, len(chs[n - 1])))

        inrange = [n for n in nums if n <= len(chs)]
        wholesale = inrange and len(overruns) >= max(2, 0.8 * len(inrange))
        lopsided = len(chs) >= max(3 * len(nums), len(nums) + 6)
        if wholesale or lopsided:
            soft.append((title, d, "SPLIT",
                         "%d chapters here against %d file(s)%s — the two sides are not "
                         "counting chapters the same way"
                         % (len(chs), len(nums),
                            ", every file overruns" if wholesale else "")))
        else:
            for name, nb, nk, n, npar in overruns:
                hard.append((title, d, "OVERRUN",
                             "%s: %d of %d keys point past chapter %d, which has %d paragraphs"
                             % (name, nb, nk, n, npar)))
            if len(nums) < len(chs):
                soft.append((title, d, "SHORT",
                             "%d chapters, %d file(s) — chapters %s have no English"
                             % (len(chs), len(nums),
                                ", ".join(str(n) for n in
                                          [x for x in range(1, len(chs) + 1)
                                           if x not in nums][:6]))))

    for title, d, kind, msg in hard:
        print("  %-9s %-26s %-24s %s" % (kind, title[:26], d[:24], msg))
    if soft and not a.quiet:
        if hard:
            print()
        for title, d, kind, msg in soft:
            print("  %-9s %-26s %-24s %s" % (kind, title[:26], d[:24], msg))

    print("\n%d paired work(s) checked: %d fault(s), %d to look at"
          % (checked, len(hard), len(soft)))
    if not hard:
        print("every English folder is numbered to match its book.")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
