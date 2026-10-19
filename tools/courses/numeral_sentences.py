#!/usr/bin/env python3
"""Real sentences with a number written out and a noun after it — «я работаю
на двух работах» — for the Grammar tab's counting drills, each with where it
comes from: a public-domain book in the library (author, title), or Tatoeba
(with its English). The number and noun are blanked; the hint is the number in
digits and the noun's dictionary form; the answer is what the text has.

    python3 tools/courses/numeral_sentences.py ~/tatoeba/rus.txt   → public/vocab/numeral-sentences.json
"""
import io, json, os, re, sys, hashlib
from collections import defaultdict
import pymorphy3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE)) if os.path.basename(HERE) == "courses" else HERE
M = pymorphy3.MorphAnalyzer()
ONES = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
TEENS = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
TENS = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят", "девяносто"]
ONE = {"N": "один одна одно", "G": "одного одной", "D": "одному одной", "A": "один одну одно одного", "I": "одним одной", "P": "одном одной"}
FEW = {2: {"N": "два две", "G": "двух", "D": "двум", "A": "два две двух", "I": "двумя", "P": "двух"},
       3: {"N": "три", "G": "трёх трех", "D": "трём трем", "A": "три трёх трех", "I": "тремя", "P": "трёх трех"},
       4: {"N": "четыре", "G": "четырёх четырех", "D": "четырём четырем", "A": "четыре четырёх четырех", "I": "четырьмя", "P": "четырёх четырех"}}
ODD = {"сорок": "сорока", "девяносто": "девяноста", "сто": "ста"}
TY = {"пятьдесят": ("пятидесяти", "пятьюдесятью"), "шестьдесят": ("шестидесяти", "шестьюдесятью"),
      "семьдесят": ("семидесяти", "семьюдесятью"), "восемьдесят": ("восьмидесяти", "восемьюдесятью восьмьюдесятью")}
FORMS = defaultdict(set)          # word form → {(value, kind, case)}  kind: unit | ten


def put(words, v, kind, c):
    for w in words.split():
        FORMS[w].add((v, kind, c))


put(ONE["N"], 1, "unit", "N")
for c in "GDAIP":
    put(ONE[c], 1, "unit", c)
for v, d in FEW.items():
    for c, ws in d.items():
        put(ws, v, "unit", c)
for v in range(5, 10):
    w = ONES[v]
    put(w, v, "unit", "N"); put(w, v, "unit", "A")
    g = "восьми" if w == "восемь" else w[:-1] + "и"
    for c in "GDP": put(g, v, "unit", c)
    put("восемью восьмью" if w == "восемь" else w + "ю", v, "unit", "I")
for i, w in enumerate(TEENS):
    v = 10 + i
    put(w, v, "unit", "N"); put(w, v, "unit", "A")
    for c in "GDP": put(w[:-1] + "и", v, "unit", c)
    put(w + "ю", v, "unit", "I")
for t in range(2, 10):
    w, v = TENS[t], t * 10
    put(w, v, "ten", "N"); put(w, v, "ten", "A")
    if w in ODD:
        for c in "GDIP": put(ODD[w], v, "ten", c)
    elif w in TY:
        for c in "GDP": put(TY[w][0], v, "ten", c)
        put(TY[w][1], v, "ten", "I")
    else:
        for c in "GDP": put(w[:-1] + "и", v, "ten", c)
        put(w + "ю", v, "ten", "I")
put("сто", 100, "ten", "N"); put("сто", 100, "ten", "A")
for c in "GDIP": put("ста", 100, "ten", c)

PYC = {"nomn": "N", "gent": "G", "datv": "D", "accs": "A", "ablt": "I", "loct": "P", "loc2": "P"}
W = re.compile(r"[А-Яа-яЁё]+")
RUDE = re.compile(r"(ху[йияеёю]|пизд|[её]б[аеиуыл]|бля|трах|шлюх|fuck|shit)", re.I)


def find(ru):
    ws = list(W.finditer(ru))
    low = [w.group().lower() for w in ws]
    out = []
    i = 0
    while i < len(low):
        f = FORMS.get(low[i])
        if not f:
            i += 1; continue
        j, val, cases = i, 0, None
        # a ten (or сто) optionally followed by a unit, in the same case
        tens = [x for x in f if x[1] == "ten"]
        units = [x for x in f if x[1] == "unit"]
        if tens and i + 1 < len(low) and FORMS.get(low[i + 1]):
            u2 = [x for x in FORMS[low[i + 1]] if x[1] == "unit" and x[0] < 10]
            cs = {x[2] for x in tens} & {x[2] for x in u2}
            if u2 and cs:
                val, cases, j = tens[0][0] + u2[0][0], cs, i + 1
        if cases is None:
            src = tens or units
            val, cases = src[0][0], {x[2] for x in src}
        k = j + 1
        if k >= len(low):
            break
        ps = [p for p in M.parse(low[k]) if p.tag.POS == "NOUN" and p.score > 0.05]
        tg = lambda p: set(str(p.tag).replace(" ", ",").split(","))
        ps = [p for p in ps if not (tg(p) & {"Name", "Surn", "Patr", "Geox", "Abbr", "Sgtm", "Pltm"})]
        if not ps or val == 1 and low[i] in ("одно",) and False:
            i = j + 1; continue
        p = ps[0]
        nc = PYC.get(p.tag.case)
        num = p.tag.number
        u = val % 10; t = val % 100
        if "N" in cases or "A" in cases:
            few = 2 <= u <= 4 and not 12 <= t <= 14
            one = u == 1 and t != 11
            if (one and num == "sing" and nc in ("N", "A")) or (few and num == "sing" and nc == "G") or \
               (not one and not few and num == "plur" and nc == "G") or (few and num == "plur" and nc == "G" and "A" in cases):
                c = "N" if (one and nc == "N") or (not one and "N" in cases and not (few and num == "plur")) else "A"
                out.append((i, k, val, p, "NA" if c in ("N", "A") and not (few and num == "plur") else "A"))
                i = k + 1; continue
        oblique = cases - {"N", "A"}
        if nc in oblique and ((u == 1 and t != 11 and num == "sing") or (not (u == 1 and t != 11) and num == "plur")):
            out.append((i, k, val, p, nc))
        i = k + 1
    return out, ws


def main():
    rows = []
    tat = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/tatoeba/rus.txt")
    for line in io.open(tat, encoding="utf-8", errors="replace"):
        c = line.rstrip("\n").split("\t")
        if len(c) >= 2:
            en, ru = (c[0], c[1]) if re.search(r"[А-Яа-я]", c[1]) else (c[1], c[0])
            rows.append((ru, en, ""))
    lib = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "library_sentences.tsv")
    for line in io.open(lib, encoding="utf-8"):
        c = line.rstrip("\n").split("\t")
        if len(c) >= 3:
            rows.append((c[0], "", c[2]))
    print(len(rows), "sentences", flush=True)
    found = defaultdict(list)
    seen = set()
    for ru, en, cite in rows:
        if ru in seen or len(ru) > 140 or RUDE.search(ru) or RUDE.search(en):
            continue
        seen.add(ru)
        if not any(w.lower() in FORMS for w in W.findall(ru)):
            continue
        hits, ws = find(ru)
        for i, k, val, p, c in hits:
            if i > 0 and ws[i].group()[:1].isupper() or not M.word_is_known(ws[k].group().lower()):
                continue
            s, e = ws[i].span()[0], ws[k].span()[1]
            if (s and ru[s - 1] in "-‑") or ru[e:e + 1] == "-":
                continue
            ans = ru[s:e]
            lem = p.normal_form
            q = ru[:s] + "___ (%d %s)" % (val, lem) + ru[e:]
            found["count" if c == "NA" else "decl"].append(
                {"q": q, "a": ans, "n": val, "c": c, "en": en, "src": cite})
    out = {}
    for key, xs in found.items():
        xs.sort(key=lambda x: (not x["en"], hashlib.md5(x["q"].encode()).hexdigest()))
        per = defaultdict(int); keep = []
        for x in xs:
            kk = (x["n"], x["c"])
            if per[kk] >= 40:
                continue
            per[kk] += 1; keep.append(x)
        out[key] = keep
        print(key, len(xs), "found,", len(keep), "kept")
    dst = os.path.join(ROOT, "public", "vocab", "numeral-sentences.json") if os.path.isdir(os.path.join(ROOT, "public")) else "numeral-sentences.json"
    io.open(dst, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print("→", dst)


if __name__ == "__main__":
    main()
