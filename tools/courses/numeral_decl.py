#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Declined numerals in real sentences, for the Declined Numerals course.

Every sentence is one somebody wrote: the library's public-domain books
(tools/courses/library_sentences.tsv, with author and title), and Tatoeba
(tatoeba.org, CC BY 2.0 FR) where a translation is given — the Tatoeba pairs
are the ones already found by tools/courses/numeral_sentences.py, in
public/vocab/numeral-sentences.json. Nothing is written by a program: the
numeral is simply blanked, and the number in digits is the hint.

    Он выпил пиво ___ (1) глотком.        → одним
    Кабель прокладывается на глубине не менее ___ (3) метров.   → трёх
    Жена не выходила из своих комнат, мужа ___ (3-й) день не было дома.  → третий

The cardinal is kept only when the noun after it is in the case the numeral
is in (tools/courses/numeral_sentences.find does that check with pymorphy3),
so «двух» in «двух часов» is the genitive and not a look-alike; an ordinal is
kept when it agrees with the noun after it in case, number and gender.

    python3 tools/courses/numeral_decl.py   → tools/courses/numeral_decl.json
"""
import io, json, os, re, sys, hashlib
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numeral_sentences as NS
M = NS.M
W = NS.W
RUDE = NS.RUDE
ROOT = os.path.dirname(os.path.dirname(HERE))

ORD = {"первый": 1, "второй": 2, "третий": 3, "четвёртый": 4, "пятый": 5, "шестой": 6, "седьмой": 7, "восьмой": 8,
       "девятый": 9, "десятый": 10, "одиннадцатый": 11, "двенадцатый": 12, "тринадцатый": 13, "четырнадцатый": 14,
       "пятнадцатый": 15, "шестнадцатый": 16, "семнадцатый": 17, "восемнадцатый": 18, "девятнадцатый": 19,
       "двадцатый": 20, "тридцатый": 30, "сороковой": 40, "пятидесятый": 50, "шестидесятый": 60, "семидесятый": 70,
       "восьмидесятый": 80, "девяностый": 90, "сотый": 100}
TENS_NOM = {"двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50, "шестьдесят": 60, "семьдесят": 70,
            "восемьдесят": 80, "девяносто": 90}
# the ending that spells out which ordinal form the digits stand for, as it
# is written after a figure: 3-й, 3-я, 3-е, 3-го, 3-му, 3-м, 3-х
def ord_suffix(word):
    w = word.lower().replace("ё", "е")
    for end in ("ого", "его", "ому", "ему", "ыми", "ими", "ых", "их", "ым", "им", "ой", "ей", "ую", "юю", "ый", "ий", "ое", "ее", "ая", "яя", "ые", "ие", "ом", "ем"):
        if w.endswith(end):
            return "-" + end[-2:] if len(end) == 3 else "-" + end[-1:]
    return "-й"


def tagset(p):
    return set(str(p.tag).replace(" ", ",").split(","))


def ordinals(ru):
    """[(start_word_index, end_word_index, value, word_objects)] — an ordinal
    (with the nominative tens before it: двадцать пятого) that agrees with
    the noun after it."""
    ws = list(W.finditer(ru))
    low = [w.group().lower().replace("ё", "е") for w in ws]
    out = []
    for i, w in enumerate(low):
        ps = [p for p in M.parse(w) if p.tag.POS == "ADJF" and p.normal_form.replace("ё", "е") in {k.replace("ё", "е") for k in ORD}]
        if not ps or i + 1 >= len(low):
            continue
        p = ps[0]
        if i > 0 and ws[i].group()[:1].isupper():
            continue
        val = [v for k, v in ORD.items() if k.replace("ё", "е") == p.normal_form.replace("ё", "е")][0]
        nouns = [q for q in M.parse(low[i + 1]) if q.tag.POS == "NOUN" and q.score > 0.05
                 and not (tagset(q) & {"Name", "Surn", "Patr", "Geox", "Abbr"})]
        ok = False
        for q in nouns:
            if q.tag.number != p.tag.number:
                continue
            pc, qc = p.tag.case, q.tag.case
            if qc in ("loc2", "gen2", "acc2"):
                qc = {"loc2": "loct", "gen2": "gent", "acc2": "accs"}[qc]
            if pc != qc:
                continue
            if p.tag.number == "sing" and p.tag.gender and q.tag.gender and p.tag.gender != q.tag.gender:
                continue
            ok = True
            break
        if not ok:
            continue
        s = i
        if val < 10 and i > 0 and low[i - 1] in TENS_NOM:
            s = i - 1
            val += TENS_NOM[low[i - 1]]
        out.append((s, i, val, ws))
    return out


def cite(src, en):
    if src:
        return "*%s*" % src
    return "*%s*" % en if en else ""


def merge():
    """Put the parts together: python3 numeral_decl.py --merge"""
    import glob
    out = defaultdict(list)
    seen = set()
    for f in sorted(glob.glob(os.path.join(HERE, "numeral_decl.part-*.json"))):
        for key, xs in json.load(io.open(f, encoding="utf-8")).items():
            for x in xs:
                if x["q"] in seen:
                    continue
                seen.add(x["q"])
                out[key].append(x)
    for key, xs in out.items():
        xs.sort(key=lambda x: (not x["en"], hashlib.md5(x["q"].encode()).hexdigest()))
        print("%-6s %5d" % (key, len(xs)), flush=True)
    dst = os.path.join(HERE, "numeral_decl.json")
    io.open(dst, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print("→", dst, sum(len(v) for v in out.values()), "sentences")


def main():
    # --part i/n: the i-th n-th of the sentences, to numeral_decl.part-i.json
    # (the whole run is long; the parts are put together with --merge)
    part, parts = 0, 1
    if "--merge" in sys.argv:
        return merge()
    if "--part" in sys.argv:
        part, parts = [int(x) for x in sys.argv[sys.argv.index("--part") + 1].split("/")]
    rows = []        # (ru, en, cite)
    lib = os.path.join(HERE, "library_sentences.tsv")
    for n, line in enumerate(io.open(lib, encoding="utf-8")):
        if n % parts != part - 1 and parts > 1:
            continue
        c = line.rstrip("\n").split("\t")
        if len(c) >= 3:
            rows.append((c[0], "", c[2]))
    print(len(rows), "library sentences", flush=True)
    # the Tatoeba sentences numeral_sentences.py already found, with their English
    tat = os.path.join(ROOT, "public", "vocab", "numeral-sentences.json")
    ntat = 0
    if os.path.exists(tat) and part <= 1:
        for xs in json.load(io.open(tat, encoding="utf-8")).values():
            for x in xs:
                if x.get("en") and not x.get("src"):
                    ru = re.sub(r"___ \([^)]*\)", x["a"], x["q"], count=1)
                    rows.append((ru, x["en"], ""))
                    ntat += 1
    print(ntat, "Tatoeba sentences", flush=True)

    found = defaultdict(list)
    seen = set()
    quick = set(NS.FORMS) | {k.replace("ё", "е") for k in ORD}
    for ru, en, src in rows:
        if ru in seen or len(ru) > 160 or RUDE.search(ru) or RUDE.search(en):
            continue
        seen.add(ru)
        lows = [w.lower().replace("ё", "е") for w in W.findall(ru)]
        if not any(w in quick or w.replace("е", "ё") in quick for w in lows):
            continue
        # cardinals in oblique cases (and the animate accusative двух, трёх…)
        hits, ws = NS.find(ru)
        for i, k, val, p, c in hits:
            if c == "NA":
                continue
            if i > 0 and ws[i].group()[:1].isupper() or not M.word_is_known(ws[k].group().lower()):
                continue
            # the numeral's own words run from word i up to the word before the noun
            s, e = ws[i].span()[0], ws[k - 1].span()[1]
            if (s and ru[s - 1] in "-‑") or ru[e:e + 1] == "-":
                continue
            ans = ru[s:e]
            if not re.fullmatch(r"[А-Яа-яЁё ]+", ans):
                continue
            key = ("one" if val == 1 else "two" if val <= 4 else "five" if val <= 20 or val == 30 else
                   "forty" if val in (40, 50, 60, 70, 80, 90, 100) else "comp")
            q = ru[:s] + "___ (%d)" % val + ru[e:]
            found[key].append({"q": q, "a": ans, "n": val, "c": c, "en": en, "src": src})
        # ordinals
        for s_i, i, val, ws2 in ordinals(ru):
            s, e = ws2[s_i].span()[0], ws2[i].span()[1]
            if (s and ru[s - 1] in "-‑") or ru[e:e + 1] == "-":
                continue
            ans = ru[s:e]
            if not re.fullmatch(r"[А-Яа-яЁё ]+", ans):
                continue
            q = ru[:s] + "___ (%d%s)" % (val, ord_suffix(ws2[i].group())) + ru[e:]
            found["ord"].append({"q": q, "a": ans, "n": val, "c": "ord", "en": en, "src": src})
    out = {}
    for key, xs in found.items():
        # translated sentences first; then a fixed shuffle
        xs.sort(key=lambda x: (not x["en"], hashlib.md5(x["q"].encode()).hexdigest()))
        out[key] = xs
        print("%-6s %5d" % (key, len(xs)), flush=True)
    dst = os.path.join(HERE, "numeral_decl.json" if parts == 1 else "numeral_decl.part-%02d.json" % part)
    io.open(dst, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print("→", dst, sum(len(v) for v in out.values()), "sentences")


if __name__ == "__main__":
    main()
