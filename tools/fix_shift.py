#!/usr/bin/env python3
"""Find whole-file key shifts by search, and let the names measure decide.

Anna Karenina's first chapter is the shape this exists for. The English file
opens with the novel's epigraph — "Vengeance is mine; I will repay" — which the
Russian FB2 does not carry as a paragraph. So English row 0 is the epigraph,
row 1 is "Happy families are all alike", and every row in the file sits one
below the Russian it belongs to. Fifteen Russian paragraphs, sixteen English
rows, and the last one is unreachable.

Nothing here asks a model. It tries every constant shift in a small range and
keeps the one the names measure likes best — does a proper noun in the Russian
turn up in the English on its own row — which is a measure the shift cannot
flatter, because moving keys around cannot invent a name.

A shift is only kept when it clears BOTH bars: the names score has to rise by
GAIN, and it has to end up above FLOOR. A file that goes from 6% to 29% has
rearranged bad English into differently bad English.

    python3 tools/fix_shift.py                 # what it would change
    python3 tools/fix_shift.py --apply
    python3 tools/fix_shift.py --book anna-karenina-en --file 01.json
"""
import argparse, glob, io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import BOOKS, INDEX, chapters, score_file

RANGE = 5
GAIN = 0.10
FLOOR = 0.55
MIN_NAMES = 6


def entries(m):
    return dict((int(k), v) for k, v in m.items()
                if k != "_note" and str(k).lstrip("-").isdigit())


def shifted(m, k, n_paras):
    """Move every key by k. Keys that fall off either end are dropped."""
    ent = entries(m)
    out = {}
    for i in sorted(ent):
        j = i + k
        if 0 <= j < n_paras:
            out[str(j)] = ent[i]
    if "_note" in m:
        out["_note"] = m["_note"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default="")
    ap.add_argument("--file", default="")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--all", action="store_true",
                    help="test every file, not only the ones already failing")
    a = ap.parse_args()

    cat = json.load(io.open(INDEX, encoding="utf-8"))
    print("%-26s %-10s %6s %6s  %s" % ("work", "file", "before", "after", "verdict"))
    fixed = held = 0
    for b in cat:
        d = b.get("parallelEn")
        if not d or d == "bible-kjv" or (a.book and d != a.book):
            continue
        p = os.path.join(BOOKS, b["filename"])
        if not os.path.exists(p):
            continue
        chs = chapters(p)
        if not chs:
            continue
        for f in sorted(glob.glob(os.path.join(BOOKS, d, "[0-9]*.json"))):
            base = os.path.basename(f)
            if a.file and base != a.file:
                continue
            n = int(re.match(r"(\d+)", base).group(1))
            if not (1 <= n <= len(chs)):
                continue
            m = json.load(io.open(f, encoding="utf-8"))
            if not entries(m):
                continue
            ch = chs[n - 1]
            r0 = score_file(ch, m)
            before, placed = r0.get("onrow"), r0.get("placed", 0)
            if before is None or placed < MIN_NAMES:
                continue
            if not a.all and before >= FLOOR:
                continue
            best, best_k = before, 0
            for k in range(-RANGE, RANGE + 1):
                if k == 0:
                    continue
                cand = shifted(m, k, len(ch))
                if not cand:
                    continue
                r = score_file(ch, cand)
                on = r.get("onrow")
                if on is not None and on > best:
                    best, best_k = on, k
            if best_k == 0:
                continue
            ok = (best - before >= GAIN) and best >= FLOOR
            print("%-26s %-10s %5.0f%% %5.0f%%  %s (shift %+d)"
                  % (b.get("title", "")[:26], base, 100 * before, 100 * best,
                     "fix" if ok else "hold", best_k))
            if ok:
                fixed += 1
                if a.apply:
                    out = shifted(m, best_k, len(ch))
                    io.open(f, "w", encoding="utf-8").write(
                        json.dumps(out, ensure_ascii=False, indent=1) + "\n")
            else:
                held += 1
    print()
    print("%d file(s) %s, %d left alone"
          % (fixed, "repaired" if a.apply else "would change", held))
    if fixed and not a.apply:
        print("nothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
