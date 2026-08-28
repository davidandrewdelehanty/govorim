#!/usr/bin/env python3
"""Build per-book stress-mark sidecars for the reader's "a-acute Stress" toggle.

For every book in the catalogue, collects the Russian words that actually occur
in its text and looks each up in tools/data/stress-dict.json.gz — a dictionary
of ~527k inflected forms (built from the OpenRussian/Wiktionary data, CC-BY-SA)
containing ONLY words whose stress is unambiguous across the whole dictionary.
Homographs and unknown words are simply absent, so every mark the reader shows
is certain; a wrong stress mark teaches a learner a wrong word, and no mark is
always better than that.

Output: public/books/stress/<fb2-basename>.json  mapping
    lowercase word -> index of the stressed vowel in that word
The app inserts U+0301 after that index at render time — display only.

Run from the repo root after adding a book:   python3 tools/gen_stress_maps.py
"""
import gzip, io, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT = os.path.join(ROOT, "tools", "data", "stress-dict.json.gz")
OUT  = os.path.join(ROOT, "public", "books", "stress")

stress = json.load(gzip.open(DICT, "rt", encoding="utf-8"))
manifest = json.load(io.open(os.path.join(ROOT, "private", "books", "index.json"), encoding="utf-8"))

os.makedirs(OUT, exist_ok=True)
word_re = re.compile(r"[а-яё]+")
total = skipped = 0
for e in manifest:
    fn = e.get("filename")
    if not fn:
        continue
    tree = "private" if e.get("restricted") else "public"
    path = os.path.join(ROOT, tree, "books", fn)
    if not os.path.exists(path):
        print("  missing, skipped:", fn); skipped += 1; continue
    raw = io.open(path, encoding="utf-8", errors="ignore").read()
    raw = re.sub(r"<binary[\s\S]*?</binary>", "", raw)
    words = set(word_re.findall(raw.lower()))
    m = {w: stress[w] for w in words if w in stress}
    stem = re.sub(r"\.(fb2\.zip|epub|fb2|txt|x?html?)$", "", os.path.basename(fn), flags=re.I)
    with io.open(os.path.join(OUT, stem + ".json"), "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, separators=(",", ":"))
    print("  %-52s %6d words marked / %6d unique" % (stem[:52], len(m), len(words)))
    total += 1
print("done: %d sidecars%s" % (total, (", %d missing files" % skipped) if skipped else ""))
