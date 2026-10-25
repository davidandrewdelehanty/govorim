# -*- coding: utf-8 -*-
"""Tatoeba sentences (CC BY 2.0 FR) with a finite form of an imperfective verb of each conjugation type:
tools/courses/conj_drills.json  {type: [[sentence, translation, verb, form, kind, who], …]}.
The dictionary only decides whether the word is that verb in that form; nothing is written by us."""
import sys, os, json, re, io, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import case_explain as CE
import verb_notes as VN
from prep_mine import load_pool
M = VN.M
def main():
    pool = json.load(open(os.path.join(HERE, "conj_pool.json"), encoding="utf-8"))
    cap = {"1": 700, "4": 600}
    fm = {}                                   # form -> (type, verb) ; ambiguous forms dropped
    bad = set()
    allv = [(z, v, n) for z, vs in pool.items() if z != "pf" for v, n in vs[:cap.get(z, 400)]]
    allv += [(z, v, n) for z, vs in pool.get("pf", {}).items() for v, n in vs[:150]]
    if True:
        for z, v, n in allv:
            try: lx = VN.entry_lexeme(v)
            except Exception: continue
            for f in lx:
                t = set(str(f.tag).replace(" ", ",").split(","))
                if "VERB" not in t or not (t & {"pres", "futr", "past"}) or t & set(VN.P.DROP) or "impr" in t: continue
                w = VN.fold(f.word)
                if w in fm and fm[w] != (z, v): bad.add(w)
                fm[w] = (z, v)
    for w in bad: fm.pop(w, None)
    print("forms", len(fm))
    sents = load_pool()
    print("sentences", len(sents))
    out = collections.defaultdict(list); seen = collections.Counter()
    for ru, en in sents.items():
        s = ru.strip()
        if not (24 <= len(s) <= 100) or re.search(r"[A-Za-z\d]", s) or s.count(",") > 3 or "?" in s and len(s) > 80: continue
        toks = [t.group() for t in CE.TOKEN.finditer(s)]
        hits = [(i, VN.fold(t)) for i, t in enumerate(toks) if CE.WORD.fullmatch(t) and VN.fold(t) in fm]
        if len(hits) != 1: continue                       # one verb form of the course per sentence
        i, w = hits[0]; z, v = fm[w]
        word = toks[i]
        ps = [p for p in M.parse(word.lower()) if p.tag.POS in ("VERB", "INFN")]
        top = M.parse(word.lower())[0]
        if top.tag.POS != "VERB" or VN.fold(top.normal_form) != v and not (v.endswith("ся") and VN.fold(top.normal_form) == v): continue
        if top.score < 0.55: continue
        got = VN.analyze(v, word)
        if len(got) != 1: continue
        kind, who = next(iter(got))
        out[z].append([s, en, v, word, kind, who])
    for z, rows in out.items():
        print(z, len(rows), collections.Counter((r[4], r[5]) for r in rows).most_common(10))
    io.open(os.path.join(HERE, "conj_drills.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
main()
