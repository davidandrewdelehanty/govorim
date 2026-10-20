#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Give every exercise in the time course the rule for the construction its
own sentence uses — or take the exercise out.

The practice sentences were mined from Tatoeba and the library by matching
time words, and each practice set then inherited its lesson's explanation
wholesale: «В + Prepositional is used to indicate the year or the month» sat
above «Я вырос в двуязычной среде», which is neither a year, a month, nor
Wednesday. Here each sentence is read for what it actually does —

    the preposition in front of the blank (или none),
    the case the answer is really in (pymorphy3, held to the hint's word),
    what kind of time word it is (a weekday, a month, a unit of time, a part
    of the day, a season, a meal…), and
    a number in front of it, which decides the noun's case itself

— and matched to the one DLI rule the course teaches for that construction.
The explanation above the question is that rule's first line; the one shown
after a right answer is the rule in full, with its DLI lesson, followed by the
sentence's own source. A sentence whose construction the course never
explains is removed and kept in tools/courses/_dropped/time-unexplained.json,
so nothing is lost and nothing is shown with an explanation that does not fit.

Every rule text below is the course's own DLI transcription (the time and
count course pages), plus «Accusative after ЧЕРЕЗ», DLI Lesson 47, p. 137,
checked against the page image.

    python3 tools/courses/explain_time.py            # report
    python3 tools/courses/explain_time.py --apply    # write (build_courses.py does this)
"""
import argparse, io, json, os, re, collections

import pymorphy3

M = pymorphy3.MorphAnalyzer()
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "public", "courses", "time")
DROPPED = os.path.join(HERE, "_dropped", "time-unexplained.json")

Y = lambda s: (s or "").lower().replace("ё", "е")
WORD = re.compile(r"[а-яёА-ЯЁ]+")

# ------------------------------------------------------------ time words
DAYS = set("понедельник вторник среда четверг пятница суббота воскресенье".split())
MONTHS = set("январь февраль март апрель май июнь июль август сентябрь октябрь ноябрь декабрь".split())
PARTS = set("утро день вечер ночь".split())
SEASONS = set("весна лето осень зима".split())
UNITS = set("секунда минута час сутки день неделя месяц год век столетие мгновение миг".split())
CLOCK = {"полдень", "полночь"}
BIG = {"год", "месяц", "век", "столетие"}
SMALL = {"день", "ночь", "час", "минута", "секунда", "момент", "миг", "мгновение", "раз"}
MEALS = set("обед ужин завтрак".split())
# Only war: «до войны», «за год до войны», «после конца войны» are DLI's own
# examples. A праздник, a урок, an экзамен is as often something prepared
# for or attended as a point in time.
EVENTS = {"война"}
# вечер is also a party («литературный вечер», «приятный вечер»), and обед,
# ужин, завтрак are meals before they are times. They count as time words
# only in DLI's own constructions and only with a modifier that is itself
# about time.
EVENTISH = {"вечер"} | MEALS
TIME_MODS = set("этот тот следующий прошлый будущий сегодняшний вчерашний завтрашний поздний ранний "
                "каждый весь целый один самый нынешний другой последний ближайший минувший предыдущий "
                "позапрошлый текущий".split())
PHASE = set("начало середина конец".split())
DURATION = (UNITS | SEASONS | {"ночь", "время"}) - {"век"}
TIME = DAYS | MONTHS | PARTS | SEASONS | UNITS | CLOCK | {"время"}
# The weekday that is also "environment": only the forms a weekday takes in
# the course's constructions count — в/каждую среду, по средам. «К среде»,
# «в среде», «по среде» are left out, because there the word is usually the
# milieu, and a sentence that might be either is not worth the risk.
AMBIGUOUS_DAY = {"среда"}

PREPS = {"в", "во", "на", "за", "до", "с", "со", "к", "ко", "по", "после", "перед",
         "передо", "через", "без", "около", "от", "в течение", "течение", "среди"}

# ------------------------------------------------------------------- rules
# (id, the line shown above the question, the full rule shown after, source)
R = {
 "v-acc": ("В + Accusative is used to indicate the time of the day, the day of the week, and how frequently something occurs.",
           "«В + Accusative is used: (a) to indicate the time of the day; (b) to indicate the day of the week; "
           "(c) to indicate how frequently something occurs.» «Note also the following expressions: В минуту "
           "опасности. В годы войны. Во время войны. В первый раз. В следующий раз. В последний раз.» «Units "
           "smaller than a week (day, hour etc.) take „В + Acc.“»",
           "DLI Grammar Reference Book, Lessons 19 and 73"),
 "v-prep": ("В + Prepositional indicates the year or the month in which an event takes place.",
            "«В + Prepositional is used: (a) to indicate the year or the month (but never the week) in which an "
            "event takes place; (b) to indicate the beginning, the middle, the end or any other phase of a period "
            "in which an event takes place.» «Units larger than a week (month, year) take „В + Loc.“»",
            "DLI Grammar Reference Book, Lessons 73 and 75"),
 "na-prep": ("НА + Prepositional indicates the week during which an event takes place.",
             "«The preposition НА + Prep. is used to indicate the week during which an event takes place.» «Note "
             "also the expression „на (этих) днях“. When referred to the past „на днях“ means „a few days ago“, „the "
             "other day“… When referred to the future, it means „within a few days“.»",
             "DLI Grammar Reference Book, Lesson 73"),
 "na-acc": ("НА + Accusative indicates how long something is expected to last.",
            "«The preposition НА + Acc. is used: (a) to indicate the length of time one expects to stay some place, "
            "or the time something is expected to last; (b) after the verb опаздывать / опоздать to indicate the "
            "amount of time by which someone is late.» «Note also such expressions as: на следующий день — (next "
            "day).»",
            "DLI Grammar Reference Book, Lesson 73"),
 "za-acc": ("ЗА + Accusative denotes the time that it takes to accomplish an action.",
            "«The preposition ЗА + Acc. denotes the time that it takes to accomplish an action.» «„ЗА + Acc.“ is "
            "also used in combination with „ДО + Gen.“ to denote the time of one event taking place before some "
            "other event: Он умер за год до войны.»",
            "DLI Grammar Reference Book, Lesson 77"),
 "cherez": ("ЧЕРЕЗ + Accusative: in time expressions it means “in”, “after”.",
            "«The preposition через means „across, over, through“. In time expressions it means „in“, „after“. This "
            "preposition is used with the accusative case: Я буду там через неделю.» And with после: «„через“ + Acc. "
            "in combination with „после“ + Gen. denotes the time of one event taking place after some other event.»",
            "DLI Grammar Reference Book, Lessons 47 (p. 137) and 77"),
 "nazad": ("“How long ago?” — the accusative, followed by (тому) назад.",
           "«In expressions answering the questions „How long?“ and „How long ago?“ the accusative case is used: "
           "Я был там год. — Я был там год тому назад.»",
           "DLI Grammar Reference Book, Lesson 41"),
 "how-long": ("“How long?” — the accusative, with no preposition.",
              "«In expressions answering the questions „How long?“ and „How long ago?“ the accusative case is used: "
              "Я был там год. Я был там месяц. Я был там неделю.»",
              "DLI Grammar Reference Book, Lesson 41"),
 "s-gen": ("С + Genitive means “from” or “since”.",
           "«С + Gen. meaning „from“ or „since“: Он живёт здесь с прошлого года. Сегодня с утра идёт дождь.» "
           "«„С + Gen. … до + Gen.“ — „from … to“: Я был занят с утра до вечера.»",
           "DLI Grammar Reference Book, Lesson 75"),
 "do-gen": ("ДО + Genitive means “till”, or “before”.",
            "«1. До + Gen. meaning „till“ or „to“ (indicating a time limit of an action): Дождь шёл до вечера. "
            "2. До + Gen. meaning „before“ (answering the question „when?“): Сегодня он пришёл домой до обеда. Они "
            "жили здесь до войны.» «The preposition „до“ + Gen. simply means „before“ without any emphasis on the "
            "closeness to the event.»",
            "DLI Grammar Reference Book, Lessons 75 and 77"),
 "posle": ("ПОСЛЕ + Genitive: after.",
           "«The preposition „после“ + Gen. is the opposite of both „перед“ and „до“: Я приду к вам после обеда. Я "
           "буду свободен после пяти.»",
           "DLI Grammar Reference Book, Lesson 77"),
 "pered": ("ПЕРЕД + Instrumental: immediately before.",
           "«The preposition „перед“ + Instr. denotes time prior to (immediately before) a certain event: Я позвоню "
           "вам перед обедом.» «„до обеда“ — anytime before dinner; „перед обедом“ — just before dinner.»",
           "DLI Grammar Reference Book, Lesson 77"),
 "k-dat": ("К + Dative denotes the time by which an event takes place.",
           "«The preposition К + Dat. denotes the time by which an event takes place. (It answers the question „By "
           "what time?“) Он вернётся к двум часам. Приготовьте доклад к понедельнику.»",
           "DLI Grammar Reference Book, Lesson 77"),
 "po-dat": ("ПО + Dative plural: something happens regularly — on Mondays, in the mornings.",
            "«The preposition по + Dat. Pl. is used to indicate that something occurs periodically, 1. on a certain "
            "day of the week: По понедельникам я работаю в штабе. 2. during a certain time of a day: По утрам я "
            "читаю газету.» «Note: Never „по дням“ except when modifier is used: „по целым дням“ — days on end; "
            "„по выходным дням“ — on off-days.»",
            "DLI Grammar Reference Book, Lesson 74"),
 "instr": ("Adverbs of time with the instrumental case endings: утром, днём, вечером, ночью, весной, летом, осенью, зимой.",
           "«Adverbs of time with the instrumental case endings»: вечер — вечером, день — днём, утро — утром, лето — "
           "летом, весна — весной, зима — зимой, осень — осенью, ночь — ночью.",
           "DLI Grammar Reference Book, Lesson 35"),
 "kazhdyy": ("“Every” in time expressions: каждый день, каждое утро, каждую среду — the accusative.",
             "«The word „every“ in time expressions answering the question „how often“ is rendered as follows: "
             "Каждый день (понедельник, вторник, четверг) — masc. (acc.); Каждое утро (воскресенье) — neut. (acc.); "
             "Каждую среду (пятницу, субботу) — fem. (acc.)»",
             "DLI Grammar Reference Book, Lesson 22"),
 "ves": ("“All” in time expressions: весь день, всё утро, всю неделю — the accusative.",
         "«The word „all“ in time expressions answering the question „how long“ is rendered as follows: весь день "
         "(год, месяц, вторник) — masc. (accus.); всё утро (воскресенье, лето) — neut. (accus.); все дни (годы) — "
         "plur. (accus.); всю неделю (зиму, осень, ночь) — fem. (accus.)»",
         "DLI Grammar Reference Book, Lesson 37"),
 "date": ("To state the date of an event, the day and the month are in the genitive.",
          "«In a date the day is rendered by an ordinal number.» «In a statement of a date the day is in the "
          "nominative and the month is in the genitive: Сегодня пятое февраля.» «To state the date of the event "
          "both the day and the month are in the genitive: Десятого августа.»",
          "DLI Grammar Reference Book, Lessons 50 and 75"),
 "god-let": ("For the genitive plural of год the word лет is used.",
             "«For the genitive plural of the noun год the word лет is used: один год, два года, пять лет.»",
             "DLI Grammar Reference Book, Lesson 41"),
 "age": ("The person whose age is in question is in the dative case.",
         "«Expressions referring to age are rendered in Russian as follows: Сколько вам лет? Мне двадцать лет. The "
         "person whose age is in question is in the dative case.»",
         "DLI Grammar Reference Book, Lesson 41"),
 "clock": ("Telling the time: в + Acc. on the hour, the ordinal of the next hour after it, без + Gen. before it.",
           "«Time on the hour: Я приехал туда в два часа. (в + Acc.)» «„five minutes past two“ is rendered in Russian "
           "by „пять минут третьего“… „the following hour“ is always denoted by an ORDINAL numeral in the Genitive "
           "case.» «Half past the hour: Я пришёл туда в половине третьего. (в + Prep.)» «Time before the hour: Я буду "
           "там без десяти три. (без + Gen.; the prep. „в“ is not used)»",
           "DLI Grammar Reference Book, Lessons 40 and 74"),
}
NUMERAL_RULE = ("«2, 3, 4 + Gen. sing.; 5 and up + Gen. plur.»: «After три and четыре… the noun is also in the genitive "
                "singular… After all other numerals (пять, шесть, семь, etc.)… the noun is in the genitive plural.» "
                "— DLI Grammar Reference Book, Lesson 39")
NUMWORD = re.compile(r"^(\d+|два|две|три|четыре|пять|шесть|семь|восемь|девять|десять|"
                     r"одиннадцать|двенадцать|\w+надцать|двадцать|тридцать|сорок|пятьдесят|шестьдесят|"
                     r"семьдесят|восемьдесят|девяносто|сто|двести|триста|четыреста|пятьсот|"
                     r"полтора|полторы|несколько|сколько|много|мало|оба|обе|пару|пара)$")


def lemmas(w):
    return {Y(p.normal_form) for p in M.parse(w)}


def analyse(word, hint_words):
    """[(lemma, case, number, tags)] for the parses of `word` that belong to
    the hint's word."""
    want = set()
    for h in hint_words:
        want |= lemmas(h)
    out = []
    for p in M.parse(word):
        lem = Y(p.normal_form)
        if want and lem not in want:
            continue
        # «в году», «с часу»: the second locative and genitive are the
        # prepositional and the genitive for every rule here
        case = {"loc2": "loct", "gen2": "gent", "acc2": "accs"}.get(p.tag.case, p.tag.case)
        out.append((lem, case, p.tag.number, str(p.tag)))
    return out


def head_of(ans, hint):
    """The answer's head noun and its readings; modifiers before it."""
    aw = WORD.findall(ans)
    hw = WORD.findall(hint)
    if not aw:
        return None, [], []
    # The head is the last word of the answer that is a noun of the hint.
    for i in range(len(aw) - 1, -1, -1):
        an = [a for a in analyse(aw[i], hw) if "NOUN" in a[3] or "ADJF" in a[3] and i == len(aw) - 1]
        if an:
            return aw[i], an, [Y(x) for x in aw[:i]]
    return aw[-1], analyse(aw[-1], hw), [Y(x) for x in aw[:-1]]


def context_words(q):
    i = q.find("___")
    before = WORD.findall(q[:i])
    after_txt = re.sub(r"^\s*\([^)]*\)", "", q[i + 3:])
    after = WORD.findall(after_txt)
    # a number written in digits right before the blank
    # a number written in digits right before the blank — but not a year
    # («с 1990 года»): a year is an ordinal, not a count of things
    m = re.search(r"(\d+)\s*$", q[:i])
    digits_before = bool(m) and int(m.group(1)) < 1000
    return [Y(x) for x in before], [Y(x) for x in after], digits_before


DATIVE_PERSON = set("мне тебе ему ей нам вам им ему".split())
EVERY = set("каждый каждая каждое каждые каждого каждую каждой каждых".split())
ALL = set("весь вся всё все всю всего всей всех целый целая целое целые целую".split())


def agrees(w):
    """A word that sits inside a noun phrase: an adjective, an ordinal, a
    pronoun like этот, a participle."""
    for p in M.parse(w):
        t = str(p.tag)
        if any(x in t for x in ("ADJF", "PRTF", "Anum", "Apro")):
            return True
    return False


def time_mod(w):
    """A modifier that is itself about time: этот, прошлый, следующий,
    каждый, весь, an ordinal, a number."""
    if NUMWORD.match(w):
        return True
    for p in M.parse(w):
        if Y(p.normal_form) in TIME_MODS or "Anum" in str(p.tag):
            return True
    return False


def classify(e):
    """(rule id, numeral-governed?) or (None, reason)."""
    q = e.get("q") or ""
    if q.count("___") != 1:
        return None, "two blanks"
    hint = (re.findall(r"___ \(([^)]*)\)", q) or [""])[0]
    ans = (e.get("answers") or [""])[0]
    if "..." in ans or "\u2026" in ans:
        return None, "answer split around other words"
    before, after, digit = context_words(q)

    # The blank may hold only the modifier: «___ (каждый) утро».
    aw = [Y(x) for x in WORD.findall(ans)]
    if len(aw) == 1 and aw[0] in EVERY | ALL and after and lemmas(after[0]) & TIME:
        gov_free = not (before and before[-1] in PREPS)
        if gov_free:
            return ("kazhdyy" if aw[0] in EVERY else "ves"), False
        return None, "a preposition before «%s» makes it something else" % aw[0]

    head, an, inner = head_of(ans, hint)
    if not an:
        return None, "answer not the hint's word"
    lem = an[0][0]
    if lem == "воскресение" and Y(head).startswith("воскресень"):
        lem = "воскресенье"             # the day, not the resurrection
    cases = {a[1] for a in an if a[1]}
    nums = {a[2] for a in an if a[2]}

    # Walk back over the words of the same phrase standing before the blank
    # («в пятнадцатом ___ (век)», «каждое ___ (лето)», «три ___ (неделя)»)
    # to the preposition, if there is one.
    outer, k = [], len(before)
    while k > 0 and (agrees(before[k - 1]) or NUMWORD.match(before[k - 1])) and before[k - 1] not in PREPS:
        outer.insert(0, before[k - 1])
        k -= 1
    gov = before[k - 1] if k > 0 and before[k - 1] in PREPS else ""
    if k >= 2 and " ".join(before[k - 2:k]) in ("в течение", "в продолжение"):
        gov = "в течение"
    mods = outer + inner
    numeral = digit or any(NUMWORD.match(m) for m in mods)
    if gov in ("в течение", "течение"):
        return None, "в течение / в продолжение + gen. is not taught in the course"
    # «в таких летах», «не по летам»: лета is age here, not years
    if "год" in Y(hint) and Y(ans).split()[-1].startswith("лет") and Y(ans).split()[-1] != "лет":
        return None, "лета here is age, not years"

    # the weekday that is also "environment"
    if lem in AMBIGUOUS_DAY and not ((gov in ("в", "во") and "accs" in cases) or
                                      (gov == "по" and "datv" in cases and "plur" in nums) or
                                      (any(m in EVERY | ALL for m in mods) and "accs" in cases)):
        return None, "среда here may be the environment, not Wednesday"
    # часы: «подходит к часам» is the clock on the wall
    if lem in ("час", "часы") and "plur" in nums and not numeral:
        return None, "часы here is a clock"

    has = lambda c: c in cases
    timeish = lem in TIME
    if lem in EVENTISH:
        if mods and not all(time_mod(m) or m == "же" for m in mods):
            return None, "%s here is an event or a meal, not a time" % lem
        if lem in MEALS and gov not in ("до", "после", "перед", "передо"):
            return None, "%s here is a meal, not a time" % lem
        if lem == "вечер" and gov in ("в", "во") and mods and all(time_mod(m) or m == "же" for m in mods):
            pass                                  # «в тот вечер», «в этот же вечер»: that evening
        elif lem == "вечер" and gov in ("в", "во", "за", "после", "через"):
            return None, "вечер here is a party, not a time"
        if lem == "вечер" and gov == "на" and not mods:
            return None, "вечер here is a party, not a time"
    only_time_mods = all(time_mod(m) or m == "же" for m in mods)

    if Y(ans) == "лет":
        return "god-let", numeral
    if lem == "год" and any(b in DATIVE_PERSON for b in before[-4:]):
        return "age", numeral
    if after and after[0] in ("назад", "тому") and lem in DURATION | {"век", "столетие", "время"}:
        return "nazad", numeral
    if any(m in EVERY for m in mods) and has("accs") and timeish and not gov:
        return "kazhdyy", False
    if any(m in ALL for m in mods) and has("accs") and timeish and not gov:
        return "ves", False
    phase_ok = lem in PHASE and after and any(lemmas(w) & (TIME | MONTHS) for w in after[:2])
    if gov in ("в", "во"):
        if has("accs") and (lem in {"неделя", "месяц", "год", "сутки"} or lem in SMALL) and \
                any(b in ("раз", "раза") for b in before[-3:]):
            return "v-acc", False
        if has("accs") and (lem in DAYS or lem in SMALL or lem == "время" or (lem == "год" and "plur" in nums)):
            return "v-acc", numeral
        if has("loct") and (lem in MONTHS or lem in BIG or phase_ok):
            return "v-prep", numeral
        if has("loct") and lem == "половина":
            return "clock", False
        return None, "в + %s %s is not one of the course's time constructions" % ("/".join(sorted(cases)), lem)
    if gov == "на":
        if has("loct") and (lem == "неделя" or (lem == "день" and "plur" in nums)):
            return "na-prep", False
        if has("accs") and lem in DURATION and only_time_mods:
            return "na-acc", numeral
        # «на следующий день / на другое утро / на следующий вечер»
        if has("accs") and lem in PARTS and mods and only_time_mods:
            return "na-acc", numeral
        return None, "на + %s %s is not one of the course's time constructions" % ("/".join(sorted(cases)), lem)
    if gov == "за":
        if has("accs") and lem in DURATION and only_time_mods:
            return "za-acc", numeral
        return None, "за + %s %s is not a time construction the course teaches" % ("/".join(sorted(cases)), lem)
    if gov == "через":
        if has("accs") and lem in DURATION | {"век", "столетие"} and only_time_mods:
            return "cherez", numeral
        return None, "через + %s %s" % ("/".join(sorted(cases)), lem)
    if gov in ("с", "со"):
        if has("gent") and (timeish or phase_ok):
            return "s-gen", numeral
        return None, "с + %s %s is not «since»" % ("/".join(sorted(cases)), lem)
    if gov == "до":
        if has("gent") and (timeish or phase_ok or lem in MEALS or lem in EVENTS):
            return "do-gen", numeral
        return None, "до + %s %s" % ("/".join(sorted(cases)), lem)
    if gov == "после":
        if has("gent") and (timeish or lem in MEALS or lem in EVENTS or phase_ok):
            return "posle", numeral
        return None, "после + %s %s" % ("/".join(sorted(cases)), lem)
    if gov in ("перед", "передо"):
        if has("ablt") and (timeish or lem in MEALS or lem in EVENTS):
            return "pered", False
        return None, "перед + %s %s" % ("/".join(sorted(cases)), lem)
    if gov in ("к", "ко"):
        if has("datv") and (timeish or phase_ok) and only_time_mods:
            return "k-dat", numeral
        return None, "к + %s %s is not «by (a time)»" % ("/".join(sorted(cases)), lem)
    if gov == "по":
        if has("datv") and "plur" in nums and (lem in DAYS or lem in {"утро", "вечер", "ночь", "будни", "выходной", "выходные"} or
                                                 (lem == "день" and mods)):
            return "po-dat", False
        return None, "по + %s %s is not «on Mondays / in the mornings»" % ("/".join(sorted(cases)), lem)
    if gov == "без":
        if lem in ("минута", "четверть") or numeral:
            return "clock", False
        return None, "без + %s" % lem
    if gov in PREPS:
        return None, "%s + %s is not taught in the course" % (gov, lem)

    # no preposition
    if has("ablt") and (lem in PARTS or lem in SEASONS) and only_time_mods and "plur" not in nums:
        return "instr", False
    if lem in MONTHS and has("gent") and (outer or before) and (
            any("Anum" in str(p.tag) for w in before[-2:] for p in M.parse(w)) or digit):
        return "date", False
    if lem in MONTHS and has("gent"):
        return "date", False
    if re.search(r"(ого|ое|ье|ьего)$", Y(ans)) and lem.endswith(("ый", "ой", "ий")) and \
            any(w in MONTHS or lemmas(w) & MONTHS for w in after[:1]):
        return "date", False
    if lem in DURATION and numeral and (has("gent") or has("accs")):
        return "how-long", True
    if has("accs") and lem in DURATION and only_time_mods:
        return "how-long", False
    return None, "no time construction found"


def apply(apply_changes=True, verbose=False):
    kept = collections.Counter()
    dropped, reasons = {}, collections.Counter()
    total = 0
    for fn in sorted(os.listdir(ROOT)):
        if not fn.endswith(".json"):
            continue
        p = os.path.join(ROOT, fn)
        sec = json.load(io.open(p, encoding="utf-8"))
        out = []
        for e in sec.get("exercises") or []:
            total += 1
            rid, num = classify(e)
            if rid is None:
                reasons[re.sub(r" \S+$", "", num) if num.startswith(("в +", "на +", "за +", "с +", "до +", "после +", "к +", "по +", "через +", "перед +")) else num] += 1
                dropped.setdefault(sec["id"], []).append(dict(e, _why_dropped=num))
                continue
            short, full, src = R[rid]
            cite = (e.get("_src") or e.get("why") or "").strip()
            # keep only the sentence's own source line, not an earlier explanation
            m = re.search(r"(Sentence and translation from Tatoeba[^·]*|From [^·]*«[^»]+»[^·]*|\*[^*]+\*)\s*$", cite)
            cite = m.group(1).strip() if m else ""
            why = full + " — " + src + "."
            if num:
                why += " " + NUMERAL_RULE + "."
            if cite:
                why += "  ·  " + cite
            out.append(dict(e, context=short + " (" + src.replace("DLI Grammar Reference Book", "DLI") + ")",
                            why=why, _rule=rid))
            kept[rid] += 1
        out = [dict(x, id="q%d" % (i + 1)) for i, x in enumerate(out)]
        if apply_changes:
            sec["exercises"] = [{k: v for k, v in x.items() if not k.startswith("_")} for x in out]
            io.open(p, "w", encoding="utf-8").write(json.dumps(sec, ensure_ascii=False, separators=(",", ":")))
    n_drop = sum(len(v) for v in dropped.values())
    print("time course: %d exercises, %d explained by their own construction, %d removed" % (total, total - n_drop, n_drop))
    for k, v in kept.most_common():
        print("   kept  %-9s %4d" % (k, v))
    for k, v in reasons.most_common(25):
        print("   drop  %4d  %s" % (v, k))
    if apply_changes:
        os.makedirs(os.path.dirname(DROPPED), exist_ok=True)
        io.open(DROPPED, "w", encoding="utf-8").write(json.dumps(dropped, ensure_ascii=False, indent=1))
    return dropped


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    apply(a.apply)


if __name__ == "__main__":
    main()
