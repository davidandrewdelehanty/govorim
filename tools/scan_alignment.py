#!/usr/bin/env python3
"""Score every parallel-text pairing in the library without asking a model.

A book with parallelEn names a folder; the app fetches /books/<dir>/NN.json for
chapter NN-1 and shows entry k of that file beside Russian paragraph k. When
that mapping is wrong the reader gets a page of English that has nothing to do
with the Russian beside it — and nothing about the catalogue looks wrong. It
has happened twice already, both times because an anthology was sliced into its
stories at the wrong boundaries.

This finds those without spending anything. The signal it leans on is that a
translation tracks its original in LENGTH: a long Russian paragraph gets a long
English one, a one-line retort gets a one-line retort. Rank correlation over a
whole chapter is therefore high when the pairing is right and collapses when it
is not — and unlike a ratio it does not care whether the translator is terse or
florid, only whether the two sides rise and fall together.

    python3 tools/scan_alignment.py                 # rank every file
    python3 tools/scan_alignment.py --book yama-en  # one folder
    python3 tools/scan_alignment.py --json out.json
    python3 tools/scan_alignment.py --offsets       # whole books off by a chapter

CHAPTER NUMBERING. This file has its own FB2 reader, and it does not have to
agree with the app's about what counts as a chapter — a cover image, a
dedication, a cast list can each be a section the app folds away and this one
keeps. That shifts every English file of the book by one and looks exactly like
a real fault. So the numbering is calibrated per book instead of assumed: each
work is scored against its chapters and against its chapters shifted a step or
two either way, and the shift that fits best is the one used. A book where no
shift fits is the interesting case, and it is reported as one.

WHAT THE COLUMNS MEAN

  rho     Spearman correlation of Russian against English paragraph length.
          Near 1 is a healthy pairing. Near 0 means the two columns have no
          relationship, which is what a wrong work or a badly shifted file
          looks like. This is the column to sort on.
  ratio   Median English chars per Russian char. Around 1.1-1.5 is normal.
          Much above that and the English is probably a longer text than the
          Russian it sits beside; that is how the Bunin and Korolenko errors
          showed themselves, at 3.3 and 3.1.
  spread  How much that ratio wobbles from paragraph to paragraph, in octaves.
          A steady translation stays under about 1. A file that is right at
          the start and wrong by the end wobbles.
  digits  Where both sides carry numbers, how often the numbers agree. Numbers
          survive translation, so disagreement is real evidence. Blank when
          the chapter has none, which is most prose.
  fit     Whether the English file's paragraph indices exist in the Russian
          chapter at all. "over" means it refers to paragraphs the chapter
          does not have, so the two are not even describing the same chapter.

WHAT IT CANNOT DO. It cannot see a shift of one or two paragraphs — lengths
still correlate across a small offset — and it cannot tell a free translation
from a wrong one when both run to similar lengths. Those need a model reading
the text. This is the pass that says which files are worth paying for.
"""
import argparse, glob, io, json, os, re, sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "private", "books", "index.json")
BOOKS = os.path.join(ROOT, "public", "books")
# Verified by hand this session; re-scanning it would only produce noise.
SKIP_DIRS = set(["bible-kjv"])

TAG = re.compile(r"\{[^}]*\}")
PARA_TAGS = ("p", "v", "subtitle")
DIGITS = re.compile(r"\d+")


def local(el):
    return TAG.sub("", el.tag) if isinstance(el.tag, str) else ""


def text_of(el):
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def paragraphs(sec):
    """Paragraphs of one chapter, in reading order.

    Mirrors the reader: <p>, <v> and <subtitle> count, <title> does not, and
    anything nested inside a title is part of the heading rather than the text.
    """
    out = []
    def walk(node, in_title):
        for ch in node:
            t = local(ch)
            if t == "title":
                walk(ch, True)
                continue
            if t == "section":
                continue                      # a nested section is its own chapter
            if t in PARA_TAGS and not in_title:
                s = text_of(ch)
                if s:
                    out.append(s)
            walk(ch, in_title)
    walk(sec, False)
    return out


ROMAN = re.compile(r"^(?:глава\s+)?([IVXLC]{1,7}|\d{1,3})[.．]?$", re.I)


def markers(sec):
    """Direct-child <subtitle> elements that name a chapter.

    Anna Karenina and Crime and Punishment are one <section> per PART, with the
    chapters inside marked only by a subtitle bearing a numeral. Without this
    the parser sees eight chapters where the English folder has 239 files, and
    every one of them goes unscored.
    """
    subs = [e for e in sec if local(e) == "subtitle" and ROMAN.match(text_of(e))]
    return subs if len(set(text_of(e) for e in subs)) >= 2 else []


def split_at_markers(sec, subs):
    mark = set(id(e) for e in subs)
    out, cur, started = [], [], False
    for ch in sec:
        if id(ch) in mark:
            if started:
                out.append(cur)
            cur, started = [], True
            continue
        if not started:
            continue                  # part-level front matter, before chapter I
        t = local(ch)
        if t == "title":
            continue
        if t in PARA_TAGS:
            s = text_of(ch)
            if s:
                cur.append(s)
        else:
            for p in paragraphs(ch):
                cur.append(p)
    if started:
        out.append(cur)
    return out


CYR = re.compile(r"[А-Яа-яЁё]")


def chapters(path):
    """Chapters of an FB2, as lists of paragraphs.

    Top-level sections are chapters, except where a section holds sections of
    its own — then the children are, which is how parts-and-chapters novels are
    built — or where it is one part with numbered subtitles inside, which is how
    the other half of them are built. The `fit` column reports any file this
    still gets wrong rather than scoring it anyway.
    """
    import xml.etree.ElementTree as ET
    try:
        raw = io.open(path, "rb").read()
    except OSError:
        return None
    # Half this library is windows-1251, and decoding those as UTF-8 with
    # errors="ignore" does not fail — it silently drops every Cyrillic byte and
    # leaves the punctuation, so a paragraph measures fifteen characters and
    # every ratio in the book comes out enormous. Read the declaration.
    m = re.match(rb"<\?xml[^>]*encoding=[\"\']([\w-]+)", raw[:200])
    encs = ([m.group(1).decode("ascii", "ignore")] if m else []) + ["utf-8", "cp1251"]
    src = None
    for enc in encs:
        try:
            src = raw.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if src is None:
        return None
    src = re.sub(r"<binary[\s\S]*?</binary>", "", src)
    # The declaration still names the original encoding; hand the parser UTF-8
    # bytes without it rather than letting it decode them a second time.
    src = re.sub(r"^\s*<\?xml[^>]*\?>", "", src, count=1)
    try:
        root = ET.fromstring(src.encode("utf-8"))
    except ET.ParseError:
        return None
    out = []
    def keep(ch):
        # A <section> holding only a cover image is not a chapter, and the
        # reader does not count it as one. Leaving it in shifted every English
        # file of that book by one and produced a very convincing false alarm.
        return len(ch) > 0
    for body in [e for e in root if local(e) == "body"]:
        for sec in [e for e in body if local(e) == "section"]:
            kids = [e for e in sec if local(e) == "section"]
            if kids:
                for c in kids:
                    subs = markers(c)
                    out.extend(split_at_markers(c, subs) if subs else [paragraphs(c)])
                continue
            subs = markers(sec)
            out.extend(split_at_markers(sec, subs) if subs else [paragraphs(sec)])
    out = [c for c in out if keep(c)]
    # A chapter list with no Cyrillic in it means the decode went wrong in a way
    # that did not raise. Better to score nothing than to score punctuation.
    if out and not any(CYR.search(p) for c in out[:6] for p in c[:6]):
        return None
    return out


def spearman(xs, ys):
    """Rank correlation, ties averaged. No scipy on the box this runs on."""
    n = len(xs)
    if n < 4:
        return None
    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    dx = sum((rx[i] - mx) ** 2 for i in range(n)) ** 0.5
    dy = sum((ry[i] - my) ** 2 for i in range(n)) ** 0.5
    return None if dx == 0 or dy == 0 else num / (dx * dy)


def median(v):
    if not v:
        return None
    s = sorted(v)
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2.0


def score_file(chapter, emap):
    """One chapter file -> a row of numbers, or a reason it could not be scored."""
    keys = [k for k in emap if k != "_note" and str(k).lstrip("-").isdigit()]
    if not keys:
        return {"note": "no entries"}
    idx = sorted(int(k) for k in keys)
    row = {"pairs": len(idx), "cover": None, "fit": "ok"}
    if chapter is None:
        row["fit"] = "no-chapter"
        return row
    row["cover"] = len(idx) / float(len(chapter)) if chapter else 0.0
    over = [i for i in idx if i >= len(chapter)]
    if len(over) > max(2, 0.05 * len(idx)):
        row["fit"] = "over"           # points at paragraphs the chapter lacks
        return row

    ru, en, dig_ok, dig_n = [], [], 0, 0
    import math
    logs = []
    for pos, i in enumerate(idx):
        if i >= len(chapter):
            continue
        # An English entry answers everything from its own paragraph down to
        # the next one that has English — which is exactly what the reader
        # renders, and the only way a deliberately sparse pairing (one Garnett
        # paragraph against several finer Russian ones) can be measured at all.
        nxt = idx[pos + 1] if pos + 1 < len(idx) else len(chapter)
        r = " ".join(chapter[i:min(nxt, len(chapter))])
        e = str(emap[str(i)]).strip()
        if len(r) < 40 or len(e) < 40:
            continue                  # one-line dialogue carries no length signal
        ru.append(len(r)); en.append(len(e))
        logs.append(math.log(len(e) / float(len(r)), 2))
        dr, de = DIGITS.findall(r), DIGITS.findall(e)
        if dr and de:
            dig_n += 1
            if sorted(dr) == sorted(de):
                dig_ok += 1
    row["used"] = len(ru)
    if len(ru) < 8:
        row["fit"] = "thin"           # too little substantial text to judge
        return row
    row["rho"] = spearman(ru, en)
    row["ratio"] = median([en[i] / float(ru[i]) for i in range(len(ru))])
    q = sorted(logs)
    row["spread"] = q[int(.75 * (len(q) - 1))] - q[int(.25 * (len(q) - 1))]
    row["digits"] = (dig_ok / float(dig_n)) if dig_n >= 3 else None
    return row


def best_shift(chs, files, span=(-2, -1, 0, 1, 2)):
    """Which chapter numbering makes this book's English make sense.

    Not a finding in itself — see CHAPTER NUMBERING above. Zero unless some
    other shift is a clear improvement, since neighbouring chapters of one
    novel correlate slightly on their own and a narrow win means nothing.
    """
    if not chs or not files:
        return 0
    got = {}
    for off in span:
        rr = []
        for f in files:
            m = re.match(r"^(\d+)\.json$", os.path.basename(f))
            if not m:
                continue
            ci = int(m.group(1)) - 1 + off
            if not (0 <= ci < len(chs)):
                continue
            try:
                emap = json.load(io.open(f, encoding="utf-8"))
            except Exception:
                continue
            r = score_file(chs[ci], emap)
            if r.get("rho") is not None:
                rr.append(r["rho"])
        got[off] = (median(rr), len(rr))
    base = got.get(0, (None, 0))
    if base[0] is None:
        return 0
    best = max((o for o in span if o and got[o][0] is not None),
               key=lambda o: got[o][0], default=None)
    if best is None:
        return 0
    return best if (got[best][0] > base[0] + 0.3 and got[best][1] >= 4) else 0


def offsets(entries):
    """Is a whole folder numbered one chapter out of step?

    A per-file score cannot tell that apart from a file that is simply wrong:
    both come out uncorrelated. Scoring the folder against its neighbouring
    chapters can — if every file suddenly makes sense one chapter along, the
    numbering is off, and the fix is a rename rather than a re-alignment.
    """
    print("%-30s %5s %5s %6s %6s %6s %6s" % ("work", "chs", "files",
                                             "at -1", "as is", "at +1", "at +2"))
    hits = []
    for b in entries:
        fb2 = os.path.join(BOOKS, b["filename"])
        chs = chapters(fb2) if os.path.exists(fb2) else None
        if not chs:
            continue
        files = sorted(glob.glob(os.path.join(BOOKS, b["parallelEn"], "[0-9]*.json")))
        got = {}
        for off in (-1, 0, 1, 2):
            rr = []
            for f in files:
                ci = int(re.match(r"(\d+)", os.path.basename(f)).group(1)) - 1 + off
                if not (0 <= ci < len(chs)):
                    continue
                try:
                    emap = json.load(io.open(f, encoding="utf-8"))
                except Exception:
                    continue
                r = score_file(chs[ci], emap)
                if r.get("rho") is not None:
                    rr.append(r["rho"])
            got[off] = (median(rr), len(rr))
        if got[0][0] is None:
            continue
        cells = " ".join(("%6.2f" % got[o][0]) if got[o][0] is not None else "    --"
                         for o in (-1, 0, 1, 2))
        print("%-30s %5d %5d %s" % (b.get("title", "")[:30], len(chs), len(files), cells))
        best = max((o for o in (-1, 1, 2) if got[o][0] is not None),
                   key=lambda o: got[o][0], default=None)
        # Only a clear win counts. Neighbouring chapters of one novel correlate
        # a little on their own, so a small edge means nothing.
        if best is not None and got[best][0] > got[0][0] + 0.3 and got[best][1] >= 4:
            hits.append((b.get("title", ""), b["parallelEn"], best,
                         got[0][0], got[best][0]))
    print()
    if hits:
        print("%d work(s) read better at a different chapter number:" % len(hits))
        for t, d, off, now, then in hits:
            print("   %-30s %-26s %+d  (%.2f -> %.2f)" % (t[:30], d, off, now, then))
        print()
        print("This says the two chapter lists do not line up. It does NOT say")
        print("which one is wrong: an FB2 whose front matter this reader counts")
        print("and the app does not looks exactly the same from here. Open the")
        print("book in the app and read one paragraph before renaming anything.")
    else:
        print("every folder is numbered in step with its book.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", help="one parallelEn folder name")
    ap.add_argument("--json", help="write every row here")
    ap.add_argument("--top", type=int, default=45, help="rows to print (default 45)")
    ap.add_argument("--offsets", action="store_true",
                    help="re-score each work against neighbouring chapters, to "
                         "catch a folder numbered a chapter out of step")
    a = ap.parse_args()

    catalogue = json.load(io.open(INDEX, encoding="utf-8"))
    entries = [b for b in catalogue if b.get("parallelEn")
               and b["parallelEn"] not in SKIP_DIRS
               and (not a.book or b["parallelEn"] == a.book)]

    if a.offsets:
        return offsets(entries)

    rows, unscored, shifted = [], [], []
    for b in entries:
        fb2 = os.path.join(BOOKS, b["filename"])
        chs = chapters(fb2) if os.path.exists(fb2) else None
        d = os.path.join(BOOKS, b["parallelEn"])
        files = sorted(glob.glob(os.path.join(d, "*.json")))
        shift = best_shift(chs, files)
        if shift:
            shifted.append((b.get("title", ""), b["parallelEn"], shift))
        for f in files:
            name = os.path.basename(f)
            m = re.match(r"^(\d+)\.json$", name)
            if not m:
                continue
            ci = int(m.group(1)) - 1 + shift
            try:
                emap = json.load(io.open(f, encoding="utf-8"))
            except Exception as e:
                unscored.append((b["parallelEn"], name, "unreadable: %s" % e))
                continue
            ch = chs[ci] if (chs and 0 <= ci < len(chs)) else None
            r = score_file(ch, emap)
            r.update(book=b.get("title", ""), dir=b["parallelEn"], file=name,
                     chapters=(len(chs) if chs else 0), shift=shift)
            (rows if r.get("rho") is not None else unscored_row(unscored, r)) and None
            if r.get("rho") is not None:
                rows.append(r)
    # Corpus-relative thresholds: what "normal" is here is what most of the
    # library already does, not a number picked in advance.
    rhos = sorted(r["rho"] for r in rows)
    ratios = sorted(r["ratio"] for r in rows)
    mid_ratio = median(ratios)
    print("scored %d files across %d works" % (len(rows), len(entries)))
    if rows:
        print("corpus: median rho %.2f, median ratio %.2f, 5th-pct rho %.2f"
              % (median(rhos), mid_ratio, rhos[int(.05 * (len(rhos) - 1))]))

    def flag(r):
        why = []
        # The two failures look different in the numbers. English from another
        # work runs to its own lengths, so the ratio goes wrong as well as the
        # correlation. English chopped into even pieces and dealt out one per
        # Russian paragraph keeps a perfectly ordinary ratio — the pieces are
        # all the same size — and destroys only the correlation.
        if r["rho"] < 0.35:
            if r["ratio"] > mid_ratio * 1.8 or r["ratio"] < mid_ratio / 1.8:
                why.append("unrelated text")
            elif r["spread"] < 1.2:
                why.append("English cut to even lengths, not to the paragraphs")
            else:
                why.append("no length relationship")
        elif r["rho"] < 0.55:
            why.append("weak length relationship")
        if r["ratio"] > mid_ratio * 2.0: why.append("English far longer")
        elif r["ratio"] < mid_ratio / 2.0: why.append("English far shorter")
        if r["spread"] > 1.6: why.append("ratio unsteady")
        if r["digits"] is not None and r["digits"] < 0.4: why.append("numbers disagree")
        return "; ".join(why)

    for r in rows:
        r["flag"] = flag(r)
    bad = [r for r in rows if r["flag"]]
    bad.sort(key=lambda r: (r["rho"], -r["spread"]))

    if shifted:
        print("\nchapter numbering calibrated for %d work(s) whose front matter "
              "this reader counts and the app does not:" % len(shifted))
        for t, d, sh in shifted:
            print("   %-30s %-26s %+d" % (t[:30], d, sh))

    print("\n%d of %d files flagged\n" % (len(bad), len(rows)))
    # By work first. A single bad file is usually one chapter to re-cut; a work
    # where most files fail is one job, and it is the job worth doing first.
    per = {}
    for r in rows:
        per.setdefault((r["book"], r["dir"]), []).append(r)
    works = []
    for (title, d), rs in per.items():
        n_bad = sum(1 for r in rs if r["flag"])
        works.append((n_bad / float(len(rs)), n_bad, len(rs), median([r["rho"] for r in rs]),
                      median([r["ratio"] for r in rs]), title, d))
    works = [w for w in works if w[1]]
    works.sort(key=lambda w: (-w[0], w[3]))
    print("%-32s %-24s %9s %6s %6s" % ("work", "folder", "flagged", "rho", "ratio"))
    for frac, nb, n, rho, rat, title, d in works[:a.top]:
        print("%-32s %-24s %4d/%-4d %6.2f %6.2f"
              % (title[:32], d[:24], nb, n, rho, rat))
    if len(works) > a.top:
        print("... %d more works with at least one flagged file" % (len(works) - a.top))

    print("\nworst individual files")
    print("%-28s %-26s %5s %6s %6s %6s  %s"
          % ("work", "file", "n", "rho", "ratio", "spread", "why"))
    for r in bad[:a.top]:
        print("%-28s %-26s %5d %6.2f %6.2f %6.2f  %s"
              % (r["book"][:28], (r["dir"][:17] + "/" + r["file"]), r["used"],
                 r["rho"], r["ratio"], r["spread"], r["flag"]))
    if len(bad) > a.top:
        print("... %d more (raise --top, or --json for all)" % (len(bad) - a.top))

    if unscored:
        print("\n%d files could not be scored:" % len(unscored))
        seen = Counter(u[2] if len(u) > 2 else "?" for u in unscored)
        for k, n in seen.most_common(8):
            print("   %-40s %d" % (k[:40], n))

    if a.json:
        io.open(a.json, "w", encoding="utf-8").write(
            json.dumps({"rows": rows, "unscored": unscored},
                       ensure_ascii=False, indent=1) + "\n")
        print("\nwrote %s" % a.json)
    return 0


def unscored_row(lst, r):
    lst.append((r.get("dir"), r.get("file"), r.get("fit") or r.get("note") or "?"))
    return False


if __name__ == "__main__":
    sys.exit(main())
