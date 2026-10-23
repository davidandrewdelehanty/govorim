# -*- coding: utf-8 -*-
"""Numerals course: (1) the hint's figure equals the hint's words; (2) the answer has the same words, in the case the prompt names."""
import glob, json, os, re, sys
from collections import Counter
import pymorphy3
M = pymorphy3.MorphAnalyzer()
norm = lambda w: w.lower().replace("ё", "е")
W = re.compile(r"[А-Яа-яЁё]+")
U = {"один": 1, "два": 2, "три": 3, "четыре": 4, "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10, "одиннадцать": 11, "двенадцать": 12,
     "тринадцать": 13, "четырнадцать": 14, "пятнадцать": 15, "шестнадцать": 16, "семнадцать": 17, "восемнадцать": 18, "девятнадцать": 19, "двадцать": 20, "тридцать": 30,
     "сорок": 40, "пятьдесят": 50, "шестьдесят": 60, "семьдесят": 70, "восемьдесят": 80, "девяносто": 90, "сто": 100, "двести": 200, "триста": 300, "четыреста": 400,
     "пятьсот": 500, "шестьсот": 600, "семьсот": 700, "восемьсот": 800, "девятьсот": 900}
ORD = {"первый": 1, "второй": 2, "третий": 3, "четвертый": 4, "пятый": 5, "шестой": 6, "седьмой": 7, "восьмой": 8, "девятый": 9, "десятый": 10, "одиннадцатый": 11,
       "двенадцатый": 12, "тринадцатый": 13, "четырнадцатый": 14, "пятнадцатый": 15, "шестнадцатый": 16, "семнадцатый": 17, "восемнадцатый": 18, "девятнадцатый": 19,
       "двадцатый": 20, "тридцатый": 30, "сороковой": 40, "пятидесятый": 50, "шестидесятый": 60, "семидесятый": 70, "восьмидесятый": 80, "девяностый": 90, "сотый": 100,
       "двухсотый": 200, "трехсотый": 300, "четырехсотый": 400, "пятисотый": 500, "шестисотый": 600, "семисотый": 700, "восьмисотый": 800, "девятисотый": 900,
       "тысячный": 1000, "двухтысячный": 2000}
CASES = {"Nominative": {"nomn"}, "Genitive": {"gent", "gen2"}, "Dative": {"datv"}, "Accusative": {"accs", "acc2", "gent", "nomn"}, "Instrumental": {"ablt"}, "Prepositional": {"loct", "loc2"}}
def lemmas(w):
    return {norm(p.normal_form) for p in M.parse(w)}
def value(words):
    total = cur = 0
    for w in words:
        ls = lemmas(w)
        v = next((U[l] for l in ls if l in U), None)
        if v is None: v = next((ORD[l] for l in ls if l in ORD), None)
        if v is None:
            if ls & {"тысяча", "тысяч"}: total += (cur or 1) * 1000; cur = 0; continue
            if ls & {"миллион"}: total += (cur or 1) * 10**6; cur = 0; continue
            return None
        cur += v
    return total + cur
bad = []; n = 0
for f in sorted(glob.glob("public/courses/numerals/*.json")):
    fn = os.path.basename(f)[:-5]
    if fn == "exam": continue
    for e in json.load(open(f, encoding="utf-8")).get("exercises") or []:
        m = re.search(r"___ \((\d+)\s*·\s*([^)]*)\)", e["q"])
        if not m: continue
        n += 1
        fig, words = int(m.group(1)), W.findall(m.group(2))
        v = value(words)
        a = W.findall(e["answers"][0])
        # 1: figure vs words (cardinal/ordinal alike)
        if v is not None and v != fig: bad.append(("fig≠words", fn[:22], e["q"][:50], e["answers"][0]))
        # 2: answer words are the same numeral words (lemma sequence)
        if len(a) != len(words) and not (len(a) == len(words) and True):
            if value(a) != fig and not (value(a) is None): bad.append(("count", fn[:22], e["q"][:50], e["answers"][0]))
        elif value(a) is not None and v is not None and value(a) != v: bad.append(("value", fn[:22], e["q"][:50], e["answers"][0]))
        # 3: case named by the prompt
        pr = e.get("prompt") or ""
        cs = set().union(*[CASES[k] for k in CASES if k in pr]) if any(k in pr for k in CASES) else None
        if cs:
            ordinal = bool(words) and bool(lemmas(words[-1]) & set(ORD))
            for x in (a[-1:] if ordinal else a):
                if not any((p.tag.case in cs) for p in M.parse(x)): bad.append(("case", fn[:22], e["q"][:50], e["answers"][0] + " | " + pr[:40])); break
print("checked", n, "problems", len(bad), dict(Counter(b[0] for b in bad)))
for b in bad[:(80 if "--all" in sys.argv else 12)]: print("  ", b)
