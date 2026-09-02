#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the Tatoeba example-sentence index for the definition popup.

Run in WSL, where pymorphy3 lives:

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/build_tatoeba.py ~/tatoeba/rus-eng.txt

Input — either shape is accepted, the script works out which:
  * the ManyThings pair file (`rus-eng.zip` → `rus.txt`), tab-separated,
    English and Russian in some order plus an attribution column;
  * Tatoeba's own per-language export: pass `--sentences rus_sentences.tsv
    --links links.csv --english eng_sentences.tsv` instead of a pair file.

Output — `public/vocab/tatoeba/`:
  index.json     { shards, version, built, lemmas, sentences }
  s00.json …     { "<lemma>": [[ru, en], …] }

Sharded because the whole index is megabytes and the browser should never
fetch more than the one bucket a word falls in. The bucket is chosen by an
FNV-1a hash that App.jsx computes the same way — change one, change both.

Licence: Tatoeba sentences are CC BY 2.0 FR (a subset CC0). The popup credits
Tatoeba on every sentence it shows, which is what the licence asks for.
"""
import argparse, io, json, os, re, sys, unicodedata
from collections import defaultdict

RU_WORD = re.compile(r"[А-Яа-яЁё][А-Яа-яЁё-]*")
HAS_CYR = re.compile(r"[А-Яа-яЁё]")
LATIN = re.compile(r"[A-Za-z]")

# Sentences that teach nothing, or teach the wrong thing.
MIN_CHARS, MAX_CHARS = 22, 110
MAX_PER_LEMMA = 3
SHARD_TARGET_KB = 120


def fnv1a(s):
    """32-bit FNV-1a over UTF-16 code units — the same arithmetic in JS."""
    h = 0x811C9DC5
    for ch in s:
        h ^= ord(ch)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def read_pairs(path):
    """(ru, en) from a tab-separated file, whichever columns hold the text.

    Tatoeba's "Sentence pairs" export is `id, russian, id, english`; the
    ManyThings file is `english, russian, attribution`. Rather than fix a
    column order, take the first Cyrillic field as the Russian and the first
    Latin-alphabet field as the English, which reads either shape and ignores
    the numeric id columns. utf-8-sig drops the export's byte-order mark, and
    the \r strip handles its Windows line endings.
    """
    out = []
    with io.open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for line in fh:
            parts = [c.strip() for c in line.replace("\r", "").rstrip("\n").split("\t")]
            ru = en = None
            for c in parts:
                if not c:
                    continue
                if ru is None and HAS_CYR.search(c):
                    ru = c
                elif en is None and LATIN.search(c) and not HAS_CYR.search(c):
                    en = c
            if ru and en:
                out.append((ru, en))
    return out

def read_exports(sentences, links, english):
    """Join Tatoeba's own three-file export into (ru, en) pairs."""
    ru, en = {}, {}
    with io.open(sentences, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3 and p[1] == "rus":
                ru[p[0]] = p[2].strip()
    with io.open(english, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3 and p[1] == "eng":
                en[p[0]] = p[2].strip()
    out = []
    with io.open(links, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) < 2:
                continue
            if p[0] in ru and p[1] in en:
                out.append((ru[p[0]], en[p[1]]))
    return out


def readable(ru, en):
    if not ru or not en:
        return False
    if not (MIN_CHARS <= len(ru) <= MAX_CHARS):
        return False
    if ru.count(",") > 3 or "(" in ru or "«" in ru and "»" not in ru:
        return False
    # A sentence that is mostly a name teaches nothing about the word.
    words = RU_WORD.findall(ru)
    if len(words) < 3 or len(words) > 16:
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pairs", nargs="?", help="tab-separated RU/EN pair file")
    ap.add_argument("--sentences"); ap.add_argument("--links"); ap.add_argument("--english")
    ap.add_argument("--out", default="public/vocab/tatoeba")
    ap.add_argument("--max-per-lemma", type=int, default=MAX_PER_LEMMA)
    ap.add_argument("--max-mb", type=float, default=30.0,
                    help="size budget for the whole index; the rarest lemmas are dropped to fit. "
                         "The index is sharded, so a bigger budget costs repository size but NOT "
                         "download size — the browser fetches one ~120 KB shard per word either way.")
    args = ap.parse_args()

    if args.pairs:
        pairs = read_pairs(args.pairs)
    elif args.sentences and args.links and args.english:
        pairs = read_exports(args.sentences, args.links, args.english)
    else:
        ap.error("give a pair file, or --sentences/--links/--english")
    print("%d raw pairs" % len(pairs))

    try:
        import pymorphy3
    except ImportError:
        print("pymorphy3 is missing — pip install pymorphy3", file=sys.stderr)
        return 1
    morph = pymorphy3.MorphAnalyzer()
    lemma_cache = {}

    def lemma_of(w):
        k = w.lower()
        if k not in lemma_cache:
            lemma_cache[k] = morph.parse(k)[0].normal_form
        return lemma_cache[k]

    # Shorter sentences first, so the best three per lemma are the readable ones.
    kept = [(ru, en) for ru, en in pairs if readable(ru, en)]
    kept.sort(key=lambda p: len(p[0]))
    print("%d usable after filtering" % len(kept))

    index = defaultdict(list)
    freq = defaultdict(int)          # how often each lemma occurs, for the trim
    seen = set()
    for ru, en in kept:
        key = re.sub(r"[^а-яё]", "", ru.lower())
        if key in seen:
            continue
        seen.add(key)
        for w in set(RU_WORD.findall(ru)):
            lem = lemma_of(w)
            if len(lem) < 3:
                continue
            freq[lem] += 1
            bucket = index[lem]
            if len(bucket) < args.max_per_lemma:
                bucket.append([ru, en])

    # A lemma that turns up in many Tatoeba sentences is a common word, and a
    # common word is the one a reader is most likely to look up — so when the
    # index will not fit the budget, the rarest lemmas go first.
    def weigh(k, v):
        return len(json.dumps(v, ensure_ascii=False)) + len(k) + 6
    budget = args.max_mb * 1e6
    total = sum(weigh(k, v) for k, v in index.items())
    if total > budget:
        ranked = sorted(index.items(), key=lambda kv: (-len(kv[1]), -freq[kv[0]], kv[0]))
        keep, used = {}, 0
        for k, v in ranked:
            w = weigh(k, v)
            if used + w > budget:
                continue
            keep[k] = v
            used += w
        print("index was %.1f MB — trimmed to %.1f MB, %d of %d lemmas kept"
              % (total / 1e6, used / 1e6, len(keep), len(index)))
        index = keep
        total = used

    shards = max(1, round(total / (SHARD_TARGET_KB * 1024)))
    out = [defaultdict(list) for _ in range(shards)]
    for lem, rows in index.items():
        out[fnv1a(lem) % shards][lem] = rows

    os.makedirs(args.out, exist_ok=True)
    for i, part in enumerate(out):
        with io.open(os.path.join(args.out, "s%02d.json" % i), "w", encoding="utf-8") as fh:
            json.dump(part, fh, ensure_ascii=False, separators=(",", ":"))
    meta = {"shards": shards, "version": 1, "lemmas": len(index),
            "sentences": sum(len(v) for v in index.values()),
            "source": "Tatoeba (CC BY 2.0 FR)"}
    with io.open(os.path.join(args.out, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False)
    total = sum(os.path.getsize(os.path.join(args.out, f)) for f in os.listdir(args.out))
    print("%d lemmas, %d sentences, %d shards, %.1f MB total (%.0f KB per shard)"
          % (meta["lemmas"], meta["sentences"], shards, total / 1e6, total / shards / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
