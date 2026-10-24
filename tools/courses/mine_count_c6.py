# -*- coding: utf-8 -*-
"""Tatoeba practice for the Counting course's «hundreds, thousands, millions» module.
Blank the counted noun (or тысяча / миллион) after a hundred, or after a number + тысяча / миллион.
Writes the picks into drills.json -> count -> c6-hundreds-thousands.
Run: python3 tools/courses/mine_count_c6.py
"""
import hashlib, io, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pymorphy3
from prep_mine import load_pool

M = pymorphy3.MorphAnalyzer()
HUND = {"сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот", "семьсот", "восемьсот", "девятьсот"}
BIG = {"тысяча", "миллион", "миллиард"}
SMALLNUM = {"два", "две", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять", "десять", "одиннадцать", "двенадцать",
            "тринадцать", "четырнадцать", "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать", "двадцать",
            "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят", "девяносто"} | HUND
W = re.compile(r"[А-Яа-яЁё\-]+")
BAD = {"Sgtm", "Pltm", "Fixd", "Name", "Surn", "Patr", "Geox", "Orgn", "Abbr", "Infr", "Slng", "Arch", "Erro"}
SRC = "Sentence and translation from Tatoeba (CC BY 2.0 FR)."


def parse(w):
    return M.parse(w.lower())


def run():
    pool = load_pool()
    cands = []
    for ru, en in pool.items():
        if re.search(r"\d", ru) or "шестнадцат" in ru:
            continue
        ws = W.findall(ru)
        if not 4 <= len(ws) <= 11:
            continue
        for i in range(1, len(ws)):
            prev = ws[i - 1].lower().replace("ё", "е")
            ps = [p for p in parse(ws[i]) if p.score > 0.3]
            if not ps:
                continue
            p = ps[0]
            lem = p.normal_form
            pl = parse(prev)[0].normal_form.replace("ё", "е")
            t = set(str(p.tag).replace(" ", ",").split(","))
            if t & BAD:
                continue
            kind = None
            if lem in BIG and pl in SMALLNUM | {"несколько", "много"} and p.tag.POS == "NOUN" and p.tag.case in ("gent",) or \
               lem in BIG and pl in SMALLNUM and p.tag.POS == "NOUN" and p.tag.case in ("gent", "nomn"):
                kind = "big"
            elif pl in HUND and p.tag.POS == "NOUN" and p.tag.case == "gent" and p.tag.number == "plur" and lem not in BIG:
                kind = "hund"
            if not kind:
                continue
            ans = ws[i]
            # the noun must be unambiguous in its form: only this one reading as a noun lemma
            q = " ".join(ru.split())
            # blank exactly this token
            toks = list(re.finditer(r"[А-Яа-яЁё\-]+", ru))
            m = toks[i]
            blanked = ru[:m.start()] + "___ (%s)" % lem + ru[m.end():]
            cands.append((kind, lem, prev, ans, blanked, en, ru))
    print(len(cands), "candidates")
    cands.sort(key=lambda c: hashlib.md5(c[6].encode()).hexdigest())
    pick, used_lem, used_prev = [], {}, {}
    for cap in (1, 2):
        for c in cands:
            kind, lem, prev, ans, blanked, en, ru = c
            if ru in [x[6] for x in pick]:
                continue
            if used_lem.get(lem, 0) >= cap + (2 if kind == "big" else 0) or used_prev.get(prev, 0) >= cap + 1:
                continue
            pick.append(c); used_lem[lem] = used_lem.get(lem, 0) + 1; used_prev[prev] = used_prev.get(prev, 0) + 1
            if len(pick) >= 14:
                break
        if len(pick) >= 14:
            break
    for c in pick:
        print(c[0], "|", c[4], "|", c[3], "|", c[5])
    out = [{"type": "fill", "q": c[4], "prompt": c[5], "answers": [c[3]], "why": SRC} for c in pick]
    if "--write" in sys.argv:
        p = os.path.join(HERE, "drills.json")
        d = json.load(io.open(p, encoding="utf-8"))
        d["count"]["c6-hundreds-thousands"] = out
        io.open(p, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=1))
        print("written", len(out))


if __name__ == "__main__":
    run()
