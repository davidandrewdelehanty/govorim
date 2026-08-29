#!/usr/bin/env python3
"""Ask the model which English line each Russian line is — and nothing else.

The Sonnet sweep taught an expensive lesson: asked "is this pairing shifted",
the model invents shifts. Of 223 files it called shifted, moving them as it
asked made 174 worse. Twelve rows of literary translation read as "off by one"
to any reader, because the translation genuinely does not answer the Russian a
line at a time.

But asked "which of these is this", it was right every time — it caught that
one folder held Chelkash instead of Twenty-Six Men and a Girl, and that another
ran into the publisher's advertisements. That is the question this asks. Not
"is line 7 shifted" but "line 7 is «Стоял он, дум великих полн» — which of
these English lines is it".

That matters for verse and nothing else can do it. A verse line is thirty
characters with no proper noun and no numeral, so length says nothing, the DP
in align_verse.py wanders, and the four Pushkin poems drift by a different
amount in every canto.

    python3 tools/verse_map.py --build            # windows and a cost
    python3 tools/verse_map.py --submit
    python3 tools/verse_map.py --status
    python3 tools/verse_map.py --fetch
    python3 tools/verse_map.py --apply            # only what improves

BAND is how far the English may have drifted. Widen it if a poem is worse than
that, but every extra line is a line the model has to read for every window.
"""
import argparse, glob, io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import BOOKS, INDEX, chapters, score_file, chapter_marker
import shape_check as SHAPE
import ai_align_check as AI

HERE = os.path.dirname(os.path.abspath(__file__))
REQS = os.path.join(HERE, "verse-map-requests.jsonl")
STATE = os.path.join(HERE, "verse-map-batch.json")
MAP = os.path.join(HERE, "verse-map-index.json")
OUT = os.path.join(HERE, "verse-map-answers.json")

VERSE_BOOKS = ["pushkin-medny-vsadnik-en", "pushkin-poltava-en",
               "pushkin-tsygany-en", "pushkin-bakhchisaraysky-fontan-en"]

SPAN, OVERLAP, BAND = 30, 6, 16
MODELS = AI.MODELS
MAX_TOKENS = 3000
MIN_GAIN = 0.02

SYSTEM = """You are matching the lines of a Russian poem to the lines of its English
verse translation. Both lists are in order and neither is reordered.

For each numbered Russian line, name the numbered English line that renders it.

A verse translator does not keep one line per line. Expect these:
  - one Russian line rendered as two English lines: name the FIRST of them
  - two Russian lines folded into one English line: name that line for both
  - a Russian line the translation drops entirely: use null

The matches must not go backwards. If Russian 7 matches English 9, Russian 8
matches English 9 or later.

Match on what the lines SAY. Rhyme and metre are rebuilt from scratch in a
verse translation and tell you nothing about which line is which.

Answer with JSON only, no other text:
{"pairs": [{"r": 0, "e": 2}, {"r": 1, "e": 3}, {"r": 2, "e": null}]}
Give one entry for every Russian line you are shown, in order."""


def en_lines(emap):
    ks = sorted(int(k) for k in emap
                if k != "_note" and str(k).lstrip("-").isdigit())
    return [str(emap[str(k)]).strip() for k in ks if str(emap[str(k)]).strip()]


def ru_lines(chapter):
    keep = [i for i, p in enumerate(chapter) if not chapter_marker(p)]
    return keep, [chapter[i] for i in keep]


def files_of(book):
    b = [x for x in json.load(io.open(INDEX, encoding="utf-8"))
         if x.get("parallelEn") == book]
    if not b:
        return None, []
    chs = chapters(os.path.join(BOOKS, b[0]["filename"]))
    out = []
    for f in sorted(glob.glob(os.path.join(BOOKS, book, "[0-9]*.json"))):
        n = int(re.match(r"(\d+)", os.path.basename(f)).group(1))
        if chs and 1 <= n <= len(chs):
            out.append((f, chs[n - 1]))
    return b[0], out


def build(books, model, effort):
    reqs, index = [], {}
    ru_ch = en_ch = 0
    for book in books:
        b, files = files_of(book)
        if not b:
            continue
        for path, chapter in files:
            emap = json.load(io.open(path, encoding="utf-8"))
            E = en_lines(emap)
            _, R = ru_lines(chapter)
            if len(R) < 8 or len(E) < 8:
                continue
            k = len(E) / float(len(R))
            step = SPAN - OVERLAP
            for a in range(0, len(R), step):
                bnd = R[a:a + SPAN]
                if len(bnd) < 6:
                    break
                mid = int(a * k)
                lo = max(0, mid - BAND)
                hi = min(len(E), int((a + len(bnd)) * k) + BAND)
                if hi - lo < 4:
                    continue
                rtxt = "\n".join("R%d: %s" % (a + i, s) for i, s in enumerate(bnd))
                etxt = "\n".join("E%d: %s" % (lo + j, E[lo + j])
                                 for j in range(hi - lo))
                body = ("Poem: %s, %s\n\nRUSSIAN LINES\n%s\n\nENGLISH LINES\n%s"
                        % (b.get("title", ""), os.path.basename(path), rtxt, etxt))
                ru_ch += len(rtxt)
                en_ch += len(etxt)
                cid = "v%05d" % len(reqs)
                index[cid] = {"dir": book, "file": os.path.basename(path),
                              "first": a, "count": len(bnd)}
                params = {"model": model, "max_tokens": MAX_TOKENS,
                          "system": SYSTEM,
                          "messages": [{"role": "user", "content": body}]}
                if effort:
                    params["output_config"] = {"effort": "low"}
                else:
                    params["temperature"] = 0
                reqs.append({"custom_id": cid, "params": params})
    with io.open(REQS, "w", encoding="utf-8") as fh:
        for r in reqs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    json.dump(index, io.open(MAP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    tin = (ru_ch + en_ch) / 3.2 + len(reqs) * 250
    tout = len(reqs) * (500 if effort else 300)
    print("%d window(s), about %.2fM in / %.0fk out" % (len(reqs), tin / 1e6, tout / 1e3))
    return len(reqs)


def monotonic(votes, n_en):
    """Keep the largest set of matches that never goes backwards."""
    rows = sorted(votes)                       # ru index -> en index
    best, back = [], []
    for i, r in enumerate(rows):
        e = votes[r]
        pick, cand = 1, -1
        for j in range(i):
            if votes[rows[j]] <= e and back[j][0] + 1 > pick:
                pick, cand = back[j][0] + 1, j
        back.append((pick, cand))
    if not back:
        return {}
    end = max(range(len(back)), key=lambda i: back[i][0])
    chain, i = [], end
    while i != -1:
        chain.append(rows[i])
        i = back[i][1]
    chain.reverse()
    return dict((r, votes[r]) for r in chain)


def rebuild(chapter, emap, pairs):
    """A monotonic ru->en map becomes the reader's key -> English, spanning.

    Every English line has to land somewhere: one that no Russian line claims
    is appended to the last one that did, because dropping it would delete
    translation from the book to make a number look better.
    """
    keep, R = ru_lines(chapter)
    E = en_lines(emap)
    m = monotonic(dict((r, e) for r, e in pairs.items()
                       if 0 <= r < len(R) and e is not None and 0 <= e < len(E)),
                  len(E))
    if len(m) < max(4, 0.35 * len(R)):
        return None
    # Two Russian lines folded into one English line share that line: the
    # FIRST of them carries it and the rest carry nothing, because the reader
    # spans an English cell down to the next row that has one. Giving each of
    # them a copy printed the same couplet five times down the page.
    order = [r for i, r in enumerate(sorted(m))
             if i == 0 or m[r] != m[sorted(m)[i - 1]]]
    out, used = {}, 0
    for pos, r in enumerate(order):
        lo = m[r]
        hi = m[order[pos + 1]] if pos + 1 < len(order) else len(E)
        if pos == 0:
            lo = 0                              # nothing before the first match
        if hi <= lo:
            continue
        text = " ".join(E[lo:hi]).strip()
        if text:
            out[str(keep[r])] = text
            used = hi
    if used < len(E) and out:
        last = max(out, key=lambda k: int(k))
        out[last] = (out[last] + " " + " ".join(E[used:])).strip()
    if "_note" in emap:
        out["_note"] = emap["_note"]
    return out


def grade(chapter, emap):
    s, _ = SHAPE.score(SHAPE.pairs_of(chapter, emap))
    r = score_file(chapter, emap)
    return s, r.get("onrow"), r.get("placed", 0)


def apply(write):
    answers = json.load(io.open(OUT, encoding="utf-8"))
    byfile = {}
    for a in answers:
        byfile.setdefault((a["dir"], a["file"]), {}).update(
            dict((int(p["r"]), p["e"]) for p in a.get("pairs", [])
                 if isinstance(p, dict) and "r" in p))
    print("%-32s %-9s %9s %9s  %s" % ("folder", "file", "shape", "names", "verdict"))
    changed = held = 0
    for book in sorted(set(k[0] for k in byfile)):
        b, files = files_of(book)
        for path, chapter in files:
            key = (book, os.path.basename(path))
            if key not in byfile:
                continue
            emap = json.load(io.open(path, encoding="utf-8"))
            new = rebuild(chapter, emap, byfile[key])
            if not new:
                print("%-32s %-9s %9s %9s  too few matches"
                      % (book, key[1], "-", "-"))
                held += 1
                continue
            s0, n0, p0 = grade(chapter, emap)
            s1, n1, p1 = grade(chapter, new)
            names_ok = (n0 is None or n1 is None or p0 < 6 or n1 >= n0 - 0.01)
            ok = (s0 is not None and s1 is not None
                  and s1 - s0 >= MIN_GAIN and names_ok)
            def pct(x):
                return "   n/a" if x is None else "%5.0f%%" % (100 * x)
            print("%-32s %-9s %s->%s %s->%s  %s"
                  % (book, key[1], pct(s0), pct(s1), pct(n0), pct(n1),
                     "rewrite" if ok else "leave"))
            if ok:
                changed += 1
                if write:
                    io.open(path, "w", encoding="utf-8").write(
                        json.dumps(new, ensure_ascii=False, indent=1) + "\n")
            else:
                held += 1
    print()
    print("%d file(s) %s, %d left alone"
          % (changed, "rewritten" if write else "would change", held))
    if changed and not write:
        print("nothing written. Re-run with --apply --write.")


def main():
    ap = argparse.ArgumentParser()
    for flag in ("build", "submit", "status", "fetch", "apply", "write"):
        ap.add_argument("--" + flag, action="store_true")
    ap.add_argument("--book", default="", help="comma separated, default the verse four")
    ap.add_argument("--model", choices=sorted(MODELS), default="sonnet")
    a = ap.parse_args()
    if not any((a.build, a.submit, a.status, a.fetch, a.apply)):
        ap.error("nothing to do — try --build")

    # Same transport, its own files: fetching one run against another run's
    # map is not an error, it is wrong answers with confident names on them.
    AI.REQS, AI.STATE, AI.MAP, AI.OUT = REQS, STATE, MAP, OUT
    model, _, _, effort = MODELS[a.model]
    books = [x.strip() for x in a.book.split(",") if x.strip()] or VERSE_BOOKS

    key = os.environ.get("ANTHROPIC_API_KEY")
    if (a.submit or a.status or a.fetch) and not key:
        sys.exit("ANTHROPIC_API_KEY is not set.")
    if a.build:
        build(books, model, effort)
    if a.submit:
        AI.submit(key)
    if a.status:
        AI.status(key)
    if a.fetch:
        AI.fetch(key)
    if a.apply:
        apply(a.write)
    return 0


if __name__ == "__main__":
    sys.exit(main())
