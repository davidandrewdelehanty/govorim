#!/usr/bin/env python3
"""Build tools/data/stress-dict.json.gz from two independent stress sources:
the OpenRussian CSV export (github.com/Badestrand/russian-dictionary,
CC BY-SA 4.0) and Koziev's all_accents.tsv (github.com/Koziev/NLP_Datasets,
Stress/all_accents.zip).

    python3 tools/build_stress_dict.py <openrussian-csv-dir> <all_accents.tsv>

The dictionary holds ONLY words whose stress is certain however they are
written. A word is kept when every one of these holds:

  * every form in the data that is spelt this way — across all lemmas, cases,
    persons — carries an explicit stress mark (or a lone vowel), and they all
    put it on the same vowel. Homographs (за́мок/замо́к, ру́ки/руки́) fail;
  * no form spelt this way when ё is written as е exists in the data. Most
    books print ё as е, so «слезы» on the page may be слезы́ (one tear's) or
    слёзы (tears), and «все» may be все́ or всё. The old dictionary folded ё
    into е before checking, so it kept «слезы» → слезы́ and marked every
    «слёзы» in a ё-less book wrong. A word with any ё relative is left out;
  * the form has at least two vowels (one vowel needs no mark) and no ё (ё is
    always the stressed vowel, so it needs no mark either).

  * the second source, Koziev's list, knows the word and puts the stress on
    the same vowel. It gives one stress per word and no homograph
    information, so it cannot stand on its own (it has «уже» as у́же), but as
    a cross-check it catches errors in either list: ~4,000 words where the two
    disagree are dropped, and ~56,000 it doesn't know are dropped with them.

Anything unmarked, doubly marked, hyphenated or multi-word poisons its
spelling: no mark is better than a guessed one.

Output: {word: index of the stressed vowel}, lowercase, е-spelt.
"""
import csv, gzip, io, json, os, re, sys
from collections import defaultdict

VOW = set("аеёиоуыэюя")
FORM_COLS = {
    "nouns.csv": ["accented", "sg_nom", "sg_gen", "sg_dat", "sg_acc", "sg_inst", "sg_prep",
                  "pl_nom", "pl_gen", "pl_dat", "pl_acc", "pl_inst", "pl_prep"],
    "adjectives.csv": ["accented", "comparative", "superlative", "short_m", "short_f", "short_n",
                       "short_pl"] + ["decl_%s_%s" % (g, c) for g in ("m", "f", "n", "pl")
                                      for c in ("nom", "gen", "dat", "acc", "inst", "prep")],
    "verbs.csv": ["accented", "imperative_sg", "imperative_pl", "past_m", "past_f", "past_n",
                  "past_pl", "presfut_sg1", "presfut_sg2", "presfut_sg3", "presfut_pl1",
                  "presfut_pl2", "presfut_pl3"],
    "others.csv": ["accented"],
}
STRESS = ("'", "́")


def parse(tok):
    """'слезы'' → ('слезы', {4}); unknown stress → ('word', None)."""
    tok = tok.strip().strip("*()[]!?.").lower()
    if not tok or " " in tok or "-" in tok:
        return None, None
    clean, pos = [], []
    for ch in tok:
        if ch in STRESS:
            if clean and clean[-1] in VOW:
                pos.append(len(clean) - 1)
            continue
        clean.append(ch)
    word = "".join(clean)
    if not re.fullmatch(r"[а-яё]+", word):
        return None, None
    nv = sum(1 for c in word if c in VOW)
    if len(pos) == 1:
        return word, {pos[0]}
    if len(pos) > 1:
        return word, set(pos)            # several marks = several readings
    if "ё" in word:
        return word, {word.index("ё")}
    if nv == 1:
        return word, {next(i for i, c in enumerate(word) if c in VOW)}
    return word, None                    # unmarked: stress unknown


def koziev(path):
    k = defaultdict(set)
    with io.open(path, encoding="utf-8") as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) != 2 or "^" not in p[1]:
                continue
            w, a = p[0].lower(), p[1].lower()
            if a.count("^") != 1 or a.replace("^", "") != w:
                continue
            k[w.replace("ё", "е")].add(a.index("^"))
    return k


def main(src, kpath, out):
    second = koziev(kpath)
    pos_by = defaultdict(set)      # е-spelt key → stress positions seen
    poisoned = set()               # е-spelt keys with an unmarked form
    has_yo = set()                 # е-spelt keys that some ё-form folds into
    for fn, cols in FORM_COLS.items():
        with io.open(os.path.join(src, fn), encoding="utf-8") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                for c in cols:
                    for tok in re.split(r"[,;/]", row.get(c) or ""):
                        word, pos = parse(tok)
                        if not word:
                            continue
                        key = word.replace("ё", "е")
                        if "ё" in word:
                            has_yo.add(key)
                        if pos is None:
                            poisoned.add(key)
                        else:
                            pos_by[key] |= pos
    d = {}
    for key, pos in pos_by.items():
        if key in poisoned or key in has_yo or len(pos) != 1:
            continue
        if sum(1 for c in key if c in VOW) < 2:
            continue
        i = next(iter(pos))
        if key[i] not in VOW:
            continue
        if second.get(key) != {i}:
            continue
        d[key] = i
    with gzip.open(out, "wt", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    print("%d spellings seen, %d unmarked somewhere, %d with a ё relative, %d kept "
          "(both sources agree) → %s"
          % (len(set(pos_by) | poisoned), len(poisoned), len(has_yo), len(d), out))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3
         else os.path.join(root, "tools", "data", "stress-dict.json.gz"))
