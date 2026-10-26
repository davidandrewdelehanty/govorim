# -*- coding: utf-8 -*-
"""Word families for the define popup: look up чувствовать and see чу́вство (noun) — "sense, feeling".

Every link is one the English Wiktionary documents (CC BY-SA 4.0) — nothing is inferred from spelling:
  * «made from»: the words a word's etymology says it is built on ({{af}}, {{surf}}, {{deverbal}}, {{back-form}} …);
  * «built on it»: the words whose etymology names this word;
  * «same root»: the root families of the Word Formation course (a root entry's Derived/Related terms, kept only
    where each word's own etymology links it to the family).
Each family word carries Wiktionary's part of speech and first definition. Common words only (library frequency).

Writes public/vocab/families/index.json and fNN.json, sharded by the same FNV-1a hash as the Tatoeba shards, so the
popup fetches one small file for the lemma it is showing.
    python3 tools/courses/wordform/wf_families.py
"""
import io, json, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import wf_course as C

SHOW = 20000      # frequency rank: furthest a family word may be
MAX = 12
SHARDS = 16
OUT = os.path.join(ROOT, "public", "vocab", "families")

def fnv1a(s):
    h = 0x811C9DC5
    for ch in s:
        # JS charCodeAt gives UTF-16 code units; every Cyrillic letter is one unit
        h ^= ord(ch); h = (h * 0x01000193) & 0xFFFFFFFF
    return h

def short(g, n=110):
    """Never cut a definition mid-word: keep whole senses up to n characters, or nothing."""
    if len(g) <= n: return g
    cut = max(g.rfind("; ", 0, n), g.rfind(", ", 0, n))
    return g[:cut] if cut > 20 and g[:cut].count("(") == g[:cut].count(")") else ""

def item(w, rel):
    return [C.acc(w), C.pos(w), short(C.gloss1(w)), rel]

def main():
    words = [w for w in C.WORDS if C.defs(w) and C.ok(w)]
    links = {w: {x for x in C.etym_links(w) if x in C.WORDS and x != w and C.ok(x) and "%s>%s" % (w, x) not in C.LINKS} for w in words}
    built_on = collections.defaultdict(set)
    for w, bs in links.items():
        for b in bs: built_on[b].add(w)
    fam_of = collections.defaultdict(set)
    import glob as _g
    taught = {json.load(io.open(f, encoding="utf-8"))["title"] for f in _g.glob(os.path.join(ROOT, "public", "courses", "wordform", "r*.json"))}
    for r in C.ROOTS:
        if r not in C.WORDS or ("The family of %s" % C.acc(r)) not in taught: continue      # only the families the course teaches (and its review checked)
        f = C.family(r)
        for w in f: fam_of[w] |= set(f)
    out = {}
    for w in words:
        seen, rows = {w}, []
        for rel, group in (("made from", links.get(w, ())), ("built on it", built_on.get(w, ())), ("same root", fam_of.get(w, ()))):
            for x in sorted(group, key=C.rank):
                if x in seen or not C.defs(x) or (C.rank(x) > SHOW and rel != "made from"): continue
                if x in C.FAM_GLOSS or not short(C.gloss1(x)): continue               # the review found its first definition misleading
                if len(C.ent(x)) > 1: continue                                       # several entries (мир «peace» / «world»): which one is meant is not documented
                seen.add(x); rows.append(item(x, rel))
        if rows: out[w] = rows[:MAX]
    os.makedirs(OUT, exist_ok=True)
    shards = collections.defaultdict(dict)
    for w, rows in out.items(): shards[fnv1a(w) % SHARDS][w] = rows
    for k in range(SHARDS):
        io.open(os.path.join(OUT, "f%02d.json" % k), "w", encoding="utf-8").write(json.dumps(shards.get(k, {}), ensure_ascii=False, separators=(",", ":")))
    io.open(os.path.join(OUT, "index.json"), "w", encoding="utf-8").write(json.dumps(
        {"shards": SHARDS, "words": len(out), "source": "English Wiktionary (CC BY-SA 4.0): etymologies, derived and related terms, definitions"}))
    print("families for", len(out), "words")

if __name__ == "__main__":
    main()
