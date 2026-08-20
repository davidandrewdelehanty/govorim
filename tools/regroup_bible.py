#!/usr/bin/env python3
"""
regroup_bible.py — rebuild the Bible FB2 so one chapter = one Bible chapter.

The NRP FB2 nests as Testament > group > book > chapter > heading-section, and
the reader's splitter descends to the heading sections — so "Каин и Авель" and
"Потомки Каина" become two chapters when they are both Genesis 4. That gave 1952
chapters against 1189 recordings, and everything after Genesis 3 was mispaired.

The book level carries the truth: each book section has exactly as many child
sections as the book has chapters (Бытие 50, Исход 40, …). Two exceptions, both
structural rather than special-cased guesses:

  * Псалмы is subdivided into the Psalter's five books, so its chapters sit one
    level deeper — 5 groups of psalms, 150 in total.
  * Откровение's chapters are promoted to the book level, appearing as bare
    "Глава 1".."Глава 22" sections beside the other books.

Heading sections are emitted as <subtitle> rather than <p>, so they still read
as headings — and the reader's chapter splitter leaves them alone, because it
only breaks on subtitles that look like roman-numeral chapter markers.

    python3 tools/regroup_bible.py --in "Новый Русский Перевод Библии.fb2" \
        --out bible-chapters.fb2 --apply
"""
import argparse, re
import xml.etree.ElementTree as ET

FB2_NS = "http://www.gribuser.ru/xml/fictionbook/2.0"
XLINK_NS = "http://www.w3.org/1999/xlink"
KEEP = {"p", "empty-line", "poem", "cite", "epigraph", "table", "image",
        "stanza", "v", "text-author"}
# Short names for chapter titles, in canon order.
BOOKS = ["Бытие","Исход","Левит","Числа","Второзаконие","Иисус Навин","Судей","Руфь",
         "1 Царств","2 Царств","3 Царств","4 Царств","1 Паралипоменон","2 Паралипоменон",
         "Ездра","Неемия","Есфирь","Иов","Псалтирь","Притчи","Екклесиаст","Песнь Песней",
         "Исаия","Иеремия","Плач Иеремии","Иезекииль","Даниил","Осия","Иоиль","Амос",
         "Авдий","Иона","Михей","Наум","Аввакум","Софония","Аггей","Захария","Малахия",
         "От Матфея","От Марка","От Луки","От Иоанна","Деяния","Римлянам","1 Коринфянам",
         "2 Коринфянам","Галатам","Ефесянам","Филиппийцам","Колоссянам","1 Фессалоникийцам",
         "2 Фессалоникийцам","1 Тимофею","2 Тимофею","Титу","Филимону","Евреям","Иакова",
         "1 Петра","2 Петра","1 Иоанна","2 Иоанна","3 Иоанна","Иуды","Откровение"]


def ln(e):
    return e.tag.split("}", 1)[-1]


def kids(e):
    return [c for c in e if ln(c) == "section"]


def title_of(e):
    t = next((c for c in e if ln(c) == "title"), None)
    if t is None:
        return ""
    return " ".join(x.strip() for x in t.itertext() if x.strip())


def read(path):
    raw = open(path, "rb").read()
    m = re.match(rb'<\?xml[^>]*encoding=["\']([\w-]+)["\']', raw)
    enc = m.group(1).decode() if m else "utf-8"
    text = raw.decode(enc, errors="replace")
    return ET.fromstring(re.sub(r"^<\?xml[^>]*\?>", "", text, count=1).strip())


def emit_content(src, out, depth=0):
    """Flatten src's descendants into out, keeping headings as subtitles."""
    for child in src:
        name = ln(child)
        if name == "title":
            if depth == 0:
                continue                       # the chapter's own heading
            txt = " ".join(x.strip() for x in child.itertext() if x.strip())
            if txt:
                ET.SubElement(out, "{%s}subtitle" % FB2_NS).text = txt
        elif name == "subtitle":
            txt = " ".join(x.strip() for x in child.itertext() if x.strip())
            if txt:
                ET.SubElement(out, "{%s}subtitle" % FB2_NS).text = txt
        elif name == "section":
            emit_content(child, out, depth + 1)
        elif name in KEEP:
            out.append(child)


def collect_chapters(body):
    """(book_index, chapter_number, section) for every Bible chapter, in order."""
    level = kids(body)
    for _ in range(2):                          # Testament > group > book
        level = [c for s in level for c in kids(s)]
    chapters, bi, revelation_seen = [], 0, False
    for sec in level:
        t = title_of(sec).strip()
        if re.match(r"^Глава\s*\d+$", t):
            # Revelation's chapters sit at book level rather than inside a book.
            if not revelation_seen:
                revelation_seen = True
                bi += 1
            n = int(re.match(r"^Глава\s*(\d+)$", t).group(1))
            chapters.append((bi, n, sec))
            continue
        bi += 1
        if t == "Псалмы":
            n = 0
            for part in kids(sec):              # the Psalter's five books
                for ps in kids(part):
                    n += 1
                    chapters.append((bi, n, ps))
        else:
            for n, chap in enumerate(kids(sec), 1):
                chapters.append((bi, n, chap))
    return chapters


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    ap.add_argument("--expect", type=int, default=1189)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    ET.register_namespace("", FB2_NS)
    ET.register_namespace("xlink", XLINK_NS)
    root = read(args.src)
    body = [e for e in root if ln(e) == "body" and e.get("name") not in ("notes", "comments")][0]
    chapters = collect_chapters(body)

    per = {}
    for bi, n, _ in chapters:
        per[bi] = max(per.get(bi, 0), n)
    print("books: %d   chapters: %d (expected %d)" % (len(per), len(chapters), args.expect))
    print("chapters per book:", [per[k] for k in sorted(per)])
    if len(chapters) != args.expect:
        raise SystemExit("chapter count does not match the recordings — refusing to write")

    if not args.apply:
        print("\nList only — re-run with --apply to write %s" % args.dst)
        return

    out_root = ET.Element("{%s}FictionBook" % FB2_NS)
    desc = next((c for c in root if ln(c) == "description"), None)
    if desc is not None:
        out_root.append(desc)
    out_body = ET.SubElement(out_root, "{%s}body" % FB2_NS)
    for bi, n, sec in chapters:
        s = ET.SubElement(out_body, "{%s}section" % FB2_NS)
        t = ET.SubElement(s, "{%s}title" % FB2_NS)
        book = BOOKS[bi - 1] if bi - 1 < len(BOOKS) else "Книга %d" % bi
        ET.SubElement(t, "{%s}p" % FB2_NS).text = "%s %d" % (book, n)
        emit_content(sec, s)
    for b in [c for c in root if ln(c) == "binary"]:
        out_root.append(b)
    ET.ElementTree(out_root).write(args.dst, encoding="utf-8", xml_declaration=True)
    print("\nWrote %s" % args.dst)


if __name__ == "__main__":
    main()
