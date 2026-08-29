#!/usr/bin/env python3
"""Move the English back into step after front matter was cut from the Russian.

Removing the digitiser's apparatus from an FB2 shortens the book, and the
English files were numbered against the version that still had it. Cutting five
paragraphs off the first chapter leaves every English entry in that chapter
pointing five paragraphs too far down; dropping a whole opening section leaves
every English FILE numbered one chapter too high.

Both are exactly undone by the shift the cut implies, which is what this does:

    python3 tools/repair_after_cut.py            # what it would change
    python3 tools/repair_after_cut.py --apply

and each book is only changed when the shift actually scores better, by the
same correlation the scanner uses. The orphaned first file of a renumbered
folder is kept as _superseded-NN.json rather than deleted.
"""
import glob, io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import BOOKS, chapters, score_file, median

PLAN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "front_matter.json")
GAIN = 0.20


def load(f):
    try:
        return json.load(io.open(f, encoding="utf-8"))
    except Exception:
        return None


def score(chs, files, fshift, pshift):
    rr = []
    for f in files:
        ci = int(re.match(r"(\d+)", os.path.basename(f)).group(1)) - 1 + fshift
        if not (0 <= ci < len(chs)):
            continue
        m = load(f)
        if not m:
            continue
        sh = pshift if ci == 0 else 0
        mm = dict((str(int(k) + sh), v) for k, v in m.items()
                  if k != "_note" and str(k).lstrip("-").isdigit())
        r = score_file(chs[ci], mm)
        if r.get("rho") is not None:
            rr.append(r["rho"])
    return (median(rr), len(rr)) if rr else (None, 0)


def main():
    apply = "--apply" in sys.argv
    plan = json.load(io.open(PLAN, encoding="utf-8"))
    done = held = 0
    for fn in sorted(plan, key=lambda k: plan[k]["title"]):
        v = plan[fn]
        d = v.get("parallelEn")
        if not d:
            continue
        chs = chapters(os.path.join(BOOKS, fn))
        files = sorted(glob.glob(os.path.join(BOOKS, d, "[0-9]*.json")))
        if not chs or not files:
            continue
        n = 1 if v["cut"] == "section" else len(v["cut"])
        now, _ = score(chs, files, 0, 0)
        if v["cut"] == "section":
            cand, fs, ps = score(chs, files, -1, 0), -1, 0
        else:
            cand, fs, ps = score(chs, files, 0, -n), 0, -n
        best = cand[0]
        # A book can be unscoreable as it stands — every pair too short to
        # measure once the English is pointing at the wrong paragraphs. A
        # candidate that scores well is still the answer there.
        unscoreable = now is None and best is not None and best >= 0.6
        if best is None or (not unscoreable and (now is None or best - now < GAIN)):
            print("  hold     %-26s %s -> %s" % (v["title"][:26],
                  ("%.2f" % now) if now is not None else "--",
                  ("%.2f" % best) if best is not None else "--"))
            held += 1
            continue
        print("  %-8s %-26s %5s -> %.2f  (%s)"
              % ("shift" if apply else "would", v["title"][:26],
                 ("%.2f" % now) if now is not None else "n/a", best,
                 "renumber files -1" if fs else "keys %+d" % ps))
        done += 1
        if not apply:
            continue
        if ps:
            f0 = os.path.join(BOOKS, d, "01.json")
            m = load(f0)
            if m:
                out = dict((k, val) for k, val in m.items() if k == "_note")
                for k, val in m.items():
                    if k == "_note" or not str(k).lstrip("-").isdigit():
                        continue
                    j = int(k) + ps
                    if j >= 0:
                        out[str(j)] = val
                io.open(f0, "w", encoding="utf-8").write(
                    json.dumps(out, ensure_ascii=False, indent=1) + "\n")
        else:
            nums = sorted(int(re.match(r"(\d+)", os.path.basename(f)).group(1))
                          for f in files)
            first = os.path.join(BOOKS, d, "%02d.json" % nums[0])
            os.rename(first, os.path.join(BOOKS, d, "_superseded-%02d.json" % nums[0]))
            for num in nums[1:]:
                os.rename(os.path.join(BOOKS, d, "%02d.json" % num),
                          os.path.join(BOOKS, d, "%02d.json" % (num - 1)))
    print("\n%d book(s) %s, %d left alone" % (done, "shifted" if apply else "would shift", held))
    if not apply:
        print("nothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
