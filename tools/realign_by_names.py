#!/usr/bin/env python3
"""Put the English back on the right rows, judged by names rather than length.

tools/scan_alignment.py now reports, for each chapter file, how often a
paragraph carrying a proper noun or a number finds it in the English on its own
row. Healthy books sit at 90-100%. A file well below that is misaligned however
good its length correlation looks — and length correlation is what every repair
in this repo optimises, so it cannot be the thing that grades them.

This tries the two repairs that exist against that measure and keeps whichever
actually helps:

  shift    move every key by the offset the names say the file is out by
  re-cut   join the English back into prose and hand it out again
           (tools/reslice_parallel.py) — only where the entries actually run
           on into one another mid-sentence, which is the evidence that the
           text is continuous and merely cut in the wrong places. Where the
           entries are whole sentences the text is NOT continuous, and re-cutting
           produces different wrong English instead of the same wrong English:
           Коляска and Нос both scored better by names after a re-cut and read
           worse on the page.

    python3 tools/realign_by_names.py            # what it would change
    python3 tools/realign_by_names.py --apply
    python3 tools/realign_by_names.py --book o-lyubvi-en --apply

A repair is kept only when the names land better afterwards, by a clear
margin, and never when it would drop English or push a key off the front.
"""
import argparse, glob, io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import BOOKS, INDEX, chapters, score_file
from reslice_parallel import reslice, diced

FLOOR = 0.80        # below this a file is worth trying to repair
GAIN = 0.12         # and a repair has to beat what is there by this much
MIN_NAMES = 4       # fewer anchors than this and the measure is not evidence


def entries(m):
    return dict((k, v) for k, v in m.items()
                if k != "_note" and str(k).lstrip("-").isdigit())


def chars(m):
    return sum(len(str(v)) for v in entries(m).values())


def grade(ch, m):
    r = score_file(ch, m)
    return r.get("onrow"), r.get("placed", 0), r.get("drift"), r.get("rho")


def shifted(m, by):
    out = dict((k, v) for k, v in m.items() if k == "_note")
    for k, v in entries(m).items():
        j = int(k) + by
        if j < 0:
            return None          # would push English off the front of the chapter
        out[str(j)] = v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    cat = json.load(io.open(INDEX, encoding="utf-8"))
    books = [b for b in cat if b.get("parallelEn") and b["parallelEn"] != "bible-kjv"
             and (not a.book or b["parallelEn"] == a.book)]
    fixed = held = 0
    for b in books:
        chs = chapters(os.path.join(BOOKS, b["filename"]))
        if not chs:
            continue
        for f in sorted(glob.glob(os.path.join(BOOKS, b["parallelEn"], "[0-9]*.json"))):
            ci = int(re.match(r"(\d+)", os.path.basename(f)).group(1)) - 1
            if not (0 <= ci < len(chs)):
                continue
            m = json.load(io.open(f, encoding="utf-8"))
            if not entries(m):
                continue
            now, placed, drift, rho = grade(chs[ci], m)
            if now is None or placed < MIN_NAMES or now >= FLOOR:
                continue

            best, how, cand = now, None, None
            if drift:
                s = shifted(m, -drift)
                if s is not None:
                    v = grade(chs[ci], s)[0]
                    if v is not None and v > best:
                        best, how, cand = v, "shift %+d" % -drift, s
            rs = reslice(chs[ci], m) if diced(m) > 0.5 else None
            if rs and chars(rs) >= chars(m) * 0.98:
                v = grade(chs[ci], rs)[0]
                if v is not None and v > best:
                    best, how, cand = v, "re-cut", rs

            ok = cand is not None and best - now >= GAIN
            print("  %-8s %-24s %-22s names %3.0f%% -> %3.0f%%  (n=%d) %s"
                  % ("fix" if (ok and a.apply) else ("would" if ok else "hold"),
                     b.get("title", "")[:24], os.path.basename(f),
                     100 * now, 100 * best, placed, how or ""))
            if ok:
                fixed += 1
                if a.apply:
                    io.open(f, "w", encoding="utf-8").write(
                        json.dumps(cand, ensure_ascii=False, indent=1) + "\n")
            else:
                held += 1
    print("\n%d file(s) %s, %d left alone"
          % (fixed, "repaired" if a.apply else "would change", held))
    if fixed and not a.apply:
        print("nothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
