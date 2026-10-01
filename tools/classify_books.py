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
VERSE_SPREAD = 1.5        # interquartile line length over the median
VERSE_LONG_SHARE = 0.15   # share of lines over 14 words

def local(e):
    return e.tag.split("}")[-1]

def body_of(root):
    bs = [b for b in root if local(b) == "body" and not b.get("name")]
    return bs[0] if bs else None

# A speech in a printed play opens with its speaker: "Медведенко. Отчего вы
# всегда ходите в чёрном?" One such line proves nothing — Chekhov's prose is
# full of "Иван Иванович." — so it takes a third of the paragraphs. It also
# takes a work of some size: a letter that opens "Любезнейший Фёдор
# Михайлович." and runs to two hundred words matched this test perfectly, and
# eleven of Turgenev's letters to Dostoevsky were filed as plays.
SPEAKER = re.compile(r"^[А-ЯЁ][А-Яа-яЁё\s\-]{1,28}\.\s+[А-ЯЁ«—]")
PLAY_MIN_WORDS, PLAY_MIN_PARAS = 1500, 8
# Wikisource's export gives a poem no verse markup: every line is a <p> like
# any other. What marks it is the shape — «И ветер, и дождик, и мгла» is seven
# words, and a paragraph of prose in these books runs to forty. So verse is
# read off the median line rather than off the tags, which is why the first
# run put six hundred lyrics on the Short Stories shelf.
VERSE_MEDIAN_WORDS = 10
# Short lines alone are not enough: a story told mostly in dialogue has them
# too, and Танька — two and a half thousand words of prose — came out as a
# poem. What separates them is the end of the line. A line of verse stops
# where the metre stops, most often on a comma or on nothing at all; a
# paragraph of prose stops on a full stop. Half the lines ending open is a
# poem; a tenth is a conversation.
VERSE_OPEN_ENDS = 0.4
ENDS_SENTENCE = re.compile(r"[.!?…:;]['\"»)]*$")

def look(path):
    root = ET.parse(path).getroot()
    body = body_of(root)
    if body is None:
        return None
    verse = prose = speech = 0
    lens = []
    for el in body.iter():
        t = local(el)
        if t == "v":
            verse += 1
            lens.append(len("".join(el.itertext()).split()))
        elif t == "p":
            prose += 1
            txt = re.sub(r"\s+", " ", "".join(el.itertext())).strip()
            lens.append(len(txt.split()))
            if SPEAKER.match(txt):
                speech += 1
    open_end = 0
    for el in body.iter():
        if local(el) in ("p", "v"):
            txt = re.sub(r"\s+", " ", "".join(el.itertext())).strip()
            if txt and not ENDS_SENTENCE.search(txt):
                open_end += 1
    lens = sorted(x for x in lens if x)
    lines = verse + prose
    # Verse keeps its lines to a length. Prose set out like verse — a mock
    # advertisement, a joke dictionary, a list of aphorisms — does not: its
    # entries run from two words to thirty. Chekhov has no verse at all and
    # 35 of his squibs were shelved as poems on short lines and open ends
    # alone, so the shape of the lines decides too. Measured as the
    # interquartile spread over the median (scale-free, so a four-word line
    # and an eight-word line are judged the same way) and the share of lines
    # long enough that no metre would hold them.
    spread = long_share = 0
    if len(lens) >= 4:
        med = lens[len(lens) // 2]
        q1 = lens[len(lens) // 4]
        q3 = lens[(3 * len(lens)) // 4]
        spread = (q3 - q1) / float(med) if med else 0
        long_share = sum(1 for x in lens if x > 14) / float(len(lens))
    return {
        "tagged_verse": verse / lines if lines else 0,
        "median_line": lens[len(lens) // 2] if lens else 0,
        "speech": speech / prose if prose else 0,
        "open_end": open_end / lines if lines else 0,
        "paras": lines,
        "spread": spread,
        "long_share": long_share,
    }

def decide(shape, words):
    if shape and shape["speech"] >= 0.33 and words >= PLAY_MIN_WORDS \
            and shape["paras"] >= PLAY_MIN_PARAS:
        return "Plays", True
    if shape and (shape["tagged_verse"] >= 0.6 or
                  (shape["median_line"] <= VERSE_MEDIAN_WORDS and shape["paras"] >= 4
                   and shape["open_end"] >= VERSE_OPEN_ENDS
                   and shape["spread"] <= VERSE_SPREAD
                   and shape["long_share"] <= VERSE_LONG_SHARE)):
        return "Poetry", False
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
    ap.add_argument("--imported-only", action="store_true",
                    help="only books this repo imported from Wikisource")
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
        if a.imported_only and not str(b.get("_note") or "").startswith("Text from Russian Wikisource"):
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
        print("%-40s %-14s -> %-14s %7s w   line %3d  open %.2f"
              % (b.get("slug")[:40], b.get("category"), cat, b.get("words"),
                 shape["median_line"] if shape else 0, shape["open_end"] if shape else 0))
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
