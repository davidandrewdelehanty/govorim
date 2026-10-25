# -*- coding: utf-8 -*-
"""Practice pages for the seven pronoun lessons of «Nouns, Adjectives, and Pronouns in Cases» (p1…p7).
Sentences: Tatoeba (CC BY 2.0 FR, with its English) first, then the library's public-domain books.  Nothing is written
by us: the word is blanked where the sentence has it, the choices are the real forms, and the explanation quotes the DLI
Grammar Reference Book sentence for the rule.  pymorphy3 (OpenCorpora) only decides which sentences fit the lesson.
    python3 tools/courses/pron_course.py [--show]      (from the repo root; then finalize_outline.py)"""
import hashlib, io, json, os, random, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import case_explain as ce
import prep_mine as pm
M = ce.M
CD = os.path.join(ROOT, "public", "courses", "cases")
OUT = os.path.join(ROOT, "src", "courses-outline.js")
TOK = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)?|[^\sА-Яа-яЁё]")
DLI = "— DLI Grammar Reference Book"
SHOW = "--show" in sys.argv
BAD = ["Эта лошадь лягается", "пуки", "Палестинц", "Статуя замирает", "Пролетариям"]                                  # sentences read and rejected (substring match)

def h(s): return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)

LIBRE = re.compile(r"-(то|нибудь)\b|\b(не|ни)(кого|чего|кому|чему|кем|чем|где|куда|откуда|когда)\b|\b(себя|себе|собой|сво[а-яё]+|котор[а-яё]+|каков[аыо]?)\b", re.I)
def load_all():
    pool = [(ru, en, "") for ru, en in pm.load_pool().items()]
    lib = []
    for l in io.open(os.path.join(HERE, "library_sentences.tsv"), encoding="utf-8"):
        a = l.rstrip("\n").split("\t")
        if len(a) >= 3 and a[0] and a[2] and LIBRE.search(a[0]): lib.append((a[0], "", a[2]))
    return pool, lib

RUDE = re.compile(r"(ху[йияеёю]|пизд|\b[её]б[аеиуыл]|[зн]аеб|[её]бан|бля|трах|сук[аи]|жоп|говн|дерьм|шлюх|мудак|мудил|сра[лт]|ссать|секс|порн|голы[йем]|насил|минет|убий|изнасил|труп|пук)", re.I)
def okay(ru):
    if RUDE.search(ru) or "\ufffd" in ru or re.search(r"[^\sА-Яа-яЁё.,!?;:—–\-«»…\"']", ru): return False
    return 22 <= len(ru) <= 110 and not re.search(r"[A-Za-z0-9\[\]()]", ru) and ru.count("«") == ru.count("»") and not any(b in ru for b in BAD)

def toks(ru): return [(m.group(), m.start(), m.end()) for m in TOK.finditer(ru)]
def top(w): return M.parse(w)[0]
def isverb(w, **kw):
    p = top(w)
    return p.tag.POS in ("VERB", "INFN") and all(getattr(p.tag, k, None) == v or v in p.tag for k, v in kw.items())

def prompt_of(en, cite):
    return en if en else ("*%s*" % cite)

def mk(ru, s, e, opts, ans, why, en, cite):
    opts = list(dict.fromkeys(opts)); random.Random(h(ru)).shuffle(opts)
    return {"type": "mc", "q": ru[:s] + "___" + ru[e:], "options": opts, "answer": opts.index(ans), "why": why,
            "prompt": prompt_of(en, cite), "id": "", "context": ""}

def pick(cands, n, key=lambda c: c["k"], cap=None, per=None):
    """cands: dicts with ru, sc, k (a class or lemma); take the best n, at most `per[k]` of a class."""
    out, cnt = [], {}
    for c in sorted(cands, key=lambda c: -c["sc"]):
        k = key(c)
        if per and cnt.get(k, 0) >= per.get(k, 99): continue
        if cap and cnt.get("L" + c.get("lem", ""), 0) >= cap: continue
        out.append(c); cnt[k] = cnt.get(k, 0) + 1; cnt["L" + c.get("lem", "")] = cnt.get("L" + c.get("lem", ""), 0) + 1
        if len(out) >= n: break
    return out

def score(ru, en):
    return -abs(len(ru) - 55) / 20.0 + (1.5 if en else 0) + (h(ru) % 100) / 300.0

# ---------------------------------------------------------------- p1  -то / -нибудь
P1W = set("кто что какой чей куда где когда откуда как почему".split())
PRE1 = re.compile(r"-(то|нибудь)\b", re.I)
P1RE = re.compile(r"^([а-яё]+)-(то|нибудь)$")
Q59 = {"нибудь": "«In interrogative and imperative sentences use -нибудь.»", "то": "«In positive statements referring to the past or present use -то.»"}
def p1(pool, lib):
    cands = []
    for ru, en, cite in pool + lib:
        if not PRE1.search(ru) or not okay(ru) or ru.count("?") + ru.count("!") > 1: continue
        t = toks(ru); ws = [x[0].lower() for x in t]
        hit = [(i, P1RE.match(w)) for i, w in enumerate(ws) if P1RE.match(w)]
        if len(hit) != 1 or any(w.endswith("-либо") for w in ws): continue
        i, m = hit[0]
        if top(m.group(1)).normal_form not in P1W and not any(x.normal_form in P1W for x in M.parse(m.group(1))[:2]): continue
        if any(w in ("не", "нет", "ни", "если", "чтобы", "бы", "будет", "будут", "буду", "будешь", "будем", "будете", "пусть") for w in ws): continue
        ver = [top(w) for w in ws if re.fullmatch(r"[а-яё]+", w) and top(w).tag.POS == "VERB"]
        if any("futr" in v.tag for v in ver): continue
        q = ru.rstrip().endswith("?"); imp = any("impr" in v.tag for v in ver)
        past_or_pres = any(("past" in v.tag or "pres" in v.tag) and "impr" not in v.tag for v in ver)
        if m.group(2) == "нибудь" and (q or imp) and not (past_or_pres and not q and not imp): kind = "нибудь"
        elif m.group(2) == "то" and not q and not imp and past_or_pres: kind = "то"
        else: continue
        w0 = m.group(0); s, e = t[i][1], t[i][2]
        other = m.group(1) + "-" + ("то" if kind == "нибудь" else "нибудь")
        why = "**%s** — %s %s, Lesson 59." % (w0, Q59[kind], DLI)
        if kind == "нибудь": why = "**%s** — %s in this %s sentence. %s, Lesson 59." % (w0, "-нибудь", "interrogative" if q else "imperative", DLI) + " " + Q59[kind]
        else: why = "**%s** — a positive statement about the past or present. %s " % (w0, Q59["то"]) + DLI + ", Lesson 59."
        ex = mk(ru, s, e, [ru[s:e], other if ru[s:e][0].islower() else other.capitalize()], ru[s:e], why, en, cite)
        ex["k"] = kind; ex["lem"] = m.group(1).lower(); ex["sc"] = score(ru, en)
        cands.append(ex)
    return pick(cands, 16, per={"то": 8, "нибудь": 8}, cap=2)

# ---------------------------------------------------------------- p2 / p3  не- ... / ни- ...
PAIR2 = {"некого": "никого", "нечего": "ничего", "некому": "никому", "нечему": "ничему", "некем": "никем", "нечем": "ничем"}
PAIR3 = {"негде": "нигде", "некуда": "никуда", "неоткуда": "ниоткуда", "некогда": "никогда"}
Q_NE = "«Used with the infinitive of the verb (without НЕ) in impersonal constructions»"
Q_NI = "«Used with any negative (НЕ) form of the verb, both in personal and impersonal constructions»"
def pairs(pool, lib, PAIR, lesson, n):
    ni2ne = {v: k for k, v in PAIR.items()}
    cands = []
    pre = re.compile(r"\b(" + "|".join(list(PAIR) + list(ni2ne)) + r")\b", re.I)
    for ru, en, cite in pool + lib:
        if not pre.search(ru) or not okay(ru): continue
        t = toks(ru); ws = [x[0].lower() for x in t]
        hit = [i for i, w in enumerate(ws) if w in PAIR or w in ni2ne]
        if len(hit) != 1: continue
        i = hit[0]; w = ws[i]
        after = [x for x in ws[i + 1:i + 4] if re.fullmatch(r"[а-яё]+", x)]
        near = ws[max(0, i - 4):i + 5]
        inf_next = any(top(x).tag.POS == "INFN" for x in after[:3])
        if w in PAIR:
            if not inf_next or "не" in ws[:i] and ws[i - 1] == "не": continue
            kind, other = "не", PAIR[w]
        else:
            if inf_next or not any(x in ("не", "нет") for x in near): continue
            if w == "ничего" and any(x in ("себе", "страшного", "особенного", "хорошего", "плохого", "такого", "подобного") for x in ws[i + 1:i + 3]): continue
            if w == "никогда" and ws[i - 1:i] == ["как"]: continue
            kind, other = "ни", ni2ne[w]
        s, e = t[i][1], t[i][2]
        o = other if ru[s:e][0].islower() else other.capitalize()
        if kind == "не": why = "**%s** — followed by an infinitive, no НЕ: %s %s, Lesson %s." % (ru[s:e], Q_NE, DLI, lesson)
        else: why = "**%s** — with the negative verb: %s %s, Lesson %s." % (ru[s:e], Q_NI, DLI, lesson)
        ex = mk(ru, s, e, [ru[s:e], o], ru[s:e], why, en, cite)
        ex["k"] = kind; ex["lem"] = kind + (w if w in PAIR else ni2ne[w]); ex["sc"] = score(ru, en) + (3 if not cite else 0)
        cands.append(ex)
    return pick(cands, n, per={"не": n // 2, "ни": n // 2}, cap=2)

# ---------------------------------------------------------------- p4  себя
SEB = {"себя", "себе", "собой", "собою"}
Q64 = "«In oblique cases it is declined like the pronoun ты: себя, себе, себя, собой, о себе.»"
def p4(pool, lib):
    cands = []
    for ru, en, cite in pool + lib:
        if not re.search(r"\b(себя|себе|собой)\b", ru, re.I) or not okay(ru): continue
        t = toks(ru); ws = [x[0].lower() for x in t]
        hit = [i for i, w in enumerate(ws) if w in SEB]
        if len(hit) != 1 or "сам" in ws: continue
        i = hit[0]; s, e = t[i][1], t[i][2]; w = ws[i]
        o = [x for x in ["себя", "себе", "собой"]]
        if w == "собою": continue
        ex = mk(ru, s, e, o, ru[s:e].lower() if ru[s:e].lower() in o else ru[s:e], "**%s** — %s %s, Lesson 64." % (ru[s:e], Q64, DLI), en, cite)
        if ru[s:e][0].isupper(): continue
        ex["k"] = w; ex["lem"] = ws[i - 1] if i else ""; ex["sc"] = score(ru, en) + (3 if not cite else 0)
        cands.append(ex)
    return pick(cands, 12, per={"себя": 4, "себе": 4, "собой": 4}, cap=2)

# ---------------------------------------------------------------- p5  свой
SVOI_F = ["свой", "своя", "своё", "свои", "своего", "своей", "своему", "своём", "своим", "свою", "своих", "своими"]
def gn(p):
    t = p.tag
    return ("plur",) if "plur" in t else (next((g for g in ("masc", "femn", "neut") if g in t), None),)
def svoi_ok(form, g):
    """could `form` (a string) be a form of свой agreeing with gender/number g = ('plur',) | ('masc',) …"""
    for p in M.parse(form):
        if p.normal_form != "свой": continue
        if g == ("plur",) and "plur" in p.tag: return True
        if g != ("plur",) and "sing" in p.tag and (g[0] in p.tag or "ms-f" in p.tag or "GNdr" in p.tag): return True
    return False
Q49 = "«The word \"свой\" is declined like \"мой\".»"
OWN = {"his": "его", "her": "её", "their": "их"}
def p5(pool, lib):
    agree, own = [], []
    for ru, en, cite in pool + lib:
        if not re.search(r"\bсво[а-яё]+\b", ru, re.I) or not okay(ru): continue
        t = toks(ru); ws = [x[0].lower() for x in t]
        hit = [i for i, w in enumerate(ws) if w in SVOI_F + ["своё", "свое", "своем", "своею", "своею"]]
        if len(hit) != 1: continue
        i = hit[0]
        if i + 1 >= len(ws) or not re.fullmatch(r"[а-яё]+", ws[i + 1]): continue
        nps = [p for p in M.parse(ws[i + 1]) if p.tag.POS == "NOUN" and p.score >= 0.1]
        if not nps: continue
        gns = {gn(p) for p in nps}
        if len(gns) != 1: continue
        g = gns.pop()
        if g[0] is None: continue
        w = ws[i]; s, e = t[i][1], t[i][2]
        if ru[s:e][0].isupper(): continue
        dis = [f for f in SVOI_F if not svoi_ok(f, g) and f != w]
        if len(dis) < 3: continue
        rnd = random.Random(h(ru)); rnd.shuffle(dis)
        opts = [ru[s:e]] + dis[:3]
        nn = ru[t[i + 1][1]:t[i + 1][2]]
        gname = {"plur": "plural", "masc": "masculine singular", "femn": "feminine singular", "neut": "neuter singular"}[g[0]]
        why = "**%s** agrees with **%s** (%s). %s %s, Lesson 49." % (ru[s:e], nn, gname, Q49, DLI)
        ex = mk(ru, s, e, opts, ru[s:e], why, en, cite)
        ex["k"] = "a"; ex["lem"] = ws[i - 1]; ex["sc"] = score(ru, en) + (3 if not cite else 0)
        agree.append(ex)
        # «his own / her own / their own»: свой, not его / её / их
        m = re.search(r"\b(his|her|their) own\b", en or "")
        if m and not cite and w in ("свой", "своя", "своё", "свои", "своего", "своей", "своему", "своём", "своим", "свою", "своих", "своими"):
            p = OWN[m.group(1)]
            why2 = ("**%s** — the object belongs to the performer of the action (\"%s own\"): \"свой\" must be used, not \"%s\". %s %s, Lesson 49."
                    % (ru[s:e], m.group(1), p, "«If the object belongs to the performer of the action, the possessive \"свой\" must be used.»", DLI))
            ex2 = mk(ru, s, e, [ru[s:e], p], ru[s:e], why2, en, cite)
            ex2["k"] = "o"; ex2["lem"] = nn.lower(); ex2["sc"] = score(ru, en) + 1
            own.append(ex2)
    return pick(agree, 7, cap=1) + pick(own, 7, cap=1)

# ---------------------------------------------------------------- p6  который
KOT = ["который", "которая", "которое", "которые", "которого", "которой", "которому", "котором", "которым", "которую", "которых", "которыми"]
def kot_ok(form, g):
    for p in M.parse(form):
        if p.normal_form != "который": continue
        if g == ("plur",) and "plur" in p.tag: return True
        if g != ("plur",) and "sing" in p.tag and (g[0] in p.tag or "GNdr" in p.tag or "ms-f" in p.tag): return True
    return False
def p6(pool, lib):
    cands = []
    for ru, en, cite in pool + lib:
        if not re.search(r"\bкотор[а-яё]+\b", ru, re.I) or not okay(ru): continue
        t = toks(ru); ws = [x[0].lower() for x in t]
        hit = [i for i, w in enumerate(ws) if w in KOT]
        if len(hit) != 1: continue
        i = hit[0]
        j = i - 1
        if j >= 0 and ws[j] in ("в", "на", "с", "о", "из", "у", "для", "к", "по", "за", "от", "до", "при", "над", "под", "без", "про", "со", "во", "об", "перед", "между", "через") and j >= 1: j -= 1
        if j < 1 or ws[j] != ",": continue
        k = j - 1
        if not re.fullmatch(r"[а-яё]+", ws[k]): continue
        nps = [p for p in M.parse(ws[k]) if p.tag.POS == "NOUN" and p.score >= 0.1]
        if not nps or top(ws[k]).tag.POS != "NOUN": continue
        gns = {gn(p) for p in nps}
        if len(gns) != 1: continue
        g = gns.pop()
        if g[0] is None: continue
        w = ws[i]; s, e = t[i][1], t[i][2]
        if ru[s:e][0].isupper(): continue
        dis = [f for f in KOT if not kot_ok(f, g) and f != w]
        if len(dis) < 3: continue
        rnd = random.Random(h(ru)); rnd.shuffle(dis)
        gname = {"plur": "plural", "masc": "masculine singular", "femn": "feminine singular", "neut": "neuter singular"}[g[0]]
        nn = ru[t[k][1]:t[k][2]]
        why = ("**%s** — it refers to **%s** (%s), and its case is that of its own clause. «\"Который\" in subordinate clauses agrees in gender and number with the noun it refers to in the main sentence, but its case is determined by its function in the subordinate clause.» %s, Lesson 53."
               % (ru[s:e], nn, gname, DLI))
        ex = mk(ru, s, e, [ru[s:e]] + dis[:3], ru[s:e], why, en, cite)
        ex["k"] = g[0]; ex["lem"] = nn.lower(); ex["sc"] = score(ru, en) + (3 if not cite else 0)
        cands.append(ex)
    return pick(cands, 14, per={"masc": 4, "femn": 4, "neut": 2, "plur": 4}, cap=1)

# ---------------------------------------------------------------- p7  каков
KAK = ["каков", "какова", "каково", "каковы"]
GN_FORM = {"каков": ("masc",), "какова": ("femn",), "каково": ("neut",), "каковы": ("plur",)}
GN_NAME = {"masc": "masculine singular", "femn": "feminine singular", "neut": "neuter singular", "plur": "plural"}
def p7(pool, lib):
    cands = []
    for ru, en, cite in pool + lib:
        if not re.search(r"\bкаков[аыо]?\b", ru, re.I) or not okay(ru): continue
        t = toks(ru); ws = [x[0].lower() for x in t]
        hit = [i for i, w in enumerate(ws) if w in KAK]
        if len(hit) != 1 or any(w in ("таков", "такова", "таково", "таковы") for w in ws): continue
        i = hit[0]; s, e = t[i][1], t[i][2]; w = ws[i]
        subj = None
        for j in range(i + 1, min(i + 5, len(ws))):
            if not re.fullmatch(r"[а-яё]+", ws[j]): break
            ps = [p for p in M.parse(ws[j]) if p.tag.POS == "NOUN" and "nomn" in p.tag and p.score >= 0.1]
            if ps and top(ws[j]).tag.POS == "NOUN":
                gs = {gn(p) for p in ps}
                if len(gs) == 1: subj = (j, gs.pop())
                break
        if not subj or subj[1] != GN_FORM[w]: continue
        nn = ru[t[subj[0]][1]:t[subj[0]][2]]
        opts = [(f if ru[s:e][0].islower() else f.capitalize()) for f in KAK]
        why = "**%s** — a short-form adjective agreeing with the subject **%s** (%s). Wiktionary, «каков» (en.wiktionary.org, CC BY-SA 4.0)." % (ru[s:e], nn, GN_NAME[subj[1][0]])
        ex = mk(ru, s, e, opts, ru[s:e], why, en, cite)
        ex["k"] = w; ex["lem"] = nn.lower(); ex["sc"] = score(ru, en) + (3 if not cite else 0)
        cands.append(ex)
    return pick(cands, 12, per={"каков": 3, "какова": 3, "каково": 3, "каковы": 3}, cap=1)

def main():
    pool, lib = load_all()
    res = {"p1-to-nibud": p1(pool, lib), "p2-nekogo": pairs(pool, lib, PAIR2, "104", 12), "p3-negde": pairs(pool, lib, PAIR3, "105", 14),
           "p4-sebya": p4(pool, lib), "p5-svoi": p5(pool, lib), "p6-kotoryi": p6(pool, lib), "p7-kakov": p7(pool, lib)}
    if SHOW:
        for k, v in res.items():
            print("==", k, len(v))
            for x in v:
                print("  %-7s %s  [%s]  %s" % (x.get("k"), x["q"], x["options"][x["answer"]], (x["prompt"] or "")[:60]))
    write(res)

NOTE = {"t": "note", "text": "Exercises: sentences from Tatoeba (tatoeba.org, CC BY 2.0 FR) and from the library's public-domain books; word forms checked with the OpenCorpora dictionary (CC BY-SA 4.0)."}

P2_TABLE = {"t": "table", "head": ["", "Used with the infinitive of the verb (without НЕ) in impersonal constructions", "Used with any negative (НЕ) form of the verb, both in personal and impersonal constructions"],
            "rows": [["Gen.", "некого, нечего", "никого, ничего"], ["Dat.", "некому, нечему", "никому, ничему"], ["Instr.", "некем, нечем", "никем, ничем"], ["Prep.", "не о ком, не о чем", "ни о ком, ни о чём"]],
            "rowHeads": True, "fit": True,
            "caption": "Negative pronouns: forms. The headings are DLI Grammar Reference Book, Lesson 105: the adverbs «are formed by the same principle as negative pronouns НЕКОГО, НЕЧЕГО»."}

def write(res):
    t = io.open(OUT, encoding="utf-8").read()
    cur = json.loads(t[t.index("export default ") + 15:].rstrip().rstrip(";"))
    m = next(c for c in cur if c["id"] == "cases")
    secs = m["sections"]
    # p2 page: forms table (once)
    pp = os.path.join(CD, "p2-nekogo.json"); pj = json.load(io.open(pp, encoding="utf-8"))
    if not any(b.get("t") == "table" for b in pj["blocks"]):
        pj["blocks"].insert(0, P2_TABLE)
        io.open(pp, "w", encoding="utf-8").write(json.dumps(pj, ensure_ascii=False))
    for lid, exs in res.items():
        if not exs: continue
        for i, e in enumerate(exs): e["id"] = "q%d" % (i + 1); e.pop("k", None); e.pop("lem", None); e.pop("sc", None)
        sid = lid + "-practice"
        title = "Practice: " + next(x["title"] for x in secs if x["id"] == lid)
        io.open(os.path.join(CD, sid + ".json"), "w", encoding="utf-8").write(json.dumps({"id": sid, "title": title, "blocks": [NOTE], "exercises": exs}, ensure_ascii=False))
        secs[:] = [x for x in secs if x["id"] != sid]
        k = next(i for i, x in enumerate(secs) if x["id"] == lid)
        secs.insert(k + 1, {"id": sid, "title": title, "n": len(exs)})
        print("wrote", sid, len(exs))
    io.open(OUT, "w", encoding="utf-8").write("// Written by tools/courses/build_courses.py — the courses, their sections and\n// how many exercises each has. The lessons themselves are in public/courses/.\nexport default " + json.dumps(cur, ensure_ascii=False, indent=1) + ";\n")

if __name__ == "__main__":
    main()
