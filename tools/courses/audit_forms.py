# -*- coding: utf-8 -*-
"""Is the answer the KIND of form its section teaches? (tense, imperative, participle, gerund, degree). Prints violations."""
import glob, json, os, re, sys
from collections import Counter, defaultdict
import pymorphy3
M = pymorphy3.MorphAnalyzer()
norm = lambda w: w.lower().replace("ё", "е")
W = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)?")
G = lambda *g: (lambda p: set(g) <= set(p.tag.grammemes))
EXPECT = {   # (course, section prefix) -> predicate on a parse of the LAST word (or the finite word of a compound)
    ("verbs", "v1-present"): lambda p: p.tag.POS == "VERB" and p.tag.tense in ("pres", "futr"),
    ("verbs", "v2-past"): lambda p: p.tag.POS == "VERB" and p.tag.tense == "past",
    ("tenses", "x06"): lambda p: p.tag.POS == "VERB" and p.tag.tense == "past",
    ("tenses", "x07"): lambda p: p.tag.POS == "VERB" and p.tag.tense == "past",
    ("tenses", "x08"): lambda p: p.tag.POS == "VERB" and p.tag.tense == "past",
    ("tenses", "x09"): lambda p: p.tag.POS == "VERB" and p.tag.tense == "past",
    ("tenses", "x10"): lambda p: p.tag.POS == "VERB" and p.tag.tense == "futr" or p.normal_form == "быть",
    ("tenses", "x11"): lambda p: p.tag.POS == "VERB" and p.tag.tense in ("pres", "futr") or p.normal_form == "быть",
    ("aspect", "a4-future"): lambda p: p.tag.POS == "VERB" and p.tag.tense in ("futr", "pres") or p.normal_form == "быть",
    ("forms", "f1"): lambda p: p.tag.mood == "impr",
    ("forms", "f3"): lambda p: p.tag.POS in ("PRTS",) ,
    ("forms", "f4"): lambda p: p.tag.POS == "PRTF" and p.tag.voice == "pssv",
    ("forms", "f5"): lambda p: p.tag.POS == "PRTF" and p.tag.voice == "actv" and p.tag.tense == "pres",
    ("forms", "f6"): lambda p: p.tag.POS == "PRTF" and p.tag.voice == "actv" and p.tag.tense == "past",
    ("forms", "f8"): lambda p: p.tag.POS == "GRND",
    ("forms", "f9"): lambda p: p.tag.POS == "GRND",
    ("compare", "c6"): lambda p: "Supr" in p.tag.grammemes or p.tag.POS == "ADJF",
    ("compare", "c7"): lambda p: p.tag.POS == "ADJS",
}
def main():
    bad = defaultdict(list); tot = Counter()
    for f in sorted(glob.glob("public/courses/*/*.json")):
        c = f.split("/")[2]; fn = os.path.basename(f)[:-5]
        if fn == "exam": continue
        keys = [k for k in EXPECT if k[0] == c and fn.startswith(k[1])]
        if not keys: continue
        pred = EXPECT[keys[0]]
        for e in json.load(open(f, encoding="utf-8")).get("exercises") or []:
            if e.get("type") != "fill": continue
            for a in e["answers"][:1]:
                ws = W.findall(a)
                if not ws: continue
                tot[keys[0]] += 1
                ok = any(pred(p) for w in ws for p in M.parse(w))
                if not ok: bad[keys[0]].append((fn[:22], e["q"][:60], a))
    print({"%s/%s" % k: v for k, v in tot.items()})
    for k, v in bad.items():
        print("==", k, len(v))
        for x in v[:(60 if "--all" in sys.argv else 6)]: print("   ", x)
main()
