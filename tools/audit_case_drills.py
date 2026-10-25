#!/usr/bin/env python3
"""Case-drill audit (Oct 2026).

Keeps a case drill only when the case of its blank can be proved from the
sentence, and makes sure no wrong option is also grammatical there:

  * the sentence (with the answer filled in) is parsed by Natasha;
  * the blank's case must be decided by something in it: a preposition
    standing right before it, a verb it is the subject of (and agrees with),
    a verb it is the object of (with a separate subject, so an inanimate
    accusative cannot be a nominative), a noun it depends on, a word of
    quantity, a negated verb, a verb that governs a case (бояться, помогать,
    заниматься …), a copula (стать, казаться …), a passive participle, or a
    time expression — the governing word in the blank's own clause;
  * every case that could also be grammatical in that spot (в + acc/prep,
    acc/gen after a verb, nom/instr after быть …) is kept out of the options;
    the options are rebuilt from pymorphy3's dictionary inflection;
  * a drill whose answer is the same word form as another viable case is
    dropped, since its case cannot be told;
  * the explanation names the construction: «в» + prepositional (где?) …,
    the subject of «сказал», «помогать» takes the dative, and so on.

Drills that fail any test are dropped; a chapter file left with none is
deleted.  Run it after tools/make_case_drills.py generates new drills.

    # WSL, once:  pip install natasha pymorphy3
    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/audit_case_drills.py                 # report only
    python3 tools/audit_case_drills.py --apply         # rewrite the files
    python3 tools/audit_case_drills.py --apply some-book__ch3.json
"""
# with...), rebuild its options so that no wrong option is also grammatical,
import re, random

CODE = [("Именит", "nomn"), ("Nominative", "nomn"), ("Родит", "gent"), ("Genitive", "gent"),
        ("Датель", "datv"), ("Dative", "datv"), ("Винит", "accs"), ("Accusative", "accs"),
        ("Творит", "ablt"), ("Instrumental", "ablt"), ("Предлож", "loct"), ("Prepositional", "loct"),
        ("Locative", "loct")]
LABEL = {"nomn": "Именительный (Nominative)", "gent": "Родительный (Genitive)", "datv": "Дательный (Dative)",
         "accs": "Винительный (Accusative)", "ablt": "Творительный (Instrumental)", "loct": "Предложный (Prepositional)"}
NAME = {"nomn": "nominative", "gent": "genitive", "datv": "dative", "accs": "accusative", "ablt": "instrumental", "loct": "prepositional"}
CASES = ["nomn", "gent", "datv", "accs", "ablt", "loct"]

def case_code(label):
    lab = label or ""
    if "Passive" in lab or "Звательный" in lab: return None
    found = {c for k, c in CODE if k in lab}
    return found.pop() if len(found) == 1 else None

# ── prepositions ─────────────────────────────────────────────────────────────
G, D, A, I, P = "gent", "datv", "accs", "ablt", "loct"
PREP = {}
for w in ("без безо для до из изо из-за из-под от ото у около после кроме мимо вокруг возле вдоль вместо среди "
          "посреди против ради сверх вне внутри позади впереди накануне подле близ вследствие насчёт насчет "
          "напротив вроде помимо поверх сзади вблизи изнутри").split():
    PREP[w] = {G}
for w in "к ко благодаря вопреки навстречу согласно подобно".split(): PREP[w] = {D}
for w in "про через чрез сквозь спустя".split(): PREP[w] = {A}
for w in "над надо перед передо пред предо".split(): PREP[w] = {I}
PREP["при"] = {P}
for w in "в во на".split(): PREP[w] = {A, P}
for w in "за под подо".split(): PREP[w] = {A, I}
for w in "о об обо".split(): PREP[w] = {P, A}
PREP["по"] = {D, P, A}
for w in "с со".split(): PREP[w] = {G, I, A}
for w in "между меж".split(): PREP[w] = {I, G}
NORM = {"во": "в", "со": "с", "ко": "к", "об": "о", "обо": "о", "изо": "из", "ото": "от", "безо": "без",
        "надо": "над", "передо": "перед", "подо": "под", "предо": "пред", "чрез": "через", "насчет": "насчёт"}

def prep_expl(p, case):
    q = NORM.get(p, p)
    multi = len(PREP.get(p, ())) > 1
    if not multi:
        return "«%s» always takes the %s" % (q, NAME[case])
    T = {
        ("в", P): "«в» takes the prepositional here (где? в чём?) — the accusative would mean movement into (куда? во что?)",
        ("в", A): "«в» takes the accusative here (куда? во что? когда?) — the prepositional would mean where something is (где? в чём?)",
        ("на", P): "«на» takes the prepositional here (где? на чём?) — the accusative would mean movement onto (куда? на что?)",
        ("на", A): "«на» takes the accusative here (куда? на что? на сколько?) — the prepositional would mean where something is (где? на чём?)",
        ("за", I): "«за» takes the instrumental here (где? за чем? за кем?) — the accusative would mean motion behind or 'for' (куда? за что?)",
        ("за", A): "«за» takes the accusative here (куда? за что? за кого?) — the instrumental would mean position behind or at (где? за чем?)",
        ("под", I): "«под» takes the instrumental here (где? под чем?) — the accusative would mean movement under (куда? под что?)",
        ("под", A): "«под» takes the accusative here (куда? под что? or near a time — под вечер) — the instrumental would mean position under (где? под чем?)",
        ("о", P): "«о» + prepositional (о ком? о чём?): about",
        ("о", A): "«о» + accusative (обо что?): against — striking or touching something",
        ("по", D): "«по» + dative (по чему? по кому?): its usual case — along, around, through, by, according to, or missing someone",
        ("по", P): "«по» + prepositional: after (по приезде, по окончании)",
        ("по", A): "«по» + accusative: up to (по колено), or so many each (по два)",
        ("с", G): "«с» takes the genitive here (с чего? откуда? с каких пор?): from, off, since — with the instrumental it would mean 'with'",
        ("с", I): "«с» takes the instrumental here (с кем? с чем?): with — with the genitive it would mean 'from, off'",
        ("с", A): "«с» + accusative: about, approximately, or the size of (с неделю, с дом)",
        ("между", I): "«между» + instrumental: between",
        ("между", G): "«между» + genitive: between (the older usage)",
        ("меж", I): "«меж» + instrumental: between",
        ("меж", G): "«меж» + genitive: between (the older usage)",
    }
    return T.get((q, case))

# ── verbs and words that govern a case ──────────────────────────────────────
GEN_VERBS = set("""бояться побояться опасаться избегать избежать достигать достичь достигнуть добиваться добиться
касаться коснуться лишать лишить лишаться лишиться стыдиться постыдиться пугаться испугаться слушаться послушаться
держаться придерживаться заслуживать сторониться остерегаться чуждаться страшиться устрашиться""".split())
GEN_ALT_VERBS = set("""ждать дожидаться дождаться ожидать подождать искать поискать просить попросить требовать
потребовать хотеть захотеть желать пожелать жаждать""".split())
DAT_VERBS = set("""помогать помочь мешать помешать верить поверить доверять доверить звонить позвонить отвечать ответить
советовать посоветовать нравиться понравиться принадлежать угрожать грозить пригрозить радоваться обрадоваться
удивляться удивиться завидовать позавидовать сочувствовать следовать последовать подражать противоречить
соответствовать уступать уступить повиноваться подчиняться подчиниться кланяться поклониться улыбаться улыбнуться
аплодировать сопротивляться мстить отомстить приказывать приказать разрешать разрешить запрещать запретить
сниться присниться надоедать надоесть предшествовать способствовать содействовать препятствовать вредить
навредить льстить польстить изумляться изумиться дивиться покоряться покориться внимать вторить
учиться научиться обучаться обучиться""".split())
INSTR_VERBS = set("""заниматься заняться интересоваться заинтересоваться увлекаться увлечься гордиться пользоваться
воспользоваться владеть овладеть управлять руководить командовать заведовать обладать восхищаться любоваться
полюбоваться наслаждаться насладиться дорожить жертвовать пожертвовать рисковать хвастаться похвастаться
злоупотреблять торговать болеть заболеть пахнуть запахнуть повелевать распоряжаться располагать пренебрегать
пренебречь брезговать гнушаться довольствоваться ограничиваться ограничиться""".split())
COPULAS = set("""быть стать становиться являться явиться казаться показаться оказаться оказываться считаться
называться назваться остаться оставаться делаться сделаться работать бывать слыть прослыть притворяться
притвориться представляться""".split())
PRED2 = set("""называть назвать считать счесть сделать делать выбрать избрать назначить назначать признать
признавать объявить объявлять звать""".split())
ACC_INSTR = set("бросать бросить кидать кинуть швырять швырнуть махать махнуть двигать двинуть шевелить шевельнуть "
                "качать качнуть трясти тряхнуть крутить вертеть жертвовать пожертвовать рисковать менять".split())
ACC_DAT = set("писать написать учить научить отвечать ответить".split())
QUANT = set("много мало немного немало несколько сколько столько сколько-нибудь больше меньше полно достаточно "
            "множество масса уйма пол".split())
DAT_ADJ = set("подобный верный равный благодарный послушный свойственный чуждый рад нужный".split())
NMOD_DAT = set("письмо подарок памятник помощь ответ благодарность привет поклон приказ указание совет угроза "
               "песня гимн хвала слава честь дань вера доверие любовь ненависть сочувствие пособие учебник "
               "конец смерть цена счёт отчёт препятствие равный враг друг".split())
NMOD_INSTR = set("руководство управление владение занятие интерес увлечение торговля командование обмен "
                 "восхищение любование наслаждение пользование злоупотребление".split())
TIME_INSTR = set("утро вечер день ночь весна лето осень зима".split())
TIME_ACC = set("день ночь неделя месяц год час минута секунда время вечер утро зима лето весна осень жизнь век "
               "сутки раз мгновение миг".split())

class Tok:
    __slots__ = ("id", "text", "pos", "rel", "head", "f", "start", "stop", "i")
    def __init__(self, t, i):
        self.id, self.text, self.pos, self.rel, self.head, self.f, self.start, self.stop = t; self.i = i

VERBISH = ("VERB", "INFN", "GRND", "PRTF", "PRTS")
def lemma_of(morph, tok, pos=None):
    best = None
    for p in morph.parse(tok.text.lower()):
        if pos == "VERB":
            if not any(x in p.tag for x in VERBISH): continue
        elif pos and pos not in p.tag: continue
        best = p.normal_form; break
    return best or tok.text.lower()

def has_other_subject(morph, h, kids):
    if h.f.get("Person") in ("1", "2") or h.f.get("Mood") == "Imp": return True
    for t in kids(h):
        if not t.rel.startswith("nsubj") or t.f.get("Case") != "Nom": continue
        if not any("nomn" in p.tag for p in morph.parse(t.text.lower())): continue
        if h.f.get("Number") and t.f.get("Number") and h.f.get("Number") != t.f.get("Number"): continue
        return True
    return False

DITRANS = set("""дать давать передать передавать сказать говорить показать показывать послать посылать
написать отдать отдавать подарить дарить продать продавать купить покупать объяснить объяснять
обещать пообещать предложить предлагать сообщить сообщать принести приносить велеть позволить позволять
вручить вручать доверить поручить поручать оставить оставлять отправить отправлять возвратить вернуть
бросить подать подавать протянуть протягивать""".split())

def analyse(drill, parse, morph):
    """Return (verdict, info). verdict: 'keep' or a reason for dropping."""
    case = case_code(drill.get("case"))
    if not case: return "label", None
    if not parse: return "noparse", None
    toks = [Tok(t, i) for i, t in enumerate(parse["toks"])]
    byid = {t.id: t for t in toks}
    b0, b1 = parse["b"]
    inside = [t for t in toks if t.start >= b0 and t.stop <= b1]
    nouns = [t for t in inside if t.pos in ("NOUN", "PROPN")]
    if len(inside) != len(drill["correct"].split()) or not nouns: return "blank-tokens", None
    noun = nouns[-1]
    # every other blank word must agree with (depend on) the noun
    for t in inside:
        if t is not noun and t.head != noun.id: return "blank-structure", None
    if (noun.f.get("Case") or "") and {"Nom": "nomn", "Gen": "gent", "Dat": "datv", "Acc": "accs", "Ins": "ablt", "Loc": "loct"}.get(noun.f.get("Case")) != case:
        return "parser-disagrees", None
    kids = lambda x: [t for t in toks if t.head == x.id]
    # the role is the first conjunct's
    n = noun
    hops = 0
    while n.rel == "conj" and n.head in byid and hops < 5:
        n = byid[n.head]; hops += 1
        if n.pos not in ("NOUN", "PROPN", "PRON"): return "conj-odd", None
    # ── preposition ──
    preps = [t for t in kids(n) if t.rel == "case" and t.pos == "ADP"]
    if noun is not n:
        own = [t for t in kids(noun) if t.rel == "case" and t.pos == "ADP"]
        if own: preps = own
    if preps:
        if len(preps) > 1: return "multi-prep", None
        p = preps[0]; pw = p.text.lower()
        if pw not in PREP: return "prep-unknown", None
        # nothing but the noun's own modifiers between preposition and blank
        first = min(inside, key=lambda t: t.i)
        for t in toks[p.i + 1:first.i]:
            if t.head not in (noun.id, n.id) or t.rel not in ("amod", "det", "nummod", "nummod:gov"):
                return "prep-gap", None
        if case not in PREP[pw]: return "prep-case-mismatch", None
        # compound prepositions («в течение», «несмотря на») leave the noun's
        # own preposition fine; but a noun preposition («в течение ___») makes
        # the blank depend on that noun — handled below as nmod, not here.
        ex = prep_expl(pw, case)
        if not ex: return "prep-no-expl", None
        viable = set(PREP[pw])
        if NORM.get(pw, pw) == "по": viable.discard(P) if case != P else None
        return "keep", {"viable": viable, "why": ex, "kind": "prep:" + NORM.get(pw, pw)}
    if hops: return "conj-no-prep", None
    # a preposition just before the blank (past the noun's own modifiers)
    # that the parse did not attach to it: the parse is not to be trusted
    first = min(inside, key=lambda t: t.i)
    j = first.i - 1
    while j >= 0 and toks[j].head == noun.id and toks[j].rel in ("amod", "det", "nummod"): j -= 1
    if j >= 0 and toks[j].pos == "ADP": return "stray-prep", None
    if j >= 0 and toks[j].pos in ("ADJ", "DET") and toks[j].head != noun.id: return "stray-modifier", None
    h = byid.get(n.head)
    rel = n.rel
    if h is None: return "nohead", None
    # the governing word must be in the blank's own clause: nothing verbal
    # and no clause boundary between them
    lo, hi = sorted((h.i, first.i))
    last = max(inside, key=lambda t: t.i)
    if h.i > last.i: lo, hi = last.i, h.i
    between = [t for t in toks[lo + 1:hi] if t not in inside]
    if any(t.pos in ("VERB", "AUX") for t in between): return "far-head", None
    if any(t.text in (";", ":", "—", "–", "(", ")") for t in between): return "far-head", None
    if any(t.text == "," for t in between) and h.pos in ("NOUN", "PROPN"): return "far-head", None
    if len(between) > 8: return "far-head", None
    hl = lemma_of(morph, h, "VERB" if h.pos in ("VERB", "AUX") else None) if h.pos in ("VERB", "AUX") else lemma_of(morph, h)
    neg = any(t.text.lower() in ("не", "ни") for t in kids(h)) or h.text.lower() == "нет"
    for a in kids(h):
        if a.rel in ("aux", "aux:pass", "cop") and any(t.text.lower() == "не" for t in kids(a)): neg = True
    cop = [t for t in kids(n) if t.rel == "cop" and t.i < n.i and n.i - t.i <= 4
           and not any(x.pos in ("VERB",) for x in toks[t.i + 1:n.i])]
    nl = lemma_of(morph, noun, "NOUN")
    anim_note = ""
    if case == "nomn":
        if rel in ("nsubj", "nsubj:pass"):
            if h.pos not in ("VERB", "AUX"): return "subj-nonverb", None
            if any(t.rel.startswith("nsubj") and t is not n for t in kids(h)): return "two-subjects", None
            if h.pos in ("VERB", "AUX"):
                num = h.f.get("Number"); nn = noun.f.get("Number")
                if h.f.get("VerbForm") == "Fin" or h.f.get("Tense"):
                    if num and nn and num != nn: return "subj-agreement", None
                    if h.f.get("Tense") == "Past" and nn == "Sing" and h.f.get("Gender") and noun.f.get("Gender") and h.f.get("Gender") != noun.f.get("Gender"):
                        return "subj-agreement", None
                else:
                    return "subj-nonfinite", None
                why = "the subject of «%s» — who or what does it — so nominative" % h.text
            else:
                why = "the subject of the sentence — nominative"
            v = {"nomn"} | ({"gent"} if neg else set())
            return "keep", {"viable": v, "why": "«%s» is %s" % (drill["correct"], why), "kind": "subject"}
        if cop:
            return "keep", {"viable": {"nomn", "ablt"},
                            "why": "«%s» is the predicate after «%s» — what someone or something is: the nominative of the predicate (the instrumental is also possible after быть, so it is not offered)" % (drill["correct"], cop[0].text),
                            "kind": "pred-nom"}
        return "nom-role", None
    if case == "accs":
        if rel == "obj" and h.pos == "VERB":
            if hl.endswith(("ся", "сь")): return "obj-of-reflexive", None
            fz = forms_for(morph, drill["correct"], "accs", "plur" if noun.f.get("Number") == "Plur" else "sing")
            if fz and fz.get("nomn", "").lower() == drill["correct"].lower():
                subj = False
                for t in kids(h):
                    if not t.rel.startswith("nsubj") or t.f.get("Case") != "Nom": continue
                    if not any("nomn" in p.tag for p in morph.parse(t.text.lower())): continue
                    if h.f.get("Number") and t.f.get("Number") and h.f.get("Number") != t.f.get("Number"): continue
                    subj = True
                person = h.f.get("Person") in ("1", "2") or h.f.get("Mood") == "Imp"
                if not (subj or person): return "acc-looks-nom-no-subject", None
            v = {"accs", "gent"}
            if hl in ACC_INSTR: v.add("ablt")
            if hl in ACC_DAT: v.add("datv")
            sync_ok = set() if (neg or hl in GEN_VERBS or hl in GEN_ALT_VERBS) else {"gent"}
            return "keep", {"viable": v, "sync_ok": sync_ok,
                            "why": "«%s» is the direct object of «%s» (кого? что?) — accusative" % (drill["correct"], h.text),
                            "kind": "object"}
        if rel == "obl" and nl in TIME_ACC and h.pos == "VERB":
            if any(t.pos == "ADP" for t in toks[max(0, first.i - 3):first.i]): return "time-prep-near", None
            if not has_other_subject(morph, h, kids): return "time-maybe-subject", None
            return "keep", {"viable": {"accs"},
                            "why": "«%s» tells how long or how often, with no preposition — accusative" % drill["correct"],
                            "kind": "time-acc"}
        return "acc-role", None
    if case == "gent":
        if rel == "nmod" and h.pos in ("NOUN", "PROPN"):
            hn = lemma_of(morph, h, "NOUN")
            vv = {"gent"}
            if hn in NMOD_DAT: vv.add("datv")
            if hn in NMOD_INSTR or hn.endswith(("ние", "ство", "тие")): vv.add("ablt")
            return "keep", {"viable": vv,
                            "why": "«%s» depends on the noun «%s» (whose? of what?) — genitive" % (drill["correct"], h.text),
                            "kind": "nmod-gen"}
        if hl in QUANT or (h.pos in ("NUM",) and False):
            return "keep", {"viable": {"gent"},
                            "why": "after «%s», a word of quantity — genitive" % h.text, "kind": "quant"}
        if h.pos == "ADJ" and h.f.get("Degree") == "Cmp" and h.i < first.i and all(
                t.head == noun.id and t.rel in ("amod", "det") for t in toks[h.i + 1:first.i]):
            return "keep", {"viable": {"gent"},
                            "why": "after the comparative «%s» (than …) — genitive" % h.text, "kind": "cmp"}
        if rel == "obj" and h.pos == "VERB":
            if neg:
                return "keep", {"viable": {"gent", "accs"},
                                "why": "«%s» is the object of a negated verb («не %s») — genitive instead of the accusative" % (drill["correct"], h.text),
                                "kind": "neg-obj"}
            if hl in GEN_VERBS:
                return "keep", {"viable": {"gent", "accs"},
                                "why": "«%s» takes its object in the genitive" % h.text, "kind": "gen-verb"}
            if hl in GEN_ALT_VERBS:
                return "keep", {"viable": {"gent", "accs"},
                                "why": "with «%s», a verb of waiting, seeking, asking or wanting, the object can stand in the genitive — as here" % h.text,
                                "kind": "gen-alt-verb"}
            return "gen-obj-unproved", None
        if rel in ("nsubj", "obl") and (neg and h.pos in ("VERB", "AUX") and lemma_of(morph, h) == "быть" or h.text.lower() == "нет"):
            return "keep", {"viable": {"gent", "nomn"},
                            "why": "what is absent after «%s» — genitive" % ("нет" if h.text.lower() == "нет" else "не " + h.text),
                            "kind": "absence"}
        return "gen-role", None
    if case == "datv":
        if h.pos == "VERB" and rel in ("iobj", "obj", "obl"):
            if hl in DAT_VERBS:
                return "keep", {"viable": {"datv", "accs"}, "why": "«%s» takes the dative (кому? чему?)" % h.text, "kind": "dat-verb"}
            if rel == "iobj" and (hl in DITRANS or any(t.rel == "obj" for t in kids(h))):
                return "keep", {"viable": {"datv", "accs"},
                                "why": "«%s» is the indirect object of «%s» — to or for whom (кому?) — dative" % (drill["correct"], h.text),
                                "kind": "iobj"}
            return "dat-unproved", None
        if h.pos == "ADJ" and lemma_of(morph, h) in DAT_ADJ:
            return "keep", {"viable": {"datv"}, "why": "«%s» takes the dative" % h.text, "kind": "dat-adj"}
        return "dat-role", None
    if case == "ablt":
        if cop and lemma_of(morph, cop[0]) in COPULAS:
            return "keep", {"viable": {"ablt", "nomn"},
                            "why": "after «%s», what someone or something is or becomes stands in the instrumental" % cop[0].text,
                            "kind": "pred-instr"}
        if h.pos in ("VERB", "AUX") or (h.pos == "ADJ" and h.f.get("VerbForm") == "Part"):
            if hl in COPULAS and rel in ("obl", "xcomp", "obj"):
                return "keep", {"viable": {"ablt", "nomn"},
                                "why": "after «%s», what someone or something is or becomes stands in the instrumental" % h.text,
                                "kind": "pred-instr"}
            if hl in PRED2 and rel in ("obl", "xcomp", "obj"):
                return "keep", {"viable": {"ablt", "nomn", "accs"},
                                "why": "after «%s» (to call, consider or make someone something), that something is in the instrumental" % h.text,
                                "kind": "pred2"}
            if hl in INSTR_VERBS:
                return "keep", {"viable": {"ablt", "accs"}, "why": "«%s» takes the instrumental" % h.text, "kind": "instr-verb"}
            if any("pssv" in p.tag for p in morph.parse(h.text.lower())) and rel in ("obl", "obl:agent", "iobj"):
                return "keep", {"viable": {"ablt"},
                                "why": "after the passive «%s», the doer or the means (by whom? with what?) is in the instrumental" % h.text,
                                "kind": "passive"}
            if nl in TIME_INSTR and rel == "obl":
                return "keep", {"viable": {"ablt"},
                                "why": "a time of day or season (when?), without a preposition — instrumental, like утром, весной",
                                "kind": "time-instr"}
            return "instr-unproved", None
        return "instr-role", None
    return "loct-no-prep", None

# ── options ──────────────────────────────────────────────────────────────────
def confirm(morph, word, pos, case, number):
    for p in morph.parse(word.lower()):
        t = p.tag
        if pos in t and case in t and (number is None or number in t):
            return p
    return None

def inflect_pair(adj_p, noun_p, case, number):
    gs = {case, number}
    n2 = noun_p.inflect(gs)
    if not n2: return None
    ag = {case, number}
    g = noun_p.tag.gender
    if g and number != "plur": ag.add(g)
    if case == "accs" and noun_p.tag.animacy: ag.add(noun_p.tag.animacy)
    a2 = adj_p.inflect(ag)
    if not a2: return None
    return a2.word, n2.word

def keep_case(word, model):
    if model[:1].isupper(): return word[:1].upper() + word[1:]
    return word

def forms_for(morph, correct, case, number):
    ws = correct.split()
    if len(ws) == 1:
        np_ = confirm(morph, ws[0], "NOUN", case, number)
        if not np_: return None
        nb = None
        for c in morph.parse(np_.normal_form):
            if "NOUN" in c.tag and c.tag.gender == np_.tag.gender: nb = c; break
        if not nb: return None
        out = {}
        for c in CASES:
            n2 = nb.inflect({c, number})
            if n2: out[c] = keep_case(n2.word, ws[0])
        if out.get(case, "").lower() != correct.lower(): return None
        return out
    if len(ws) != 2: return None
    a, nw = ws
    ap = confirm(morph, a, "ADJF", case, number) or confirm(morph, a, "PRTF", case, number)
    np_ = confirm(morph, nw, "NOUN", case, number)
    if not ap or not np_: return None
    def base(lemma, pos):
        for c in morph.parse(lemma):
            if pos in c.tag: return c
        return None
    ab = base(ap.normal_form, "ADJF") or base(ap.normal_form, "PRTF")
    nb = base(np_.normal_form, "NOUN")
    if not ab or not nb: return None
    out = {}
    for c in CASES:
        pr = inflect_pair(ab, nb, c, number)
        if pr: out[c] = keep_case(pr[0], a) + " " + keep_case(pr[1], nw)
    if out.get(case, "").lower() != correct.lower(): return None
    return out

def rebuild(drill, info, morph, number):
    case = case_code(drill["case"])
    forms = forms_for(morph, drill["correct"], case, number)
    if not forms: return "forms", None
    viable = info["viable"] | {case}
    viable_strings = {forms[c].lower() for c in viable if c in forms}
    # the correct form must not also be the form of another viable case,
    # or the case could not be told from the sentence
    for c in viable:
        if c != case and c in forms and forms[c].lower() == drill["correct"].lower() and c not in info.get("sync_ok", ()):
            return "syncretic", None
    pool = []
    seen = {drill["correct"].lower()}
    for c in CASES:
        if c in viable or c not in forms: continue
        s = forms[c]
        if s.lower() in seen or s.lower() in viable_strings: continue
        seen.add(s.lower()); pool.append((c, s))
    if len(pool) < 3: return "too-few-distractors", None
    old = [o for o in drill["options"] if o != drill["correct"]]
    # keep the drill's own wrong options where they are still wrong
    keepers = [o for o in old if o.lower() in {s.lower() for _, s in pool}]
    rest = [s for _, s in pool if s.lower() not in {k.lower() for k in keepers}]
    rnd = random.Random(drill["sentence"] + drill["correct"])
    rnd.shuffle(rest)
    wrong = (keepers + rest)[:3]
    opts = list(drill["options"])
    if len(opts) == 4 and set(o.lower() for o in wrong) == set(o.lower() for o in old):
        return "keep", opts  # unchanged
    new = [drill["correct"]] + wrong
    rnd.shuffle(new)
    return "keep", new

# ── driver ───────────────────────────────────────────────────────────────────
import argparse, collections, json, os, sys

ANIM_NOTE = " (animate: the accusative has the genitive's ending)"

def parse_drill(doc_cls, seg, mt, sp, drill):
    s = drill.get("sentence", ""); corr = drill.get("correct", "")
    if s.count("___") != 1: return None
    full = s.replace("___", corr)
    b0 = s.index("___")
    doc = doc_cls(full); doc.segment(seg); doc.tag_morph(mt); doc.parse_syntax(sp)
    toks = [(t.id, t.text, t.pos, t.rel, t.head_id, dict(t.feats or {}), t.start, t.stop) for t in doc.tokens]
    return {"full": full, "b": (b0, b0 + len(corr)), "toks": toks}

def process(drill, parse, morph):
    v, info = analyse(drill, parse, morph)
    if v != "keep": return v, None
    case = case_code(drill["case"])
    b0, b1 = parse["b"]
    noun = [t for t in parse["toks"] if t[6] >= b0 and t[7] <= b1 and t[2] in ("NOUN", "PROPN")][-1]
    number = "plur" if noun[5].get("Number") == "Plur" else "sing"
    r, opts = rebuild(drill, info, morph, number)
    if r != "keep": return r, None
    why = info["why"]
    if info["kind"] == "object" and "gent" in info.get("sync_ok", ()):
        f = forms_for(morph, drill["correct"], case, number)
        if f and f.get("gent", "").lower() == drill["correct"].lower(): why += ANIM_NOTE
    if info["kind"].startswith("prep:"): why = "«%s» — %s." % (drill["correct"], why)
    else: why = (why[0].upper() + why[1:] + ".") if not why.startswith("«") else why + "."
    nd = dict(drill); nd["options"] = opts; nd["case"] = LABEL[case]; nd["explain"] = why
    return "keep", nd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    exd = os.path.join(root, "public", "books", "exercises")
    import pymorphy3
    from natasha import Segmenter, NewsEmbedding, NewsMorphTagger, NewsSyntaxParser, Doc
    morph = pymorphy3.MorphAnalyzer()
    emb = NewsEmbedding(); seg = Segmenter(); mt = NewsMorphTagger(emb); sp = NewsSyntaxParser(emb)
    files = a.files or sorted(f for f in os.listdir(exd) if f.endswith(".json") and not f.startswith("_"))
    stats = collections.Counter()
    for n, f in enumerate(files):
        path = os.path.join(exd, os.path.basename(f))
        d = json.load(open(path, encoding="utf-8"))
        new, seen = [], set()
        for drill in d.get("cases", []):
            v, nd = process(drill, parse_drill(Doc, seg, mt, sp, drill), morph)
            stats[v] += 1
            if nd:
                key = (nd["sentence"], nd["correct"])
                if key in seen: stats["duplicate"] += 1; continue
                seen.add(key); new.append(nd)
        if a.apply:
            if new: json.dump({"cases": new}, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            else: os.remove(path)
        if n % 200 == 0: print(n, "/", len(files), flush=True)
    print(stats.most_common())

if __name__ == "__main__":
    main()
