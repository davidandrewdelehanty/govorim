#!/usr/bin/env python3
"""
regroup_fb2.py — rebuild an FB2 so its chapters match how a recording was split.

flatten_fb2.py handles the common case: the audio is one file per part, the
markup is one chapter per scene, so you collapse a nesting level. This handles
the awkward case — a LibriVox-style reading where the reader stopped wherever it
suited them, so one file covers chapters I and II, the next covers III and IV.
There is no level to collapse; you have to say which chapters belong together.

Groups are 1-based indices into the chapters the READER sees (what Auto-MFA's
app/fb2.py produces, which src/App.jsx mirrors):

    --groups "1-2,3-4,5,6-7"        ranges and singles, ascending
    --groups all                    keep every chapter separate (for --split only)

--split cuts one chapter in two at a phrase, for when a reader stopped
mid-chapter and resumed in the next file.

Output is built from the original XML elements, so paragraphs, verse lines and
poems survive intact. (Auto-MFA's extract_chapters returns text with paragraph
breaks already collapsed — fine for aligning audio, useless for rebuilding a
document, which is why this reads the tree itself.)

    python3 tools/regroup_fb2.py --in book.fb2 --out book-grouped.fb2 \
        --groups "1-2,3-4,5" --apply
"""
import argparse, importlib.util, os, re, sys
import xml.etree.ElementTree as ET
from pathlib import Path

FB2_NS = "http://www.gribuser.ru/xml/fictionbook/2.0"
XLINK_NS = "http://www.w3.org/1999/xlink"


def ln(e):
    return e.tag.split("}", 1)[-1]


def kids(e):
    return [c for c in e if ln(c) == "section"]


def load_splitter(automfa):
    for cand in filter(None, [automfa, os.path.expanduser("~/projects/Auto-MFA")]):
        p = os.path.join(os.path.expanduser(cand), "app", "fb2.py")
        if os.path.exists(p):
            spec = importlib.util.spec_from_file_location("automfa_fb2", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise SystemExit("Could not find Auto-MFA's app/fb2.py — pass --automfa. Grouping "
                     "against a different splitter than the reader uses would silently "
                     "produce the wrong chapters.")


def read_root(path):
    raw = open(path, "rb").read()
    m = re.match(rb'<\?xml[^>]*encoding=["\']([\w-]+)["\']', raw)
    enc = m.group(1).decode() if m else "utf-8"
    text = raw.decode(enc, errors="replace")
    return ET.fromstring(re.sub(r"^<\?xml[^>]*\?>", "", text, count=1).strip())


def title_of(sec):
    t = next((c for c in sec if ln(c) == "title"), None)
    if t is None:
        return ""
    return re.sub(r"\s+", " ", " ".join(x.strip() for x in t.itertext() if x.strip())).strip()


def leaf_sections(root):
    body = [e for e in root if ln(e) == "body" and e.get("name") not in ("notes", "comments")][0]
    out = []

    def walk(sec):
        k = kids(sec)
        if k:
            for c in k:
                walk(c)
        else:
            out.append(sec)

    for sec in kids(body):
        walk(sec)
    return out


def content_of(sec):
    """Everything under a leaf section except its own <title>."""
    return [c for c in sec if ln(c) != "title"]


def eltext(e):
    return re.sub(r"\s+", " ", " ".join(x.strip() for x in e.itertext() if x.strip())).strip()


def parse_groups(spec, total):
    if spec.strip().lower() in ("all", "each", "singles"):
        return [[i] for i in range(1, total + 1)]
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
    if sorted(flat) != flat or len(set(flat)) != len(flat):
        raise SystemExit("groups must be ascending and must not overlap")
    if flat and max(flat) > total:
        raise SystemExit("group references chapter %d but the FB2 has %d" % (max(flat), total))
    return groups


def apply_splits(chapters, specs):
    """Cut a chapter in two at a phrase, so it can pair with two recordings.

    chapters is a list of (title, [elements]); the cut lands on an element
    boundary, so no paragraph is ever torn in half.
    """
    for spec in specs:
        if ":" not in spec:
            raise SystemExit("--split wants N:TEXT, got %r" % spec)
        n, phrase = spec.split(":", 1)
        n = int(n.strip()); phrase = re.sub(r"\s+", " ", phrase.strip())
        if not (1 <= n <= len(chapters)):
            raise SystemExit("--split refers to chapter %d; there are %d" % (n, len(chapters)))
        title, els = chapters[n - 1]
        hits = [i for i, e in enumerate(els) if phrase in eltext(e)]
        if not hits:
            raise SystemExit("--split phrase not found in chapter %d: %r" % (n, phrase[:60]))
        if len(hits) > 1:
            raise SystemExit("--split phrase appears in %d elements of chapter %d; make it longer"
                             % (len(hits), n))
        cut = hits[0]
        if cut == 0:
            raise SystemExit("--split phrase is in the very first paragraph of chapter %d" % n)
        head = eltext(els[cut])
        second_title = head if 0 < len(head) <= 90 else (title + " (продолжение)").strip()
        chapters = (chapters[:n - 1] + [(title, els[:cut]), (second_title, els[cut:])]
                    + chapters[n:])
        print("split chapter %d (%s) before %r -> %d + %d elements; later chapters renumber"
              % (n, title[:24], phrase[:34], cut, len(els) - cut))
    return chapters


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    ap.add_argument("--groups", required=True,
                    help='Comma-separated N or N-M, ascending. Or "all" to keep every chapter.')
    ap.add_argument("--split", action="append", default=[], metavar="N:TEXT",
                    help="Split chapter N before the element containing TEXT. Applied before "
                         "grouping; renumbers everything after.")
    ap.add_argument("--automfa", default=None)
    ap.add_argument("--drop-tail", action="store_true",
                    help="discard chapters after the last group (FB2 is a collection)")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    root = read_root(args.src)
    leaves = leaf_sections(root)
    mod = load_splitter(args.automfa)
    n_reader = len(mod.extract_chapters(Path(args.src)))
    if len(leaves) != n_reader:
        raise SystemExit(
            "This FB2 has %d leaf sections but the reader splits it into %d chapters — they "
            "disagree, so group numbers would not mean what you think.\nUse a tool that "
            "understands this file's structure instead." % (len(leaves), n_reader))

    chapters = [(title_of(s), content_of(s)) for s in leaves]
    chapters = apply_splits(chapters, args.split)
    groups = parse_groups(args.groups, len(chapters))
    covered = max((i for g in groups for i in g), default=0)
    tail = [] if args.drop_tail else list(range(covered + 1, len(chapters) + 1))

    print("\nsource: %d chapters -> %d output chapters%s"
          % (n_reader, len(groups) + len(tail),
             "" if not tail else " (%d tail chapters kept)" % len(tail)))
    for n, g in enumerate(groups[:60], 1):
        names = [chapters[i - 1][0] for i in g]
        label = names[0] if len(names) == 1 else "%s–%s" % (names[0][:20], names[-1][:20])
        print("  %3d  ch %-9s %s" % (n, ",".join(str(i) for i in g), label[:56]))
    if len(groups) > 60:
        print("  ... %d more" % (len(groups) - 60))

    if not args.apply:
        print("\nList only — re-run with --apply to write %s" % args.dst)
        return

    ET.register_namespace("", FB2_NS)
    ET.register_namespace("xlink", XLINK_NS)
    out_root = ET.Element("{%s}FictionBook" % FB2_NS)
    desc = next((c for c in root if ln(c) == "description"), None)
    if desc is not None:
        out_root.append(desc)
    body = ET.SubElement(out_root, "{%s}body" % FB2_NS)

    def emit(indices):
        sec = ET.SubElement(body, "{%s}section" % FB2_NS)
        t = ET.SubElement(sec, "{%s}title" % FB2_NS)
        ET.SubElement(t, "{%s}p" % FB2_NS).text = chapters[indices[0] - 1][0]
        for pos, i in enumerate(indices):
            name, els = chapters[i - 1]
            # A merged chapter keeps the later headings, demoted to subtitles so
            # they still read on the page without becoming chapter breaks.
            if pos > 0 and name:
                ET.SubElement(sec, "{%s}subtitle" % FB2_NS).text = name
            for e in els:
                sec.append(e)

    for g in groups:
        emit(g)
    for i in tail:
        emit([i])
    for b in [c for c in root if ln(c) == "binary"]:
        out_root.append(b)
    ET.ElementTree(out_root).write(args.dst, encoding="utf-8", xml_declaration=True)
    print("\nWrote %s" % args.dst)


if __name__ == "__main__":
    main()
