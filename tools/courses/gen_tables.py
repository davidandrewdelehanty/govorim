# -*- coding: utf-8 -*-
"""Generate every table in the Grammar Tables course from the OpenCorpora
dictionary (through pymorphy3) and write them to tables_data.json.

Nothing here writes a Russian ending by hand: each cell is the dictionary's
own form for the word and grammatical tags asked for, so no form in the
finished course can be invented.  Re-run it and the tables rebuild:

    pip install pymorphy3 pymorphy3-dicts-ru
    python3 tools/courses/gen_tables.py
"""
import io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paradigms as P
_P = P

OUT = {}


def put(key, head, rows, caption=None):
    OUT[key] = {"head": head, "rows": rows}
    if caption:
        OUT[key]["caption"] = caption
    return OUT[key]


def _n(word, tag, num):
    """One noun form, straight from the dictionary."""
    return P._cell(P._lemma(word, "NOUN").lexeme, tag, num)


# =========================================================== SPELLING  RULES

# ы never follows г к х ж ч ш щ: the regular -ы of the nominative plural and of
# the feminine genitive singular comes out as -и.
SP = ["книга", "река", "госпожа", "девушка", "учебник", "гараж",
      "карандаш", "ключ", "товарищ"]
put("spell-y", ["", "Gen. sing.", "Nom. plur."],
    [[_n(w, "nomn", "sing"), _n(w, "gent", "sing"), _n(w, "nomn", "plur")] for w in SP])

# unstressed -ей after ж ч ш щ ц, stressed -ой
put("spell-ey", ["", "Instr. sing."],
    [[_n(w, "nomn", "sing"), _n(w, "ablt", "sing")]
     for w in ["госпожа", "учительница", "улица", "душа"]])

put("spell-yoy", ["", "Instr. sing."],
    [[_n(w, "nomn", "sing"), _n(w, "ablt", "sing")]
     for w in ["деревня", "армия", "семья", "земля"]])


# ======================================================================  NOUNS

put("noun-masc-neut-sg", *P.noun_num(
    ["студент", "дом", "учитель", "автомобиль", "Андрей", "трамвай",
     "окно", "поле", "здание"], "sing"))
put("noun-masc-neut-pl", *P.noun_num(
    ["студент", "дом", "учитель", "автомобиль", "Андрей", "трамвай",
     "окно", "поле", "здание"], "plur"))
put("noun-fem-sg", *P.noun_num(["сестра", "тётя", "армия", "часть"], "sing"))
put("noun-fem-pl", *P.noun_num(["сестра", "тётя", "армия", "часть"], "plur"))

# the whole noun system in one grid, singular beside plural
put("noun-all", *P.nouns(
    ["студент", "учитель", "трамвай", "окно", "поле", "здание",
     "сестра", "тётя", "армия", "часть"]))

# -- irregular and awkward nouns -------------------------------------------
put("noun-mat-doch", *P.nouns(["мать", "дочь"]))
put("noun-mya", *P.nouns(["имя", "время", "знамя", "племя", "семя"]))
put("noun-put", *P.nouns(["путь", "дитя"]))
put("noun-anin", *P.nouns(["крестьянин", "англичанин", "гражданин", "хозяин", "господин"]))
put("noun-yonok", *P.nouns(["ребёнок", "котёнок", "телёнок"]))
put("noun-ya-plural", *P.nouns(["брат", "друг", "сын", "стул", "лист", "дерево", "крыло", "перо", "зуб"]))
put("noun-a-plural", *P.nouns(["дом", "город", "лес", "берег", "вечер", "поезд", "доктор", "профессор"]))
put("noun-genpl-bare", *P.nouns(["раз", "солдат", "глаз", "чулок", "ботинок", "сапог", "партизан", "грамм"]))
put("noun-suppletive", *P.nouns(["человек", "год", "цветок", "небо", "чудо", "ухо"]))
# these have no singular, so only the plural column is shown
put("noun-plural-only", *P.noun_num(["ножницы", "часы", "деньги", "ворота", "сани", "очки", "брюки", "сутки"], "plur"))
put("noun-indeclinable", *P.nouns(["пальто", "кино", "метро", "кафе", "такси", "радио", "шоссе"]))
put("noun-fleeting", *P.nouns(["отец", "американец", "кусок", "звонок", "день", "окно", "сестра", "письмо", "девушка"]))
put("noun-masc-in-a", *P.nouns(["мужчина", "дедушка", "дядя", "старшина", "судья"]))

# ================================================================  ADJECTIVES

ADJ5 = ["новый", "синий", "русский", "хороший", "большой"]
ADJL = ["hard (новый)", "soft (синий)", "velar к г х (русский)",
        "sibilant ж ш ч щ (хороший)", "stressed ending (большой)"]
for g, key in (("masc", "adj-masc"), ("femn", "adj-fem"), ("neut", "adj-neut")):
    put(key, *P.adj_case_table(ADJ5, labels=ADJL, gender=g))
put("adj-plur", *P.adj_case_table(ADJ5, labels=ADJL, num="plur"))
put("adj-nom-all", *P.adj_row_table(ADJ5, labels=ADJL))

put("adj-possessive-mamin", *P.pron_full("мамин"))
put("adj-possessive-lisiy", *P.pron_full("лисий"))
put("adj-third", *P.pron_full("третий"))

SHORT = ["новый", "хороший", "умный", "больной", "сильный", "молодой", "лёгкий", "весёлый"]
put("adj-short", ["", "Masc.", "Fem.", "Neut.", "Plural"],
    [[w] + P.adj_short(w) for w in SHORT])
put("noun-genpl", ["", "Gen. plur."],
    [[w, _n(w, "gent", "plur")] for w in
     ["студент", "музей", "учитель", "карандаш", "ключ", "месяц",
      "комната", "неделя", "армия", "часть", "окно", "поле", "здание"]])

COMP = ["новый", "хороший", "плохой", "большой", "маленький", "старый", "молодой",
        "дорогой", "дешёвый", "высокий", "низкий", "далёкий", "близкий", "лёгкий",
        "тихий", "громкий", "широкий", "узкий", "глубокий", "частый", "редкий",
        "короткий", "долгий", "сладкий", "простой", "богатый", "чистый", "густой"]
put("adj-comparative", ["", "Comparative", "with по-", "Superlative"],
    [[w] + list(P.adj_comp(w)) + [P.adj_supr(w)] for w in COMP])

# ==================================================================  PRONOUNS

put("pron-personal", *P.personal(["я", "ты", "он", "она", "оно", "мы", "вы", "они"]))
put("pron-kto-chto", *P.pron_table(["кто", "что"], num=None))
put("pron-sebya", *P.pron_table(["себя"], num=None))
for w, key in (("этот", "pron-etot"), ("тот", "pron-tot"), ("весь", "pron-ves"),
               ("сам", "pron-sam"), ("самый", "pron-samyy"),
               ("мой", "pron-moy"), ("твой", "pron-tvoy"), ("свой", "pron-svoy"),
               ("наш", "pron-nash"), ("ваш", "pron-vash"), ("чей", "pron-chey"),
               ("какой", "pron-kakoy"), ("который", "pron-kotoryy"),
               ("каждый", "pron-kazhdyy"), ("другой", "pron-drugoy"),
               ("один", "pron-odin"), ("никакой", "pron-nikakoy"), ("ничей", "pron-nichey")):
    put(key, *P.pron_full(w))
put("pron-nikto", *P.pron_table(["никто", "ничто"], num=None))

# ==================================================================  NUMERALS

put("num-1-4", *P.numr_table(["два", "три", "четыре"]))
put("num-5-up", *P.numr_table(["пять", "восемь", "десять", "двадцать", "тридцать", "пятьдесят"]))
put("num-tens", *P.numr_table(["сорок", "девяносто", "сто", "двести", "триста", "четыреста", "пятьсот"]))
put("num-collective", *P.numr_table(["двое", "трое", "четверо", "оба", "полтора"]))
put("num-big", *P.nouns(["тысяча", "миллион", "миллиард"]))
put("num-ordinal-third", *P.pron_full("третий"))
put("num-ordinal-first", *P.pron_full("первый"))

# =====================================================================  VERBS

put("spell-verb", *P.verb_present(["читать", "говорить", "служить", "держать"]))

put("verb-two-conj", *P.verb_present(
    ["читать", "работать", "говорить", "любить"],
    labels=["читать (I)", "работать (I)", "говорить (II)", "любить (II)"]))

MUT = [("б → бл", "любить"), ("п → пл", "купить"), ("в → вл", "ловить"),
       ("ф → фл", "графить"), ("м → мл", "кормить"), ("д → ж", "ходить"),
       ("з → ж", "возить"), ("с → ш", "просить"), ("ст → щ", "чистить"),
       ("т → ч", "платить"), ("т → щ", "защитить"), ("к → ч", "плакать"),
       ("г → ж", "лгать"), ("х → ш", "писать"), ("ск → щ", "искать")]
rows = []
for label, w in MUT:
    try:
        h, r = P.verb_present([w])
        rows.append([label, w, r[0][1], r[2][1]])
    except Exception:
        rows.append([label, w, "—", "—"])
put("verb-mutation", ["", "Infinitive", "я", "он"], rows)

CLASSES = [
    (1,  "-ать, -ять, -еть", ["делать", "читать", "гулять", "уметь"]),
    (2,  "-овать, -евать",   ["рисовать", "советовать", "танцевать", "требовать"]),
    (3,  "-нуть",            ["гибнуть", "рискнуть", "взглянуть", "привыкнуть"]),
    (4,  "-ить",             ["жалить", "щадить", "любить", "просить", "ходить"]),
    (5,  "-ать, -ять, -еть", ["видеть", "велеть", "смотреть", "держать", "лежать"]),
    (6,  "-ать, -ять",       ["писать", "искать", "ждать", "брать", "звать"]),
    (7,  "-зти, -зть, -сти, -сть", ["нести", "везти", "вести", "класть", "расти"]),
    (8,  "-чь",              ["мочь", "печь", "беречь", "лечь", "жечь"]),
    (9,  "-ереть",           ["умереть", "запереть", "тереть"]),
    (10, "-олоть, -ороть",   ["колоть", "пороть", "молоть"]),
    (11, "-ить",             ["пить", "бить", "шить", "лить", "вить"]),
    (12, "-ыть, -уть, -еть", ["мыть", "крыть", "дуть", "греть", "петь", "брить"]),
    (13, "-авать",           ["давать", "вставать", "узнавать"]),
    (14, "-ать, -ять",       ["занять", "принять", "взять", "начать", "понять"]),
    (15, "-ть (present -ну)", ["деть", "стать", "застрять"]),
    (16, "-ть (present -ву)", ["жить", "плыть", "слыть"]),
]
for n, ending, verbs in CLASSES:
    put("class-%d-pres" % n, *P.verb_present(verbs))
    put("class-%d-past" % n, *P.verb_past(verbs))
    put("class-%d-impr" % n, *P.verb_impr(verbs))
OUT["_classes"] = [{"n": n, "ending": e, "verbs": v} for n, e, v in CLASSES]

# быть is apart: its present survives only in the 3rd person (есть), and
# буду/будешь… are its future, so it gets a table of its own.
put("verb-byt-pres", *P.verb_pres_only(["быть"]))
put("verb-byt-futr", *P.verb_futr(["быть"]))
put("verb-byt-past", *P.verb_past(["быть"]))
put("verb-byt-impr", *P.verb_impr(["быть"]))

IRREG = ["есть", "дать", "хотеть", "бежать", "идти", "ехать"]
put("verb-irregular-pres", *P.verb_present(IRREG))
put("verb-irregular-past", *P.verb_past(IRREG))
put("verb-irregular-impr", *P.verb_impr(IRREG))

PAST = ["читать", "идти", "нести", "везти", "вести", "мочь", "печь", "беречь",
        "умереть", "запереть", "привыкнуть", "исчезнуть", "есть", "класть", "расти"]
put("verb-past-irregular", *P.verb_past(PAST))

IMPR = ["читать", "говорить", "писать", "ждать", "вставать", "давать", "пить",
        "есть", "лечь", "ехать", "идти", "быть", "помнить", "встать"]
put("verb-imperative", *P.verb_impr(IMPR, incl=True))

PARTV = ["читать", "говорить", "писать", "нести", "видеть", "строить",
         "прочитать", "написать", "открыть", "купить", "принести", "взять"]
put("verb-participles-a", *P.verb_participles(PARTV[:6]))
put("verb-participles-b", *P.verb_participles(PARTV[6:]))
put("part-short", ["", "Masc.", "Fem.", "Neut.", "Plural"],
    [[w] + P.part_short(w) for w in
     ["прочитать", "написать", "открыть", "купить", "построить", "принести", "взять", "забыть"]])
put("part-decl-pssv", *P.part_decl("прочитать"))
put("part-decl-actv", *P.part_decl("читать", which=("pres", "actv")))

GERV = ["читать", "говорить", "нести", "идти", "быть", "прочитать", "написать",
        "принести", "прийти", "увидеть"]
put("verb-participles-c", *P.verb_participles(GERV))




# =====================================================================  DRILLS
#
# Each drill is [headword, what is asked for, [every accepted answer]].  The
# answers are the dictionary's own forms for exactly those grammatical tags,
# so a drill cannot ask for a form that does not exist or accept one that is
# wrong.  tables_course.py wraps these into exercises and puts the section's
# own quoted rule above each one.

DRILLS = {}

CASE_EN = {"nomn": "nominative", "gent": "genitive", "datv": "dative",
           "accs": "accusative", "ablt": "instrumental", "loct": "prepositional"}
NUM_EN = {"sing": "singular", "plur": "plural"}


def _forms(lex, *tags):
    return _P._pick(lex, *tags)


def noun_drills(key, words, cases=("gent", "datv", "accs", "ablt", "loct"), nums=("sing", "plur")):
    out = []
    for w in words:
        try:
            lex = P._lemma(w, "NOUN").lexeme
        except P.NotInDict:
            continue
        for num in nums:
            for c in cases:
                got = P._pick(lex, c, num)
                if not got:
                    continue
                out.append([w, "%s %s" % (CASE_EN[c], NUM_EN[num]), got])
    DRILLS.setdefault(key, []).extend(out)


def adj_drills(key, words, genders=("masc", "femn", "neut"), cases=("gent", "datv", "ablt", "loct")):
    out = []
    for w in words:
        lex = P._lemma(w, "ADJF").lexeme
        for g in genders:
            for c in cases:
                got = P._pick(lex, "ADJF", c, g, "sing", drop=P.ADJ_DROP)
                if got:
                    out.append([w, "%s %s singular" % (CASE_EN[c], {"masc": "masculine", "femn": "feminine", "neut": "neuter"}[g]), got])
        for c in cases:
            got = P._pick(lex, "ADJF", c, "plur", drop=P.ADJ_DROP)
            if got:
                out.append([w, "%s plural" % CASE_EN[c], got])
    DRILLS.setdefault(key, []).extend(out)


def pron_drills(key, words):
    out = []
    for w in words:
        lex = P.pron(w)
        for c in ("gent", "datv", "accs", "ablt", "loct"):
            got = P._pick(lex, c)
            if got:
                out.append([w, CASE_EN[c], got])
    DRILLS.setdefault(key, []).extend(out)


PERSON_EN = [("sing", "1per", "\u044f"), ("sing", "2per", "\u0442\u044b"), ("sing", "3per", "\u043e\u043d"),
             ("plur", "1per", "\u043c\u044b"), ("plur", "2per", "\u0432\u044b"), ("plur", "3per", "\u043e\u043d\u0438")]


def verb_drills(key, words, what=("pres",)):
    out = []
    for w in words:
        lex = P._lemma(w, "INFN").lexeme
        if "pres" in what:
            for num, per, pro in PERSON_EN:
                got = P._pick(lex, "VERB", num, per, "pres") or P._pick(lex, "VERB", num, per, "futr")
                if got:
                    out.append([w, "the %s form" % pro, got])
        if "past" in what:
            for tags, pro in [(("masc", "sing"), "\u043e\u043d"), (("femn", "sing"), "\u043e\u043d\u0430"),
                              (("neut", "sing"), "\u043e\u043d\u043e"), (("plur",), "\u043e\u043d\u0438")]:
                got = P._pick(lex, "VERB", "past", *tags)
                if got:
                    out.append([w, "the past tense, %s" % pro, got])
        if "impr" in what:
            for num, pro in [("sing", "\u0442\u044b"), ("plur", "\u0432\u044b")]:
                got = P._pick(lex, "VERB", "impr", "excl", num)
                if got:
                    out.append([w, "the imperative, %s" % pro, got])
        if "part" in what:
            for tags, label in P.PART:
                got = P._pick(lex, "PRTF", "masc", "sing", "nomn", *tags)
                if got:
                    out.append([w, "the %s participle" % label.lower().replace(" participle", ""), got])
        if "grnd" in what:
            for tag, label in [("pres", "imperfective gerund"), ("past", "perfective gerund")]:
                got = P._pick(lex, "GRND", tag)
                if got:
                    out.append([w, "the %s" % label, got])
    DRILLS.setdefault(key, []).extend(out)


noun_drills("g1-spelling", SP, cases=("gent",), nums=("sing",))
noun_drills("g1-spelling", SP, cases=("nomn",), nums=("plur",))
noun_drills("g1-spelling", ["\u0433\u043e\u0441\u043f\u043e\u0436\u0430", "\u0443\u0447\u0438\u0442\u0435\u043b\u044c\u043d\u0438\u0446\u0430", "\u0443\u043b\u0438\u0446\u0430", "\u0434\u0435\u0440\u0435\u0432\u043d\u044f", "\u0430\u0440\u043c\u0438\u044f", "\u0441\u0435\u043c\u044c\u044f", "\u0437\u0435\u043c\u043b\u044f"],
            cases=("ablt",), nums=("sing",))

noun_drills("g2-nouns-sg", ["\u0441\u0442\u0443\u0434\u0435\u043d\u0442", "\u0434\u043e\u043c", "\u0443\u0447\u0438\u0442\u0435\u043b\u044c", "\u0430\u0432\u0442\u043e\u043c\u043e\u0431\u0438\u043b\u044c", "\u0442\u0440\u0430\u043c\u0432\u0430\u0439", "\u043e\u043a\u043d\u043e", "\u043f\u043e\u043b\u0435",
                           "\u0437\u0434\u0430\u043d\u0438\u0435", "\u0441\u0435\u0441\u0442\u0440\u0430", "\u0442\u0451\u0442\u044f", "\u0430\u0440\u043c\u0438\u044f", "\u0447\u0430\u0441\u0442\u044c", "\u043c\u0443\u0436\u0447\u0438\u043d\u0430", "\u0434\u044f\u0434\u044f"], nums=("sing",))
noun_drills("g3-nouns-pl", ["\u0441\u0442\u0443\u0434\u0435\u043d\u0442", "\u043c\u0443\u0437\u0435\u0439", "\u0443\u0447\u0438\u0442\u0435\u043b\u044c", "\u043a\u0430\u0440\u0430\u043d\u0434\u0430\u0448", "\u043a\u043b\u044e\u0447", "\u043c\u0435\u0441\u044f\u0446", "\u043a\u043e\u043c\u043d\u0430\u0442\u0430",
                           "\u043d\u0435\u0434\u0435\u043b\u044f", "\u0430\u0440\u043c\u0438\u044f", "\u0447\u0430\u0441\u0442\u044c", "\u043e\u043a\u043d\u043e", "\u043f\u043e\u043b\u0435", "\u0437\u0434\u0430\u043d\u0438\u0435"], nums=("plur",))
noun_drills("g4-noun-irregular", ["\u043c\u0430\u0442\u044c", "\u0434\u043e\u0447\u044c", "\u0438\u043c\u044f", "\u0432\u0440\u0435\u043c\u044f", "\u043f\u0443\u0442\u044c", "\u043a\u0440\u0435\u0441\u0442\u044c\u044f\u043d\u0438\u043d", "\u0430\u043d\u0433\u043b\u0438\u0447\u0430\u043d\u0438\u043d",
                                  "\u0440\u0435\u0431\u0451\u043d\u043e\u043a", "\u043a\u043e\u0442\u0451\u043d\u043e\u043a", "\u0431\u0440\u0430\u0442", "\u0434\u0440\u0443\u0433", "\u0434\u0435\u0440\u0435\u0432\u043e", "\u0433\u043e\u0440\u043e\u0434", "\u0447\u0435\u043b\u043e\u0432\u0435\u043a", "\u0443\u0445\u043e", "\u043d\u0435\u0431\u043e"])
noun_drills("g5-noun-awkward", ["\u043e\u0442\u0435\u0446", "\u0430\u043c\u0435\u0440\u0438\u043a\u0430\u043d\u0435\u0446", "\u043a\u0443\u0441\u043e\u043a", "\u0437\u0432\u043e\u043d\u043e\u043a", "\u0434\u0435\u043d\u044c", "\u0441\u0435\u0441\u0442\u0440\u0430", "\u043f\u0438\u0441\u044c\u043c\u043e", "\u0434\u0435\u0432\u0443\u0448\u043a\u0430",
                                "\u0441\u043e\u043b\u0434\u0430\u0442", "\u0433\u043b\u0430\u0437", "\u0441\u0430\u043f\u043e\u0433", "\u043d\u043e\u0436\u043d\u0438\u0446\u044b", "\u0434\u0435\u043d\u044c\u0433\u0438", "\u0441\u0443\u0442\u043a\u0438"])

adj_drills("g6-adjectives", ADJ5)
pron_drills("g9-pronouns", ["\u044f", "\u0442\u044b", "\u043e\u043d", "\u043e\u043d\u0430", "\u043c\u044b", "\u0432\u044b", "\u043e\u043d\u0438", "\u043a\u0442\u043e", "\u0447\u0442\u043e", "\u0441\u0435\u0431\u044f"])
adj_drills("g10-determiners", ["\u044d\u0442\u043e\u0442", "\u0442\u043e\u0442", "\u0432\u0435\u0441\u044c", "\u043c\u043e\u0439", "\u043d\u0430\u0448", "\u0447\u0435\u0439", "\u0441\u0430\u043c", "\u043a\u0430\u043a\u043e\u0439", "\u043e\u0434\u0438\u043d"])
pron_drills("g11-numerals", ["\u0434\u0432\u0430", "\u0442\u0440\u0438", "\u0447\u0435\u0442\u044b\u0440\u0435", "\u043f\u044f\u0442\u044c", "\u0441\u043e\u0440\u043e\u043a", "\u0441\u0442\u043e", "\u0434\u0432\u0435\u0441\u0442\u0438", "\u043e\u0431\u0430", "\u0434\u0432\u043e\u0435", "\u0442\u0440\u043e\u0435"])

verb_drills("g12-conjugation", ["\u0447\u0438\u0442\u0430\u0442\u044c", "\u0440\u0430\u0431\u043e\u0442\u0430\u0442\u044c", "\u0433\u043e\u0432\u043e\u0440\u0438\u0442\u044c", "\u043b\u044e\u0431\u0438\u0442\u044c", "\u0441\u043b\u0443\u0436\u0438\u0442\u044c", "\u0434\u0435\u0440\u0436\u0430\u0442\u044c"])
verb_drills("g13-mutation", [w for _, w in MUT])
for _n2, _e2, _vs in CLASSES:
    verb_drills("g14-classes", _vs[:3])
verb_drills("g15-irregular-verbs", IRREG + ["\u0431\u044b\u0442\u044c"], what=("pres", "past", "impr"))
verb_drills("g16-past", PAST, what=("past",))
verb_drills("g17-imperative", IMPR, what=("impr",))
verb_drills("g18-participles", PARTV, what=("part",))
verb_drills("g19-gerunds", GERV, what=("grnd",))

def _label(tasks):
    """Name several grammatical slots that share one form, as briefly as the
    English allows: "genitive masculine/neuter singular", not two sentences."""
    if len(tasks) == 1:
        return tasks[0]
    # Tasks of the same shape differing in one word collapse onto that word.
    groups, order = {}, []
    for t in tasks:
        w = t.split()
        key = None
        for k in order:
            kw = k.split()
            if len(kw) == len(w) and sum(a != b for a, b in zip(kw, w)) <= 1:
                key = k
                break
        if key is None:
            order.append(t)
            groups[t] = [w]
        else:
            groups[key].append(w)
    parts = []
    for k in order:
        ws = groups[k]
        base = ws[0][:]
        for i in range(len(base)):
            seen = []
            for w in ws:
                if w[i] not in seen:
                    seen.append(w[i])
            base[i] = "/".join(seen)
        parts.append(" ".join(base))
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def _merge(rows):
    """\u041c\u0430\u0442\u044c is \u043c\u0430\u0442\u0435\u0440\u0438 in the genitive, the dative and the prepositional: ask once
    and name all three, rather than three identical questions."""
    order, by = [], {}
    for word, task, answers in rows:
        k = (word, tuple(answers))
        if k not in by:
            by[k] = []
            order.append(k)
        by[k].append(task)
    return [[w, _label(by[(w, a)]), list(a)] for w, a in order]


OUT["_drills"] = {k: _merge(v) for k, v in DRILLS.items()}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "tables_data.json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(OUT, ensure_ascii=False, indent=1))
    cells = sum(len(r) for t in OUT.values() if isinstance(t, dict) for r in t.get("rows", []))
    print("%d tables, %d cells -> %s" % (len(OUT) - 1, cells, p))


if __name__ == "__main__":
    main()
