#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""split_fb2.py — turn <subtitle> chapter markers into real <section> chapters.

The mirror image of flatten_fb2.py. Some FB2s mark a part as one <section> and
its chapters only as <subtitle> lines inside it. The reader's splitter makes a
chapter per leaf <section>, so Анна Каренина became 8 chapters against a video
map of 239, and no timing could be attached to anything.

Each subtitle becomes a child section titled by that subtitle, holding the
content up to the next one. Sections with no subtitles are left exactly as they
are — Бесы's Приложение stays one chapter, which is what it is.

NOTHING IS REWRITTEN OR DROPPED. Every element is moved, never recreated, and
the script refuses to write unless the word count and paragraph count of the
result match the input exactly.

    python3 tools/split_fb2.py --in public/books/novel/anna-karenina.fb2 --check
    python3 tools/split_fb2.py --in public/books/novel/anna-karenina.fb2 --write
"""
import argparse, io, os, re, shutil, sys
import xml.etree.ElementTree as ET

FB2_NS = "http://www.gribuser.ru/xml/fictionbook/2.0"


def sn(t): return t.split("}", 1)[-1]


def read(path):
    raw = open(path, "rb").read()
    m = re.match(rb"<\?xml[^>]*encoding=[\"']([\w-]+)[\"']", raw)
    enc = m.group(1).decode() if m else "utf-8"
    text = raw.decode(enc, errors="replace")
    return ET.fromstring(re.sub(r"^<\?xml[^>]*\?>", "", text, count=1).strip()), enc


def words(el):
    return len(" ".join(x for x in el.itertext()).split())


def paras(el):
    """Body paragraphs — those NOT inside a <title>.

    A converted subtitle becomes a <p> inside its new chapter's <title>, so the
    raw <p> count rises by exactly one per chapter created. That is the edit
    working, not content appearing, and counting title paragraphs here made the
    safety check fire on a correct result. Body paragraphs must not move.
    """
    inside = {id(t) for el2 in el.iter() if sn(el2.tag) == "title" for t in el2.iter()}
    return sum(1 for c in el.iter() if sn(c.tag) == "p" and id(c) not in inside)


def subtitles(el):
    return sum(1 for c in el.iter() if sn(c.tag) == "subtitle")


def split_section(sec, ns):
    """Replace a section's subtitle-delimited body with child sections."""
    kids = list(sec)
    idx = [i for i, c in enumerate(kids) if sn(c.tag) == "subtitle"]
    if not idx:
        return 0
    title_el = next((c for c in kids if sn(c.tag) == "title"), None)
    keep = [c for c in kids[:idx[0]]]          # title and anything before chapter one
    made = []
    bounds = idx + [len(kids)]
    for a, b in zip(bounds, bounds[1:]):
        sub = kids[a]
        child = ET.Element(ns + "section")
        t = ET.SubElement(child, ns + "title")
        p = ET.SubElement(t, ns + "p")
        # Move the subtitle's own content into the title, keeping any markup.
        p.text = sub.text
        for g in list(sub):
            p.append(g)
        p.tail = None
        for c in kids[a + 1:b]:
            child.append(c)
        made.append(child)
    for c in list(sec):
        sec.remove(c)
    for c in keep:
        sec.append(c)
    for c in made:
        sec.append(c)
    return len(made)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out")
    ap.add_argument("--write", action="store_true", help="replace the input, keeping a .bak")
    ap.add_argument("--check", action="store_true", help="report only")
    args = ap.parse_args()

    root, enc = read(args.src)
    ns = "{%s}" % FB2_NS if root.tag.startswith("{") else ""
    before_w, before_p, before_s = words(root), paras(root), subtitles(root)

    bodies = [el for el in root.iter() if sn(el.tag) == "body"
              and el.get("name") not in ("notes", "comments")]
    total = 0
    for b in bodies:
        for sec in [c for c in b if sn(c.tag) == "section"]:
            total += split_section(sec, ns)

    # Count what the reader's splitter would now see: leaf sections with text.
    leaves = 0
    def walk(sec):
        nonlocal leaves
        subs = [c for c in sec if sn(c.tag) == "section"]
        if subs:
            for c in subs: walk(c)
            return
        if words(sec) > 0: leaves += 1
    for b in bodies:
        for sec in [c for c in b if sn(c.tag) == "section"]: walk(sec)

    after_w, after_p, after_s = words(root), paras(root), subtitles(root)
    print("%s\n  chapters created from subtitles: %d\n  chapters the reader will now see: %d"
          % (args.src, total, leaves))
    print("  words %d -> %d   body paragraphs %d -> %d   subtitles %d -> %d"
          % (before_w, after_w, before_p, after_p, before_s, after_s))
    if before_w != after_w or before_p != after_p or after_s != before_s - total:
        print("  REFUSING TO WRITE: content changed.", file=sys.stderr)
        return 1
    if args.check or (not args.write and not args.out):
        print("  (check only — nothing written)")
        return 0

    ET.register_namespace("", FB2_NS)
    out = args.out or args.src
    if args.write and not args.out:
        bak = args.src + ".bak-presplit"
        if not os.path.exists(bak):
            shutil.copyfile(args.src, bak)
            print("  backup: %s" % bak)
    data = ET.tostring(root, encoding="unicode")
    io.open(out, "w", encoding="utf-8").write('<?xml version="1.0" encoding="utf-8"?>\n' + data)
    print("  wrote %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
