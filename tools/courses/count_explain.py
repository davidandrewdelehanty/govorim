# -*- coding: utf-8 -*-
"""Counting Things: one short explanation per exercise, shown after the answer, about that exercise only.

Before this the course showed the same long lesson quote above the question (`context`) and again after the answer (`why`).
Now `context` is empty and `why` is one line: the number range the counting word belongs to and the case it takes
(2–4, 22–24, 32–34… → genitive singular;  5–20, 25–30, 35–40… → genitive plural), or, for the declined numerals and ordinals,
the word that decides the case.  Exercises that are not about counting (a noun after a preposition, a verb, a pronoun) are dropped.
Usage: count_explain.py [--apply]
"""
import io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DIR = os.path.join(ROOT, "public", "courses", "count")

# exercises that are not about counting things  {file: {ids}}
DROP = {
    "c2-genitive-plural": {"q3", "q7"},                        # same sentences as c1-numbers-nouns q2, q3
    "c6-hundreds-thousands": {"q2", "q4", "q5", "q6", "q10", "q13", "q14"},   # a noun after a preposition / ordinal: no number involved
    "c7-ordinals-fractions": {"q1", "q2", "q3"},               # a verb, a verb, a pronoun
}

R2 = "2–4, 22–24, 32–34… (not 12–14)"
R1 = "1, 21, 31… take the nominative singular"
R5 = "5–20, 25–30, 35–40…"
RR = "round tens and hundreds (30, 50, 100, 800…)"

W2 = {"два", "две", "три", "четыре", "полтора", "полторы"}
WA = {"пять", "шесть", "семь", "восемь", "девять", "десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать",
      "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать", "двадцать"}
WR = {"тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят", "девяносто", "сто", "двести", "триста",
      "четыреста", "пятьсот", "шестьсот", "семьсот", "восемьсот", "девятьсот"}
NUMW = W2 | WA | WR | {"один", "одна", "одно", "тысяча", "тысячи", "тысяч", "миллион"}
COLL = {"двое", "трое", "четверо", "пятеро", "шестеро", "семеро"}
QUANT = {"много", "несколько", "сколько"}
MASS = {"рис", "джем", "вода"}
SPECIAL = {"год": "год → лет, irregular", "человек": "plural люди → людей", "ребёнок": "plural дети → детей",
           "сын": "plural сыновья → сыновей"}


def pre(q):
    """The words before the blank, lowercased."""
    return re.findall(r"[А-Яа-яЁё]+", q.split("___")[0].lower())


def hint(q):
    m = re.search(r"___ \(([^)]*)\)", q)
    return m.group(1).strip() if m else ""


_M = []


def _gen_number(h, a):
    """'sing' / 'plur' when the answer is only the genitive singular / plural of the hint noun (pymorphy3), else None."""
    try:
        if not _M:
            import pymorphy3
            _M.append(pymorphy3.MorphAnalyzer())
        M = _M[0]
    except Exception:
        return None
    nn = lambda w: w.lower().replace("ё", "е")
    nums = {p.tag.number for p in M.parse(a) if p.tag.POS == "NOUN" and p.tag.case in ("gent", "gen2") and nn(p.normal_form) == nn(h)}
    return next(iter(nums)) if len(nums) == 1 else None


def counted(e):
    q, a = e["q"], e["answers"][0]
    w, h = pre(q), hint(q)
    prev = w[-1] if w else ""
    if prev in W2 | WA | WR:
        phrase = []
        for x in reversed(w):
            if x in NUMW:
                phrase.insert(0, x)
            else:
                break
        num = " ".join(phrase)
        shown = "**%s %s**" % (num, a)
        form = "%s → %s" % (h, a)
        if h in SPECIAL:
            form = SPECIAL[h]
        if prev in W2:
            form = "%s → %s" % (h, a)
            extra = " (полтора / полторы with a feminine noun)" if prev.startswith("полтор") else ""
            return "%s — %s take the genitive singular (%s); %s." % (shown, R2, form, R1) if not extra else \
                   "%s — полтора (полторы with a feminine noun) takes the genitive singular, like 2–4 (%s)." % (shown, form)
        if prev in WA:
            return "%s — %s take the genitive plural (%s)." % (shown, R5, form)
        return "%s — %s take the genitive plural (%s)." % (shown, RR, form)
    if prev in COLL:
        return "**%s %s** — двое, трое, четверо… семеро (collective numerals for people) take the genitive plural (%s)." % (
            prev, a, SPECIAL.get(h, "%s → %s" % (h, a)))
    if prev in QUANT:
        if h in MASS or _gen_number(h, a) == "sing":
            return "**%s %s** — %s with something you cannot count takes the genitive singular (%s → %s)." % (prev, a, prev, h, a)
        return "**%s %s** — %s with something you can count takes the genitive plural (%s)." % (prev, a, prev, SPECIAL.get(h, "%s → %s" % (h, a)))
    return None


# written by hand for the exercises counted() cannot read: declined numerals, ordinals, thousands, one, plain genitive plurals
MAN = {
    "c1-numbers-nouns": {
        "q3": "**две тысячи рублей** — тысяча is itself a noun, and a noun of quantity takes the genitive plural of what is counted: тысяч(и) + рублей (рубль → рублей).",
        "q4": "**одно небольшое поле** — 1, 21, 31… take the nominative singular, so одно and небольшое agree with its gender: поле is neuter.",
        "q6": "**одна спокойная мысль** — 1, 21, 31… take the nominative singular, so одна and спокойная agree with its gender: мысль is feminine.",
    },
    "c2-genitive-plural": {
        "q1": "**хороших цен** — нет takes the genitive, plural here (хороших). Feminine -а drops its ending: цена → цен.",
        "q2": "**от теней** — от takes the genitive, plural here. Nouns in -ь take -ей: тень → теней.",
        "q4": "**осколки тарелок** — a noun that depends on a noun («pieces of what?») is genitive, plural here. Feminine -а drops its ending: тарелка → тарелок.",
        "q5": "**каких хитростей не придумывал** — after a negated verb the object is genitive, plural here. Nouns in -ь take -ей: хитрость → хитростей.",
        "q6": "**вид войск** — «the sight of what?» is genitive, plural here. Neuter -о drops its ending: войско → войск.",
        "q9": "**без слов** — без takes the genitive, plural here. Neuter -о drops its ending: слово → слов.",
    },
    "c4-one-two-three-four-practice": {
        "q1": "**родила двух** — родить takes the accusative; for people the accusative of два/три/четыре equals the genitive: двух.",
        "q2": "**о четырёх ногах** — о (here: «with») takes the prepositional; четыре → четырёх.",
        "q3": "**больше трёх лет** — больше takes the genitive: три → трёх.",
        "q4": "**обеих стран** — the numeral agrees with стран (genitive plural, feminine): обе → обеих.",
        "q5": "**завалил двух студентов** — animate accusative equals the genitive: два → двух.",
        "q6": "**около четырёх недель** — около takes the genitive: четыре → четырёх.",
        "q7": "**у трёх старушек** — у takes the genitive: три → трёх.",
        "q8": "**вам обоим** — «how old are you?» puts the person in the dative (вам), and обоим agrees with it: оба → обоим.",
        "q9": "**из четырёх атомов** — из takes the genitive: четыре → четырёх.",
        "q10": "**между двумя странами** — между takes the instrumental: два → двумя.",
        "q11": "**более четырёх миллионов** — более takes the genitive: четыре → четырёх.",
        "q12": "**Двух овец** — animate accusative equals the genitive (овец is genitive plural): два → двух.",
        "q13": "**эквивалентна трём чайным** — эквивалентный takes the dative: три → трём.",
        "q14": "**в трёх матчах** — в takes the prepositional here: три → трёх.",
    },
    "c4-one-two-three-four": {
        "q1": "**две тысячи** — тысяча is feminine, so «two» is две (not два); the noun after it is genitive singular: тысячи.",
        "q2": "**между этими двумя** — между takes the instrumental: два → двумя.",
        "q3": "**Эти две силы** — nominative, and сила is feminine: две.",
        "q4": "**каким-то двум парням** — продажа кому? takes the dative: два → двум.",
        "q5": "**обеими руками** — instrumental of a feminine noun: обе → обеими.",
        "q6": "**Две женщины** — nominative, and женщина is feminine: две.",
        "q7": "**за обоими** — идти за (follow) takes the instrumental: оба → обоими.",
        "q8": "**при всех трёх экзаменах** — при takes the prepositional: три → трёх.",
        "q9": "**к семи часам** — к takes the dative: семь → семи.",
        "q10": "**в двадцати саженях** — в takes the prepositional; every part of a numeral declines: двадцать → двадцати.",
        "q11": "**в четырёх зеркалах** — в takes the prepositional: четыре → четырёх.",
        "q12": "**присниться двум людям** — присниться кому? takes the dative: два → двум.",
    },
    "c5-five-and-up-practice": {
        "q1": "**из десяти** — из takes the genitive: десять → десяти.",
        "q2": "**нет тридцати** — нет takes the genitive: тридцать → тридцати.",
        "q3": "**до шестнадцати** — до takes the genitive: шестнадцать → шестнадцати.",
        "q4": "**из пятисот** — из takes the genitive, and both parts of пятьсот decline: пятьсот → пятисот.",
        "q5": "**больше сорока** — больше takes the genitive: сорок → сорока.",
        "q6": "**с девяти** — с («from… on») takes the genitive: девять → девяти.",
        "q7": "**семи пядей** — a fixed phrase with the genitive of quality: семь → семи.",
        "q8": "**больше ста** — больше takes the genitive: сто → ста.",
        "q9": "**в пяти актах** — в takes the prepositional: пять → пяти.",
        "q10": "**из двенадцати** — из takes the genitive: двенадцать → двенадцати.",
        "q11": "**около двадцати** — около takes the genitive: двадцать → двадцати.",
        "q12": "**около восьмидесяти** — около takes the genitive, and both parts of восемьдесят decline: восемьдесят → восьмидесяти.",
        "q13": "**нет девяноста** — нет takes the genitive: девяносто → девяноста.",
        "q14": "**для тринадцати лет** — для takes the genitive: тринадцать → тринадцати.",
    },
    "c5-five-and-up": {
        "q1": "**обеими руками** — instrumental of a feminine noun: обе → обеими.",
        "q2": "**двумя картонками** — груженный takes the instrumental: две → двумя.",
        "q3": "**покрытый двумя простынями** — покрытый takes the instrumental: две → двумя.",
        "q4": "**к пяти** — к takes the dative: пять → пяти.",
        "q5": "**в трёх гостиницах** — в takes the prepositional: три → трёх.",
        "q6": "**в сорока верстах** — в takes the prepositional: сорок → сорока.",
        "q7": "**в трёх местах** — в takes the prepositional: три → трёх.",
        "q8": "**нам обоим** — укрыться впору нам, so обоим is dative: оба → обоим.",
        "q9": "**к обоим берегам** — к takes the dative: оба → обоим.",
    },
    "c6-hundreds-thousands": {
        "q3": "**две тысячи** — 2–4 take the genitive singular: тысяча → тысячи.",
        "q7": "**дам тысячу рублей** — a direct object is accusative: тысяча → тысячу (feminine -а → -у); what is counted then goes in the genitive plural.",
        "q8": "**полторы тысячи** — полторы (feminine) takes the genitive singular, like 2–4: тысяча → тысячи.",
        "q9": "**двадцать пять тысяч** — 25–30 take the genitive plural: тысяча → тысяч (feminine -а drops its ending).",
        "q11": "**около сорока человек** — около takes the genitive: сорок → сорока.",
        "q12": "**от тысячи двухсот** — от takes the genitive, and the whole number declines: тысяча → тысячи.",
    },
    "c7-ordinals-fractions-practice": {
        "q1": "**вторая пуговица** — an ordinal agrees with its noun like an adjective: пуговица is feminine nominative, so вторая.",
        "q2": "**девятый месяц** — месяц is masculine nominative, so девятый.",
        "q3": "**раньше шестой недели** — раньше takes the genitive, and неделя is feminine: шестой.",
        "q4": "**Первым баптистом был** — after был the predicate is instrumental, masculine: первым.",
        "q5": "**четвёртого** — a date in the genitive («on the 4th») takes -ого.",
        "q6": "**четырёхмиллионное предложение** — предложение is neuter, nominative or accusative: -ое.",
        "q7": "**сорок пятый добавочный** — the ordinal agrees with добавочный (masculine nominative): пятый.",
        "q8": "**на седьмом месяце** — на takes the prepositional, masculine: седьмом.",
        "q9": "**хочу третий вариант** — masculine inanimate accusative equals the nominative: третий.",
        "q10": "**в середине девяностых** — середины takes the genitive; (годы) is plural: девяностых.",
        "q11": "**мой семнадцатый день рождения** — день is masculine nominative: семнадцатый.",
        "q12": "**к четырнадцатому** — к takes the dative; a date is neuter: -ому.",
        "q13": "**статуя шестнадцатого века** — век is masculine genitive: -ого.",
        "q14": "**двадцатое октября** — «it is the 20th» is a neuter nominative (число): -ое.",
    },
}

TIDY = [("серебром-с,.", "серебром-с.")]


def process(j, stem):
    drop = DROP.get(stem, set())
    man = MAN.get(stem, {})
    out, dropped, fails = [], [], []
    for e in j.get("exercises") or []:
        if e["id"] in drop:
            dropped.append(e["id"]); continue
        w = man.get(e["id"]) or counted(e)
        if not w:
            fails.append(e["id"]); out.append(e); continue
        e["why"] = w
        e["context"] = ""
        for a, b in TIDY:
            e["q"] = e["q"].replace(a, b)
        out.append(e)
    j["exercises"] = out
    return dropped, fails


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    apply = "--apply" in argv
    tot = 0
    for fn in sorted(os.listdir(DIR)):
        if fn == "exam.json" or not fn.endswith(".json"):
            continue
        p = os.path.join(DIR, fn)
        j = json.load(io.open(p, encoding="utf-8"))
        before = len(j.get("exercises") or [])
        dropped, fails = process(j, fn[:-5])
        tot += before - len(j["exercises"])
        print("%-34s %2d -> %2d  dropped %s  unexplained %s" % (fn, before, len(j["exercises"]), dropped, fails))
        if apply:
            io.open(p, "w", encoding="utf-8").write(json.dumps(j, ensure_ascii=False))
    print("count_explain: %d dropped%s" % (tot, "" if apply else " (dry run)"))


if __name__ == "__main__":
    main()
