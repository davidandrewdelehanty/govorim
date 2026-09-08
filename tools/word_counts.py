#!/usr/bin/env python3
"""How long is each book? Writes `words` into every catalogue entry.

The reader can count its own words the moment a book is open — that is what
the reading record already does — but the library has to say how long a book
is BEFORE anyone opens it, and parsing a hundred and sixty FB2s to draw a list
is not a thing to do in a browser. So the count is made here, once, and
carried in the manifest.

Counted the way the reader counts (App.jsx `ruCount`): Russian words only, in
the chapter text the reader actually shows — no headings, no front matter it
drops, no romanisation or page furniture. tools/reader_chapters.py does the
cutting, so the number on the card is the number the open book agrees with.

    python3 tools/word_counts.py            # report, writes nothing
    python3 tools/word_counts.py --write    # update private/books/index.json
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reader_chapters as rc

MANIFEST = "private/books/index.json"
RU_WORD = re.compile(r"[А-Яа-яЁё][А-Яа-яЁё-]*")


def count_book(path, one_page=False):
    chs, _how = rc.reader_chapters(path)
    if one_page:
        # The reader keeps these whole (a poem whose stanza numbers are not
        # chapters), which changes the chaptering, never the words.
        text = "\n\n".join(c["text"] for c in chs)
        return len(RU_WORD.findall(text))
    return sum(len(RU_WORD.findall(c["text"])) for c in chs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--manifest", default=MANIFEST)
    a = ap.parse_args()

    man = json.load(open(a.manifest, encoding="utf-8"))
    changed = 0
    failed = []
    for b in man:
        fn = b.get("filename")
        if not fn:
            continue
        path = os.path.join("public/books", fn)
        if not os.path.exists(path):
            path = os.path.join("private/books", fn)
        if not os.path.exists(path):
            failed.append((b.get("slug"), "file missing"))
            continue
        try:
            n = count_book(path, bool(b.get("onePage")))
        except Exception as e:
            failed.append((b.get("slug"), str(e)[:60]))
            continue
        if not n:
            failed.append((b.get("slug"), "no Russian words"))
            continue
        if b.get("words") != n:
            changed += 1
        b["words"] = n

    total = sum(b.get("words") or 0 for b in man if b.get("public"))
    print("counted %d entries, %d changed" % (len(man) - len(failed), changed))
    print("public library: %s words" % format(total, ","))
    for slug, why in failed:
        print("  !! %-34s %s" % (slug, why))

    if a.write:
        with open(a.manifest, "w", encoding="utf-8", newline="\n") as f:
            json.dump(man, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("manifest written")


if __name__ == "__main__":
    main()
