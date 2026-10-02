#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build «Цемент» (1926) from the scan, not from a text site's copy.

The FB2 floating around the text sites is the REVISED novel. Gladkov rewrote
it from 1930 on and the late-Soviet editions carry his revisions:

    1926   море ... кипело горячим молоком и осколками солнца
    later  море ... кипело солнцем

So the original has to come off the 1926 printing. The scan's OCR layer is
good — 78,000 Cyrillic words, 128 stray Latin letters in 577,000 characters —
but pdftotext's default reading order throws away the one thing that marks
where a paragraph begins: the printer's indent. With --layout the indent
survives, and that is what this reads.

    python3 tools/cement_from_scan.py --pdf <scan.pdf> --dry-run
    python3 tools/cement_from_scan.py --pdf <scan.pdf>

Writes public/books/novel/cement.fb2 and upserts the catalogue entry, using
the same FB2 builder the Wikisource importer uses, so the reader chapters it
the same way as every other book.
"""
import argparse
import difflib
import io
import os
import re
import subprocess
import sys

sys.path.insert(0, "tools")
from add_wikisource import build_fb2

INDENT = 2          # a line this far in starts a paragraph; 0 continues one
CENTRED = 8         # this far in is centred type, not a margin
RUNNING = re.compile(r"(ЦЕМЕНТ|ЦЕМЕЯT|ЦЕМЕНT|ФЕДОР\s+ГЛАДКОВ|Ф\.\s*ГЛАДКОВ)")
PAGENO = re.compile(r"^[0-9IVXlvx]{1,4}$")
# A numeral alone on a centred line heads either a part or a chapter, and the
# numeral cannot say which: the scanner reads the part numeral «II» as the
# Cyrillic «П», and part I and chapter 1 are both «1» often enough. The names
# below them do say which — this edition sets a part name in capitals
# («ПУСТЫННЫЙ ЗАВОД») and a chapter title in sentence case («У порога
# гнезда»). Going by the numeral alone ate every part's first chapter.
NUMERAL = re.compile(r"^(?:[IVXivx]{1,5}|[ПпНн]{1,3}|\d{1,2})\s*[.,«\u00ab]?$")

def is_caps(s):
    letters = [c for c in s if c.isalpha()]
    if len(letters) < 3:
        return False
    return sum(1 for c in letters if c.isupper()) / float(len(letters)) >= 0.8

def unspace(s):
    """«М о р о к» -> «Морок». The original sets its chapter titles
    letter-spaced, which arrives as a row of one-letter words."""
    toks = s.split()
    if len(toks) >= 3 and sum(1 for t in toks if len(t) == 1) >= len(toks) * 0.6:
        return "".join(toks)
    return s

# OCR confusions seen in this scan. Narrow on purpose: each is a shape the
# scanner mistook, never a guess at what a word ought to be.
FIXES = [
    ("­", ""),                    # the soft hyphen left where a line broke
    ("‐", "-"), ("‑", "-"),
    ("Бвг.", "Евг."),
    ("JV»", "№"), ("JV>", "№"), ("J№", "№"),
    ("To-есть", "То-есть"), ("Ha-гой", "Нагой"),
    ("Ha-днях", "На-днях"), ("iлазах", "глазах"),
    ("A-а", "А-а"), ("й" + "—", "и—"),
]


LEADER = re.compile(r"[.\u2024\u2027\u00b7\u2022]{3,}")
CH_LINE = re.compile(r"^(\d{1,2})\s*[.,\u00ab\u00bb)]\s*(.+)$")
SKIP_LINE = re.compile(r"^(ОГЛАВЛЕНИЕ|Стр\.?|[\d\s.,\u2026\u00b7\u2022IÎ\[\]]*)$")


def read_contents(pdf, page):
    """The book's own ОГЛАВЛЕНИЕ, which is the only trustworthy source for
    the names.

    Nothing here reads the numerals. The scanner renders the part numbers as
    «П.», «1П.», «VH.», «VIIL», «[X.», «ХП.», «ХУТ.» — Cyrillic for Latin,
    brackets for letters — so a pattern over numerals would be a pattern over
    the scanner's mistakes. The line's shape is sound instead: a chapter line
    opens with an arabic numeral and a stop, and every other line of text is
    the part it belongs to.
    """
    out = subprocess.run(["pdftotext", "-layout", "-f", str(page),
                          "-l", str(page + 1), pdf, "-"], capture_output=True)
    text = out.stdout.decode("utf-8", "replace")
    want, part = [], ""
    for raw in text.split("\n"):
        line = re.sub(r"\s+", " ", LEADER.sub(" ", raw)).strip()
        # The page number at the end of the line is often not a number by the
        # time the scanner has finished with it: «Морок … И» for 11, «Массы …
        # Î41» for 141, «Братва … *» for 22. Anything short and wordless
        # trailing the title is that column, not part of the name.
        line = re.sub(r"[\s.,\u2026\u00b7\u2022]+[\dIÎliOИЗОБизо\u00ab\u00bb*\u2022.,]{1,4}$", "", line).strip()
        line = re.sub(r"[\s.,\u2026\u00b7\u2022*]+$", "", line).strip()
        line = re.sub(r"\s+Стр\.?$", "", line).strip()
        if not line or SKIP_LINE.match(line):
            continue
        m = CH_LINE.match(line)
        if m:
            want.append((part, m.group(1), m.group(2).strip()))
        else:
            part = re.sub(r"^[^\s.]*\.\s*", "", line).strip() or line
    return want


def pdf_lines(pdf, first, last):
    out = subprocess.run(
        ["pdftotext", "-layout", "-f", str(first), "-l", str(last), pdf, "-"],
        capture_output=True)
    if out.returncode != 0:
        sys.exit("pdftotext failed: %s" % out.stderr.decode("utf-8", "replace")[:300])
    return out.stdout.decode("utf-8", "replace").split("\f")


def strip_furniture(page):
    """Drop the page number and the running head, keep everything else — and
    keep the indent, which is the only thing that says where a paragraph or a
    heading begins.

    Two traps here, both found the hard way. With --layout the page number and
    the running head share one line («6      ФЕДОР ГЛАДКОВ»), so a test for a
    line that is ONLY the head leaves the number behind and starts a spurious
    paragraph with it. And a chapter numeral is also a bare number on its own
    line: dropping every such line threw away every «1», «2», «I» in the book,
    which is why the first run found no chapters at all. The margin tells them
    apart — a page number sits at the edge, a chapter numeral is centred.
    """
    kept = []
    for raw in page.split("\n"):
        line = raw.rstrip()
        bare = line.strip()
        if not bare:
            continue
        if RUNNING.search(bare):
            continue                      # the head, with or without a number
        indent = len(line) - len(line.lstrip())
        if PAGENO.match(bare) and indent < CENTRED:
            continue                      # a page number at the margin
        kept.append(line)
    return kept


def paragraphs(lines):
    """Indent decides. A line pushed in begins a paragraph; a flush line
    continues the one before it.

    A word broken over a line break has to be put back together before the
    join, not after: the break leaves a soft hyphen at the end of the line, so
    joining with a space first gives «красные го ловы» and no later cleanup
    can tell that from two real words.
    """
    paras, cur = [], ""
    for line in lines:
        text = line.strip()
        indent = len(line) - len(line.lstrip())
        if indent >= INDENT or not cur:
            if cur:
                paras.append(cur)
            cur = text
        elif cur.endswith(("\u00ad", "\u2010", "\u2011", "-")):
            cur = cur[:-1] + text          # the word continues
        else:
            cur = cur + " " + text
    if cur:
        paras.append(cur)
    return paras


def tidy(s):
    for a, b in FIXES:
        s = s.replace(a, b)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+([,.;:!?…])", r"\1", s)
    return s.strip()


def norm(s):
    return re.sub(r"[^\u0430-\u044f\u0451a-z]", "", unspace(s).lower())


def near(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def split_chapters(paras, want):
    """Cut the body where the contents says a chapter begins.

    Driven from the contents list, in order, rather than from a pattern over
    the body — because the body cannot be patterned reliably. «Щепки» lost its
    numeral in the scan, so a numeral-above-a-title rule never saw it; and the
    part headings «Отчий дом» and «Тихий ход» came through in lower case, so a
    capitals rule read them as chapters. Matching the next title we are
    actually looking for is immune to both: it knows what it expects, and a
    scanning error has to be bad enough to break the resemblance.
    """
    parts = {norm(w[0]) for w in want if w[0]}
    chapters, cur, idx = [], [], 0
    pre = []
    for i, p in enumerate(paras):
        if len(p) <= 60:
            if idx < len(want) and near(p, want[idx][2]) >= 0.75:
                if chapters or cur:
                    (chapters[-1]["blocks"].extend([("p", t) for t in cur])
                     if chapters else pre.extend(cur))
                cur = []
                part, num, title = want[idx]
                name = "%s \u2014 %s. %s" % (part, num, title) if part else \
                       "%s. %s" % (num, title)
                chapters.append({"title": name, "blocks": []})
                idx += 1
                continue
            if norm(p) in parts or any(near(p, q) >= 0.8 for q in parts):
                continue                      # a part heading
            if NUMERAL.match(p) and len(p) <= 12:
                continue                      # its numeral
        cur.append(p)
    if cur:
        (chapters[-1]["blocks"].extend([("p", t) for t in cur])
         if chapters else pre.extend(cur))
    return chapters, pre


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--first", type=int, default=6)
    ap.add_argument("--last", type=int, default=318)
    ap.add_argument("--contents-page", type=int, default=319)
    ap.add_argument("--out", default="public/books/novel/cement.fb2")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    pages = pdf_lines(a.pdf, a.first, a.last)
    lines = []
    for pg in pages:
        lines.extend(strip_furniture(pg))
    paras = [tidy(p) for p in paragraphs(lines)]
    paras = [p for p in paras if p]
    want = read_contents(a.pdf, a.contents_page)
    chapters, pre = split_chapters(paras, want)
    print("contents lists %d chapters in %d parts; the body gives %d cuts"
          % (len(want), len({w[0] for w in want}), len(chapters)))
    if pre:
        print("%d paragraph(s) before the first chapter, dropped as front matter"
              % len(pre))
    if len(want) != len(chapters):
        print("\n!! the two disagree — not writing. Compare the list below "
              "against the ОГЛАВЛЕНИЕ before trusting it.")

    words = sum(len(t.split()) for c in chapters for _k, t in c["blocks"])
    print("pages %d   lines %d   paragraphs %d   chapters %d   words %s"
          % (len(pages), len(lines), len(paras), len(chapters), format(words, ",")))
    print()
    for c in chapters:
        n = sum(len(t.split()) for _k, t in c["blocks"])
        print("   %-44s %3d paras  %6s words"
              % ((c["title"] or "(untitled)")[:44], len(c["blocks"]), format(n, ",")))

    if a.dry_run or len(want) != len(chapters):
        return
    fb2 = build_fb2("Цемент", "Гладков Ф.В.", chapters,
                    "Ф. Гладков, Собрание сочинений, т. 2: Цемент. "
                    "Ленинград: Прибой, 1926")
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(fb2)
    print("\nwrote %s" % a.out)


if __name__ == "__main__":
    main()
