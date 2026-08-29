#!/usr/bin/env python3
"""Re-cut a parallel English file that was chopped in the wrong places.

Some of the English chapter files hold the right translation, complete and in
order, sliced into pieces of roughly equal size and dealt out one per Russian
paragraph. The join between consecutive pieces lands mid-sentence — "...just
three days after my tenth birthday, when I h" / "from under the coverlet,
steadied the still shaking image" — and the reader shows each fragment beside a
paragraph it has nothing to do with. tools/scan_alignment.py finds these: they
score near zero on length correlation while keeping a perfectly ordinary
length ratio.

Nothing is missing from those files, so nothing needs translating again. The
English only has to be cut where the Russian is cut. This joins the pieces back
into continuous prose, splits that into sentences, and hands the sentences back
out so each Russian paragraph gets the English that belongs to it — matching on
how long the paragraph is, and anchoring wherever both sides carry the same
number or the same foreign phrase, which they often do in Tolstoy.

    python3 tools/reslice_parallel.py                     # what it would change
    python3 tools/reslice_parallel.py --apply
    python3 tools/reslice_parallel.py --book yunost-en --apply

A file is only rewritten when the result scores better than what is there now,
measured with the same correlation the scanner uses. A file it cannot improve
is left exactly as it was and named in the report.

HOW FAR TO TRUST IT. The split reasons about length, and so does the score that
grades it, so a high score after re-cutting is not by itself proof that the
English on a row is the translation of the Russian beside it. Read a few rows.
Where the Russian is paragraphed as the translator paragraphed it — Detstvo,
where the German lines Tolstoy leaves untranslated anchor the split exactly —
the result is right row for row. Where the Russian text is cut finer than the
translation is (Belye nochi, and the Garnett texts generally), the correspondence
comes back but can sit a sentence or two out, because no cutting of the English
can match one Russian paragraph that the translator wrote as half of one. That
is still far better than the wholesale offset it replaces, and it is the point
at which a model reading the text earns its money.
"""
import argparse, glob, io, json, math, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import BOOKS, INDEX, chapters, score_file, median

# Sentence end, but not after an abbreviation or an initial.
ABBR = r"(?<!\bMr)(?<!\bMrs)(?<!\bDr)(?<!\bSt)(?<!\bNo)(?<!\bMme)(?<!\bMlle)(?<![A-Z])"
SENT = re.compile(ABBR + r"(?<=[.!?…])[\"'”’)\]]*\s+(?=[\"'“‘(\[]?[A-ZÀ-Þ])")
LATIN = re.compile(r"[A-Za-zÀ-ɏ]{4,}")
DIGIT = re.compile(r"\d+")
# How much a paragraph left without English costs. Cheap enough that an
# epigraph or a one-word heading can be skipped, dear enough that the split
# does not simply abandon half the chapter.
EMPTY = 1.1
MAX_BLOCK = 14          # sentences one paragraph can absorb


def sentences(text):
    parts = [p.strip() for p in SENT.split(text) if p.strip()]
    return parts if parts else ([text.strip()] if text.strip() else [])


def epigraph_run(chapter):
    """How many paragraphs of verse and markup a chapter opens with.

    Belye nochi opens on a wiki-template leftover and four lines of Turgenev.
    They are not prose and have no English, but a split that only reasons about
    length will happily give them the story's first sentences. Only a run at
    the very top counts, and only where real prose follows — a chapter that
    opens on short dialogue is not an epigraph and must not be trimmed.
    """
    lead = 0
    for t in chapter:
        if "{{" in t or "}}" in t or len(t) < 90:
            lead += 1
        else:
            break
    if lead < 2 or lead >= len(chapter):
        return 0
    rest = chapter[lead:lead + 4]
    return lead if any(len(t) >= 150 for t in rest) else 0


def foreign(ru):
    """Latin-script words inside a Russian paragraph — the French and German a
    translator carries across untouched, and the surest anchor in the book."""
    return set(w.lower() for w in LATIN.findall(ru))


def reslice(chapter, emap):
    """Give each Russian paragraph the English that belongs to it."""
    keys = sorted(int(k) for k in emap if k != "_note" and str(k).lstrip("-").isdigit())
    if not keys:
        return None
    joined = " ".join(str(emap[str(k)]).strip() for k in keys)
    sents = sentences(joined)
    start = epigraph_run(chapter)
    paras = list(range(start, min(len(chapter), (max(keys) + 1) if keys else 0)))
    if len(sents) < 4 or len(paras) < 3:
        return None

    slen = [len(s) for s in sents]
    plen = [max(len(chapter[i]), 1) for i in paras]
    scale = sum(slen) / float(sum(plen))
    cum = [0]
    for L in slen:
        cum.append(cum[-1] + L)

    sdig = [set(DIGIT.findall(s)) for s in sents]
    slat = [set(w.lower() for w in LATIN.findall(s)) for s in sents]
    pdig = [set(DIGIT.findall(chapter[i])) for i in paras]
    plat = [foreign(chapter[i]) for i in paras]

    n, m = len(paras), len(sents)
    INF = float("inf")
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    bk = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(n):
        want = plen[i] * scale
        for j in range(m + 1):
            base = dp[i][j]
            if base == INF:
                continue
            if base + EMPTY < dp[i + 1][j]:
                dp[i + 1][j] = base + EMPTY
                bk[i + 1][j] = j
            top = min(m, j + MAX_BLOCK)
            for k in range(j + 1, top + 1):
                got = cum[k] - cum[j]
                c = abs(math.log(got / want)) if want > 0 else 0.0
                # An anchor is worth more than any length argument: numbers and
                # foreign phrases survive translation unchanged.
                hit = False
                for t in range(j, k):
                    if (pdig[i] and sdig[t] & pdig[i]) or (plat[i] and slat[t] & plat[i]):
                        hit = True
                        break
                if hit:
                    c -= 1.2
                v = base + c
                if v < dp[i + 1][k]:
                    dp[i + 1][k] = v
                    bk[i + 1][k] = j
    if dp[n][m] == INF:
        return None

    out, i, j = {}, n, m
    while i > 0:
        j0 = bk[i][j]
        if j0 is None:
            return None
        if j0 < j:
            out[str(paras[i - 1])] = " ".join(sents[j0:j])
        i, j = i - 1, j0
    if "_note" in emap:
        out["_note"] = emap["_note"]
    return out


def rho_of(chapter, emap):
    r = score_file(chapter, emap)
    return r.get("rho"), r.get("used", 0)


def diced(emap):
    """Does this file read as one continuous text cut at the wrong points?"""
    ks = sorted(int(k) for k in emap if k != "_note" and str(k).lstrip("-").isdigit())
    if len(ks) < 5:
        return 0.0
    br = 0
    for a, b in zip(ks, ks[1:]):
        ta, tb = str(emap[str(a)]).strip(), str(emap[str(b)]).strip()
        if not ta or not tb:
            continue
        if not (ta[-1:] in ".!?”\"’'" and (tb[:1].isupper() or tb[:1] in "“\"‘'")):
            br += 1
    return br / float(len(ks) - 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", help="one parallelEn folder")
    ap.add_argument("--apply", action="store_true", help="write the improved files")
    ap.add_argument("--min-gain", type=float, default=0.25,
                    help="how much better a re-cut must score to be kept")
    a = ap.parse_args()

    catalogue = json.load(io.open(INDEX, encoding="utf-8"))
    entries = [b for b in catalogue if b.get("parallelEn")
               and (not a.book or b["parallelEn"] == a.book)]

    print("%-26s %-12s %6s %6s %7s" % ("work", "file", "before", "after", "verdict"))
    kept = skipped = 0
    gains = []
    for b in entries:
        fb2 = os.path.join(BOOKS, b["filename"])
        chs = chapters(fb2) if os.path.exists(fb2) else None
        if not chs:
            continue
        for f in sorted(glob.glob(os.path.join(BOOKS, b["parallelEn"], "[0-9]*.json"))):
            m = re.match(r"^(\d+)\.json$", os.path.basename(f))
            if not m:
                continue
            ci = int(m.group(1)) - 1
            if not (0 <= ci < len(chs)):
                continue
            emap = json.load(io.open(f, encoding="utf-8"))
            if diced(emap) <= 0.5:
                continue
            before, used = rho_of(chs[ci], emap)
            if before is None or used < 6:
                continue
            new = reslice(chs[ci], emap)
            if not new:
                continue
            after, _ = rho_of(chs[ci], new)
            if after is None:
                continue
            ok = after - before >= a.min_gain
            print("%-26s %-12s %6.2f %6.2f %7s"
                  % (b.get("title", "")[:26], os.path.basename(f), before, after,
                     "keep" if ok else "leave"))
            if ok:
                kept += 1
                gains.append(after - before)
                if a.apply:
                    io.open(f, "w", encoding="utf-8").write(
                        json.dumps(new, ensure_ascii=False, indent=1, sort_keys=False) + "\n")
            else:
                skipped += 1

    print()
    if gains:
        print("%d file(s) improve, by %.2f on average%s"
              % (kept, sum(gains) / len(gains), " — written" if a.apply else ""))
    if skipped:
        print("%d file(s) the re-cut does not improve; left untouched" % skipped)
    if kept and not a.apply:
        print("\nnothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
