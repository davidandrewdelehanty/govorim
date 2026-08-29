#!/usr/bin/env python3
"""Find the publisher and scanner front matter readers are opening books on.

Thirty of the FB2s in this library begin with the apparatus of whoever
digitised them rather than with the book. Хамелеон opens, for an actual
reader, on five lines like these:

    Полное собрание сочинений и писем в тридцати томах
    Сочинения в восемнадцати томах
    М., "Наука", 1983
    Scan: Ershov V. G., 28.03.2006
    Read&Check: sad369 (06.05.2006)

and only then on the story. It comes in two shapes. Sometimes the apparatus is
a run of paragraphs at the top of the first real chapter; sometimes it is an
entire <section>, so the reader's first chapter contains no story at all.

    python3 tools/front_matter.py            # propose, and print for reading
    python3 tools/front_matter.py --write    # save the proposals to review

The proposals are a starting point, not an answer. A leading short paragraph
can just as easily be the author's own subtitle ("Из детских воспоминаний
моего приятеля"), a dedication, an epigraph, or the cast list a play opens on,
and none of those should go. Read the table, correct tools/front_matter.json by
hand, and only then apply it.
"""
import io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import BOOKS, INDEX, chapters

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "front_matter.json")

# Lines that are the digitiser talking, not the author.
JUNK = re.compile(r"""(?ix)
   ^(scan|ocr|read\W*check|spellcheck|вычитка|сканирование|распознавание)\b
 | полное\s+собрание\s+сочинений | собрание\s+сочинений | сочинения\s+в\s+\w+\s+томах
 | ^источник \b | ^книга: | ^оригинал\s+здесь | ^版
 | ^м\.\s*[,:"] | ^спб | ^л\.\s*[,:] | издательств | ^изд\b | типограф | гослитиздат
 | project\s+gutenberg | gutenberg\.org | royallib | ^lib\.ru | flibusta | www\. | https?:// | narod\.ru
 | электронн\w+\s+библиотек | публичная\s+электронная | товарный\s+знак
 | ^-{10,}$ | ^версия\s+\d | права\s+на\s+этот
""")
# Lines that look like front matter but belong to the book.
KEEP = re.compile(r"""(?ix)
   ^(действующие\s+лица|лица|посвящаю|содержание)\b
 | ^[IVXLC]{1,6}[.．]?$ | ^глава\b | ^действие\b | ^часть\b | ^явление\b
""")
NARRATIVE = 220          # a paragraph this long is the book talking


def looks_like_apparatus(t):
    return bool(JUNK.search(t)) and not KEEP.search(t)


def propose(chs):
    """(kind, n) — drop a whole section, or n paragraphs off the first chapter."""
    if not chs or not chs[0]:
        return None
    first = chs[0]
    # Shape one: the whole first section is apparatus and the book starts after.
    if (len(chs) > 1 and len(first) <= 10
            and not any(len(t) >= NARRATIVE for t in first)
            and any(looks_like_apparatus(t) for t in first)
            and sum(1 for t in first if KEEP.search(t)) == 0):
        return ("section", 1)
    # Shape two: a run of apparatus at the top of the first chapter. Stop at the
    # first thing that is the book — narrative, a chapter marker, a cast list.
    lead, seen = 0, False
    for t in first[:10]:
        if len(t) >= NARRATIVE or KEEP.search(t):
            break
        if looks_like_apparatus(t):
            seen = True
        lead += 1
    if not seen:
        return None
    # Trim back to the last apparatus line: an author's subtitle sitting under
    # the publisher's name stays with the book.
    while lead > 0 and not looks_like_apparatus(first[lead - 1]):
        lead -= 1
    return ("paragraphs", lead) if lead else None


def main():
    write = "--write" in sys.argv
    catalogue = json.load(io.open(INDEX, encoding="utf-8"))
    out = {}
    for e in catalogue:
        fn = e.get("filename")
        if not fn:
            continue
        p = os.path.join(BOOKS, fn)
        if not os.path.exists(p):
            continue
        chs = chapters(p)
        pr = propose(chs)
        if not pr:
            continue
        kind, n = pr
        first = chs[0]
        print("\n%-30s  %s  %s" % (e.get("title", "")[:30],
                                   "drop the whole first section" if kind == "section"
                                   else "drop %d leading paragraph(s)" % n,
                                   "[has English]" if e.get("parallelEn") else ""))
        shown = first if kind == "section" else first[:n + 1]
        for i, t in enumerate(shown[:8]):
            gone = (kind == "section") or i < n
            print("    %s %s" % ("cut " if gone else "KEEP", t[:84]))
        if kind == "section" and len(chs) > 1:
            print("    KEEP %s" % (chs[1][0][:84] if chs[1] else ""))
        out[fn] = {"title": e.get("title", ""), "kind": kind, "n": n,
                   "parallelEn": e.get("parallelEn") or None,
                   "chapters": len(chs),
                   "cut": [t[:120] for t in (first if kind == "section" else first[:n])]}
    print("\n%d book(s) proposed" % len(out))
    if write:
        io.open(OUT, "w", encoding="utf-8").write(
            json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
        print("wrote %s — read it and correct it before applying" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
