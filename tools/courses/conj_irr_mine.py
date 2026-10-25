# -*- coding: utf-8 -*-
"""Tatoeba sentences (CC BY 2.0 FR) with a finite form of one of the verbs on the site's irregular-verbs list (src/verbs-irregular.json):
tools/courses/conj_irr_drills.json  {group: [[sentence, translation, verb, form, kind, who], …]}.
The dictionary only decides whether the word is that verb in that form; nothing is written by us.   (run from the repo root)"""
import sys, os, json, re, io, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import case_explain as CE
import verb_notes as VN
from prep_mine import load_pool
M = VN.M
RUDE = re.compile(r"(ху[йияеёю]|пизд|[её]б[аеиуыл]|бля|трах|сук[аи]|жоп|говн|дерьм|шлюх|мудак|мудил|сра[лт]|ссать|секс|порн|голы[йем]|насил|минет|убий|изнасил|труп)", re.I)
def main():
    groups = json.load(open(os.path.join(HERE, "..", "..", "src", "verbs-irregular.json"), encoding="utf-8"))["groups"]
    fm = {}; bad = set()
    for g in groups:
        for v, *_ in g["verbs"]:
            try: lx = VN.entry_lexeme(v)
            except Exception: continue
            for f in lx:
                t = set(str(f.tag).replace(" ", ",").split(","))
                if "VERB" not in t or not (t & {"pres", "futr", "past"}) or t & set(VN.P.DROP) or "impr" in t: continue
                w = VN.fold(f.word)
                if w in fm and fm[w] != (g["id"], v): bad.add(w)
                fm[w] = (g["id"], v)
    for w in bad: fm.pop(w, None)
    print("forms", len(fm))
    sents = load_pool()
    out = collections.defaultdict(list)
    for ru, en in sents.items():
        s = ru.strip()
        if not (24 <= len(s) <= 100) or re.search(r"[A-Za-z\d]", s) or s.count(",") > 3 or RUDE.search(s): continue
        toks = [t.group() for t in CE.TOKEN.finditer(s)]
        hits = [(i, VN.fold(t)) for i, t in enumerate(toks) if CE.WORD.fullmatch(t) and VN.fold(t) in fm]
        if len(hits) != 1: continue
        i, w = hits[0]; z, v = fm[w]; word = toks[i]
        top = M.parse(word.lower())[0]
        if top.tag.POS != "VERB" or (VN.fold(top.normal_form) != v and not v.endswith("ся")) or top.score < 0.55: continue
        got = VN.analyze(v, word)
        if len(got) != 1: continue
        kind, who = next(iter(got))
        out[z].append([s, en, v, word, kind, who])
    for z, rows in out.items():
        print(z, len(rows), collections.Counter(r[2] for r in rows).most_common(6))
    io.open(os.path.join(HERE, "conj_irr_drills.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
main()
