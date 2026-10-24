# -*- coding: utf-8 -*-
"""Hint word vs answer: the hint (dictionary form in brackets) must be of the part of speech the answer is.
Lists every fill exercise whose hint cannot be the answer's part of speech.   audit_hint_pos.py [--course X] [--json out]"""
import glob, io, json, os, re, sys
import pymorphy3
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
M = pymorphy3.MorphAnalyzer()
G = {"VERB": "V", "INFN": "V", "ADJF": "A", "ADJS": "A", "COMP": "A", "PRTF": "P", "PRTS": "P", "GRND": "P", "NOUN": "N", "NUMR": "M", "NPRO": "R",
     "ADVB": "D", "PRED": "D", "PREP": "X", "CONJ": "X", "PRCL": "X", "INTJ": "X", "None": "?"}
OK_PAIRS = {("A", "P"), ("P", "A"), ("A", "D"), ("D", "A"), ("A", "N"), ("N", "A"), ("M", "A"), ("A", "M"), ("R", "A"), ("A", "R"),
            ("N", "R"), ("R", "N"), ("M", "N"), ("N", "M"), ("M", "R"), ("R", "M"), ("D", "R"), ("R", "D"), ("D", "X"), ("X", "D"), ("N", "D"), ("D", "N"),
            ("X", "R"), ("R", "X"), ("X", "N"), ("N", "X"), ("A", "X"), ("X", "A"), ("D", "M"), ("M", "D"), ("V", "D"), ("D", "V")}
only = sys.argv[sys.argv.index("--course") + 1] if "--course" in sys.argv else None
bad = []
for f in sorted(glob.glob(os.path.join(ROOT, "public", "courses", "*", "*.json"))):
    c = f.split(os.sep)[-2]
    if only and c != only or f.endswith("exam.json"):
        continue
    for e in json.load(io.open(f, encoding="utf-8")).get("exercises") or []:
        if e.get("type") != "fill" or not e.get("answers"):
            continue
        m = re.search(r"___ \(([^)]*)\)", e["q"])
        if not m:
            continue
        h = re.split(r"[,;— ]", m.group(1).strip())[0].lower().replace("ё", "е")
        a = e["answers"][0].lower().replace("ё", "е")
        if not re.fullmatch(r"[а-я]+", h) or not re.fullmatch(r"[а-я\-]+", a):
            continue
        hc = {G.get(str(p.tag.POS), "?") for p in M.parse(h) if p.normal_form.replace("ё", "е") == h and p.score > 0.02} or {"?"}
        ac = {G.get(str(p.tag.POS), "?") for p in M.parse(a) if p.score > 0.02} or {"?"}
        if "?" in hc or "?" in ac or hc & ac:
            continue
        if any((x, y) in OK_PAIRS for x in hc for y in ac):
            continue
        bad.append((c, os.path.basename(f)[:-5], e["id"], m.group(1), e["answers"][0], e["q"]))
import collections
cnt = collections.Counter(b[0] for b in bad)
print(len(bad), dict(cnt))
for b in bad:
    print("%-9s %-28s %-4s (%s) -> %s | %s" % (b[0], b[1], b[2], b[3], b[4], b[5][:70]))
if "--json" in sys.argv:
    json.dump(bad, io.open(sys.argv[sys.argv.index("--json") + 1], "w", encoding="utf-8"), ensure_ascii=False)
