#!/usr/bin/env python3
"""Re-pair a verse translation line by line, by dynamic programming.

A shift cannot fix verse. Medny vsadnik's English sits one line late at the
top and, by line 96, "Fair city of the hero, hail!" is beside "Об ней свежо
воспоминанье" — many lines from «Красуйся, град Петров». The two sides do not
drift by a constant, because a verse translator does not keep one line per
line: he spends two English lines on one Russian, or folds two Russian lines
into one, and every one of those decisions moves everything after it.

So this does what the Synodal aligner does for verses, for lines. It finds the
cheapest monotonic path through the two line lists, with four moves:

    1:1   the ordinary case
    1:2   one Russian line answered by two English ones
    2:1   two Russian lines folded into one English line
    1:0   a Russian line the translation simply does not render

Cost is the log ratio of lengths against the poem's own average expansion,
which is what makes it scale-free, pulled about by three anchors that cross
the language barrier: numerals, proper nouns, and the SHAPE of the line — a
question stays a question, a line of dialogue keeps its dash. Merges and skips
are priced so the path does not invent offsetting pairs of them where 1:1
already fits.

NOTHING IS WRITTEN ON TRUST. The result is graded by the same two measures
that judge everything else here — shape agreement (tools/shape_check.py) and
names on their own row (scan_alignment) — and a file that does not improve is
left exactly as it was. Neither measure is what the DP optimises, so both can
contradict it.

    python3 tools/align_verse.py --book pushkin-medny-vsadnik-en
    python3 tools/align_verse.py --book pushkin-medny-vsadnik-en --apply
"""
import argparse, glob, io, json, math, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import (BOOKS, INDEX, chapters, score_file, chapter_marker,
                            ru_stems, en_stems)
import shape_check as SHAPE

DIGITS = re.compile(r"\d+")

# A merge or a skip has to earn its place. The line counts force how many there
# must be; these only stop the path inventing offsetting pairs of them where
# one-to-one already fits.
MERGE_PENALTY = 0.55
SKIP_PENALTY = 0.85

# How much an anchor is allowed to move the decision. A shared proper noun is
# strong evidence and a matching line-shape is weak evidence, and they are
# priced accordingly - shape alone must never outvote length.
NAME_BONUS = 0.60
DIGIT_BONUS = 0.45
SHAPE_WEIGHT = 0.30

MIN_GAIN = 0.02


def digits(s):
    return tuple(sorted(DIGITS.findall(s)))


def align(R, E):
    """Monotonic line alignment. Returns [(ri, rspan, ei, espan), ...]."""
    n, m = len(R), len(E)
    rl = [max(len(x), 1) for x in R]
    el = [max(len(x), 1) for x in E]
    rd = [digits(x) for x in R]
    ed = [digits(x) for x in E]
    rs = [ru_stems(x) for x in R]
    es = [en_stems(x) for x in E]
    k = sum(el) / float(sum(rl)) if sum(rl) else 1.0

    def anchors(ri_lo, ri_hi, ei_lo, ei_hi):
        rdg = tuple(sorted(sum((list(rd[i]) for i in range(ri_lo, ri_hi)), [])))
        edg = tuple(sorted(sum((list(ed[j]) for j in range(ei_lo, ei_hi)), [])))
        b = 0.0
        if rdg and edg:
            b -= DIGIT_BONUS if rdg == edg else -0.20
        rn = set().union(*[rs[i] for i in range(ri_lo, ri_hi)]) if ri_hi > ri_lo else set()
        en_ = set().union(*[es[j] for j in range(ei_lo, ei_hi)]) if ei_hi > ei_lo else set()
        if rn and en_:
            b -= NAME_BONUS * min(len(rn & en_), 2) / 2.0
        return b

    def cost(ri_lo, ri_hi, ei_lo, ei_hi):
        a = sum(rl[i] for i in range(ri_lo, ri_hi))
        b = sum(el[j] for j in range(ei_lo, ei_hi))
        c = abs(math.log(max(b, 1) / (max(a, 1) * k)))
        c += anchors(ri_lo, ri_hi, ei_lo, ei_hi)
        ru = " ".join(R[ri_lo:ri_hi])
        en = " ".join(E[ei_lo:ei_hi])
        c += SHAPE_WEIGHT * (1.0 - SHAPE.agree(ru, en))
        return c

    INF = float("inf")
    d = [[INF] * (m + 1) for _ in range(n + 1)]
    bk = [[None] * (m + 1) for _ in range(n + 1)]
    d[0][0] = 0.0
    for i in range(n + 1):
        row = d[i]
        for j in range(m + 1):
            c = row[j]
            if c == INF:
                continue
            if i < n and j < m:
                v = c + cost(i, i + 1, j, j + 1)
                if v < d[i + 1][j + 1]:
                    d[i + 1][j + 1] = v
                    bk[i + 1][j + 1] = (i, j, 1, 1)
            if i < n and j + 2 <= m:
                v = c + cost(i, i + 1, j, j + 2) + MERGE_PENALTY
                if v < d[i + 1][j + 2]:
                    d[i + 1][j + 2] = v
                    bk[i + 1][j + 2] = (i, j, 1, 2)
            if i + 2 <= n and j < m:
                v = c + cost(i, i + 2, j, j + 1) + MERGE_PENALTY
                if v < d[i + 2][j + 1]:
                    d[i + 2][j + 1] = v
                    bk[i + 2][j + 1] = (i, j, 2, 1)
            if i < n:
                v = c + SKIP_PENALTY
                if v < d[i + 1][j]:
                    d[i + 1][j] = v
                    bk[i + 1][j] = (i, j, 1, 0)
    if d[n][m] == INF:
        return None
    out, i, j = [], n, m
    while i or j:
        step = bk[i][j]
        if step is None:
            return None
        pi, pj, a, b = step
        out.append((pi, a, pj, b))
        i, j = pi, pj
    return out[::-1]


def en_lines(emap):
    """The English of one file, in order, as the lines it was cut into."""
    ks = sorted(int(k) for k in emap
                if k != "_note" and str(k).lstrip("-").isdigit())
    return [str(emap[str(k)]).strip() for k in ks if str(emap[str(k)]).strip()]


def rekey(pairs, E):
    """Turn an alignment into the reader's shape: key -> English, spanning."""
    out = {}
    for ri, ra, ei, ea in pairs:
        if ea == 0:
            continue              # a line the translation does not render
        out[str(ri)] = " ".join(E[ei:ei + ea]).strip()
    return out


def grade(chapter, emap):
    s, _ = SHAPE.score(SHAPE.pairs_of(chapter, emap))
    r = score_file(chapter, emap)
    return s, r.get("onrow"), r.get("placed", 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True, help="one parallelEn folder")
    ap.add_argument("--file", default="")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--max-lines", type=int, default=1200,
                    help="skip a chapter bigger than this; the DP is n*m")
    a = ap.parse_args()

    cat = json.load(io.open(INDEX, encoding="utf-8"))
    entry = [b for b in cat if b.get("parallelEn") == a.book]
    if not entry:
        sys.exit("no book with parallelEn %r" % a.book)
    b = entry[0]
    chs = chapters(os.path.join(BOOKS, b["filename"]))
    if not chs:
        sys.exit("could not read %s" % b["filename"])

    print("%-10s %5s %5s %9s %9s  %s"
          % ("file", "ru", "en", "shape", "names", "verdict"))
    changed = held = 0
    for f in sorted(glob.glob(os.path.join(BOOKS, a.book, "[0-9]*.json"))):
        base = os.path.basename(f)
        if a.file and base != a.file:
            continue
        n = int(re.match(r"(\d+)", base).group(1))
        if not (1 <= n <= len(chs)):
            continue
        emap = json.load(io.open(f, encoding="utf-8"))
        E = en_lines(emap)
        # A stanza numeral is a heading, not a line of the poem, and pairing
        # one against an English line costs the path a real pairing.
        R = [p for p in chs[n - 1] if not chapter_marker(p)]
        keep = [i for i, p in enumerate(chs[n - 1]) if not chapter_marker(p)]
        if not R or not E:
            continue
        if len(R) * len(E) > a.max_lines * a.max_lines:
            print("%-10s %5d %5d %9s %9s  too big" % (base, len(R), len(E), "-", "-"))
            continue
        pairs = align(R, E)
        if not pairs:
            continue
        new = dict((str(keep[int(k)]), v) for k, v in rekey(pairs, E).items())
        if "_note" in emap:
            new["_note"] = emap["_note"]
        s0, n0, p0 = grade(chs[n - 1], emap)
        s1, n1, p1 = grade(chs[n - 1], new)
        names_ok = (n0 is None or n1 is None or p0 < 6 or n1 >= n0 - 0.01)
        ok = (s0 is not None and s1 is not None
              and s1 - s0 >= MIN_GAIN and names_ok)
        def pct(x):
            return "   n/a" if x is None else "%5.0f%%" % (100 * x)
        print("%-10s %5d %5d %s->%s %s->%s  %s%s"
              % (base, len(R), len(E), pct(s0), pct(s1), pct(n0), pct(n1),
                 "rewrite" if ok else "leave",
                 "" if names_ok else "  (names would fall)"))
        if ok:
            changed += 1
            if a.apply:
                io.open(f, "w", encoding="utf-8").write(
                    json.dumps(new, ensure_ascii=False, indent=1) + "\n")
        else:
            held += 1
    print()
    print("%d file(s) %s, %d left alone"
          % (changed, "rewritten" if a.apply else "would change", held))
    if changed and not a.apply:
        print("nothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
