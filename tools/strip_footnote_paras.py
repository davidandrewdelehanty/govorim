#!/usr/bin/env python3
"""Take the orphaned footnote lines out of a book, and re-key its English.

Дядюшкин сон carries 38 paragraphs of the form

    1 "Записок дьявола" (франц.).

They are footnote texts that lost their anchors somewhere before this FB2 was
made. They read as nonsense on the page, and worse, they are paragraphs: the
reader counts them, so the English lands on them. About half of them are
sitting on a real paragraph of Garnett's translation, and each one pushes
everything after it one row out.

So: drop those paragraphs from the FB2, and move each chapter's English up by
the number of them removed before it. English that was keyed ON a footnote row
is appended to the row above, because that is where it belongs and because
dropping it would delete translation from the book.

    python3 tools/strip_footnote_paras.py --book dyadyushkin-son-en
    python3 tools/strip_footnote_paras.py --book dyadyushkin-son-en --apply
"""
import argparse, glob, io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import BOOKS, INDEX, chapters, score_file

# A digit or two, then a short gloss, then the language in brackets. Anchored
# hard: this deletes text from a book, so it must not match a real paragraph.
FOOTNOTE = re.compile(r"^\d{1,2}\s+.{0,70}?\((?:франц|нем|итал|лат|англ|греч)\.\)\.?$")


def para_text(p):
    return re.sub(r"\s+", " ", "".join(p.itertext())).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    cat = json.load(io.open(INDEX, encoding="utf-8"))
    b = [x for x in cat if x.get("parallelEn") == a.book]
    if not b:
        sys.exit("no book with parallelEn %r" % a.book)
    b = b[0]
    fb2 = os.path.join(BOOKS, b["filename"])

    raw = io.open(fb2, "rb").read()
    m = re.match(rb"<\?xml[^>]*encoding=[\"']([\w-]+)", raw[:200])
    enc = m.group(1).decode("ascii", "ignore") if m else "utf-8"
    src = raw.decode(enc)

    # Which paragraph indices go, per chapter — measured on the chapter list
    # the reader builds, so the keys move by exactly what the reader will see.
    chs = chapters(fb2)
    if not chs:
        sys.exit("could not read chapters")
    drops = {}
    for ci, ch in enumerate(chs):
        hit = [i for i, p in enumerate(ch) if FOOTNOTE.match(p)]
        if hit:
            drops[ci] = hit
    total = sum(len(v) for v in drops.values())
    print("%d footnote paragraph(s) in %d chapter(s)" % (total, len(drops)))
    if not total:
        return 0

    # The same paragraphs, out of the source.
    gone = [0]
    def cut(mt):
        if FOOTNOTE.match(re.sub(r"<[^>]+>", "", mt.group(0)).strip()):
            gone[0] += 1
            return ""
        return mt.group(0)
    out_src = re.sub(r"<p>.{0,120}?</p>", cut, src, flags=re.S)
    print("%d paragraph(s) cut from the FB2" % gone[0])

    moved = kept = 0
    for ci, hit in sorted(drops.items()):
        f = os.path.join(BOOKS, a.book, "%02d.json" % (ci + 1))
        if not os.path.exists(f):
            continue
        emap = json.load(io.open(f, encoding="utf-8"))
        ent = dict((int(k), v) for k, v in emap.items()
                   if k != "_note" and str(k).lstrip("-").isdigit())
        drop = set(hit)
        new = {}
        pending = ""
        for i in sorted(ent):
            shift = sum(1 for d in hit if d < i)
            if i in drop:
                pending = (pending + " " + str(ent[i])).strip()
                continue
            j = i - shift
            txt = str(ent[i])
            if pending:
                # English that sat on a footnote row belongs to the row above.
                prev = [k for k in sorted(new) if int(k) < j]
                if prev:
                    new[prev[-1]] = (new[prev[-1]] + " " + pending).strip()
                else:
                    txt = (pending + " " + txt).strip()
                pending = ""
            new[str(j)] = txt
        if pending and new:
            last = max(new, key=lambda k: int(k))
            new[last] = (new[last] + " " + pending).strip()
        if "_note" in emap:
            new["_note"] = emap["_note"]
        newch = [p for i, p in enumerate(chs[ci]) if i not in drop]
        before = score_file(chs[ci], emap).get("onrow")
        after = score_file(newch, new).get("onrow")
        fmt = lambda x: "  n/a" if x is None else "%3.0f%%" % (100 * x)
        print("  ch %-3d -%d footnote(s)  names %s -> %s"
              % (ci + 1, len(hit), fmt(before), fmt(after)))
        if a.apply:
            io.open(f, "w", encoding="utf-8").write(
                json.dumps(new, ensure_ascii=False, indent=1) + "\n")
        moved += 1
    if a.apply:
        io.open(fb2, "wb").write(out_src.encode(enc))
        print("wrote the FB2 and %d English file(s)" % moved)
    else:
        print("\nnothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
