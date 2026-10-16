#!/usr/bin/env python3
"""English beside a Russian book, chapter against chapter — no alignment.

The reader shows the two texts as two columns that each flow at their own
length (flowEn in App.jsx), so nothing is gained by pairing paragraphs: the
English for a chapter only has to be the whole chapter, in order. This writes
it that way. Input is the English already cut into the book's chapters, as
tools/translations/en/<slug>.groups.json — a list with one entry per reader
chapter, each a list of English paragraphs. Each chapter is written as
public/books/<outdir>/NN.json = {"0": "para\\n\\npara\\n\\n…"}; the reader
splits on the blank lines.

    python3 tools/parallel_en_flow.py chto-delat chto-delat-en
"""
import io, json, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from reader_chapters import reader_chapters

BOOKS = "public/books"


def main():
    slug, outdir = sys.argv[1], sys.argv[2]
    idx = json.load(io.open("private/books/index.json", encoding="utf-8"))
    book = next(b for b in idx if b.get("slug") == slug)
    chs, _ = reader_chapters(os.path.join(BOOKS, book["filename"]))
    groups = json.load(io.open("tools/translations/en/%s.groups.json" % slug, encoding="utf-8"))
    if len(groups) != len(chs):
        sys.exit("%d English chapters for %d Russian ones — fix the grouping first" % (len(groups), len(chs)))
    d = os.path.join(BOOKS, outdir)
    os.makedirs(d, exist_ok=True)
    for i, (c, g) in enumerate(zip(chs, groups), 1):
        paras = [p.replace("⁠", "").strip() for p in g if p.strip()]
        io.open(os.path.join(d, "%02d.json" % i), "w", encoding="utf-8").write(
            json.dumps({"0": "\n\n".join(paras)} if paras else {}, ensure_ascii=False))
        print("  %02d %-48s ru %4d paras   en %4d paras" % (i, c["heading"][:48], len(c["paras"]), len(paras)))


if __name__ == "__main__":
    main()
