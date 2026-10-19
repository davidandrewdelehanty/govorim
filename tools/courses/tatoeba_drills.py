#!/usr/bin/env python3
"""Practice drills from Tatoeba: real Russian sentences with their English
translations, written by people (CC BY 2.0 FR, tatoeba.org). For each course
section a set of sentences that use the very form the section teaches; the
form is blanked and the reader types it (the dictionary form is the hint) or
picks it from its own other forms.

Nothing here is invented: the sentence and its translation are Tatoeba's;
the answer is the word the sentence actually has. The script only finds
sentences and decides which word to blank (pymorphy3 reads the grammar).

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/courses/tatoeba_drills.py ~/tatoeba/rus.txt
    python3 tools/courses/build_courses.py

Writes tools/courses/drills.json; build_courses.py adds a "practice"
section after each section that has drills.
"""
import hashlib, io, json, os, re, sys
from collections import defaultdict

import pymorphy3

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from tense_examples import read          # the tab-separated Tatoeba export reader

M = pymorphy3.MorphAnalyzer()
PER = 14                                  # drills per section
WORD = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)?")
CASES = ["nomn", "gent", "datv", "accs", "ablt", "loct"]
CASE_EN = {"nomn": "nominative", "gent": "genitive", "datv": "dative", "accs": "accusative",
           "ablt": "instrumental", "loct": "prepositional", "loc2": "prepositional"}
PREP = {}
for w in "без для из от у около после до кроме мимо против вместо из-за из-под возле вокруг среди".split():
    PREP[w] = {"gent"}
for w in "к ко благодаря".split():
    PREP[w] = {"datv"}
for w in "через про сквозь".split():
    PREP[w] = {"accs"}
for w in "над надо перед передо между".split():
    PREP[w] = {"ablt"}
for w in "о об обо при".split():
    PREP[w] = {"loct", "loc2"}
for w in "в во на".split():
    PREP[w] = {"accs", "loct", "loc2"}
for w in "с со".split():
    PREP[w] = {"gent", "ablt"}
for w in "за под".split():
    PREP[w] = {"accs", "ablt"}
SKIP_TAGS = {"Name", "Surn", "Patr", "Abbr", "Init", "Erro", "Dist", "Infr", "Slng", "Arch"}
NUM_GS = {"два", "две", "три", "четыре", "оба", "обе"}
NUM_GP = set("пять шесть семь восемь девять десять одиннадцать двенадцать тринадцать четырнадцать пятнадцать "
             "шестнадцать семнадцать восемнадцать девятнадцать двадцать тридцать сорок пятьдесят шестьдесят "
             "семьдесят восемьдесят девяносто сто двести триста четыреста пятьсот шестьсот семьсот восемьсот девятьсот".split())
QUANT = {"много", "мало", "сколько", "несколько", "немного", "немало"}
COLLECT = {"двое", "трое", "четверо", "пятеро", "шестеро", "семеро", "полтора", "полторы"}
MONTHS = set("январь февраль март апрель май июнь июль август сентябрь октябрь ноябрь декабрь".split())
DAYS = set("понедельник вторник среда четверг пятница суббота воскресенье".split())
TIMEW = set("час минута секунда день неделя месяц год утро вечер ночь обед ужин завтрак полдень полночь лето зима весна осень век".split())
MOTION = {"идти": "ходить", "ехать": "ездить", "лететь": "летать", "бежать": "бегать", "плыть": "плавать",
          "нести": "носить", "вести": "водить", "везти": "возить", "брести": "бродить", "ползти": "ползать",
          "катить": "катать", "тащить": "таскать", "гнать": "гонять", "лезть": "лазить"}
MOTION.update({v: k for k, v in list(MOTION.items())})
PREFIX = re.compile(r"^(при|у|в|вы|под|от|до|пере|про|об|обо|за|с|со|по|вз|вс|раз|рас)(йти|ходить|ехать|езжать|ездить|лететь|летать|бежать|бегать|плыть|плывать|нести|носить|вести|водить|везти|возить)$")


# Sentences a learner should not be drilled on.
RUDE_EN = re.compile(r"\b(fuck\w*|shit\w*|bitch\w*|cunt|dick|cock|pussy|whore|slut|bastard|asshole|arse\w*|piss\w*|sex\w*|penis|vagina|boob\w*|nude|naked|porn\w*|rape\w*|horny|orgasm|condom|masturbat\w*|twig and berries|nigg\w*|fag\w*|retard\w*|cum|tits?)\b", re.I)
RUDE_RU = re.compile(r"(ху[йияеёю]|пизд|[её]б[аеиуыл]|бля|трах|сук[аи]|жоп|говн|дерьм|шлюх|мудак|мудил|сра[лт]|ссать|секс|порн|голы[йем]|насил|минет|член\w* (?!клуб|партии|семьи))", re.I)
FIXED = re.compile(r"\b(во время|до сих пор|вести себя|ведёт себя|вёл себя|вела себя|ведут себя|отно\w+ себя|на днях|походит на|походить на|походил\w? на|(?:мне|тебе|вам|ему|ей|им|нам) (?:не )?ид[её]т|ид[её]т дождь|ид[её]т снег|идут дожди|речь ид[её]т|влетело|влетит)\b", re.I)

_cache = {}
def parses(w):
    k = w.lower()
    if k not in _cache:
        _cache[k] = M.parse(k)
    return _cache[k]


def tags(p):
    return set(str(p.tag).replace(" ", ",").split(","))


def form_of(p, grams):
    try:
        x = p.inflect(set(grams))
        return x.word if x else None
    except Exception:
        return None


def noun_case(w, allowed):
    """The case of noun `w` when it is one of `allowed` and the word reads no other way among them."""
    ps = [p for p in parses(w) if p.tag.POS == "NOUN" and p.score > 0.01 and not (tags(p) & SKIP_TAGS)]
    if not ps:
        return None
    lem = ps[0].normal_form
    cs = {p.tag.case for p in ps if p.normal_form == lem and p.tag.case in allowed}
    cs = {("loct" if c == "loc2" else c) for c in cs}
    if len(cs) != 1:
        return None
    c = cs.pop()
    p = next(p for p in ps if p.normal_form == lem and ("loct" if p.tag.case == "loc2" else p.tag.case) == c)
    return p, c


def case_options(p, number, answer):
    opts = []
    for c in CASES:
        f = form_of(p, {c, number})
        if f and f not in opts:
            opts.append(f)
    if answer.lower() not in opts:
        opts.append(answer.lower())
    return opts


class Drill:
    def __init__(self, ru, en, words, i, answer, lemma, why, options=None, extra=()):
        self.ru, self.en, self.words, self.i = ru, en, words, i
        self.answer, self.lemma, self.why, self.options = answer, lemma, why, options or []
        self.extra = list(extra)

    def blanked(self, with_hint):
        s, e = self.words[self.i].span()
        hint = (" (" + self.lemma + ")") if with_hint else ""
        return self.ru[:s] + "___" + hint + self.ru[e:]


def scan(ru, en):
    """Every drill this sentence offers: (course, section, Drill)."""
    out = []
    ws = list(WORD.finditer(ru))
    low = [w.group().lower() for w in ws]
    if not (3 <= len(ws) <= 12) or re.search(r"\d", ru) or RUDE_EN.search(en) or RUDE_RU.search(ru):
        return out
    if any(tags(parses(w)[0]) & {"Infr", "Slng", "Obsc"} for w in low):
        return out
    fixed = [m.span() for m in FIXED.finditer(ru)]

    def ok(i):
        """A word that can be blanked: a real dictionary word, not a name, not inside an idiom."""
        w = ws[i].group()
        if i > 0 and w[:1].isupper():
            return False
        if not M.word_is_known(w.lower()):
            return False
        a, b = ws[i].span()
        return not any(x <= a < y or x < b <= y for x, y in fixed)

    def D(i, answer_p, why, options=None, lemma=None):
        if not ok(i) or (i == 0 and any(t in tags(answer_p) for t in ("Name", "Surn", "Geox"))):
            return None
        return Drill(ru, en, ws, i, ws[i].group(), lemma or answer_p.normal_form, why, options)

    for i, w in enumerate(low):
        ps = parses(w)
        p0 = ps[0]
        t0 = tags(p0)
        # ── prepositions + noun (and adjective + noun) ──
        if w in PREP and i + 1 < len(low):
            j = i + 1
            adj = None
            if j < len(low) - 1:
                pa = [p for p in parses(low[j]) if p.tag.POS == "ADJF" and p.score > 0.05 and p.normal_form not in ("сей", "тот", "этот", "весь", "такой", "который", "какой")]
                if pa:
                    adj, j = j, j + 1
            if j < len(low):
                r = noun_case(low[j], PREP[w])
                if r:
                    p, c = r
                    num = p.tag.number or "sing"
                    why = "«%s» + %s %s." % (w, CASE_EN[c], "plural" if num == "plur" else "singular")
                    opts = case_options(p, num, ws[j].group())
                    sec = {"loct": "k1-nom-prep", "accs": "k2-accusative", "gent": "k3-genitive",
                           "datv": "k4-dative", "ablt": "k5-instrumental"}[c]
                    if num == "plur":
                        sec = "k7-genitive-plural" if c == "gent" else "k8-plural-cases"
                    out.append(("cases", sec, D(j, p, why, opts)))
                    out.append(("cases", "k11-prepositions", D(j, p, why, opts)))
                    if num == "sing":
                        out.append(("cases", "k6-singular-tables", D(j, p, why, opts)))
                    if adj is not None:
                        pa = [q for q in parses(low[adj]) if q.tag.POS == "ADJF" and q.tag.case == p.tag.case
                              and (q.tag.number == num) and (num == "plur" or q.tag.gender in (p.tag.gender, None))]
                        if pa:
                            q = pa[0]
                            aopts = []
                            for cc in CASES:
                                f = form_of(q, {cc, num} | ({q.tag.gender} if num == "sing" and q.tag.gender else set()))
                                if f and f not in aopts:
                                    aopts.append(f)
                            awhy = "The adjective agrees with «%s»: %s %s." % (ws[j].group(), CASE_EN[c], "plural" if num == "plur" else "singular")
                            out.append(("cases", "k10-adjectives-plural" if num == "plur" else "k9-adjectives-singular", D(adj, q, awhy, aopts)))
                    # time words after prepositions
                    lem = p.normal_form
                    if lem in DAYS and w in ("в", "во") and adj is None:
                        out.append(("time", "t3-day-week-month-year", D(j, p, "«в» + accusative for the day: в понедельник, в среду.", opts)))
                    elif lem in MONTHS and w in ("в", "во") and adj is None:
                        out.append(("time", "t5-months-dates", D(j, p, "«в» + prepositional for the month: в январе, в мае.", opts)))
                    elif lem in TIMEW or lem in DAYS or lem in MONTHS:
                        out.append(("time", "t6-from-till-by", D(j, p, why, opts)))
        # ── numbers + noun ──
        if (w in NUM_GS or w in NUM_GP or w in QUANT or w in COLLECT) and i + 1 < len(low):
            j = i + 1
            ps2 = [p for p in parses(low[j]) if p.tag.POS == "NOUN" and p.tag.case == "gent" and not (tags(p) & SKIP_TAGS)]
            if ps2 and p0.tag.case in (None, "nomn", "accs"):
                p = ps2[0]
                num = p.tag.number
                if w in NUM_GS and num == "sing":
                    out.append(("count", "c1-numbers-nouns", D(j, p, "After «%s» the noun is genitive singular." % w, case_options(p, "sing", ws[j].group()) + [form_of(p, {"gent", "plur"}) or ""])))
                elif (w in NUM_GP) and num == "plur":
                    out.append(("count", "c2-genitive-plural", D(j, p, "After «%s» the noun is genitive plural." % w, [ws[j].group().lower(), form_of(p, {"gent", "sing"}) or "", form_of(p, {"nomn", "plur"}) or ""])))
                elif w in QUANT:
                    out.append(("count", "c3-how-many", D(j, p, "After «%s» the noun is genitive %s." % (w, "plural" if num == "plur" else "singular"), [ws[j].group().lower(), form_of(p, {"nomn", "sing"}) or "", form_of(p, {"gent", "plur" if num == "sing" else "sing"}) or ""])))
                elif w in COLLECT:
                    out.append(("count", "c8-collective-half", D(j, p, "After «%s» the noun is genitive %s." % (w, "plural" if num == "plur" else "singular"), [ws[j].group().lower(), form_of(p, {"nomn", "plur"}) or "", form_of(p, {"gent", "plur" if num == "sing" else "sing"}) or ""])))
                if p.normal_form in TIMEW:
                    out.append(("time", "t4-how-long" if p.normal_form not in ("час",) else "t1-clock", D(j, p, "After «%s»: genitive %s." % (w, "plural" if num == "plur" else "singular"))))
        # numerals in oblique cases (двум, тремя, пяти …): blank the numeral
        if p0.tag.POS == "NUMR" and p0.tag.case in ("gent", "datv", "ablt", "loct") and w not in QUANT:
            base = p0.normal_form
            sec = "c4-one-two-three-four" if base in ("два", "три", "четыре", "оба") else "c5-five-and-up" if base in NUM_GP else None
            if sec:
                opts = []
                for c in CASES:
                    f = form_of(p0, {c})
                    if f and f not in opts:
                        opts.append(f)
                out.append(("count", sec, D(i, p0, "The number agrees in case with the noun: %s." % CASE_EN[p0.tag.case], opts)))
        if p0.tag.POS == "ADJF" and "Anum" in t0 and p0.score > 0.3 and p0.normal_form not in ("один",) and not p0.normal_form.endswith(("тысячный", "сотый", "десятый")) or (p0.tag.POS == "ADJF" and p0.normal_form in ("первый", "второй", "третий", "десятый") and p0.score > 0.3):
            out.append(("count", "c7-ordinals-fractions", D(i, p0, "An ordinal is declined like an adjective.")))
        # time adverbs
        if w in ("утром", "днём", "днем", "вечером", "ночью"):
            if ok(i) and not (i > 0 and (low[i - 1] in PREP or parses(low[i - 1])[0].tag.POS == "ADJF")):
                out.append(("time", "t2-parts-of-day", Drill(ru, en, ws, i, ws[i].group(), {"утром": "утро", "днём": "день", "днем": "день", "вечером": "вечер", "ночью": "ночь"}[w], "The instrumental of the noun is the adverb of time.", ["утром", "днём", "вечером", "ночью"])))
        if w.startswith("кажд") and p0.normal_form == "каждый" and i + 1 < len(low):
            out.append(("time", "t2-parts-of-day", D(i, p0, "«каждый» agrees with the noun after it.")))
        # ── verb forms ──
        pv = [p for p in ps if p.score > 0.2]
        if not pv:
            continue
        p = pv[0]
        T = tags(p)
        if p.tag.POS == "VERB" and "impr" in T and "excl" in T:
            other = form_of(p, {"impr", "excl", "plur" if "sing" in T else "sing"})
            out.append(("forms", "f1-imperative", D(i, p, "The imperative, %s form." % ("ты" if "sing" in T else "вы"), [w, other or "", form_of(p, {"pres", "3per", "sing"}) or form_of(p, {"futr", "3per", "sing"}) or ""], lemma=p.normal_form + (", ты" if "sing" in T else ", вы"))))
        if p.tag.POS == "VERB" and "past" in T and any(x == "бы" for x in low[max(0, i - 2):i + 3]):
            out.append(("forms", "f2-conditional", D(i, p, "With «бы» the verb is in the past tense.", [w, form_of(p, {"futr" if p.tag.aspect == "perf" else "pres", "3per", "sing"}) or "", p.normal_form])))
        if p.tag.POS == "PRTS" and "pssv" in T:
            out.append(("forms", "f3-short-passive", D(i, p, "A short past passive participle agrees with the subject.")))
        if p.tag.POS == "PRTF":
            sec = None
            if "pssv" in T and "past" in T:
                sec, why = "f4-long-passive", "A long past passive participle, declined like an adjective."
            elif "actv" in T and "pres" in T:
                sec, why = "f5-present-active", "A present active participle: -щий, declined like an adjective."
            elif "actv" in T and "past" in T:
                sec, why = "f6-past-active", "A past active participle: -вший / -ший, declined like an adjective."
            elif "pssv" in T and "pres" in T:
                sec, why = "f7-passive-present", "A present passive participle: -емый / -имый."
            if sec:
                out.append(("forms", sec, D(i, p, why)))
        if p.tag.POS == "GRND":
            if "impf" in T:
                out.append(("forms", "f8-gerund-imperfective", D(i, p, "An imperfective деепричастие: -я / -а, an action at the same time.")))
            else:
                d = D(i, p, "A perfective деепричастие: -в / -вшись, an action done first.")
                if w.endswith("в"):
                    d.extra = [w + "ши"]
                out.append(("forms", "f9-gerund-perfective", d))
        # ── verbs of motion ──
        if p.tag.POS == "VERB" and p.normal_form in MOTION and ("pres" in T or "past" in T or "futr" in T):
            pair = M.parse(MOTION[p.normal_form])[0]
            gr = {g for g in (p.tag.tense, p.tag.person, p.tag.number, p.tag.gender) if g}
            f = form_of(pair, gr)
            if f and f != w:
                uni = p.normal_form in ("идти", "ехать", "лететь", "бежать", "плыть", "нести", "вести", "везти", "брести", "ползти", "катить", "тащить", "гнать", "лезть")
                sec = "m01-two-kinds" if p.normal_form in ("идти", "ходить", "ехать", "ездить", "лететь", "летать") else "m03-carry-lead-drive"
                if ok(i): out.append(("motion", sec, Drill(ru, en, ws, i, ws[i].group(), "", "%s: %s." % (p.normal_form, "one way, under way" if uni else "round trips, habit, or in general"), [w, f])))
        if p.tag.POS == "VERB" and PREFIX.match(p.normal_form):
            pre = PREFIX.match(p.normal_form).group(1)
            sec = {"при": "m04-prefixes", "у": "m04-prefixes", "в": "m05-in-out", "вы": "m05-in-out", "под": "m06-toward-away",
                   "от": "m06-toward-away", "до": "m07-reach-cross", "пере": "m07-reach-cross", "про": "m08-through-around",
                   "об": "m08-through-around", "обо": "m08-through-around", "за": "m09-drop-by-down", "с": "m09-drop-by-down",
                   "со": "m09-drop-by-down", "по": "m02-setting-out"}.get(pre)
            if pre == "по" and not re.match(r"^по(йти|ехать|лететь|бежать|плыть|нести|вести|везти)$", p.normal_form):
                sec = None
            if sec and not (i + 1 < len(low) and low[i + 1] in ("себя", "на")):
                out.append(("motion", sec, D(i, p, "«%s-»: %s." % (pre, p.normal_form))))
    return [x for x in out if x[2] is not None]


def key(d):
    return hashlib.md5((d.ru + "|" + d.answer).encode("utf-8")).hexdigest()


def exercise(d, n):
    src = " Sentence and translation from Tatoeba (CC BY 2.0 FR)."
    opts = [o for o in dict.fromkeys(x for x in (d.options or []) if x)]
    ans = d.answer.lower()
    if len(opts) >= 3 and n % 2 == 1 and ans in opts:
        opts = [ans] + [o for o in opts if o != ans][:3]
        h = int(key(d)[:6], 16)
        k = h % len(opts)
        opts[0], opts[k] = opts[k], opts[0]
        return {"type": "mc", "q": d.en, "ru": d.blanked(False), "options": opts, "answer": opts.index(ans), "why": d.why + src}
    if len(opts) == 2 and not d.lemma:        # motion pairs: always a choice
        o = sorted(opts)
        return {"type": "mc", "q": d.en, "ru": d.blanked(False), "options": o, "answer": o.index(ans), "why": d.why + src}
    return {"type": "fill", "q": d.blanked(bool(d.lemma)), "prompt": d.en, "answers": [d.answer] + d.extra, "why": d.why + src}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/tatoeba/rus.txt")
    pairs = read(path)
    print("%d sentence pairs" % len(pairs), flush=True)
    found = defaultdict(list)
    seen = set()
    for ru, en, _ in pairs:
        if ru in seen:
            continue
        seen.add(ru)
        for c, s, d in scan(ru, en):
            found[(c, s)].append(d)
    out = defaultdict(dict)
    for (c, s), ds in sorted(found.items()):
        ds.sort(key=lambda d: (len(d.words) > 9, hashlib.md5((s + key(d)).encode()).hexdigest()))
        pick, lem, sents = [], defaultdict(int), set()
        for cap in (1, 2, 4):                       # one sentence per word, unless the section is short of words
            for d in ds:
                lk = (d.lemma or d.answer.lower()).split(",")[0]
                if lem[lk] >= cap or d.ru in sents:
                    continue
                lem[lk] += 1; sents.add(d.ru); pick.append(d)
                if len(pick) >= PER:
                    break
            if len(pick) >= PER:
                break
        out[c][s] = [exercise(d, n) for n, d in enumerate(pick)]
        print("%-7s %-26s %4d found, %2d used" % (c, s, len(ds), len(pick)))
    io.open(os.path.join(HERE, "drills.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
