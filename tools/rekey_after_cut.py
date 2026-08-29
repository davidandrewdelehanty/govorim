#!/usr/bin/env python3
"""Put the English back on the right paragraphs after front matter was cut.

The English files were keyed against the Russian as it was — apparatus and
all. Cutting the apparatus moves every paragraph in the first chapter, and
dropping a whole opening section moves every chapter, so the keys have to be
re-made rather than nudged.

Nudging is what fails here, and it fails quietly. A constant shift looks right
by length correlation while sitting two paragraphs out, and a negative shift
silently drops the entries that fall off the front. So the entries are handed
back out the way tools/reslice_parallel.py does it — by how long each Russian
paragraph is, anchored on shared numbers and foreign words — and nothing is
written unless the result scores better AND still holds all the English it
started with.

    python3 tools/rekey_after_cut.py            # what it would change
    python3 tools/rekey_after_cut.py --apply
"""
import glob, io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import BOOKS, chapters, score_file
from reslice_parallel import reslice

PLAN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "front_matter.json")
GAIN = 0.15


def entries(m):
    return dict((k, v) for k, v in m.items()
                if k != "_note" and str(k).lstrip("-").isdigit())


def chars(m):
    return sum(len(str(v)) for v in entries(m).values())


def rho(ch, m):
    return score_file(ch, m).get("rho")


def main():
    apply = "--apply" in sys.argv
    plan = json.load(io.open(PLAN, encoding="utf-8"))
    changed = held = 0
    for fn in sorted(plan, key=lambda k: plan[k]["title"]):
        v = plan[fn]
        d = v.get("parallelEn")
        if not d:
            continue
        folder = os.path.join(BOOKS, d)
        chs = chapters(os.path.join(BOOKS, fn))
        if not chs:
            continue
        title = v["title"][:26]

        # A dropped section takes a chapter with it, so every file after the
        # first slides down one. Whatever English the first file held belongs
        # to the chapter the second one covers, so it is carried over, not lost.
        # _merged-01.json is the receipt that this folder has already slid down.
        # Renumbering twice would throw a real chapter away.
        already = os.path.exists(os.path.join(folder, "_merged-01.json"))
        if v["cut"] == "section" and apply and not already:
            nums = sorted(int(re.match(r"(\d+)", os.path.basename(f)).group(1))
                          for f in glob.glob(os.path.join(folder, "[0-9]*.json")))
            if nums and nums[0] == 1:
                first = json.load(io.open(os.path.join(folder, "01.json"), encoding="utf-8"))
                second_p = os.path.join(folder, "%02d.json" % nums[1]) if len(nums) > 1 else None
                if second_p and entries(first):
                    second = json.load(io.open(second_p, encoding="utf-8"))
                    merged = dict(second)
                    for k, val in sorted(entries(first).items(), key=lambda kv: int(kv[0])):
                        while k in merged:
                            k = str(int(k) + 1)
                        merged[k] = val
                    io.open(second_p, "w", encoding="utf-8").write(
                        json.dumps(merged, ensure_ascii=False, indent=1) + "\n")
                os.rename(os.path.join(folder, "01.json"),
                          os.path.join(folder, "_merged-01.json"))
                for num in nums[1:]:
                    os.rename(os.path.join(folder, "%02d.json" % num),
                              os.path.join(folder, "%02d.json" % (num - 1)))
                print("  renumber %-26s dropped chapter, files slid down one" % title)

        for f in sorted(glob.glob(os.path.join(folder, "[0-9]*.json"))):
            ci = int(re.match(r"(\d+)", os.path.basename(f)).group(1)) - 1
            if not (0 <= ci < len(chs)):
                continue
            if v["cut"] != "section" and ci != 0:
                continue          # a paragraph cut only moves the first chapter
            m = json.load(io.open(f, encoding="utf-8"))
            if not entries(m):
                continue
            before = rho(chs[ci], m)
            new = reslice(chs[ci], m)
            if not new:
                continue
            after = rho(chs[ci], new)
            kept = chars(new) >= chars(m) * 0.98
            good = (after is not None and (before is None or after - before >= GAIN) and kept)
            print("  %-8s %-26s %-9s %5s -> %5s%s"
                  % ("re-key" if (good and apply) else ("would" if good else "hold"),
                     title, os.path.basename(f),
                     ("%.2f" % before) if before is not None else "n/a",
                     ("%.2f" % after) if after is not None else "n/a",
                     "" if kept else "   REFUSED: would lose English"))
            if good:
                changed += 1
                if apply:
                    io.open(f, "w", encoding="utf-8").write(
                        json.dumps(new, ensure_ascii=False, indent=1) + "\n")
            else:
                held += 1
    print("\n%d file(s) %s, %d left alone" % (changed, "re-keyed" if apply else "would change", held))
    if not apply:
        print("nothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
