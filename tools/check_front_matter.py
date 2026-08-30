#!/usr/bin/env python3
"""Find sections that are about the book rather than part of it.

Дубровский opened on nineteen words naming the print edition the file was
scanned from and the website that hosted it. That is chapter 1 in the picker,
the first thing a reader sees, and the first thing an audio or English pairing
lands on - so every pairing in the book is off by one.

Two faults, two repairs:

  a PROVENANCE LINE - a source note, a URL, a scanning credit - is removed
  wherever it appears, even in the middle of real prose. Два гусара ends with
  the story, its date, and then a link; the link goes and the story stays.

  an APPARATUS SECTION - a table of contents, an editor's note - is removed
  whole, matched BY ITS TEXT and never by its position. The reader already
  drops sections the file has and it does not show, so a section's place in
  the file is not its chapter number, and deleting by index takes out the
  wrong text.

The test for a provenance line is deliberately narrow: it must be short AND
carry one of the marks below. Deleting a paragraph of a novel to tidy a picker
would be far worse than leaving a note in it.

    python3 tools/check_front_matter.py            # what it would remove
    python3 tools/check_front_matter.py --apply
"""
import argparse, io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import BOOKS, INDEX, chapters

MAX_LINE_WORDS = 25       # a provenance line is one sentence, not a paragraph
MAX_SECTION_WORDS = 400   # an apparatus section is short

# Every one of these can ONLY be provenance. An earlier draft matched
# "распозна" for scanning credits and caught Betsy on Nilsson in Anna Karenina
# and two verses of scripture; "флибуст" for the pirate library caught real
# flibustiers in Бесы and Мастер и Маргарита. A pattern that can appear in
# prose has no place here, however many notes it would otherwise catch.
MARKS = re.compile("|".join([
    r"источник\s+текста", r"оригинал\s+(?:здесь|взят)",
    r"воспроизводится\s+по\s+издани", r"спасибо,?\s+что\s+скачали",
    r"http[s]?://", r"www\.",
    r"\bocr\b", r"spell ?check",
    r"электронн\w+\s+библиотек", r"виртуальн\w+\s+библиотек",
    r"публичная\s+электронная\s+библиотека",
    r"\blib\.ru\b", r"royallib", r"aldebaran", r"booksreader",
    r"^v ?\d[\d.]*\s*[-–—]", r"\bisbn\b",
]), re.I)

APPARATUS = re.compile(r"^\s*(содержание|оглавление|комментари|примечани|"
                       r"аннотаци|об\s+автор|от\s+редактор|от\s+издател|"
                       r"выходные\s+данные|библиограф)\s*$", re.I)


def wc(s):
    return len(re.findall(r"\S+", s))


def flat(x):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip()


def read(path):
    raw = io.open(path, "rb").read()
    m = re.match(rb"<\?xml[^>]*encoding=[\"']([\w-]+)", raw[:200])
    enc = m.group(1).decode() if m else "utf-8"
    return raw.decode(enc, errors="replace"), enc


def spans(src):
    """Depth-1 <section> spans inside the first unnamed <body>."""
    bodies = [(m.start(), m.group(1)) for m in re.finditer(r"<body([^>]*)>", src)]
    if not bodies:
        return []
    start = next((p for p, at in bodies if "name=" not in at), bodies[0][0])
    end = src.find("</body>", start)
    out, depth, at = [], 0, None
    for m in re.finditer(r"<(/?)section\b[^>]*>", src[start:end]):
        if not m.group(1):
            depth += 1
            if depth == 1:
                at = start + m.start()
        else:
            depth -= 1
            if depth == 0:
                out.append((at, start + m.end()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    cat = json.load(io.open(INDEX, encoding="utf-8"))
    plan = []
    for b in cat:
        f = b.get("filename")
        path = os.path.join(BOOKS, f) if f else None
        if not path or not os.path.exists(path):
            continue
        chs = chapters(path)
        if not chs or len(chs) < 2:
            continue
        src, _ = read(path)
        lines = [flat(m.group(0)) for m in re.finditer(r"<p>.{0,400}?</p>", src, re.S)]
        cut = [t for t in lines if t and wc(t) <= MAX_LINE_WORDS and MARKS.search(t)]
        drop = []
        for pos in (0, len(chs) - 1):
            body = chs[pos]
            if body and APPARATUS.match(body[0]) and wc(" ".join(body)) <= MAX_SECTION_WORDS:
                drop.append((pos, body))
        if cut or drop:
            plan.append((b, path, cut, drop))

    print("%-32s %6s  %s" % ("title", "lines", "sections to drop"))
    for b, path, cut, drop in plan:
        print("%-32s %6d  %s" % (b.get("title", "")[:32], len(cut),
                                 ", ".join(d[1][0][:30] for d in drop) or "-"))
    print("\n%d book(s) affected" % len(plan))
    if not args.apply:
        print("nothing written. Re-run with --apply.")
        return 0

    for b, path, cut, drop in plan:
        src, enc = read(path)
        before = len(chapters(path) or [])
        gone = [0]

        def strip(m):
            t = flat(m.group(0))
            if t and wc(t) <= MAX_LINE_WORDS and MARKS.search(t):
                gone[0] += 1
                return ""
            return m.group(0)
        src = re.sub(r"<p>.{0,400}?</p>", strip, src, flags=re.S)

        removed = 0
        for pos, body in drop:
            head = body[0]
            for lo, hi in reversed(spans(src)):
                seg = flat(src[lo:hi])
                # The heading is not always the first thing in the span: the
                # contents page of Стихотворения в прозе sits under the book's
                # own title. Look for it near the top instead of at the top.
                if head[:40] in seg[:120] and wc(seg) <= MAX_SECTION_WORDS:
                    src = src[:lo] + src[hi:]
                    removed += 1
                    break
        io.open(path, "wb").write(src.encode(enc))
        after = len(chapters(path) or [])
        print("%-32s -%d line(s), -%d section(s), chapters %d -> %d"
              % (b.get("title", "")[:32], gone[0], removed, before, after))
    return 0


if __name__ == "__main__":
    sys.exit(main())
