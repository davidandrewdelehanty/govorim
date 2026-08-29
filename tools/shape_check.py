#!/usr/bin/env python3
"""A measure for the texts the names measure cannot see.

The names measure asks whether a proper noun in the Russian turns up in the
English on its own row. That works for novels and fails completely for «Я вас
любил», «Пари», «Хорёк», «Два товарища» — short works with no proper nouns at
all, which score 0% whether they are perfectly aligned or shuffled. It also
under-reports verse, where the same three names recur in every stanza and a
neighbouring row matches as well as the right one.

This measures the SHAPE of a row instead, which survives translation even when
no word does:

  ending     a question stays a question, an exclamation an exclamation
  speech     a line of dialogue keeps its dash or quotation marks
  emphasis   the count of ? and ! in the row
  digits     numerals cross unchanged

None of it depends on vocabulary, so it works on a lyric with no names in it.
And none of it is what any re-slicer optimises, so it cannot be gamed by the
thing it is checking.

The raw agreement means nothing on its own — nearly every row ends in a full
stop, so a shuffled text still scores well. What means something is the LIFT
over the same rows paired with the wrong English, rotated half a chapter along.
A real pairing beats its own shuffle. One that does not is not aligned.

    python3 tools/shape_check.py             # every paired work
    python3 tools/shape_check.py --book pari-en
"""
import argparse, glob, io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import BOOKS, INDEX, chapters, median, chapter_marker

DIGIT = re.compile(r"\d+")
SPEECH_OPEN = ("—", "–", "-", "«", "“", '"', "'", "‘")


def ending(s):
    s = s.rstrip().rstrip("»”\"'’)")
    if not s:
        return ""
    c = s[-1]
    if c in "?": return "?"
    if c in "!": return "!"
    if c in ".…": return "."
    if c in ":;,": return ":"
    if c in "—–-": return "-"
    return "x"


def shape(s):
    s = s.strip()
    return (
        ending(s),
        s[:1] in SPEECH_OPEN,
        min(s.count("?"), 3),
        min(s.count("!"), 3),
        tuple(sorted(DIGIT.findall(s))[:4]),
    )


def agree(a, b):
    """0..1 — how much two rows look alike, before any word is read."""
    sa, sb = shape(a), shape(b)
    score = 0.0
    score += 2.0 if sa[0] == sb[0] else 0.0
    score += 1.0 if sa[1] == sb[1] else 0.0
    score += 1.0 if sa[2] == sb[2] else 0.0
    score += 1.0 if sa[3] == sb[3] else 0.0
    if sa[4] or sb[4]:
        score += 1.0 if sa[4] == sb[4] else 0.0
        return score / 6.0
    return score / 5.0


def pairs_of(chapter, emap):
    keys = sorted(int(k) for k in emap
                  if k != "_note" and str(k).lstrip("-").isdigit())
    out = []
    for pos, i in enumerate(keys):
        if i >= len(chapter):
            continue
        nxt = keys[pos + 1] if pos + 1 < len(keys) else len(chapter)
        span = chapter[i:min(nxt, len(chapter))]
        # Drop a bare stanza or chapter numeral at the head of the span. The
        # Russian carries "I" as its own line and the English does not, and a
        # numeral has no ending punctuation and opens no dialogue, so leaving
        # it in made every stanza of Demon look mismatched and the measure
        # asked for a shift on a poem that was already right.
        while len(span) > 1 and chapter_marker(span[0]):
            span = span[1:]
        ru = " ".join(span).strip()
        en = str(emap[str(i)]).strip()
        if ru and en:
            out.append((ru, en))
    return out


def score(pairs):
    if len(pairs) < 6:
        return None, None
    hit = sum(agree(r, e) for r, e in pairs) / len(pairs)
    half = len(pairs) // 2
    null = sum(agree(r, pairs[(i + half) % len(pairs)][1])
               for i, (r, _) in enumerate(pairs)) / len(pairs)
    return hit, (hit - null)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default="")
    ap.add_argument("--all", action="store_true", help="every work, not just the quiet ones")
    a = ap.parse_args()
    cat = json.load(io.open(INDEX, encoding="utf-8"))
    rows = []
    for b in cat:
        d = b.get("parallelEn")
        if not d or d == "bible-kjv" or (a.book and d != a.book):
            continue
        p = os.path.join(BOOKS, b["filename"])
        if not os.path.exists(p):
            continue
        chs = chapters(p)
        if not chs:
            continue
        allp = []
        for f in sorted(glob.glob(os.path.join(BOOKS, d, "[0-9]*.json"))):
            n = int(re.match(r"(\d+)", os.path.basename(f)).group(1))
            if not (1 <= n <= len(chs)):
                continue
            allp.extend(pairs_of(chs[n - 1], json.load(io.open(f, encoding="utf-8"))))
        s, lift = score(allp)
        if s is None:
            continue
        rows.append((lift, s, len(allp), d, b.get("title", "")))
    rows.sort()
    print("%-32s %7s %7s %6s  %s" % ("folder", "shape", "lift", "rows", "title"))
    for lift, s, n, d, t in rows:
        if not a.all and lift >= 0.05:
            continue
        print("%-32s %6.0f%% %+6.3f %6d  %s" % (d, 100 * s, lift, n, t))
    lifts = [r[0] for r in rows]
    print("\n%d work(s): median lift %+.3f, %d below +0.05"
          % (len(rows), median(lifts), sum(1 for x in lifts if x < 0.05)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
