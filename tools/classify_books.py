#!/usr/bin/env python3
"""Put each imported book on the right shelf, from the book itself.

The import list has to name a category per row, and at one row it can be
judged by hand. At six hundred it cannot, so the list carries a placeholder
and this reads the FB2 afterwards and decides: verse by how the text is marked
up, a play by how its paragraphs open, and prose by its length.

    python3 tools/classify_books.py --author Пушкин --dry-run
    python3 tools/classify_books.py --author Пушкин --author Бунин

Only entries whose category is still the placeholder are touched, so a shelf
set by hand is never overruled. Plays are reported as well as set, because
that is the judgement most worth a second pair of eyes — it also switches on
`"play": true`, which is what makes the reader lay speeches out as a script.
"""
import argparse
import io
import json
import re
import xml.etree.ElementTree as ET

MANIFEST = "private/books/index.json"
NOVEL = 50000      # words. Анна Каренина is 350k, Ася is 22k, Тоска is 1.2k
NOVELLA = 15000
PLACEHOLDER = {"Short Stories", "Novels & Stories", ""}

def local(e):
    return e.tag.split("}")[-1]

def body_of(root):
    bs = [b for b in root if local(b) == "body" and not b.get("name")]
    return bs[0] if bs else None

# A speech in a printed play opens with its speaker: "Медведенко. Отчего вы
# всегда ходите в чёрном?" One such line proves nothing — Chekhov's prose is
# full of "Иван Иванович." — so it takes a third of the paragraphs.
SPEAKER = re.compile(r"^[А-ЯЁ][А-Яа-яЁё\s\-]{1,28}\.\s+[А-ЯЁ«—]")

def look(path):
    root = ET.parse(path).getroot()
    body = body_of(root)
    if body is None:
        return None
    verse = prose = speech = 0
    for el in body.iter():
        t = local(el)
        if t == "v":
            verse += 1
        elif t == "p":
            prose += 1
            txt = re.sub(r"\s+", " ", "".join(el.itertext())).strip()
            if SPEAKER.match(txt):
                speech += 1
    lines = verse + prose
    return {
        "verse": verse / lines if lines else 0,
        "speech": speech / prose if prose else 0,
    }

def decide(shape, words):
    if shape and shape["verse"] >= 0.6:
        return "Poetry", False
    if shape and shape["speech"] >= 0.33:
        return "Plays", True
    if words >= NOVEL:
        return "Novels", False
    if words >= NOVELLA:
        return "Novellas", False
    return "Short Stories", False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--author", action="append", default=[])
    ap.add_argument("--slug", action="append", default=[])
    ap.add_argument("--manifest", default=MANIFEST)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="also re-shelve books whose category was set by hand")
    a = ap.parse_args()
    if not a.author and not a.slug:
        ap.error("give --author or --slug")

    idx = json.load(io.open(a.manifest, encoding="utf-8"))
    books = idx["books"] if isinstance(idx, dict) and "books" in idx else idx
    moved, plays, same = 0, [], 0
    for b in books:
        if not isinstance(b, dict) or not b.get("filename"):
            continue
        if not (any(s in str(b.get("author") or "") for s in a.author) or b.get("slug") in a.slug):
            continue
        if not a.force and b.get("category") not in PLACEHOLDER:
            continue
        try:
            shape = look("public/books/" + b["filename"])
        except Exception as e:
            print("   unreadable  %-34s %s" % (b.get("slug"), str(e)[:50]))
            continue
        cat, is_play = decide(shape, b.get("words") or 0)
        if cat == b.get("category") and bool(b.get("play")) == is_play:
            same += 1
            continue
        print("%-34s %-14s -> %-14s %6s w   verse %.2f  speech %.2f"
              % (b.get("slug"), b.get("category"), cat, b.get("words"),
                 shape["verse"] if shape else 0, shape["speech"] if shape else 0))
        if is_play:
            plays.append(b.get("slug"))
        if not a.dry_run:
            b["category"] = cat
            if is_play:
                b["play"] = True
            elif b.get("play"):
                del b["play"]
        moved += 1

    if not a.dry_run and moved:
        io.open(a.manifest, "w", encoding="utf-8").write(
            json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
    print("\n%d re-shelved%s, %d already right" % (moved, " (dry run)" if a.dry_run else "", same))
    if plays:
        print("read as plays — worth checking: %s" % ", ".join(plays))

if __name__ == "__main__":
    main()
