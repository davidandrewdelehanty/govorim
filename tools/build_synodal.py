#!/usr/bin/env python3
"""Build the Synodal Bible entry: the five books of Moses and the four Gospels.

Two public-domain texts, verified before use: the Russian Synodal (1876) and
the King James (1611). Both come from one source with one schema, so their
book and chapter indices line up without any mapping guesswork.

Output:
  public/books/novel/bible-synodal.fb2   one <section> per chapter
  public/books/bible-kjv/NN-CC.json      verse number -> King James text

The FB2 puts ONE verse in each paragraph, led by its number and a space. That
is exactly what the reader looks for — it reads the leading digits off a
paragraph and fetches that verse's English — so the two cannot drift apart.
"""
import io, json, os, re, sys, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.abspath(os.path.join(ROOT, "..", "govorim-sources", "bible"))

# (index in the 66-book file, Russian name, canonical two-digit number)
BOOKS = [
    (0,  "Бытие",        "01"), (1,  "Исход",  "02"), (2, "Левит", "03"),
    (3,  "Числа",        "04"), (4,  "Второзаконие", "05"),
    (39, "Матфея",       "40"), (40, "Марка",  "41"), (41, "Луки",  "42"),
    (42, "Иоанна",       "43"),
]

def esc(s):
    return html.escape(str(s), quote=False)

def main():
    ru = json.load(io.open(os.path.join(SRC, "ru_synodal.json"), encoding="utf-8-sig"))
    en = json.load(io.open(os.path.join(SRC, "en_kjv.json"), encoding="utf-8-sig"))

    endir = os.path.join(ROOT, "public", "books", "bible-kjv")
    os.makedirs(endir, exist_ok=True)

    secs, chapters, verses, enfiles = [], 0, 0, 0
    for idx, name, no in BOOKS:
        rb, eb = ru[idx], en[idx]
        if len(rb["chapters"]) != len(eb["chapters"]):
            sys.exit("chapter count mismatch in %s" % name)
        for ci, rch in enumerate(rb["chapters"]):
            ech = eb["chapters"][ci]
            head = "%s %d" % (name, ci + 1)
            body = []
            for vi, v in enumerate(rch):
                t = re.sub(r"\s+", " ", str(v)).strip()
                if not t:
                    continue
                # "12 В начале…" — the number, a space, then the verse.
                body.append("<p>%d %s</p>" % (vi + 1, esc(t)))
                verses += 1
            if not body:
                continue
            secs.append("<section>\n<title><p>%s</p></title>\n%s\n</section>"
                        % (esc(head), "\n".join(body)))
            chapters += 1

            # English for the same chapter, keyed by verse number.
            emap = {}
            for vi, v in enumerate(ech):
                t = re.sub(r"\s+", " ", str(v)).strip()
                if t:
                    emap[str(vi + 1)] = t
            with io.open(os.path.join(endir, "%s-%02d.json" % (no, ci + 1)),
                         "w", encoding="utf-8") as f:
                json.dump(emap, f, ensure_ascii=False, separators=(",", ":"))
            enfiles += 1

    fb2 = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">\n'
           '<description><title-info>'
           '<book-title>Библия. Синодальный перевод</book-title>'
           '<author><last-name></last-name></author>'
           '</title-info></description>\n<body>\n'
           + "\n".join(secs) + "\n</body>\n</FictionBook>\n")
    out = os.path.join(ROOT, "public", "books", "novel", "bible-synodal.fb2")
    io.open(out, "w", encoding="utf-8").write(fb2)

    print("chapters: %d   verses: %d   english files: %d" % (chapters, verses, enfiles))
    print("fb2: %s (%.1f MB)" % (out, os.path.getsize(out) / 1e6))

if __name__ == "__main__":
    main()
