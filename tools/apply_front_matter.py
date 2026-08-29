#!/usr/bin/env python3
"""Cut the digitiser's apparatus out of the FB2s, per tools/front_matter.json.

tools/front_matter.py proposes; that JSON is the reviewed decision; this
applies it. Two shapes: a whole opening <section> that holds no book at all,
or a run of paragraphs at the top of the first chapter.

    python3 tools/apply_front_matter.py            # say what would change
    python3 tools/apply_front_matter.py --apply

The edit is made on the raw text at byte offsets rather than by re-serialising
the XML, because half these files are windows-1251 and every one of them has
its own idea of namespace prefixes and whitespace; a round trip through a
parser would rewrite the whole file to fix five lines. Each file is re-read
and re-parsed afterwards and the result checked — same chapter count, or one
fewer for a section drop; exactly the expected paragraphs gone; the first
paragraph now the one the review said it should be. A file that fails any of
those is restored and reported, never left half-edited.
"""
import io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import BOOKS, chapters

PLAN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "front_matter.json")
TAG = re.compile(r"<(/?)([A-Za-z][\w:.-]*)((?:\"[^\"]*\"|'[^']*'|[^>\"'])*?)(/?)>")
PARA = ("p", "v", "subtitle")


def read(path):
    raw = io.open(path, "rb").read()
    m = re.match(rb"<\?xml[^>]*encoding=[\"']([\w-]+)", raw[:200])
    enc = m.group(1).decode("ascii", "ignore") if m else "utf-8"
    for e in (enc, "utf-8", "cp1251"):
        try:
            return raw.decode(e), e
        except (UnicodeDecodeError, LookupError):
            continue
    return None, None


def spans(src):
    """Offsets of the chapter the book opens on, and of its paragraphs.

    Not simply the first <section>: some of these files wrap everything in an
    outer section, so the chapter a reader actually opens on is the first
    section that holds no sections of its own. Same rule the scanner's FB2
    reader follows.
    """
    stack = []
    sections = []           # [start, end, had_child]
    open_secs = []
    paras = []              # [start, end, section_index]
    in_title = 0
    for m in TAG.finditer(src):
        closing, name, selfclose = m.group(1), m.group(2).split(":")[-1], m.group(4)
        if selfclose:
            continue
        if not closing:
            stack.append((name, m.start()))
            if name == "section":
                if open_secs:
                    sections[open_secs[-1]][2] = True
                sections.append([m.start(), None, False])
                open_secs.append(len(sections) - 1)
            elif name == "title":
                in_title += 1
            elif name in PARA and open_secs and not in_title:
                paras.append([m.start(), None, open_secs[-1]])
        else:
            while stack and stack[-1][0] != name:
                stack.pop()
            if not stack:
                continue
            opened = stack.pop()
            if name == "title":
                in_title = max(0, in_title - 1)
            elif name == "section" and open_secs:
                sections[open_secs.pop()][1] = m.end()
            elif name in PARA and paras and paras[-1][1] is None \
                    and paras[-1][0] == opened[1]:
                paras[-1][1] = m.end()
    # These files open with a couple of stub sections — an empty-line, a blank
    # paragraph, a title and nothing else — which the reader drops. The chapter
    # a reader sees is the first leaf section with any text in it at all.
    def body_text(a, b):
        return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", src[a:b])).strip()

    leaf = None
    for i, sc in enumerate(sections):
        if sc[2] or sc[1] is None:
            continue
        if any(body_text(a, b) for a, b, si in paras if si == i and b is not None):
            leaf = i
            break
    if leaf is None:
        return None, []
    sec = (sections[leaf][0], sections[leaf][1])
    mine = [[a, b] for a, b, si in paras if si == leaf and b is not None
            and body_text(a, b)]
    return sec, mine


def main():
    apply = "--apply" in sys.argv
    plan = json.load(io.open(PLAN, encoding="utf-8"))
    ok = failed = 0
    for fn in sorted(plan):
        v = plan[fn]
        path = os.path.join(BOOKS, fn)
        if not os.path.exists(path):
            print("  MISSING  %s" % fn)
            continue
        before = chapters(path)
        src, enc = read(path)
        if src is None or not before:
            print("  UNREADABLE %s" % v["title"])
            continue
        # Already done. Without this a second run would cut the same count of
        # paragraphs again, this time out of the book itself.
        if v.get("keeps_next") and before[0] and \
                before[0][0][:60] == v["keeps_next"][:60]:
            print("  already cut  %s" % v["title"][:28])
            continue
        sec, paras = spans(src)
        cut = v["cut"]
        if cut == "section":
            if not sec:
                print("  NO SECTION FOUND  %s" % v["title"])
                failed += 1
                continue
            kill = [tuple(sec)]
            want_chs, want_paras = len(before) - 1, None
        else:
            if max(cut) >= len(paras):
                print("  ONLY %d PARAGRAPHS FOUND  %s" % (len(paras), v["title"]))
                failed += 1
                continue
            kill = [tuple(paras[i]) for i in cut]
            want_chs, want_paras = len(before), len(before[0]) - len(cut)

        out = src
        for s, e in sorted(kill, reverse=True):
            out = out[:s] + out[e:]

        if not apply:
            print("  would cut %-2d from %-28s (%s)"
                  % (len(kill), v["title"][:28], "whole section" if cut == "section" else "paragraphs"))
            ok += 1
            continue

        original = io.open(path, "rb").read()
        io.open(path, "wb").write(out.encode(enc))
        after = chapters(path)
        good = bool(after) and len(after) == want_chs
        if good and want_paras is not None:
            good = len(after[0]) == want_paras
        if good and v.get("keeps_next"):
            good = after[0] and after[0][0][:60] == v["keeps_next"][:60]
        if good:
            print("  cut %-2d  %-28s -> now opens: %s"
                  % (len(kill), v["title"][:28], (after[0][0][:56] if after[0] else "")))
            ok += 1
        else:
            io.open(path, "wb").write(original)
            print("  REVERTED %-28s (check failed)" % v["title"][:28])
            failed += 1

    print("\n%d file(s) %s, %d failed" % (ok, "changed" if apply else "would change", failed))
    if not apply:
        print("nothing written. Re-run with --apply.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
