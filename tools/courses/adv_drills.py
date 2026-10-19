#!/usr/bin/env python3
"""Drills for the advanced grammar courses — aspect, comparison, short
adjectives, -то/-нибудь, некого/нечего, себя, который, каков, чтобы,
complex conjunctions, пока/пока не, ли, -ся verbs — from real sentences only
(Tatoeba with its English; the library's public-domain books with author and
title). Each exercise's explanation is the DLI Grammar Reference Book's own
sentence for the rule it tests.

    python3 tools/courses/adv_drills.py ~/tatoeba/rus.txt   → tools/courses/adv_drills.json
"""
import hashlib, io, json, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import tatoeba_drills as td
from tatoeba_drills import M, WORD, parses, tags, form_of
from case_drills import D2
from tense_examples import read
from adv_more import scan_more

CAP = int(os.environ.get("CAP", "420"))
DLI = {
    "asp": "«The imperfective aspect emphasizes the action itself. The perfective aspect places the emphasis on the result of the action.» — DLI, Lesson 37.",
    "asp:neg": "«The negative imperative is, as a rule, in the imperfective aspect … The negative imperative in the perfective aspect … has the meaning of a strict warning.» — DLI, Lesson 84.",
    "asp:imp": "«The imperative may be formed from both the imperfective and the perfective verbs.» — DLI, Lesson 42.",
    "comp": "«The comparative degree of Russian adjectives is formed by adding \"-ее\" (sometimes shortened to \"-ей\") to the stem of the adjective.» — DLI, Lesson 80.",
    "comp:irr": "«Certain adjectives have irregular comparatives»: выше, ниже, шире, короче, легче, глубже, дороже, дешевле, лучше, хуже, больше, меньше, старше, моложе … — DLI, Lessons 80–82.",
    "comp:obj": "«An adjective in the comparative degree may be followed by the object of comparison in the Genitive case, or by a phrase consisting of \"чем\" plus the object of comparison in the Nominative case.» — DLI, Lesson 80.",
    "comp:bolee": "«The adjective after \"более\" or \"менее\" must agree in case, gender and number with the noun modified.» — DLI, Lesson 80.",
    "sup:samyi": "«To get the superlative degree in Russian place the word \"самый\" before the adjective … \"Самый\" is declined like regular adjective.» — DLI, Lesson 83.",
    "sup:eish": "«The superlative degree of qualitatives can be formed by changing the ending of an adjective to \"-ейший\" (or \"-айший\" after sibilants).» — DLI, Lesson 83.",
    "short": "«There is a limited number of adjectives that normally take the short form when used predicatively … The short form of an adjective can never be used as a modifier.» — DLI, Lesson 57.",
    "indef": "«In general, the particle \"-нибудь\" implies complete indefiniteness; the particle \"-то\" implies some degree of certainty.» a) In interrogative and imperative sentences use -нибудь. b) In positive statements referring to the past or present use -то. — DLI, Lesson 59.",
    "negpron": "«НЕКОГО, НЕЧЕГО … are used in impersonal constructions with the infinitive of the verb (without НЕ); никого, ничего … with any negative (НЕ) form of the verb.» — DLI, Lessons 104–105.",
    "negadv": "«НЕГДЕ, НЕКУДА, НЕОТКУДА, НЕКОГДА: used with the Infinitive of the verb (without НЕ) in impersonal constructions. нигде, никуда, ниоткуда, никогда: used with any negative (НЕ) form of the verb.» — DLI, Lesson 105.",
    "chtoby": "«\"Чтобы\" is used to express an order or a wish, whereas \"что\" would be used to make a statement or convey information.» — DLI, Lesson 92.",
    "complex": "«When a preposition refers to a whole clause, a complex conjunction is used consisting of: 1) the preposition, 2) the pronoun \"то\" in the case required by the preposition, 3) a linking word»: до того как, перед тем как, о том что, за то что, вместо того чтобы. — DLI, Lesson 92.",
    "poka": "«Пока is used as an adverb of time and as a conjunction. Пока не (until) is a conjunction … ПОКА НЕ has no negative meaning and the particle НЕ is not translated.» — DLI, Lesson 105.",
    "li": "«The particle ЛИ never begins the clause; it takes the second place in the clause following the word to which the question or doubt refers.» — DLI, Lesson 91.",
    "kotoryi": "«\"Который\" in subordinate clauses agrees in gender and number with the noun it refers to in the main sentence, but its case is determined by its function in the subordinate clause.» — DLI, Lesson 53.",
    "sebya": "«\"Себя\" has no nominative case, since it can never be the subject of a sentence. In oblique cases it is declined like the pronoun \"ты\".» — DLI, Lesson 64.",
    "sya": "«The verbs in \"-ся\" may be divided into several groups»: reflexive (я моюсь), intransitive (урок продолжается), reciprocal (мы встречаемся), and verbs which never occur without \"-ся\". — DLI, Lesson 67.",
    "kakov": "",
    "subst": "«Больной, раненый and знакомый are often used as adjectival nouns.» — DLI, Lesson 57.",
    "shortcomp": "«There is a limited number of adjectives that normally take the short form when used predicatively»: доволен, согласен, рад, знаком, занят, готов. — DLI, Lesson 57.",
    "mnogie": "«\"Многие\" (немногие) expresses 2 ideas: some + many (few) … На лекции было много студентов (as a group). Многие студенты были на лекции (as individuals).» — DLI, Lesson 88.",
    "imptypes": "«Пусть он (она) делает, сделает это» — let him do it. «Давайте + infinitive of the imperfective … давайте + perfective future» — let's. — DLI, Lesson 84.",
    "where": "«The adverbs здесь (here), там (there), дома (at home) indicate location and answer the question где … сюда (here), туда (there), домой (home) indicate direction and answer the question куда.» — DLI, Lesson 19.",
    "here": "«The adverbs здесь (here), там (there), дома (at home) indicate location and answer the question где … сюда (here), туда (there), домой (home) indicate direction and answer the question куда.» — DLI, Lesson 19.",
    "there": "«The adverbs здесь (here), там (there), дома (at home) indicate location and answer the question где … сюда (here), туда (there), домой (home) indicate direction and answer the question куда.» — DLI, Lesson 19.",
    "home": "«The adverbs здесь (here), там (there), дома (at home) indicate location and answer the question где … сюда (here), туда (there), домой (home) indicate direction and answer the question куда.» — DLI, Lesson 19.",
    "iano": "«И (and) indicates addition or similarity … А (and, but) indicates difference, contrast, or denial … Но (but) is used when the second statement somewhat limits the significance of the first one or when it introduces a statement contrary to it.» — DLI, Lesson 19.",
    "condconj": "«First type: \"если\" clauses … being statements of direct fact, they are expressed by the indicative mood. Second type: \"если бы\" clauses … the conditions are either improbable or downright contrary to existing fact.» — DLI, Lesson 90.",
    "cause:prep": "«из-за — from behind; because of» (+ genitive); «благодаря + Dat. — thanks to». — DLI, Lessons 60, 103.",
    "timeconj": "«Future tense after \"когда\" and \"как только\" … » and «the complex conjunctions: до того как, после того как, перед тем как». — DLI, Lessons 37, 92.",
    "prefix": "«Adding a prefix to the repeated function verbs … usually does not form the perfective aspect but merely changes the meaning of the original verb.» — DLI, Lesson 63.",
    "conj:pres": "«The following verbs belong to the \"Е\" type of conjugation: думать — я думаю, ты думаешь … они думают … The verb лежать belongs to the \"И\" type of conjugation: я лежу, ты лежишь … они лежат.» — DLI, Lesson 16.",
    "conj:fut": "«The perfective future consists of one word only and resembles in form the present tense. It is formed from the perfective infinitive: напишу, сделаю, получу, выучу.» — DLI, Lesson 37.",
    "conj:past": "«The past tense is formed by dropping -ть from the infinitive and adding -л for the masculine, -ла for the feminine, -ло for the neuter, -ли for the plural … the past does not have special endings for each person, but shows the gender and the number.» — DLI, Lesson 36.",
    "pos": "«Phrases meaning direction are used to denote the place where something is put (\"на\" + Acc., \"в\" + Acc.)» (ставить, класть). «Садиться / сесть implies movement to a \"seat\" and, therefore, answers the question \"куда?\"»; сидеть, лежать, стоять answer \"где?\". — DLI, Lessons 42, 68.",
    "svoi": "«The possessive \"свой\" indicates that the object belongs to the performer of the action … When the performer of the action is in the 3rd person … the possessives \"его, её, их\" are used if the object does not belong to the performer of the action. If the object belongs to the performer of the action, the possessive \"свой\" must be used.» — DLI, Lesson 49.",
}
PAIRS = json.load(io.open(sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.dirname(HERE)), "public", "vocab", "verbs", "index.json"), encoding="utf-8")).get("pairs", {})
INDEF = re.compile(r"^(кто|кого|кому|кем|ком|что|чего|чему|чем|какой|какая|какое|какие|какого|какую|каким|каком|какой|каких|какими|чей|чья|чьё|чьи|чьего|чью|чьим|куда|где|когда|откуда|как|почему|зачем)-(то|нибудь|либо)$", re.I)
NEG = {"некого": "никого", "некому": "никому", "нечего": "ничего", "нечему": "ничему", "нечем": "ничем",
       "негде": "нигде", "некуда": "никуда", "неоткуда": "ниоткуда", "некогда": "никогда"}
NEG.update({v: k for k, v in list(NEG.items())})
NEGADV = {"негде", "нигде", "некуда", "никуда", "неоткуда", "ниоткуда", "некогда", "никогда"}
COMPLEX = re.compile(r"\b(до|после|перед|о|за|из-за|для|вместо|с|кроме)\s+(того|тем|том|то)(,?)\s+(как|что|чтобы)\b", re.I)
KAKOV = ["каков", "какова", "каково", "каковы"]
SEBYA = ["себя", "себе", "собой"]
WHOLE = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)*")


def scan(ru, en, cite):
    out = []
    ws = list(WHOLE.finditer(ru))
    low = [w.group().lower() for w in ws]
    if not (3 <= len(ws) <= 16) or re.search(r"\d", ru) or td.RUDE_EN.search(en or "") or td.RUDE_RU.search(ru):
        return out
    if any(tags(parses(w)[0]) & {"Infr", "Slng", "Obsc"} for w in low if "-" not in w):
        return out

    def ok(i):
        w = ws[i].group()
        return not (i > 0 and w[:1].isupper())

    def D(key, i0, i1, ans, lemma, opts, fill=False):
        d = D2(ru, en, cite, ws, i0, i1, ans, lemma, DLI.get(key.split("/")[0], ""), opts)
        d.key, d.fill = key, fill
        out.append((key, d))

    for i, w in enumerate(low):
        if "-" in w:
            m = INDEF.match(w)
            if m and ok(i):
                base = w.rsplit("-", 1)[0]
                D("indef", i, i, ws[i].group(), "", [base + "-то", base + "-нибудь"] + (["кое-" + base] if base in ("кто", "что", "кого", "чего", "кому", "чем", "кем", "где", "куда", "какой", "какая") else []))
            continue
        ps = parses(w); p0 = ps[0]; T = tags(p0)
        prev = low[i - 1] if i else ""
        # aspect
        if p0.tag.POS in ("VERB", "INFN") and p0.normal_form in PAIRS and p0.score > 0.3 and ok(i):
            partners = [x for x in (PAIRS[p0.normal_form][1] or [])][:2]
            gr = None
            if "past" in T:
                gr, key = {"past"} | ({p0.tag.gender} if p0.tag.gender else set()) | ({p0.tag.number} if p0.tag.number else set()), "asp:past"
            elif p0.tag.POS == "INFN":
                gr, key = set(), "asp:inf"
            elif "impr" in T:
                gr, key = {"impr", "excl", p0.tag.number or "sing"}, ("asp:neg" if prev == "не" else "asp:imp")
            if gr is not None:
                opts = [w]
                for pl in partners:
                    q = next((x for x in M.parse(pl) if x.normal_form == pl and x.tag.POS == "INFN"), None)
                    f = (q.word if not gr else (form_of(q, gr) if q else None)) if q else None
                    if f and f not in opts:
                        opts.append(f)
                if len(opts) >= 2:
                    D(key, i, i, ws[i].group(), "", opts)
        # comparison
        if p0.tag.POS == "COMP" and w not in ("более", "менее") and ok(i) and p0.score > 0.3:
            reg = bool(re.search(r"(ее|ей)$", w))
            D("comp" if reg else "comp:irr", i, i, ws[i].group(), p0.normal_form, [], fill=True)
            if i + 1 < len(low) and low[i + 1] != "чем":
                r = [q for q in parses(low[i + 1]) if q.tag.POS == "NOUN" and q.tag.case == "gent" and q.score > 0.2 and not (tags(q) & {"Name", "Surn", "Geox"})]
                if r and ok(i + 1):
                    q = r[0]
                    opts = [x for x in dict.fromkeys(form_of(q, {c, q.tag.number}) for c in ("nomn", "gent", "datv", "ablt")) if x]
                    D("comp:obj", i + 1, i + 1, ws[i + 1].group(), q.normal_form, opts)
        if w in ("более", "менее") and i + 1 < len(low):
            r = [q for q in parses(low[i + 1]) if q.tag.POS == "ADJF" and q.score > 0.2 and not (tags(q) & {"Apro", "Anum"})]
            if r and ok(i + 1) and low[i + 1] not in ("того", "одной", "одного", "одну", "половины"):
                q = r[0]
                gr = {q.tag.number} | ({q.tag.gender} if q.tag.gender else set())
                opts = [x for x in dict.fromkeys(form_of(q, {c} | gr) for c in ("nomn", "gent", "datv", "accs", "ablt", "loct")) if x]
                D("comp:bolee", i + 1, i + 1, ws[i + 1].group(), q.normal_form, opts)
        if p0.normal_form == "самый" and p0.tag.POS == "ADJF" and i + 1 < len(low) and any(q.tag.POS == "ADJF" for q in parses(low[i + 1])[:1]) and ok(i):
            gr = {p0.tag.number} | ({p0.tag.gender} if p0.tag.gender else set())
            opts = [x for x in dict.fromkeys(form_of(p0, {c} | gr) for c in ("nomn", "gent", "datv", "accs", "ablt", "loct")) if x]
            D("sup:samyi", i, i, ws[i].group(), "самый", opts)
        if p0.tag.POS == "ADJF" and "Supr" in T and re.search(r"(ейш|айш)", w) and ok(i):
            D("sup:eish", i, i, ws[i].group(), p0.normal_form, [], fill=True)
        if p0.tag.POS == "ADJS" and p0.score > 0.4 and ok(i) and len(w) > 2 and not any(q.tag.POS in ("VERB", "PRTS", "ADVB") for q in ps):
            D("short", i, i, ws[i].group(), p0.normal_form, [], fill=True)
        # negative pronouns and adverbs
        if w in NEG and ok(i):
            neg_series = w.startswith("не")
            if w == "некогда" and not any(parses(x)[0].tag.POS == "INFN" for x in low[i + 1:i + 4]):
                pass
            elif neg_series or "не" in low:
                D("negadv" if w in NEGADV else "negpron", i, i, ws[i].group(), "", [w, NEG[w]])
        # себя, который, каков
        if w in ("себя", "себе", "собой", "собою") and ok(i):
            D("sebya", i, i, ws[i].group(), "", SEBYA if w != "собою" else SEBYA[:2] + ["собою"])
        if p0.normal_form == "который" and p0.tag.POS == "ADJF" and ok(i) and prev not in ("в", "во"):
            gr = {p0.tag.number} | ({p0.tag.gender} if p0.tag.gender and p0.tag.number == "sing" else set())
            opts = [x for x in dict.fromkeys(form_of(p0, {c} | gr) for c in ("nomn", "gent", "datv", "accs", "ablt", "loct")) if x]
            D("kotoryi", i, i, ws[i].group(), "", opts)
        if p0.normal_form == "свой" and p0.tag.POS == "ADJF" and ok(i) and not ({"я", "ты", "мы", "вы"} & set(low)) \
                and any(("3per" in tags(parses(x)[0]) or "past" in tags(parses(x)[0])) for x in low):
            D("svoi", i, i, ws[i].group(), "", [w, "его", "её", "их"])
        if w in KAKOV and ok(i):
            D("kakov", i, i, ws[i].group(), "", KAKOV)
        # -ся verbs
        if p0.tag.POS in ("VERB", "INFN") and re.search(r"(ся|сь)$", w) and re.search(r"(ся|сь)$", p0.normal_form) and ok(i):
            base = p0.normal_form[:-2]
            bq = next((x for x in M.parse(base) if x.normal_form == base and x.tag.POS == "INFN"), None)
            if bq and M.word_is_known(base):
                gr = {g for g in (p0.tag.tense, p0.tag.person, p0.tag.number, p0.tag.gender, p0.tag.mood if p0.tag.mood == "impr" else None) if g}
                f = bq.word if p0.tag.POS == "INFN" else form_of(bq, gr)
                if f and f != w:
                    D("sya", i, i, ws[i].group(), "", [w, f])
    # conjugation and position verbs
    for i, w in enumerate(low):
        if "-" in w or not ok(i):
            continue
        p0 = parses(w)[0]; T = tags(p0)
        if p0.tag.POS == "VERB" and p0.score > 0.4 and p0.normal_form not in ("быть", "являться") and M.word_is_known(w):
            if "pres" in T:
                D("conj:pres", i, i, ws[i].group(), p0.normal_form, [], fill=True)
            elif "futr" in T:
                D("conj:fut", i, i, ws[i].group(), p0.normal_form, [], fill=True)
            elif "past" in T:
                D("conj:past", i, i, ws[i].group(), p0.normal_form, [], fill=True)
            for grp in POS_GROUPS:
                if p0.normal_form in grp:
                    gr = {g for g in (p0.tag.tense, p0.tag.person, p0.tag.number, p0.tag.gender, p0.tag.mood if p0.tag.mood == "impr" else None) if g}
                    opts = [w]
                    for v in grp:
                        if v == p0.normal_form:
                            continue
                        q = next((x for x in M.parse(v) if x.normal_form == v and x.tag.POS == "INFN"), None)
                        f = form_of(q, gr) if (q and gr) else None
                        if f and f not in opts:
                            opts.append(f)
                    if len(opts) >= 2:
                        D("pos", i, i, ws[i].group(), "", opts[:4])
                    break
        elif p0.tag.POS == "INFN":
            for grp in POS_GROUPS:
                if p0.normal_form in grp:
                    D("pos", i, i, ws[i].group(), "", [w] + [v for v in grp if v != w][:3])
                    break
    scan_more(ru, en, ws, low, ok, D)
    # чтобы / что (Tatoeba only: the English decides)
    if en:
        for i, w in enumerate(low):
            if w in ("чтобы", "что") and i > 0 and ru[ws[i].start() - 2:ws[i].start()].strip() == "," and ok(i) \
                    and not (i + 1 < len(low) and low[i + 1] in ("ли", "же")):
                D("chtoby", i, i, ws[i].group(), "", ["что", "чтобы"])
    # complex conjunctions: blank the то-form
    for m in COMPLEX.finditer(ru):
        k = next((j for j, x in enumerate(ws) if x.start() == m.start(2)), None)
        if k is not None:
            D("complex", k, k, ws[k].group(), "", ["того", "тем", "том", "то"])
    # пока / пока не
    for i, w in enumerate(low):
        if w == "пока" and ok(i) and (i == 0 or ru[ws[i].start() - 2:ws[i].start()].strip() in (",", "")):
            if i + 1 < len(low) and low[i + 1] == "не":
                D("poka", i, i + 1, ru[ws[i].start():ws[i + 1].end()], "", ["пока", "пока не"])
            elif i + 2 < len(low) and any(parses(x)[0].tag.POS == "VERB" for x in low[i + 1:i + 3]) and low[i + 1] not in ("что", "ещё", "еще", "все", "всё"):
                D("poka", i, i, ws[i].group(), "", ["пока", "пока не"])
    # ли: blank the verb (or word) and ли together
    if en and " ли" in ru:
        for i, w in enumerate(low):
            if w == "ли" and i >= 1 and ok(i - 1) and parses(low[i - 1])[0].tag.POS in ("VERB", "ADJS", "PRED", "ADVB", "NOUN", "NPRO"):
                p = parses(low[i - 1])[0]
                lem = p.normal_form if p.tag.POS in ("VERB", "ADJS", "NOUN") else low[i - 1]
                d = D2(ru, en, "", ws, i - 1, i, ru[ws[i - 1].start():ws[i].end()], lem + " + ли", DLI["li"], [])
                d.key, d.fill = "li", True
                out.append(("li", d))
    return out


def exercise(d, n):
    src = (" From %s." % d.cite) if d.cite else " Sentence and translation from Tatoeba (CC BY 2.0 FR)."
    why = (d.why + src).strip()
    ans = d.answer
    if d.fill or not d.options:
        if not d.lemma:
            return None
        return {"type": "fill", "q": d.blanked(True), "prompt": d.en or ("*" + d.cite + "*"), "answers": [ans], "why": why}
    opts = [o for o in dict.fromkeys(x for x in d.options if x)]
    a = ans.lower()
    if a not in [o.lower() for o in opts]:
        opts.insert(0, a)
    h = int(hashlib.md5((d.ru + a).encode()).hexdigest()[:6], 16)
    o = opts[:4]
    if a not in [x.lower() for x in o]:
        o[-1] = a
    k = h % len(o)
    idx = [x.lower() for x in o].index(a)
    o[idx], o[k] = o[k], o[idx]
    return {"type": "mc", "q": d.en or ("Which fits? *" + d.cite + "*"), "ru": d.blanked(False), "options": o,
            "answer": [x.lower() for x in o].index(a), "why": why}


POS_GROUPS = [["стоять", "поставить", "встать", "ставить"], ["лежать", "положить", "лечь", "класть"],
              ["сидеть", "посадить", "сесть", "сажать"], ["висеть", "повесить", "вешать"]]
FIXED_SET = {"cause:prep", "causeconj", "concession", "condconj", "timeconj", "tozhe", "iano", "coord", "disj", "particles", "imptypes",
             "where", "here", "there", "home", "corr", "sam", "mnogie", "chtoby", "complex", "poka", "sebya", "kakov", "negadv", "negpron", "sup:samyi", "kotoryi", "svoi", "indef", "li"}


def main():
    rows = [(ru, en, "") for ru, en, _ in read(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/tatoeba/rus.txt"))]
    lib = os.path.join(HERE, "library_sentences.tsv")
    if os.path.exists(lib):
        for line in io.open(lib, encoding="utf-8"):
            c = line.rstrip("\n").split("\t")
            if len(c) >= 3 and c[0]:
                rows.append((c[0], "", c[2]))
    print(len(rows), "sentences", flush=True)
    found = defaultdict(list); seen = set()
    for k, (ru, en, cite) in enumerate(rows):
        if ru in seen:
            continue
        seen.add(ru)
        for key, d in scan(ru, en, cite):
            found[key].append(d)
        if k and k % 100000 == 0:
            print("  %d…" % k, flush=True)
    out = {}
    for key, ds in sorted(found.items()):
        ds.sort(key=lambda d: (not d.en, len(d.words) > 11, hashlib.md5((key + d.ru).encode()).hexdigest()))
        pick, lem, sents = [], defaultdict(int), set()
        for cap in (1, 2, 4, 8, 16):
            for d in ds:
                lk = d.ru if key in FIXED_SET else (d.lemma or d.answer.lower())
                if lem[lk] >= cap or d.ru in sents:
                    continue
                lem[lk] += 1; sents.add(d.ru); pick.append(d)
                if len(pick) >= CAP:
                    break
            if len(pick) >= CAP:
                break
        exs = [e for e in (exercise(d, n) for n, d in enumerate(pick)) if e]
        out[key] = exs
        print("%-12s %7d found, %4d kept" % (key, len(ds), len(exs)))
    io.open(os.path.join(HERE, "adv_drills.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
