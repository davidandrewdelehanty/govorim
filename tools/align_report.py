#!/usr/bin/env python3
"""Dump alignment samples for human or AI review.

The confidence score in ingest.py only inspects where the two texts MEET. It
cannot see drift: an alignment that starts correctly and slips a paragraph at
chapter 7 scores exactly the same. So this samples each book at three depths —
near the start, the middle, and the end — and prints the Russian beside the
English it was paired with.

    python3 tools/align_report.py            > align-review.txt
    python3 tools/align_report.py --pairs 5  > align-review.txt   # deeper

Read the output, or hand it to Claude: the question for each pair is simply
"is this the same passage?", which is exactly the judgement a length-based
aligner cannot make.
"""
import argparse, io, json, os, re, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOKS = os.path.join(ROOT, "public", "books")
MANIFEST = os.path.join(ROOT, "private", "books", "index.json")
TAGS = re.compile(r"<[^>]+>")

def clean(s):
    import html as H
    return re.sub(r"\s+", " ", H.unescape(TAGS.sub(" ", s))).strip()

def ru_paras_by_chapter(fb2_path):
    x = io.open(fb2_path, encoding="utf-8", errors="replace").read()
    x = re.sub(r"<binary[\s\S]*?</binary>", "", x)
    m = re.search(r"<body(?:\s[^>]*)?>([\s\S]*?)</body>", x)
    if not m:
        return []
    def leaves(s, out):
        parts, depth, start = [], 0, None
        for mm in re.finditer(r"<section(?:\s[^>]*)?>|</section>", s):
            if mm.group(0).startswith("<section"):
                depth += 1
                if depth == 1: start = mm.end()
            else:
                depth -= 1
                if depth == 0: parts.append(s[start:mm.start()])
        if not parts: out.append(s)
        else:
            for p in parts: leaves(p, out)
    secs = []; leaves(m.group(1), secs)
    out = []
    for sec in secs:
        body = re.sub(r"<title>[\s\S]*?</title>", "", sec)
        body = re.sub(r"<epigraph>[\s\S]*?</epigraph>", "", body)
        ps = [clean(p) for p in re.findall(r"<p(?:\s[^>]*)?>([\s\S]*?)</p>", body)]
        ps = [p for p in ps if p]
        if ps: out.append(ps)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=int, default=3, help="samples per book")
    ap.add_argument("--chars", type=int, default=180)
    a = ap.parse_args()
    man = json.load(io.open(MANIFEST, encoding="utf-8"))
    # Only books THIS pipeline built. The older hand-aligned ones are indexed
    # against the app's own chapter splitter, not this file's, so re-deriving
    # their paragraph numbers here would report mismatches that aren't real.
    import csv as _csv
    ledger = os.path.join(ROOT, "tools", "data", "sources.tsv")
    mine = set()
    if os.path.exists(ledger):
        for r in _csv.DictReader(io.open(ledger, encoding="utf-8"), delimiter="\t"):
            mine.add(r["slug"])
    books = [e for e in man if e.get("parallelEn") and e.get("slug") in mine]
    print("ALIGNMENT REVIEW — %d books, %d samples each" % (len(books), a.pairs))
    print("For each pair: are the Russian and English the same passage?\n")
    for e in sorted(books, key=lambda x: x["slug"]):
        fb2 = os.path.join(BOOKS, e["filename"])
        d = os.path.join(BOOKS, e["parallelEn"])
        if not os.path.exists(fb2) or not os.path.isdir(d):
            continue
        chs = ru_paras_by_chapter(fb2)
        files = sorted(glob.glob(os.path.join(d, "*.json")))
        # every (chapter, ru_index, ru_text, en_text) that actually got English
        pairs = []
        for ci, f in enumerate(files):
            if ci >= len(chs): break
            try: mp = json.load(io.open(f, encoding="utf-8"))
            except Exception: continue
            for k, v in mp.items():
                # Hand-built parallel files carry a "_note" key beside the
                # numeric paragraph keys.
                if not str(k).lstrip("-").isdigit():
                    continue
                ki = int(k)
                if ki < len(chs[ci]) and v:
                    pairs.append((ci + 1, ki, chs[ci][ki], v))
        pairs.sort(key=lambda t: (t[0], t[1]))
        if not pairs:
            print("=== %-34s NO PAIRS\n" % e["slug"]); continue
        print("=== %-34s %s — %s" % (e["slug"], e.get("title",""), e.get("author","")))
        n = len(pairs)
        picks = [int(n * f) for f in ([0.02, 0.5, 0.95] if a.pairs == 3
                 else [i / (a.pairs - 1 or 1) * 0.95 + 0.02 for i in range(a.pairs)])]
        for idx in picks:
            ci, ki, ru, en = pairs[min(idx, n - 1)]
            print("  [ch %d, para %d]" % (ci, ki))
            print("    RU: %s" % ru[:a.chars])
            print("    EN: %s" % en[:a.chars])
        print()

if __name__ == "__main__":
    main()
