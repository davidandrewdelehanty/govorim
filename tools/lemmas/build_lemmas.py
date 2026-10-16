#!/usr/bin/env python3
"""Word form → lemma table for the define popup, built with pymorphy3.

pymorphy3 (MIT) analyses Russian with the OpenCorpora dictionary: every
inflected form of ~400k lemmas, with part of speech, plus an ending-based
guesser for words the dictionary lacks. The reader's text is a closed set —
the library — so instead of running a Python analyser behind the API, every
distinct form in the library is analysed once, here, and the answers ship as
static files. api/define.js reads the one shard a clicked word needs.

    pip install pymorphy3                         # brings its dictionary along
    python3 tools/lemmas/collect_words.py         # words.txt.gz from the library
    python3 tools/lemmas/build_lemmas.py          # → public/lemmas/<shard>.json

Shard: the form's first two letters, spelled in ASCII so file names stay
portable ("ст" → "is.json"); the few large ones are cut by a third letter,
listed in index.json. Entry: "lemma:pos" readings joined by "|",
best first; a leading "?" means pymorphy3 guessed (the word is not in its
dictionary), so define treats those lemmas as candidates to verify, not as
facts. Forms whose only reading is themselves are left out — the define stack
already tries the clicked form first.

The dictionary data is OpenCorpora's, CC BY-SA 3.0: see public/lemmas/LICENSE.
"""
import gzip, io, json, os, sys
import pymorphy3

ALPH = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
CODE = "0123456789abcdefghijklmnopqrstuvw"
POS = {"NOUN": "noun", "ADJF": "adjective", "ADJS": "adjective", "COMP": "comparative",
       "VERB": "verb", "INFN": "verb", "PRTF": "participle", "PRTS": "participle",
       "GRND": "gerund", "NUMR": "numeral", "ADVB": "adverb", "NPRO": "pronoun",
       "PRED": "predicative", "PREP": "preposition", "CONJ": "conjunction",
       "PRCL": "particle", "INTJ": "interjection"}


def shard_of(w):
    k = "".join(CODE[ALPH.index(c)] if c in ALPH else "_" for c in w[:2])
    return k if len(k) == 2 else k + "_"


def readings(m, w):
    ps = m.parse(w)
    if not ps:
        return None, False
    top = ps[0].score or 1e-9
    seen, out = set(), []
    for p in ps:
        if p.score < 0.08 * top and out:
            continue
        pos = POS.get(p.tag.POS or "", "")
        lem = p.normal_form
        # A participle or gerund's normal form is the participle itself in
        # pymorphy; the dictionary headword a learner wants is the verb.
        if pos in ("participle", "gerund"):
            try:
                inf = p.inflect({"INFN"})
                if inf:
                    lem = inf.word
            except Exception:
                pass
        if pos == "comparative":
            lem = p.normal_form
        key = (lem, pos)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
        if len(out) == 3:
            break
    return out, m.word_is_known(w)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "tools/lemmas/words.txt.gz"
    dst = sys.argv[2] if len(sys.argv) > 2 else "public/lemmas"
    m = pymorphy3.MorphAnalyzer()
    words = gzip.open(src, "rt", encoding="utf-8").read().split()
    shards, kept, known_n, guessed_n = {}, 0, 0, 0
    for i, w in enumerate(words):
        r, known = readings(m, w)
        if not r:
            continue
        if len(r) == 1 and r[0][0] == w:
            continue                     # its own lemma, nothing to say
        if not known:
            r = r[:1]                    # a guess: keep only pymorphy3's best one
            if r[0][0] == w:
                continue
        val = "|".join("%s:%s" % (l, p) for l, p in r)
        if not known:
            val = "?" + val
            guessed_n += 1
        else:
            known_n += 1
        shards.setdefault(shard_of(w), {})[w] = val
        kept += 1
        if i % 100000 == 0:
            print("  %d/%d" % (i, len(words)), flush=True)
    os.makedirs(dst, exist_ok=True)
    # A two-letter shard over ~350 KB («по», «пр», «на» …) is cut again by the
    # third letter, so no lookup ever pulls a large file. index.json lists the
    # cut prefixes; the reader loads it once.
    split = []
    for k in list(shards):
        d = shards[k]
        if len(json.dumps(d, ensure_ascii=False).encode("utf-8")) > 350000:
            split.append(k)
            for w, v in shards.pop(k).items():
                k3 = k + (CODE[ALPH.index(w[2])] if len(w) > 2 and w[2] in ALPH else "_")
                shards.setdefault(k3, {})[w] = v
    io.open(os.path.join(dst, "index.json"), "w", encoding="utf-8").write(json.dumps({"split": sorted(split)}))
    total = 0
    for k, d in shards.items():
        s = json.dumps(d, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        io.open(os.path.join(dst, k + ".json"), "w", encoding="utf-8").write(s)
        total += len(s.encode("utf-8"))
    io.open(os.path.join(dst, "LICENSE"), "w", encoding="utf-8").write(
        "Form-to-lemma tables built with pymorphy3 (MIT, https://github.com/no-plagiarism/pymorphy3)\n"
        "from the OpenCorpora dictionary (http://opencorpora.org), licensed CC BY-SA 3.0.\n"
        "These tables are a derived work and are distributed under the same licence.\n")
    print("%d forms → %d entries (%d known, %d guessed) in %d shards, %.1f MB"
          % (len(words), kept, known_n, guessed_n, len(shards), total / 1e6))


if __name__ == "__main__":
    main()
