#!/usr/bin/env python3
"""Control test for the Synodal/King James verse aligner.

The aligner in build_synodal.py has to pair verses in 41 chapters where the
two sources disagree about how many there are. There is no answer key for
those. There is a near-enough one for the other 235: where the counts agree,
the pairing is almost always the identity one, and an aligner that cannot
return a known answer has no business guessing an unknown one.

    python3 tools/check_bible_align.py

Prints the rate and names every chapter where the aligner departs from the
identity pairing. A departure is not automatically a bug — Mark 7 has equal
counts and genuinely misaligned verses (the English source drops one at 7:11
and regains one at 7:33) and the aligner is right to say so. Read any new
name on this list before trusting or blaming it.
"""
import io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_synodal import BOOKS, SRC, align, clean_ru, clean_en


def main():
    ru = json.load(io.open(os.path.join(SRC, "ru_synodal.json"), encoding="utf-8-sig"))
    en = json.load(io.open(os.path.join(SRC, "en_kjv.json"), encoding="utf-8-sig"))

    exact = tot = 0
    misses = []
    for idx, name, ename in BOOKS:
        for ci, rch in enumerate(ru[idx]["chapters"]):
            R = [clean_ru(x) for x in rch]
            E = [clean_en(x) for x in en[idx]["chapters"][ci]]
            if len(R) != len(E):
                continue
            tot += 1
            a = align(R, E)
            if all(s == 1 and t == 1 for (_, s, _, t) in a):
                exact += 1
            else:
                misses.append("%s %d (%d verses)" % (ename, ci + 1, len(R)))

    print("control: %d of %d equal-count chapters pair one-to-one (%.2f%%)"
          % (exact, tot, 100.0 * exact / tot))
    for m in misses:
        print("   departs from positional:", m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
