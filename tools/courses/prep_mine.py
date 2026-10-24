# -*- coding: utf-8 -*-
"""Mine the Tatoeba sentences already indexed for the definition popup (public/vocab/tatoeba, CC BY 2.0 FR)
for each module of the Prepositions course: a sentence in which the module's preposition governs a noun
(or personal pronoun) in the module's case.  The noun is blanked, its dictionary form is the hint.
Writes tools/courses/prep_drills.json  {slug: [exercise, ...]} — best candidates first.
    python3 tools/courses/prep_mine.py [--per 8] [--only slug ...]
Nothing is written by us: the sentence and its translation are Tatoeba's; pymorphy3 (OpenCorpora) only
decides whether the preposition and the noun's case fit the module."""
import glob, hashlib, io, json, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import case_explain as ce
from prep_data import MODULES

M = ce.M
# Sentences that fit the pattern but not the module's meaning (found by reading the picks)
BAD = ["Нечто чрезвычайно решительное мелькнуло", "страдание выразилось в лице", "что-то страшно знакомое показалось", "Катал же ты их",
       "надо прежде всего", "Прежде всего его поразило", "Позади меня на софе", "Даже что-то вроде жалости ко мне", "Какая-то забота и вдумчивость", "настоящей краски нет",
       "Прежде деньги были", "женщин-водителей", "страдание изобразилось в лице", "Красный цвет в лице", "В лице господина Негри", "Несмотря на "]
NAME_OK = {"v-otnoshenii"}      # a place name is fine where the pool is thin
PERS = {"я", "ты", "он", "она", "оно", "мы", "вы", "они", "кто", "что"}
PO_PRP = set("приезд прибытие окончание истечение завершение возвращение получение выход выходе отъезд отбытие прочтение предъявление осмотр".split())
MOTION = set("идти ходить ехать ездить пойти поехать прийти приехать войти вернуться лететь полететь прыгнуть положить поставить бросить попасть класть "
             "сесть сидеть сесть залезть забраться подняться упасть отправиться отправить бежать побежать вбежать повесить".split())
AMB = {"в": {"accs", "loct"}, "во": {"accs", "loct"}, "на": {"accs", "loct"}, "за": {"accs", "ablt"}, "под": {"accs", "ablt"},
       "с": {"gent", "accs", "ablt"}, "со": {"gent", "accs", "ablt"}, "о": {"loct", "accs"}, "об": {"loct", "accs"}, "обо": {"loct", "accs"},
       "по": {"datv", "loct", "accs"}, "над": {"ablt"}, "надо": {"ablt"}}
MODIFIER_POS = {"ADJF", "PRTF"}


def cases_of(parses):
    return {ce._cn(p.tag.case) for p in parses if p.tag.case and ce._cn(p.tag.case) in ce.CASES}


def head_of(lw, k):
    """(index, parse) of the noun/pronoun after the preposition (up to two modifiers between), or None."""
    for n in range(3):
        if k + n >= len(lw) or not ce.WORD.fullmatch(lw[k + n]):
            return None
        w = lw[k + n]
        ps = M.parse(w)
        if any(p.tag.POS == "NUMR" for p in ps[:1]) or w.isdigit():
            return None
        pers = [p for p in ps if p.tag.POS == "NPRO" and p.normal_form in PERS]
        if pers:
            return k + n, pers[0]
        top = ps[0]
        nouns = [p for p in ps if p.tag.POS == "NOUN" and p.score >= 0.15]
        if top.tag.POS in MODIFIER_POS or (top.tag.POS == "NPRO" and top.normal_form not in PERS) or (top.tag.POS == "ADJF"):
            continue                        # a modifier: look at the next word
        if nouns:
            return k + n, nouns[0]
        return None
    return None


def load_pool():
    pool = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "public", "vocab", "tatoeba", "s*.json"))):
        for lem, v in json.load(io.open(f, encoding="utf-8")).items():
            for ru, en in v:
                pool[ru] = en
    ex = os.path.join(HERE, "prep_extra.tsv")          # sentences fetched from tatoeba.org for the rare prepositions the index lacks
    if os.path.exists(ex):
        for line in io.open(ex, encoding="utf-8"):
            a = line.rstrip("\n").split("\t")
            if len(a) >= 2:
                pool[a[0]] = a[1]
    return pool


def candidates(pool, only=None):
    idx = defaultdict(list)
    for mod in MODULES:
        if only and mod["slug"] not in only:
            continue
        for forms in mod["forms"]:
            idx[forms[0]].append((mod, forms))
    out = defaultdict(list)
    for ru, en in pool.items():
        if re.search(r"[A-Za-z0-9]", ru):
            continue
        toks = [(t.group(), t.start(), t.end()) for t in ce.TOKEN.finditer(ru)]
        lw = [t[0].lower() for t in toks]
        for i, w in enumerate(lw):
            for mod, forms in idx.get(w, ()):
                j = i + len(forms)
                if lw[i:j] != forms:
                    continue
                h = head_of(lw, j)
                if not h:
                    continue
                k, p = h
                word = toks[k][0]
                case = mod["case"]
                allp = M.parse(lw[k])
                cs = cases_of([x for x in allp if x.tag.POS in ("NOUN", "NPRO")])
                prep0 = forms[0] if len(forms) == 1 else None
                amb = AMB.get(forms[0], {case}) if len(forms) == 1 else {case}
                if case not in cs:
                    continue
                lemma = p.normal_form
                if mod["slug"] == "po-dat":
                    if lemma in PO_PRP or "datv" not in cs:
                        continue
                    amb = {"datv", "accs"}
                elif mod["slug"] == "po-prp":
                    if lemma not in PO_PRP:
                        continue
                    amb = {"loct"}
                if (cs & amb) != {case}:
                    continue
                name = word[:1].isupper() and k > 0 and mod["slug"] not in NAME_OK
                motion = any(x.normal_form in MOTION for w2 in lw for x in M.parse(w2)[:1])
                sc = -abs(len(ru) - 52) / 18.0 - (3 if name else 0)
                if case == "accs" and mod["slug"] in ("v-acc", "na-acc", "za-acc", "pod-acc"):
                    sc += 2 if motion else -1
                elif mod["slug"] in ("v-prp", "na-prp", "za-ins", "pod-ins"):
                    sc += 0 if motion else 1
                if len(ru) < 18 or len(toks) < 4:
                    sc -= 2
                sc += (int(hashlib.md5(ru.encode()).hexdigest()[:4], 16) % 100) / 400.0       # a steady shuffle
                out[mod["slug"]].append(dict(ru=ru, en=en, s=toks[k][1], e=toks[k][2], word=word, lemma=lemma, name=name, score=sc))
    return out


def book_pool(slugs):
    """Sentences of the library's public-domain books (library_sentences.tsv: ru, '', «Author, Title») containing the module's
    preposition — only for the modules Tatoeba has too few sentences for."""
    mods = [m for m in MODULES if m["slug"] in slugs]
    rx = re.compile("|".join(r"(?<![А-Яа-яЁё])" + r"\s+".join(f) + r"(?![А-Яа-яЁё])" for m in mods for f in m["forms"]), re.I)
    pool = {}
    for line in io.open(os.path.join(HERE, "library_sentences.tsv"), encoding="utf-8"):
        a = line.rstrip("\n").split("\t")
        if len(a) < 3 or any(b in a[0] for b in BAD) or not (24 <= len(a[0]) <= 120) or re.search(r"[A-Za-z0-9]", a[0]) or not rx.search(a[0]):
            continue
        pool[a[0]] = a[2]
    wk = os.path.join(HERE, "prep_wiki.tsv")      # Russian Wikipedia (CC BY-SA 4.0), where books and Tatoeba have none (в преддверии)
    if os.path.exists(wk):
        for line in io.open(wk, encoding="utf-8"):
            a = line.rstrip("\n").split("\t")
            if len(a) >= 2:
                pool[a[0]] = "Russian Wikipedia, «%s» (CC BY-SA 4.0)" % a[1]
    return pool


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    per = int(argv[argv.index("--per") + 1]) if "--per" in argv else 8
    only = set(argv[argv.index("--only") + 1:]) if "--only" in argv else None
    pool = load_pool()
    print("pool", len(pool), flush=True)
    cand = candidates(pool, only)
    outp = os.path.join(HERE, "prep_drills.json")
    res = json.load(io.open(outp, encoding="utf-8")) if (only and os.path.exists(outp)) else {}
    used = set()
    for mod in MODULES:
        slug = mod["slug"]
        if only and slug not in only:
            continue
        cs = sorted(cand.get(slug, []), key=lambda c: -c["score"])
        picked, lemmas = [], set()
        for c in cs:
            if len(picked) >= per:
                break
            if c["ru"] in used or c["lemma"] in lemmas or c["name"] or any(b in c["ru"] for b in BAD):
                continue
            q = c["ru"][:c["s"]] + "___ (" + c["lemma"] + ")" + c["ru"][c["e"]:]
            e = {"type": "fill", "q": q, "answers": [c["word"]], "prompt": c["en"]}
            r = ce.rewrite(e, {mod["case"]})
            if r is ce.DROP or not r:
                continue
            e["q"], e["why"] = r
            e.pop("_gov", None); e.pop("_conflict", None)
            picked.append(e); used.add(c["ru"]); lemmas.add(c["lemma"])
        res[slug] = picked
        print("%-18s candidates %4d  kept %d" % (slug, len(cs), len(picked)), flush=True)
    short = [m["slug"] for m in MODULES if (not only or m["slug"] in only) and len(res.get(m["slug"], [])) < 5]
    if short and "--books" in argv:
        bp = book_pool(set(short))
        print("books:", short, len(bp), flush=True)
        bc = candidates(bp, set(short))
        for slug in short:
            picked, lemmas = list(res.get(slug, [])), {e["answers"][0].lower() for e in res.get(slug, [])}
            for c in sorted(bc.get(slug, []), key=lambda c: -c["score"]):
                if len(picked) >= 5:
                    break
                if c["ru"] in used or c["word"].lower() in lemmas or c["name"]:
                    continue
                if slug == "v-lice" and not (bp[c["ru"]].startswith("Russian Wikipedia") or c["ru"].startswith(("Гроза разразилась", "Да будет проклят"))):
                    continue                    # «в лице» in books is mostly the literal «in the face»; keep only «represented by»
                q = c["ru"][:c["s"]] + "___ (" + c["lemma"] + ")" + c["ru"][c["e"]:]
                e = {"type": "fill", "q": q, "answers": [c["word"]], "prompt": bp[c["ru"]], "src": "wiki" if bp[c["ru"]].startswith("Russian Wikipedia") else "book"}
                mod = next(m for m in MODULES if m["slug"] == slug)
                r = ce.rewrite(e, {mod["case"]})
                if r is ce.DROP or not r:
                    continue
                e["q"], e["why"] = r
                e.pop("_gov", None); e.pop("_conflict", None)
                picked.append(e); used.add(c["ru"]); lemmas.add(c["word"].lower())
            res[slug] = picked
            print("%-18s with books: %d" % (slug, len(picked)), flush=True)
    io.open(outp, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
