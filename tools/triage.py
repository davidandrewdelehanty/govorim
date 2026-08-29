#!/usr/bin/env python3
"""Sort every paired file into what is actually wrong with it.

The model's OFFSET verdicts turned out to be mostly imagination: of 223 files
it called shifted, moving them the way it asked made 174 WORSE by the names
measure, and 142 of them already scored 80% or better. A twelve-row window of
loose literary translation reads as "shifted by one" to any reader, human or
machine, because a literary translation genuinely does not answer the Russian
one line at a time. So the model is not the screen. It is only good at the
question it got right every time: is this the same work at all.

Two mechanical measures do the screening instead, and neither knows what the
model said:

  names   how often a proper noun in the Russian lands in the English on its
          own row (scan_alignment.score_file). Low means misaligned.
  length  English words against Russian words. English runs about 1.05x the
          Russian across this library. Well under that means the translation
          is abridged or truncated, and no amount of re-slicing invents the
          missing text.

    python3 tools/triage.py            # the whole library, worst first
    python3 tools/triage.py --bad      # only what needs a decision
"""
import argparse, glob, io, json, os, re, statistics, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import BOOKS, INDEX, chapters, score_file

NAMES_FLOOR = 0.55      # below this the file is not aligned
SHORT_RATIO = 0.72      # below this the English is missing text


def words(s):
    return len(re.findall(r"\S+", s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bad", action="store_true", help="only files needing a decision")
    ap.add_argument("--book", default="")
    a = ap.parse_args()

    cat = json.load(io.open(INDEX, encoding="utf-8"))
    per_book = {}
    for b in cat:
        d = b.get("parallelEn")
        if not d or d == "bible-kjv":
            continue
        if a.book and d != a.book:
            continue
        p = os.path.join(BOOKS, b["filename"])
        if not os.path.exists(p):
            continue
        chs = chapters(p)
        if not chs:
            continue
        rows, empties, ruw, enw = [], [], 0, 0
        for f in sorted(glob.glob(os.path.join(BOOKS, d, "[0-9]*.json"))):
            n = int(re.match(r"(\d+)", os.path.basename(f)).group(1))
            if not (1 <= n <= len(chs)):
                continue
            m = json.load(io.open(f, encoding="utf-8"))
            ent = dict((k, v) for k, v in m.items()
                       if k != "_note" and str(k).lstrip("-").isdigit())
            if not ent:
                empties.append(os.path.basename(f))
                continue
            r = score_file(chs[n - 1], m)
            rw = sum(words(x) for x in chs[n - 1])
            ew = sum(words(str(v)) for v in ent.values())
            ruw += rw
            enw += ew
            rows.append((os.path.basename(f), r.get("onrow"), r.get("placed", 0),
                         (ew / rw) if rw else 0.0))
        if not rows:
            continue
        scored = [r[1] for r in rows if r[1] is not None]
        per_book[d] = {
            "title": b.get("title", ""),
            "files": len(rows) + len(empties),
            "chapters": len(chs),
            "empty": len(empties),
            "names": statistics.median(scored) if scored else 0.0,
            "ratio": (enw / ruw) if ruw else 0.0,
            "covered": (len(rows) + len(empties)) / len(chs) if chs else 0.0,
            "placed": sum(r[2] for r in rows),
            "rows": rows,
        }

    def verdict(v):
        if v["empty"] and v["empty"] == v["files"]:
            return "NO ENGLISH"
        if v["ratio"] and v["ratio"] < SHORT_RATIO:
            return "ABRIDGED"
        if v["covered"] < 0.9:
            return "PARTIAL BOOK"
        if v["names"] < NAMES_FLOOR:
            # A score computed from three proper nouns is not evidence. Short
            # verse carries almost none, and every one of these came back 0%.
            return "MISALIGNED" if v["placed"] >= 8 else "NO EVIDENCE"
        if v["empty"]:
            return "EMPTY FILES"
        return "ok"

    out = sorted(per_book.items(), key=lambda kv: (kv[1]["names"], kv[1]["ratio"]))
    print("%-30s %-12s %6s %5s %6s %6s %5s  %s"
          % ("folder", "verdict", "names", "n", "len", "cover", "empty", "title"))
    shown = 0
    for d, v in out:
        w = verdict(v)
        if a.bad and w == "ok":
            continue
        shown += 1
        print("%-30s %-12s %5.0f%% %5d %5.2fx %5.0f%% %5d  %s"
              % (d, w, 100 * v["names"], v["placed"], v["ratio"],
                 100 * v["covered"], v["empty"], v["title"]))
    bad = [v for v in per_book.values() if verdict(v) != "ok"]
    print("\n%d paired work(s): %d need a decision" % (len(per_book), len(bad)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
