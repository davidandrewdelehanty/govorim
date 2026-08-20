#!/usr/bin/env python3
"""
regroup_fb2.py — rebuild an FB2 so its chapters match how a recording was
actually split.

flatten_fb2.py handles the common case: the audio is one file per part, the
markup is one chapter per scene, so you collapse a whole nesting level. This
handles the awkward case: a LibriVox-style reading where the reader stopped
wherever it suited them, so one file covers chapters I and II, the next covers
III and IV, and so on. There is no level to collapse — you need to say which
chapters belong together.

Groups are 1-based indices into the chapters the READER sees (i.e. what
Auto-MFA's app/fb2.py produces, which src/App.jsx mirrors). Ranges and singles:

    --groups "1-2,3-4,5,6-7,8,9-10,11,12-13,14,15,16,17,18,19,20,21,22"

Chapters after the last group are kept as ordinary chapters unless you pass
--drop-tail (useful when the FB2 is a collection and only the first work has
audio).

    python3 tools/regroup_fb2.py --in book.fb2 --out book-grouped.fb2 \
        --groups "1-2,3-4,5" --apply

Always verify the result with the reader's own splitter before relying on it —
the count is the thing that has to match the recording count.
"""
import argparse, importlib.util, os, re, sys
import xml.etree.ElementTree as ET
from pathlib import Path

FB2_NS = "http://www.gribuser.ru/xml/fictionbook/2.0"
XLINK_NS = "http://www.w3.org/1999/xlink"


def load_splitter(automfa):
    for cand in filter(None, [automfa,
                              os.path.join(os.path.dirname(os.path.abspath(".")), "Auto-MFA"),
                              os.path.expanduser("~/projects/Auto-MFA")]):
        p = os.path.join(os.path.expanduser(cand), "app", "fb2.py")
        if os.path.exists(p):
            spec = importlib.util.spec_from_file_location("automfa_fb2", p)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            return m
    raise SystemExit("Could not find Auto-MFA's app/fb2.py — pass --automfa. "
                     "Grouping against a different splitter than the reader uses "
                     "would silently produce the wrong chapters.")


def parse_groups(spec, total):
    groups = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(\d+)\s*-\s*(\d+)$", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a > b:
                raise SystemExit("bad range %r" % part)
            groups.append(list(range(a, b + 1)))
        elif part.isdigit():
            groups.append([int(part)])
        else:
            raise SystemExit("bad group %r — use N or N-M, comma separated" % part)
    flat = [i for g in groups for i in g]
    if sorted(flat) != flat:
        raise SystemExit("groups must be in ascending order and must not overlap")
    if len(set(flat)) != len(flat):
        raise SystemExit("a chapter appears in more than one group")
    if flat and max(flat) > total:
        raise SystemExit("group references chapter %d but the FB2 has %d" % (max(flat), total))
    return groups


def apply_splits(chapters, specs):
    """Cut a chapter in two at a phrase, so it can pair with two recordings.

    A reader who stops mid-chapter and resumes in the next file leaves the text
    with no corresponding break. Rather than merge the audio, split the text at
    the exact words where the second file picks up.
    """
    for spec in specs:
        if ":" not in spec:
            raise SystemExit("--split wants N:TEXT, got %r" % spec)
        n, phrase = spec.split(":", 1)
        n = int(n.strip()); phrase = phrase.strip()
        if not (1 <= n <= len(chapters)):
            raise SystemExit("--split refers to chapter %d; there are %d" % (n, len(chapters)))
        text = chapters[n - 1].get("text") or ""
        # Match on collapsed whitespace so a line break inside the phrase doesn't defeat it.
        flat = re.sub(r"\s+", " ", text)
        pos = flat.find(phrase)
        if pos < 0:
            raise SystemExit("--split phrase not found in chapter %d: %r" % (n, phrase[:60]))
        if flat.find(phrase, pos + 1) >= 0:
            raise SystemExit("--split phrase appears more than once in chapter %d; make it longer" % n)
        # Walk the original text to the same word offset.
        words_before = len(flat[:pos].split())
        cut, seen = 0, 0
        for mm in re.finditer(r"\S+", text):
            if seen == words_before:
                cut = mm.start(); break
            seen += 1
        else:
            cut = len(text)
        title = roman_or_title(chapters[n - 1].get("title"))
        first = dict(chapters[n - 1]); first["text"] = text[:cut].rstrip()
        second = dict(chapters[n - 1]); second["text"] = text[cut:].lstrip()
        second["title"] = (title + " (продолжение)").strip()
        chapters = chapters[:n - 1] + [first, second] + chapters[n:]
        print("split chapter %d (%s) at %r -> %d + %d chars; everything after renumbers"
              % (n, title[:20], phrase[:34], len(first["text"]), len(second["text"])))
    return chapters


def roman_or_title(t):
    t = (t or "").strip().replace("\n", " ")
    return re.sub(r"\s+", " ", t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    ap.add_argument("--groups", required=True)
    ap.add_argument("--split", action="append", default=[], metavar="N:TEXT",
                    help="Split chapter N in two, immediately before the first occurrence "
                         "of TEXT. Use when one chapter was read across two files. Splits "
                         "are applied BEFORE grouping and renumber everything after them, "
                         "so run once without --groups to see the new numbering.")
    ap.add_argument("--automfa", default=None)
    ap.add_argument("--drop-tail", action="store_true",
                    help="discard chapters after the last group (FB2 is a collection)")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    m = load_splitter(args.automfa)
    chapters = m.extract_chapters(Path(args.src))
    chapters = apply_splits(chapters, args.split)
    groups = parse_groups(args.groups, len(chapters))
    covered = max((i for g in groups for i in g), default=0)
    tail = [] if args.drop_tail else list(range(covered + 1, len(chapters) + 1))

    print("source FB2 splits into %d chapters" % len(chapters))
    print("%d groups%s\n" % (len(groups), "" if not tail else " + %d tail chapters kept" % len(tail)))
    for n, g in enumerate(groups, 1):
        titles = [roman_or_title(chapters[i - 1].get("title")) for i in g]
        label = titles[0] if len(titles) == 1 else "%s–%s" % (titles[0], titles[-1])
        chars = sum(len(chapters[i - 1].get("text") or "") for i in g)
        print("  %2d  fb2 %-9s %-22s %d chars" % (n, ",".join(str(i) for i in g), label[:22], chars))
    if tail:
        print("  ... then %d more chapters unchanged (%s …)"
              % (len(tail), roman_or_title(chapters[tail[0] - 1].get("title"))[:30]))

    if not args.apply:
        print("\nList only — re-run with --apply to write %s" % args.dst)
        return

    ET.register_namespace("", FB2_NS)
    ET.register_namespace("xlink", XLINK_NS)
    raw = open(args.src, "rb").read()
    enc = re.match(rb'<\?xml[^>]*encoding=["\']([\w-]+)["\']', raw)
    text = raw.decode(enc.group(1).decode() if enc else "utf-8", errors="replace")
    root = ET.fromstring(re.sub(r"^<\?xml[^>]*\?>", "", text, count=1).strip())

    out_root = ET.Element("{%s}FictionBook" % FB2_NS)
    desc = next((c for c in root if c.tag.split("}", 1)[-1] == "description"), None)
    if desc is not None:
        out_root.append(desc)
    body = ET.SubElement(out_root, "{%s}body" % FB2_NS)

    def emit(indices):
        sec = ET.SubElement(body, "{%s}section" % FB2_NS)
        titles = [roman_or_title(chapters[i - 1].get("title")) for i in indices]
        label = titles[0] if len(titles) == 1 else "%s–%s" % (titles[0], titles[-1])
        t = ET.SubElement(sec, "{%s}title" % FB2_NS)
        ET.SubElement(t, "{%s}p" % FB2_NS).text = label
        for i in indices:
            for para in (chapters[i - 1].get("text") or "").split("\n"):
                para = para.strip()
                if para:
                    ET.SubElement(sec, "{%s}p" % FB2_NS).text = para

    for g in groups:
        emit(g)
    for i in tail:
        emit([i])
    for b in [c for c in root if c.tag.split("}", 1)[-1] == "binary"]:
        out_root.append(b)

    ET.ElementTree(out_root).write(args.dst, encoding="utf-8", xml_declaration=True)
    print("\nWrote %s" % args.dst)


if __name__ == "__main__":
    main()
