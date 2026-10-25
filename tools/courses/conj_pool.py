# -*- coding: utf-8 -*-
"""Imperfective verbs of the library, sorted into conjugation types: tools/courses/conj_pool.json  {type: [[verb, count], …]}"""
import sys, os, json, glob, re, collections, io
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import conj_classes as C
import verb_notes as VN
IMPF_BOTH = {"находиться", "проходить", "заходить", "переходить", "выглядеть", "покидать", "строить", "считать", "пахнуть", "использовать",
             "обещать", "замыкать", "замыкаться", "разбегаться", "простираться", "высыпаться", "подрезать", "срезать", "конфисковать", "жениться"}
def impf(v):
    a = VN.aspect_of(v)
    return a == {"impf."} or (len(a) == 2 and v in IMPF_BOTH)
def main():
    freq = {}
    for f in glob.glob("public/vocab/verbs/*.json"):
        d = json.load(open(f, encoding="utf-8"))
        for k, v in d.items():
            if isinstance(v, dict): freq[k] = v.get("n", 0)
    pool = collections.defaultdict(list)
    pf = collections.defaultdict(list)             # perfective verbs of the types that have (almost) no imperfective ones
    for v, n in sorted(freq.items(), key=lambda x: -x[1]):
        if n < 6 or not re.fullmatch(r"[а-яё]+", v): continue
        try:
            a = VN.aspect_of(v)
            z = C.zclass(v)
        except Exception: continue
        if z is None: continue
        if a == {"pf."} and z in (9, 10, 14, 15):
            pf[str(z)].append([v, n]); continue
        if not impf(v): continue
        pool[str(z)].append([v, n])
    pool["pf"] = pf
    io.open(os.path.join(HERE, "conj_pool.json"), "w", encoding="utf-8").write(json.dumps(pool, ensure_ascii=False))
    for k in sorted(pool, key=lambda x: (len(x), x)):
        if k != "pf": print(k, len(pool[k]), [x[0] for x in pool[k][:14]])
    for k in sorted(pf): print("pf", k, len(pf[k]), [x[0] for x in pf[k][:16]])
main()
