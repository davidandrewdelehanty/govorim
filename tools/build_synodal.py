#!/usr/bin/env python3
"""Build the Synodal Bible entry: the five books of Moses and the four Gospels.

Two public-domain texts, verified before use: the Russian Synodal (1876) and
the King James (1611).

Output:
  public/books/novel/bible-synodal.fb2   one <section> per CHAPTER
  public/books/bible-kjv/NN.json         paragraph index -> King James text

ONE PAGE PER CHAPTER, numbered straight through: Бытие 1 is 01.json, Иоанна 21
is 276.json. It was briefly one page per book, so that a single book-length
recording could cover its whole page — but Genesis is fifty chapters and 1,529
verses, and a page nobody can find their way down is worse than a recording
that only covers the top of one. Per-chapter readings go on their own chapters.

The English is keyed by PARAGRAPH INDEX within the chapter, the scheme
parallelEn already uses for prose, so entry 0 is verse 1.

RUN-ON WORDS. The Russian source drops the odd space — "И стал свет" arrives
as "И сталсвет" — and the reader shows text exactly as it is written. The
splits live in tools/synodal_fixes.json, made and reviewed by
tools/find_run_ons.py; that file has the whole account of how they were found
and what the method cannot do. Applying them here needs neither the tool nor
its dictionary.

ALIGNMENT. The two sources disagree about verse counts in 41 of the 276
chapters — each omits or merges where the other divides. Pairing by position,
which is what this entry shipped with, silently shifts every verse after the
first disagreement for the rest of the chapter. So the verses are aligned
instead, by a monotonic DP over four moves: 1:1; one Russian verse holding two
English; two holding one; and a Russian verse with NO English at all, for the
verses the King James source is simply missing (Matthew 2:16 among them).
Scoring is how far a pairing's length ratio sits from the chapter's own
average, with matching numerals counted as evidence for and clashing ones as
evidence against.

Without that fourth move a missing English verse had to be absorbed by a 2:1
merge, which put verse 15's English against verses 15 AND 16 and left 16
looking translated when it was not. A gap shown as a gap is the honest
rendering; the English text itself is never dropped, since the reverse case
(a verse the Russian source lacks) still joins onto its neighbour.

The 235 chapters where the counts agree are the control: the pairing there
should be the identity one, and the DP returns it in 234. The exception,
Mark 7, is not a failure — the English source drops a verse in the middle and
gains one back at verse 33, so its counts match while its verses do not, and
the DP is right to refuse the identity pairing there. It places the gap one
verse early (at 7:11 rather than 7:12), which is the known limit of scoring on
length alone. Re-run tools/check_bible_align.py to reproduce this.
"""
import io, json, math, os, re, sys, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.abspath(os.path.join(ROOT, "..", "govorim-sources", "bible"))

# (index in the 66-book source, Russian name, English name)
BOOKS = [
    (0,  "Бытие",        "Genesis"),
    (1,  "Исход",        "Exodus"),
    (2,  "Левит",        "Leviticus"),
    (3,  "Числа",        "Numbers"),
    (4,  "Второзаконие", "Deuteronomy"),
    (39, "Матфея",       "Matthew"),
    (40, "Марка",        "Mark"),
    (41, "Луки",         "Luke"),
    (42, "Иоанна",       "John"),
]

# A merge has to earn its place. The number of merges is forced by the verse
# counts, so this constant does not decide how many there are -- it only stops
# the DP inventing offsetting pairs of them where 1:1 already fits.
MERGE_PENALTY = 3.0

# A Russian verse the English source does not have at all. Priced the same as
# a merge because it is the same kind of event — one verse that will not pair
# one-to-one — and letting the length term pick between them is the point.
SKIP_PENALTY = 3.0


def esc(s):
    return html.escape(str(s), quote=False)


FIXES = json.load(io.open(os.path.join(ROOT, "tools", "synodal_fixes.json"),
                          encoding="utf-8"))
# Every split must put the same letters back, or a "fix" is quietly rewriting
# scripture rather than spacing it.
for _k, _v in FIXES.items():
    if "".join(_v.split()) != _k:
        sys.exit("synodal_fixes.json: %r does not spell %r" % (_v, _k))
# Cut positions, so the original capitals survive: "Младенцас" is cut, not
# looked up and replaced by a lowercase copy of itself.
CUTS = dict((k, [len(p) for p in v.split()]) for k, v in FIXES.items())
WORD = re.compile(r"[А-Яа-яЁё]+")


def clean_ru(v):
    return re.sub(r"\s+", " ", str(v)).strip()


def unrun(text, tally):
    """Put back the spaces the source lost."""
    def one(m):
        w = m.group(0)
        lens = CUTS.get(w.lower())
        if not lens:
            return w
        tally[0] += 1
        out, i = [], 0
        for n in lens:
            out.append(w[i:i + n])
            i += n
        return " ".join(out)
    return WORD.sub(one, text)


def clean_en(v):
    # The King James marks translator-supplied words with braces. They are a
    # typographic instruction (set these in italics), not part of the verse.
    return re.sub(r"\s+", " ", str(v).replace("{", "").replace("}", "")).strip()


def _digits(s):
    return tuple(sorted(re.findall(r"\d+", s)))


def align(R, E):
    """Monotonic verse alignment. Returns [(ri, rspan, ei, espan), ...]."""
    rl = [max(len(x), 1) for x in R]
    el = [max(len(x), 1) for x in E]
    rd = [_digits(x) for x in R]
    ed = [_digits(x) for x in E]
    k = sum(el) / float(sum(rl)) if sum(rl) else 1.0

    def cost(a, b):
        return abs(math.log(max(b, 1) / (max(a, 1) * k)))

    def dcost(rs, es):
        if not rs and not es:
            return 0.0
        if rs == es:
            return -0.30
        return 0.25 if (rs and es) else 0.10

    n, m = len(R), len(E)
    INF = float("inf")
    d = [[INF] * (m + 1) for _ in range(n + 1)]
    bk = [[None] * (m + 1) for _ in range(n + 1)]
    d[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            c = d[i][j]
            if c == INF:
                continue
            if i < n and j < m:
                v = c + cost(rl[i], el[j]) + dcost(rd[i], ed[j])
                if v < d[i + 1][j + 1]:
                    d[i + 1][j + 1] = v
                    bk[i + 1][j + 1] = (i, j, 1, 1)
            if i < n and j + 1 < m:
                v = (c + cost(rl[i], el[j] + el[j + 1])
                     + dcost(rd[i], tuple(sorted(ed[j] + ed[j + 1]))) + MERGE_PENALTY)
                if v < d[i + 1][j + 2]:
                    d[i + 1][j + 2] = v
                    bk[i + 1][j + 2] = (i, j, 1, 2)
            if i + 1 < n and j < m:
                v = (c + cost(rl[i] + rl[i + 1], el[j])
                     + dcost(tuple(sorted(rd[i] + rd[i + 1])), ed[j]) + MERGE_PENALTY)
                if v < d[i + 2][j + 1]:
                    d[i + 2][j + 1] = v
                    bk[i + 2][j + 1] = (i, j, 2, 1)
            if i < n:
                v = c + SKIP_PENALTY
                if v < d[i + 1][j]:
                    d[i + 1][j] = v
                    bk[i + 1][j] = (i, j, 1, 0)
    if d[n][m] == INF:
        sys.exit("no alignment path (ru=%d en=%d)" % (n, m))
    out, i, j = [], n, m
    while i or j:
        pi, pj, a, b = bk[i][j]
        out.append((pi, a, pj, b))
        i, j = pi, pj
    return out[::-1]


def main():
    ru = json.load(io.open(os.path.join(SRC, "ru_synodal.json"), encoding="utf-8-sig"))
    en = json.load(io.open(os.path.join(SRC, "en_kjv.json"), encoding="utf-8-sig"))

    endir = os.path.join(ROOT, "public", "books", "bible-kjv")
    os.makedirs(endir, exist_ok=True)
    for f in os.listdir(endir):
        if f.endswith(".json"):
            os.remove(os.path.join(endir, f))

    tally = [0]
    secs, totals, merged_chapters = [], [], 0
    for si, (idx, name, ename) in enumerate(BOOKS):
        rb, eb = ru[idx], en[idx]
        if len(rb["chapters"]) != len(eb["chapters"]):
            sys.exit("chapter count mismatch in %s" % name)

        p = 0
        chapters = verses = 0
        for ci, rch in enumerate(rb["chapters"]):
            ech = [clean_en(x) for x in eb["chapters"][ci]]
            rch = [unrun(clean_ru(x), tally) for x in rch]
            if len(rch) != len(ech):
                merged_chapters += 1

            body, emap = [], {}
            for vi, t in enumerate(rch):
                body.append("<p>%d %s</p>" % (vi + 1, esc(t)))
                verses += 1

            for (ri, rspan, ei, espan) in align(rch, ech):
                text = " ".join(x for x in ech[ei:ei + espan] if x)
                if text:
                    emap[str(ri)] = text

            chapters += 1
            p += len(rch)
            secs.append("<section>\n<title><p>%s %d</p></title>\n%s\n</section>"
                        % (esc(name), ci + 1, "\n".join(body)))
            with io.open(os.path.join(endir, "%02d.json" % len(secs)),
                         "w", encoding="utf-8") as f:
                json.dump(emap, f, ensure_ascii=False, separators=(",", ":"))
        totals.append((name, ename, chapters, verses, p, len(secs)))

    fb2 = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">\n'
           '<description><title-info>'
           '<book-title>Библия. Синодальный перевод</book-title>'
           '<author><last-name></last-name></author>'
           '</title-info></description>\n<body>\n'
           + "\n".join(secs) + "\n</body>\n</FictionBook>\n")
    out = os.path.join(ROOT, "public", "books", "novel", "bible-synodal.fb2")
    io.open(out, "w", encoding="utf-8").write(fb2)

    print("%-14s %-12s %5s %7s %7s %9s" % ("book", "english", "chs", "verses",
                                           "paras", "last file"))
    for name, ename, c, v, pn, e in totals:
        print("%-14s %-12s %5d %7d %7d %9d" % (name, ename, c, v, pn, e))
    print("\n%d run-on words split (%d in the table)" % (tally[0], len(FIXES)))
    print("%d sections, %d chapters, %d verses, %d chapters needed alignment"
          % (len(secs), sum(t[2] for t in totals), sum(t[3] for t in totals),
             merged_chapters))
    print("wrote %s (%.1f MB)" % (out, os.path.getsize(out) / 1e6))


if __name__ == "__main__":
    main()
