#!/usr/bin/env python3
"""
flatten_fb2.py — rewrite an FB2 so its chapters match the granularity of the
recording.

The problem this solves: some audiobooks are read at a coarser grain than the
book is marked up. Доктор Живаго is recorded as 17 части but its FB2 splits into
232 numbered chapters; Горе от ума is recorded as 4 acts but splits into 27
явления. Pairing audio to chapters is impossible until the two agree, and the
reader's own splitter is what decides — so the fix is to give it an FB2 whose
chapters ARE the acts (or the части).

This keeps every word. Nested sections are unwrapped in document order, and
<subtitle> markers become ordinary paragraphs so they still read on the page but
no longer trigger a chapter break.

    # each top-level section becomes one chapter
    python3 tools/flatten_fb2.py --in book.fb2 --out book-flat.fb2 --level 1

    # each second-level section becomes one chapter (parts inside books)
    python3 tools/flatten_fb2.py --in zhivago.fb2 --out zhivago-flat.fb2 --level 2

Verify the result with the same splitter the reader uses before you rely on it:

    python3 - <<'EOF'
    import importlib.util; from pathlib import Path
    s=importlib.util.spec_from_file_location("f","~/projects/Auto-MFA/app/fb2.py")
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
    print(len(m.extract_chapters(Path("book-flat.fb2"))))
    EOF
"""
import argparse, re, sys
import xml.etree.ElementTree as ET

FB2_NS = "http://www.gribuser.ru/xml/fictionbook/2.0"
XLINK_NS = "http://www.w3.org/1999/xlink"
# Content that carries text and should be preserved verbatim inside a chapter.
CONTENT_TAGS = {"p", "empty-line", "poem", "cite", "epigraph", "table",
                "image", "stanza", "v", "text-author"}


def ln(tag):
    return tag.split("}", 1)[-1]


def read(path):
    raw = open(path, "rb").read()
    m = re.match(rb'<\?xml[^>]*encoding=["\']([\w-]+)["\']', raw)
    enc = m.group(1).decode() if m else "utf-8"
    text = raw.decode(enc, errors="replace")
    return ET.fromstring(re.sub(r"^<\?xml[^>]*\?>", "", text, count=1).strip())


def title_of(section):
    t = next((c for c in section if ln(c.tag) == "title"), None)
    if t is None:
        return ""
    return " ".join(x.strip() for x in t.itertext() if x.strip())


def content_of(section, out):
    """Everything under `section` except its own <title>, in document order.

    Nested <section>s are unwrapped: their titles become bold-ish paragraphs so
    the structure still reads, and their content flows into the same chapter.
    """
    first_title_skipped = [False]

    def walk(el, depth):
        for child in el:
            name = ln(child.tag)
            if name == "title":
                if depth == 0 and not first_title_skipped[0]:
                    first_title_skipped[0] = True   # the chapter's own heading
                    continue
                txt = " ".join(x.strip() for x in child.itertext() if x.strip())
                if txt:
                    p = ET.SubElement(out, "{%s}p" % FB2_NS)
                    p.text = txt
                continue
            if name == "subtitle":
                # A subtitle is what the reader's splitter treats as a chapter
                # marker. Demote it to a paragraph: same words, no split.
                txt = " ".join(x.strip() for x in child.itertext() if x.strip())
                if txt:
                    p = ET.SubElement(out, "{%s}p" % FB2_NS)
                    p.text = txt
                continue
            if name == "section":
                walk(child, depth + 1)
                continue
            if name in CONTENT_TAGS:
                out.append(child)
    walk(section, 0)


def collect(body, level, keep):
    """Sections that should become chapters.

    A section at exactly `level` qualifies. A section shallower than `level`
    with no subsections qualifies too — otherwise a foreword sitting beside the
    numbered parts would be dropped silently.
    """
    picked = []

    def walk(el, depth):
        subs = [c for c in el if ln(c.tag) == "section"]
        if depth == level or not subs:
            picked.append(el)
            return
        for c in subs:
            walk(c, depth + 1)

    for sec in [c for c in body if ln(c.tag) == "section"]:
        walk(sec, 1)
    if keep:
        rx = re.compile(keep, re.I)
        picked = [s for s in picked if rx.search(title_of(s) or "")]
    return picked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    ap.add_argument("--level", type=int, default=1,
                    help="1 = each top-level section is a chapter, 2 = each second-level section")
    ap.add_argument("--keep", help="regex: only keep sections whose title matches")
    ap.add_argument("--apply", action="store_true", help="write the file (otherwise list only)")
    args = ap.parse_args()

    ET.register_namespace("", FB2_NS)
    ET.register_namespace("xlink", XLINK_NS)
    root = read(args.src)

    bodies = [e for e in root if ln(e.tag) == "body" and e.get("name") not in ("notes", "comments")]
    if not bodies:
        raise SystemExit("no main <body> in this FB2")
    picked = []
    for b in bodies:
        picked += collect(b, args.level, args.keep)
    if not picked:
        raise SystemExit("level %d matched no sections" % args.level)

    print("%d chapters after flattening at level %d:" % (len(picked), args.level))
    for i, s in enumerate(picked, 1):
        if i <= 4 or i > len(picked) - 2:
            print("  %3d  %s" % (i, (title_of(s) or "(untitled)")[:64]))
        elif i == 5:
            print("   …")

    if not args.apply:
        print("\nList only — re-run with --apply to write %s" % args.dst)
        return

    out_root = ET.Element("{%s}FictionBook" % FB2_NS)
    desc = next((c for c in root if ln(c.tag) == "description"), None)
    if desc is not None:
        out_root.append(desc)
    out_body = ET.SubElement(out_root, "{%s}body" % FB2_NS)
    # The body may carry the work's own title ("Евгений Онегин") outside any
    # section. Rebuilding without it lost those words.
    for src_body in bodies:
        bt = next((c for c in src_body if ln(c.tag) == "title"), None)
        if bt is not None:
            out_body.append(bt)
            break
    for s in picked:
        sec = ET.SubElement(out_body, "{%s}section" % FB2_NS)
        t = ET.SubElement(sec, "{%s}title" % FB2_NS)
        tp = ET.SubElement(t, "{%s}p" % FB2_NS)
        tp.text = title_of(s) or ""
        content_of(s, sec)
    # Footnote and comment bodies are content, not structure. This rebuilt the
    # file from the main body alone and silently dropped them: Евгений Онегин
    # lost its whole <body name="notes"> — 202 words translating the French,
    # Italian and Latin — and the loss showed up only as a word count that did
    # not add up. Carry every other body through untouched.
    for b in [c for c in root if ln(c.tag) == "body" and c.get("name") in ("notes", "comments")]:
        out_root.append(b)
    # Binary payloads (cover images) are referenced from <description>; keep them
    # so the file stays a valid, self-contained FB2.
    for b in [c for c in root if ln(c.tag) == "binary"]:
        out_root.append(b)

    ET.ElementTree(out_root).write(args.dst, encoding="utf-8", xml_declaration=True)
    print("\nWrote %s" % args.dst)


if __name__ == "__main__":
    main()
