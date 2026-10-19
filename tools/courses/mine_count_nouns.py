"""Countable nouns from the library's own Russian (and Tatoeba): the commonest
nouns that turn up in the plural, with the three forms counting needs."""
import collections, io, json, re, sys
import pymorphy3
M = pymorphy3.MorphAnalyzer()
BAD = {"Sgtm", "Pltm", "Fixd", "Name", "Surn", "Patr", "Geox", "Orgn", "Abbr", "Trad", "Infr", "Slng", "Arch", "Erro", "Dist", "Init", "Ms-f", "Anum"}
W = re.compile(r"[а-яё]+")
lem_n = collections.Counter(); plur = collections.Counter(); seen = {}
files = sys.argv[1:]
for f in files:
    for k, line in enumerate(io.open(f, encoding="utf-8")):
        cols = line.split("\t")
        ru = cols[0] if f.endswith("library_sentences.tsv") else (cols[1] if len(cols) > 1 else "")
        for w in W.findall(ru.lower()):
            r = seen.get(w)
            if r is None:
                p = M.parse(w)[0]
                t = set(str(p.tag).replace(" ", ",").split(","))
                r = (p.normal_form, "plur" in t) if p.tag.POS == "NOUN" and p.score >= 0.5 and not (t & BAD) else False
                seen[w] = r
            if r:
                lem_n[r[0]] += 1
                if r[1]: plur[r[0]] += 1
out = []
for lem, n in lem_n.most_common():
    if plur[lem] < 3 or len(lem) < 3:
        continue
    p = next((q for q in M.parse(lem) if q.tag.POS == "NOUN" and q.normal_form == lem and q.tag.case == "nomn" and q.tag.number == "sing"), None)
    if not p:
        continue
    t = set(str(p.tag).replace(" ", ",").split(","))
    if t & BAD or p.tag.gender not in ("masc", "femn", "neut"):
        continue
    gs = p.inflect({"gent", "sing"}); gp = p.inflect({"gent", "plur"})
    if not gs or not gp:
        continue
    out.append([lem, gs.word, gp.word, p.tag.gender[0]])
    if len(out) >= 2500:
        break
json.dump({"n": out}, io.open("count-nouns.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(out), out[:15], out[-5:])
