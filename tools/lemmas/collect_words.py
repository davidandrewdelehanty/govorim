#!/usr/bin/env python3
"""Every distinct Russian word form the reader can show: all FB2s in
public/books/novel plus the song lyrics. Writes tools/lemmas/words.txt.gz,
one lower-case form per line — the input to tools/lemmas/build_lemmas.py."""
import glob, gzip, io, json, os, re
W = re.compile(r"[а-яё]+(?:-[а-яё]+)*")
words = set()
def take(text):
    for w in W.findall(text.lower()):
        words.add(w)
        if "-" in w:
            words.update(p for p in w.split("-") if p)
for f in glob.glob("public/books/novel/*.fb2"):
    raw = open(f, "rb").read()
    m = re.search(rb'encoding="([^"]+)"', raw[:200])
    enc = (m.group(1).decode() if m else "utf-8")
    try:
        t = raw.decode(enc, errors="replace")
    except LookupError:
        t = raw.decode("utf-8", errors="replace")
    take(re.sub(r"<[^>]+>", " ", t))
for f in glob.glob("public/music/*.json"):
    take(io.open(f, encoding="utf-8").read())
with gzip.open("tools/lemmas/words.txt.gz", "wt", encoding="utf-8") as g:
    g.write("\n".join(sorted(words)))
print(len(words), "forms")
