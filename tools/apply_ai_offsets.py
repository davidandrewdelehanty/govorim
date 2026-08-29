#!/usr/bin/env python3
"""Act on the offsets the model found, and only where they can be checked.

tools/ai_align_check.py comes back with verdicts like "English rows 34-39 are
shifted 2 positions ahead: EN[34] matches RU[36]". That is a repair: the text
is right and the keys are wrong. This applies them.

    python3 tools/apply_ai_offsets.py            # what it would change
    python3 tools/apply_ai_offsets.py --apply

Two shapes turn up. Where every window of a file reports the same offset, the
whole file is shifted by it. Where they disagree — Tsvety dlya Eldzhernona
reported +3, +2, -3, -1, +8, +6 and -10 across one chapter — the file has
drifted rather than slipped, and each window's rows are moved by that window's
own offset.

NOTHING IS TAKEN ON TRUST. Every change is checked against the names measure
in tools/scan_alignment.py, which counts how often a proper noun in the Russian
turns up in the English on its own row. That measure knows nothing about what
the model said, so it is the one thing here that can contradict it — and a
model that is confidently wrong is exactly what a repair pass must survive. A
file that does not improve is left alone and named in the report.
"""
import argparse, io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import BOOKS, INDEX, chapters, score_file

HERE = os.path.dirname(os.path.abspath(__file__))
FINDINGS = os.path.join(HERE, "ai-align-findings.json")
WINDOW = 12
GAIN = 0.10
# And it has to end up somewhere near right, not merely less wrong. A repair
# that lifts a file from 6%% to 29%% has rearranged bad English into differently
# bad English, which is worse than leaving it: it costs the reader the same and
# it costs the next pass its evidence.
FLOOR = 0.55


def entries(m):
    return dict((k, v) for k, v in m.items()
                if k != "_note" and str(k).lstrip("-").isdigit())


def grade(ch, m):
    r = score_file(ch, m)
    return r.get("onrow"), r.get("placed", 0)


def remap(m, moves):
    """Move each key by the offset of the window it falls in.

    The English is in order and stays in order, so the mapping has to be
    strictly increasing. Windows overlap and disagree at their seams, and a
    naive per-range shift happily sends two keys to the same row — which is how
    the first version of this refused every file it was given. Assign in
    ascending order and never let a key land on or behind the one before it.
    """
    starts = sorted(moves, key=lambda t: t[0])
    def shift_for(i):
        sh = 0
        for lo, _hi, s in starts:
            if lo <= i:
                sh = s
            else:
                break
        return sh
    out = dict((k, v) for k, v in m.items() if k == "_note")
    prev = -1
    for k in sorted(entries(m), key=lambda x: int(x)):
        i = int(k)
        j = max(0, i + shift_for(i))
        if j <= prev:
            j = prev + 1
        out[str(j)] = m[k]
        prev = j
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--findings", default=FINDINGS)
    a = ap.parse_args()
    found = json.load(io.open(a.findings, encoding="utf-8"))

    cat = json.load(io.open(INDEX, encoding="utf-8"))
    byfolder = dict((b["parallelEn"], b) for b in cat if b.get("parallelEn"))

    per = {}
    for v in found:
        if v.get("verdict") != "OFFSET" or v.get("offset") in (None, 0):
            continue
        per.setdefault((v["dir"], v["file"]), []).append(v)

    done = held = 0
    for (d, f), vs in sorted(per.items()):
        b = byfolder.get(d)
        if not b:
            continue
        chs = chapters(os.path.join(BOOKS, b["filename"]))
        ci = int("".join(c for c in f if c.isdigit())) - 1
        if not chs or not (0 <= ci < len(chs)):
            continue
        path = os.path.join(BOOKS, d, f)
        m = json.load(io.open(path, encoding="utf-8"))
        now, placed = grade(chs[ci], m)

        offs = sorted(set(int(v["offset"]) for v in vs))
        # The model reports "row N's English belongs to row N+k", so the key
        # holding it has to move back by k.
        if len(offs) == 1:
            moves = [(0, 10 ** 9, -offs[0])]
            how = "shift the file %+d" % -offs[0]
        else:
            moves = sorted(((int(v["row"]), int(v["row"]) + WINDOW - 1,
                             -int(v["offset"])) for v in vs), key=lambda t: t[0])
            how = "%d windows, offsets %s" % (len(vs), ",".join("%+d" % o for o in offs))
        cand = remap(m, moves)
        after = grade(chs[ci], cand)[0] if cand else None

        ok = (cand is not None and after is not None and now is not None
              and after - now >= GAIN and after >= FLOOR)
        near = (cand is not None and after is not None and now is not None
                and after - now >= GAIN and after < FLOOR)
        print("  %-7s %-26s %-10s names %s -> %s  (n=%s)  %s"
              % ("fix" if (ok and a.apply) else ("would" if ok else ("closer" if near else "hold")),
                 b.get("title", "")[:26], f,
                 ("%3.0f%%" % (100 * now)) if now is not None else " n/a",
                 ("%3.0f%%" % (100 * after)) if after is not None else " n/a",
                 placed, how))
        if ok:
            done += 1
            if a.apply:
                io.open(path, "w", encoding="utf-8").write(
                    json.dumps(cand, ensure_ascii=False, indent=1) + "\n")
        else:
            held += 1

    print("\n%d file(s) %s, %d left for a person"
          % (done, "repaired" if a.apply else "would change", held))
    print("\"closer\" means the offsets helped but the file is still wrong — more\n"
          "windows may settle it, or it needs reading.")
    if done and not a.apply:
        print("nothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
