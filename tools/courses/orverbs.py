# -*- coding: utf-8 -*-
"""The OpenRussian verbs table (github.com/Badestrand/russian-dictionary, CC BY-SA 4.0), kept as tools/data/openrussian-verbs.csv.gz:
every verb's accented present/future, past and imperative forms and its aspect.  A stress mark in the table is an apostrophe after the vowel;
here it becomes the combining acute the site draws (ё and a word's only vowel carry none)."""
import csv, gzip, os, io
HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools", "data", "openrussian-verbs.csv.gz")
ACUTE = "́"
VOW = "аеёиоуыэюя"
def fold(w): return (w or "").lower().replace("ё", "е").replace("'", "").replace(ACUTE, "")
def acute(w):
    if not w: return ""
    if "'" not in w: return w
    plain = w.replace("'", "")
    out = []
    for i, ch in enumerate(w):
        if ch == "'":
            if out and out[-1] in VOW + VOW.upper() and out[-1] not in "ёЁ" and sum(c.lower() in VOW for c in plain) > 1:
                out.append(ACUTE)
        else:
            out.append(ch)
    return "".join(out)
_E = {}
def _load():
    if _E: return
    with gzip.open(PATH, "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            _E.setdefault(r["bare"].lower(), []).append(r)
KEYS_PRES = ["presfut_sg1", "presfut_sg2", "presfut_sg3", "presfut_pl1", "presfut_pl2", "presfut_pl3"]
KEYS_PAST = ["past_m", "past_f", "past_n", "past_pl"]
def entries(inf): _load(); return _E.get(inf.lower(), [])
def forms_of(r):
    def split(v): return [acute(x.strip()) for x in (v or "").split(",") if x.strip()]
    return {"pres": [split(r[k]) for k in KEYS_PRES], "past": [split(r[k]) for k in KEYS_PAST],
            "impr": [split(r["imperative_sg"]), split(r["imperative_pl"])], "aspect": {"imperfective": "impf.", "perfective": "pf.", "both": "impf./pf."}.get(r["aspect"], ""),
            "partner": r["partner"], "accented": acute(r["accented"])}
def entry(inf, ans=None):
    """The table entry of `inf` that has the answer among its forms (писать «write» or «urinate»), else the first; None when the verb is not in the table."""
    es = entries(inf)
    if not es: return None
    if ans:
        for r in es:
            f = forms_of(r)
            allf = {fold(x) for k in ("pres", "past", "impr") for ws in f[k] for x in ws}
            if fold(ans) in allf: return f
    return forms_of(es[0])
if __name__ == "__main__":
    import sys
    for v in sys.argv[1:]:
        print(v, entry(v))
