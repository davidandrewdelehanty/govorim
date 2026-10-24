#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every pattern a lesson teaches, practised in its exercises.

A lesson's prose and tables show several patterns at once — the past tense
in -л, -ла, -ло and -ли; the genitive after из, с and от; the Е and И
conjugations; masculine, feminine and plural endings — and its exercises,
mined by construction, may show only some of them. This pass lists the
patterns of each lesson (FACETS, by section id, in the terms of
pertinence.py) and counts the exercises of the lesson and its practice sets
that show each one.

    python3 tools/courses/coverage.py              # the report: what is missing
    python3 tools/courses/coverage.py --mine       # find sentences for what is missing
                                                   #   → tools/courses/coverage_fill.json
    python3 tools/courses/coverage.py --apply      # add them to the lessons (build_courses does this)

Mining reads the library's public-domain sentences
(tools/courses/library_sentences.tsv, from library_sentences.py): a sentence
is kept when, with the right word blanked and its dictionary form as the
hint, it shows the missing pattern and fits what the section teaches; the
exercise cites the book. Nothing is written by us."""
import argparse, io, json, os, random, re, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pertinence as P

COURSES = P.COURSES


class _Cached(object):
    """pymorphy3 with its parses remembered: the same words come round again."""
    def __init__(self, m):
        import functools
        self._m = m
        self.parse = functools.lru_cache(maxsize=400000)(m.parse)


if P.M is not None:
    P.M = _Cached(P.M)
FILL = os.path.join(HERE, "coverage_fill.json")
LIB = os.path.join(HERE, "library_sentences.tsv")
MIN = 3            # exercises a pattern needs, lesson and practice sets together
ADD = 3            # how many to add for a pattern that has fewer

G = "masc|femn|neut"


def gender_facets(case, pos="NOUN"):
    return [("masculine", "%s %s masc sing" % (pos, case)), ("feminine", "%s %s femn sing" % (pos, case)),
            ("neuter", "%s %s neut sing" % (pos, case)), ("plural", "%s %s plur" % (pos, case))]


def adj_facets(case):
    return [("adjective, masculine", "ADJF %s masc sing" % case), ("adjective, feminine", "ADJF %s femn sing" % case),
            ("adjective, plural", "ADJF %s plur" % case)]


def preps(case, *ps):
    return [("%s + %s" % (p, case), "%s prep:%s" % (case, p)) for p in ps]


# The patterns each lesson teaches. Terms as in pertinence.ok, plus
# sent:regex (the whole sentence), end:regex (the answer's ending),
# prevlem:regex (dictionary form of a word before the blank), per:1|2|3.
FACETS = {
    "case-nom": {
        "n1-subject": gender_facets("nomn"), "n2-eto": gender_facets("nomn"),
        "n3-adjectives": adj_facets("nomn") + [("adjective, neuter", "ADJF nomn neut sing")],
    },
    "case-gen": {
        "g1-possession": gender_facets("gent"),
        "g2-no": [("нет + genitive", "gent sent:\\bнет\\b"), ("не + verb + genitive", "gent neg sent:\\bне\\b"), ("не было / не будет", "gent sent:не_(было/будет)")],
        "g3-counting": [("after два, три, четыре", "gent sing afternum"), ("after пять and up", "gent plur afternum"), ("after много, мало, несколько, сколько", "gent sent:(много/мало/несколько/сколько/немного/столько)\\s")],
        "g4-from": preps("gent", "из", "с", "от"),
        "g5-u-dlya-bez": preps("gent", "у", "для", "без"),
        "g6-more-prepositions": preps("gent", "до", "после", "около", "мимо", "кроме", "вместо", "против", "вокруг", "возле", "среди", "вдоль", "из-за", "из-под", "напротив"),
        "g7-verbs": [("бояться", "gent prevlem:^боя"), ("ждать", "gent prevlem:^(ждать/ожидать/дождаться)"), ("желать, требовать, достигать…", "gent prevlem:^(желать/пожелать/требовать/потребовать/достигать/достичь/достигнуть/избегать/избежать/касаться/коснуться/лишить/лишать/добиться/добиваться/заслуживать/искать/просить/хотеть)")],
        "g8-endings": adj_facets("gent") + [("adjective, neuter", "ADJF gent neut sing"), ("pronoun:_этого,_моего,_его", "NPRO|lemma:^(этот/мой/твой/наш/ваш/свой/тот/весь/такой/который) gent")],
    },
    "case-dat": {
        "d1-to-whom": gender_facets("datv") + [("pronoun", "NPRO datv")],
        "d2-mne-nravitsya": [("нужно, надо", "datv sent:(нужн/надо/необходим)"), ("можно, нельзя", "datv sent:(можно/нельзя)"), ("нравится", "datv sent:нрав"), ("age:_мне 20_лет", "datv sent:(лет/год)\\b")],
        "d3-verbs": [("помогать", "datv prevlem:^помо"), ("обещать", "datv prevlem:^(обещать/пообещать)"), ("говорить, сказать, рассказывать", "datv prevlem:^(говорить/сказать/рассказ)"), ("звонить, отвечать", "datv prevlem:^(звонить/позвонить/отвечать/ответить)"), ("показывать, давать", "datv prevlem:^(показ/давать/дать/отдать/передать)"), ("верить, мешать, советовать…", "datv prevlem:^(верить/поверить/мешать/помешать/советовать/посоветовать/завидовать/служить/принадлежать/радоваться/удивляться/улыбаться/учить/научить/учиться/надоесть)")],
        "d4-k": gender_facets("datv") + [("к + pronoun", "NPRO datv prep:к")],
        "d5-po": preps("datv", "по", "благодаря", "вопреки", "согласно", "навстречу"),
        "d6-endings": adj_facets("datv") + [("adjective, neuter", "ADJF datv neut sing"), ("pronoun:_этому,_моему", "NPRO|lemma:^(этот/мой/твой/наш/ваш/свой/тот/весь/такой/который) datv")],
    },
    "case-acc": {
        "a1-object": [("masculine animate", "accs masc sing anim"), ("masculine inanimate", "accs masc sing inan"), ("feminine", "accs femn sing"), ("neuter", "accs neut sing"), ("plural animate", "accs plur anim"), ("plural inanimate", "accs plur inan")],
        "a2-v-na": preps("accs", "в", "на"),
        "a3-za-pod": preps("accs", "за", "под"),
        "a4-cherez-pro": preps("accs", "через", "про", "сквозь"),
        "a5-time": [("каждый день", "accs sent:\\bкажд"), ("весь день, всю неделю", "accs sent:\\b(весь/всю/всё/все)\\b"), ("в + time", "accs prep:в"), ("на + length of time", "accs prep:на"), ("за + time taken", "accs prep:за"), ("через", "accs prep:через")],
        "a6-endings": [("adjective, masculine inanimate", "ADJF accs masc inan"), ("adjective, masculine animate", "ADJF accs masc anim"), ("adjective, feminine", "ADJF accs femn"), ("adjective, plural", "ADJF accs plur"), ("pronoun:_этот,_эту,_мою", "NPRO|lemma:^(этот/мой/твой/наш/ваш/свой/тот/весь/такой/который) accs")],
    },
    "case-ins": {
        "i1-with": gender_facets("ablt") + [("с + pronoun", "NPRO ablt")],
        "i2-means": gender_facets("ablt"),
        "i3-being": [("быть + instrumental", "ablt sent:\\b(был/была/были/будет/будут/быть/было)\\b"), ("стать, становиться", "ablt sent:\\bста(л/ла/ли/нет/нут/новит/новят/ть)\\b"), ("работать + instrumental", "ablt sent:работа"), ("казаться, считаться, называться", "ablt sent:(каза/счита/называ/являе/оказа)")],
        "i4-where": preps("ablt", "над", "под", "за", "перед", "между"),
        "i5-verbs": [("заниматься", "ablt prevlem:^занима|prevlem:^занять"), ("пользоваться", "ablt prevlem:^пользова|prevlem:^воспользова"), ("интересоваться, увлекаться", "ablt prevlem:^(интересова/увлек/увлечь/заинтересова)"), ("гордиться, восхищаться, любоваться", "ablt prevlem:^(гордиться/восхищаться/любоваться/наслаждаться)"), ("владеть, управлять, руководить, командовать", "ablt prevlem:^(владеть/овладеть/обладать/управлять/руководить/командовать/заведовать)"), ("смеяться над", "ablt prep:над prevlem:^(смеяться/посмеяться/насмехаться/издеваться)")],
        "i6-time": [("утром, вечером, днём, ночью", "ablt ans:^(утром/вечером/днем/ночью)$"), ("зимой, летом, весной, осенью", "ablt ans:^(зимой/зимою/летом/весной/весною/осенью)$"), ("этим летом, прошлой зимой", "ablt adj+")],
        "i7-endings": adj_facets("ablt") + [("adjective, neuter", "ADJF ablt neut sing"), ("pronoun:_этим,_моим", "NPRO|lemma:^(этот/мой/твой/наш/ваш/свой/тот/весь/такой/который) ablt")],
    },
    "case-prp": {
        "p1-where": preps("loct|loc2", "в", "на") + gender_facets("loct"),
        "p2-about": [("о + masculine", "loct masc prep:о"), ("о + feminine", "loct femn prep:о"), ("о + plural", "loct plur prep:о"), ("об before a vowel", "loct sent:\\bоб\\b"), ("о +_pronoun:_обо_мне,_о_нём", "NPRO loct prep:о")],
        "p3-v-lesu": [("в + -у", "loc2 prep:в"), ("на + -у", "loc2 prep:на")],
        "p4-pri-transport": [("при", "loct prep:при"), ("на + transport", "loct prep:на lemma:^(поезд/автобус/машина/метро/самолет/трамвай/велосипед/такси/корабль/лошадь/пароход/извозчик/телега/сани)"), ("в + year, month", "loct sent:(году/месяце/январе/феврале/марте/апреле/мае/июне/июле/августе/сентябре/октябре/ноябре/декабре)")],
        "p5-endings": adj_facets("loct") + [("adjective, neuter", "ADJF loct neut sing"), ("pronoun:_этом,_моём", "NPRO|lemma:^(этот/мой/твой/наш/ваш/свой/тот/весь/такой/который) loct")],
    },
    "cases": {
        "k2-accusative": [("animate", "accs anim"), ("inanimate", "accs inan"), ("feminine", "accs femn")],
        "k3-genitive": [("possession", "gent !prep"), ("after a preposition", "gent prep"), ("after negation", "gent neg")],
        "k4-dative": [("indirect object", "datv !prep"), ("к, по", "datv prep")],
        "k5-instrumental": [("with с", "ablt prep:с"), ("without a preposition", "ablt !prep"), ("над, под, за, перед, между", "ablt prep:над|prep:под|prep:за|prep:перед|prep:между")],
        "k7-genitive-plural": [("masculine -ов, -ев", "gent plur masc"), ("feminine, zero ending", "gent plur femn"), ("neuter", "gent plur neut")],
        "k8-plural-cases": [("nominative", "nomn plur"), ("genitive", "gent plur"), ("dative", "datv plur"), ("accusative", "accs plur"), ("instrumental", "ablt plur"), ("prepositional", "loct plur")],
        "k9-adjectives-singular": [("masculine", "masc sing"), ("feminine", "femn sing"), ("neuter", "neut sing")],
    },
    # "count": lessons there carry no extra book sentences: their practice sets are Tatoeba (with English)
    "aspect": {
        "a1-process-result": [("imperfective past", "past impf"), ("perfective past", "past perf"), ("imperfective future", "futr impf"), ("perfective future", "futr perf")],
        "a2-context": [("duration:_долго,_весь_день", "impf sent:(долго/недолго/весь/всю/всё/целый/целую)"), ("habit:_обычно,_всегда,_часто", "impf sent:(обычно/всегда/иногда/часто/редко/кажд/по_утрам/по_вечерам)")],
        "a3-commands": [("imperfective imperative", "impr impf"), ("perfective imperative", "impr perf"), ("negative imperative", "impr neg")],
        "a4-future": [("я", "futr perf 1per sing"), ("ты", "futr perf 2per sing"), ("он, она", "futr perf 3per sing"), ("мы", "futr perf 1per plur"), ("вы", "futr perf 2per plur"), ("они", "futr perf 3per plur")],
        "a5-po-s": [("по-", "ans:^по"), ("с-", "ans:^с")],
    },
    "verbs": {
        "v1-present": [("Е type: -ешь, -ет, -ют", "pres end:(ешь/ёшь/ет/ёт/ем/ём/ете/ёте/ют/ут)$"), ("И type: -ишь, -ит, -ят", "pres end:(ишь/ит/им/ите/ат/ят)$"), ("я", "pres 1per sing"), ("ты", "pres 2per sing"), ("он, она", "pres 3per sing"), ("мы", "pres 1per plur"), ("вы", "pres 2per plur"), ("они", "pres 3per plur"), ("consonant_change:_пишу,_сижу,_вижу", "pres 1per sing end:(шу/жу/чу/щу/блю/плю/влю/млю)$")],
        "v2-past": [("-л", "past masc"), ("-ла", "past femn"), ("-ло", "past neut"), ("-ли", "past plur"), ("-ся", "past sya")],
        "v3-position": [("ставить, поставить", "lemma:^(ставить/поставить)"), ("класть, положить", "lemma:^(класть/положить)"), ("садиться, сесть", "lemma:^(садиться/сесть/сажать/посадить)"), ("ложиться, лечь", "lemma:^(ложиться/лечь)"), ("стоять, лежать, сидеть", "lemma:^(стоять/лежать/сидеть/постоять/полежать/посидеть)")],
        "v4-sya": [("present", "sya pres"), ("past", "sya past"), ("infinitive", "sya INFN")],
    },
    "compare": {
        "c1-comparative": [("-ее", "COMP end:(ее/ей)$"), ("-е:_дороже,_легче", "COMP end:[^е]е$"), ("adverb:_быстрее,_лучше", "COMP prevlem:^(идти/говорить/работать/бежать/ехать/жить/писать/читать/петь/бегать/ходить/делать/стать/становиться/учиться)")],
        "c2-irregular": [("лучше, хуже", "ans:^(лучше/хуже)$"), ("больше, меньше", "ans:^(больше/меньше)$"), ("старше, моложе", "ans:^(старше/моложе/младше)$"), ("выше, ниже, шире, уже", "ans:^(выше/ниже/шире/уже/короче/глубже/мельче)$"), ("дальше, ближе, раньше, позже", "ans:^(дальше/ближе/раньше/позже/реже/чаще)$"), ("дороже, дешевле, легче, тяжелее", "ans:^(дороже/дешевле/легче/тяжелее/проще/тише/громче)$")],
        "c3-than": [("чем", "blank:чем sent:(ее/ей/ше/же/че)_"), ("the genitive", "gent !prep prevpos:COMP")],
        "c4-bolee": [("более", "blank:более"), ("менее", "blank:менее")],
        "c5-samyi": [("самый, masculine", "samyi masc"), ("самая, feminine", "samyi femn"), ("самые, plural", "samyi plur"), ("самый in another case", "samyi !nomn")],
        "c6-eishiy": [("-ейший", "ans:ейш"), ("-айший", "ans:айш"), ("лучше всех, больше всего", "ans:(всех/всего)")],
        "c7-short": [("masculine", "ADJS masc"), ("feminine", "ADJS femn"), ("neuter", "ADJS neut"), ("plural", "ADJS plur")],
    },
    "complex": {
        "x1-chtoby": [("чтобы", "blank:чтобы"), ("что", "blank:что sent:,_что")],
        "x2-do-togo-kak": [("до того как, прежде чем", "blank:до_того_как/прежде_чем"), ("после того как", "blank:после_того_как"), ("о том, что", "blank:о_том,_что")],
        "x3-poka": [("пока", "blank:пока sent:^(?!.*пока_не)"), ("пока не", "blank:пока_не")],
        "x4-li": [("ли after a verb", "+ли VERB"), ("ли after another word", "+ли !VERB")],
    },
    "inter2": {
        "i01-acc-or-gen": [("accusative", "accs"), ("genitive after negation", "gent neg"), ("genitive:_some, of", "gent !neg")],
        "i08-aspect-past": [("imperfective", "past impf"), ("perfective", "past perf")],
        "i09-aspect-infinitive": [("imperfective", "INFN impf"), ("perfective", "INFN perf")],
        "i10-aspect-imperative": [("imperfective", "impr impf"), ("perfective", "impr perf"), ("negative", "impr neg")],
        "i11-prefixed-motion": [(p + "-", "ans:^" + p) for p in ("при", "у", "вы", "под", "от", "пере", "про", "за", "до", "об", "в", "с", "по")],
        "i12-participles-active": [("present:_-ущий,_-ющий,_-ащий,_-ящий", "PRTF pres actv"), ("past:_-вший,_-ший", "PRTF past actv")],
        "i13-participles-passive": [("present:_-емый,_-имый", "PRTF pres pssv"), ("past, long: -нный, -тый", "PRTF past pssv"), ("past, short: сделан, открыт", "PRTS pssv")],
        "i14-gerunds": [("imperfective:_-я,_-а", "GRND impf"), ("perfective:_-в,_-вши", "GRND perf")],
        "i15-passive": [("short_participle:_построен", "PRTS"), ("long participle", "PRTF pssv"), ("-ся passive: строится", "sya impf pres !PRTF !PRTS")],
        "i20-comparison": [("comparative", "COMP"), ("более, менее", "blank:более/менее"), ("самый", "samyi")],
        "i22-negation": [("нет + genitive", "gent sent:\\bнет\\b"), ("не + verb + genitive", "gent sent:\\bне\\b")],
        "i26-imperative-types": [("давай, давайте", "blank:давай/давайте"), ("пусть", "blank:пусть"), ("the plain imperative", "impr")],
    },
    "adv3": {
        "v01-time-clauses": [("когда", "blank:когда"), ("пока", "blank:пока"), ("как только", "blank:как_только"), ("после того как, до того как, прежде чем", "blank:после_того_как/до_того_как/прежде_чем")],
        "v02-condition": [("если", "blank:если sent:^(?!.*если_бы)"), ("если бы", "blank:если_бы")],
        "v03-cause": [("потому что", "blank:потому_что"), ("так как", "blank:так_как"), ("из-за, благодаря", "gent|datv prep:из-за|prep:благодаря")],
        "v04-concession": [("хотя", "blank:хотя"), ("несмотря на", "blank:несмотря_на")],
        "v05-nechego-delat": [("нечего, некого", "blank:нечего/некого"), ("некуда, негде, некогда", "blank:некуда/негде/некогда")],
        "v06-no-subject": [("надо, нужно, можно + dative", "datv sent:(надо/нужно/можно/нельзя)"), ("impersonal_verb:_хочется,_кажется", "datv sent:(хочется/кажется/казалось/хотелось/приходится/пришлось/удалось)"), ("state:_холодно,_скучно", "datv sent:(холодно/тепло/скучно/весело/грустно/трудно/легко/жаль/жарко/больно/страшно/стыдно)")],
        "v07-coord": [("зато", "blank:зато"), ("а то", "blank:а_то")],
        "v08-disj": [("либо", "blank:либо"), ("или", "blank:или")],
        "v09-object-clauses": [("что", "blank:что sent:,_что"), ("чтобы", "blank:чтобы"), ("ли", "+ли")],
        "v10-attributive": [("который, которая, которые", "blank:который/которая/которые"), ("которого, которую", "blank:которого/которую"), ("которой, которым, которых", "blank:которой/которым/которых"), ("о котором, которому", "blank:котором/которому")],
        "v12-particles": [("же", "blank:же"), ("ведь", "blank:ведь"), ("разве", "blank:разве"), ("неужели", "blank:неужели"), ("даже", "blank:даже")],
        "v11-correlatives": [("там … где", "blank:где sent:\\bтам\\b"), ("такой … какой", "blank:какой/какая/какое/какие sent:\\b(такой/такая/такое/такие)\\b")],
        "v13-prefixes": [(p + "-", "ans:^" + p) for p in ("при", "у", "вы", "под", "от", "пере", "про", "за", "до", "об", "в", "с", "по", "на", "раз", "из")],
    },
    "forms": {
        "f1-imperative": [("-й, -йте", "impr end:(й/йте/йся/йтесь)$"), ("-и, -ите", "impr end:(и/ите/ись/итесь)$"), ("-ь, -ьте", "impr end:(ь/ьте/ься/ьтесь)$"), ("imperfective", "impr impf"), ("perfective", "impr perf"), ("-ся", "impr sya"), ("пусть", "blank:пусть"), ("давайте", "blank:давайте/давай")],
        "f2-conditional": [("бы with the past", "past"), ("если бы", "past sent:если_бы")],
        "f3-short-passive": [("masculine", "PRTS masc"), ("feminine", "PRTS femn"), ("neuter", "PRTS neut"), ("plural", "PRTS plur"), ("-т:_открыт,_закрыт", "PRTS end:(т/та/то/ты)$")],
        "f4-long-passive": [("-нный", "PRTF end:нн(ый/ая/ое/ые/ого/ой/ую/ым/ых/ыми/ому)$"), ("-тый", "PRTF end:т(ый/ая/ое/ые/ого/ой/ую/ым/ых/ыми/ому)$"), ("-ённый", "PRTF ans:(ённ/енн)")],
        "f5-present-active": [("-ущий, -ющий", "PRTF ans:(ущ/ющ)"), ("-ащий, -ящий", "PRTF ans:(ащ/ящ)"), ("-ся", "PRTF sya")],
        "f6-past-active": [("-вший", "PRTF ans:вш"), ("-ший:_принёсший,_шедший", "PRTF ans:[^в]ш(ий/ая/ее/ие/его/ей/ую/им/их/ими/ему)$"), ("-ся", "PRTF sya")],
        "f7-passive-present": [("-ся passive: строится", "sya impf pres !PRTF"), ("-емый", "PRTF pssv pres end:ем(ый/ая/ое/ые/ого/ой/ую/ым/ых/ыми/ому/ом/ем)$"), ("-имый", "PRTF pssv pres end:им(ый/ая/ое/ые/ого/ой/ую/ым/ых/ыми/ому/ом)$")],
        "f8-gerund-imperfective": [("-я", "GRND end:я$"), ("-а", "GRND end:а$"), ("-ясь, -ась", "GRND sya")],
        "f9-gerund-perfective": [("-в", "GRND end:в$"), ("-вшись", "GRND sya"), ("-я:_придя", "GRND end:я$")],
    },
    "tenses": {
        "x02-present": [("affirmative", "pres !neg"), ("negative", "pres neg")],
        "x06-past": [("imperfective", "past impf"), ("perfective", "past perf")],
        "x10-future": [("perfective future", "futr perf"), ("буду + infinitive", "ans:^буд")],
    },
}


# Conjunctions and particles a lesson teaches: blanked themselves, with the
# lesson's own English for them as the hint.
GLOSS = {"когда": "when", "пока": "while", "пока не": "until", "как только": "as soon as", "после того как": "after",
         "до того как": "before", "прежде чем": "before", "если": "if", "если бы": "if (unreal)", "потому что": "because",
         "так как": "since, as", "хотя": "although", "несмотря на": "in spite of", "зато": "but then", "а то": "or else",
         "либо": "or", "или": "or", "чтобы": "so that, in order to", "что": "that", "пусть": "let him, her, them",
         "давай": "let’s", "давайте": "let’s", "нечего": "nothing to", "некуда": "nowhere to", "негде": "nowhere to",
         "некогда": "no time to", "некого": "no one to", "чем": "than", "более": "more", "менее": "less",
         "который": "which, who", "которая": "which, who", "которые": "which, who", "которого": "which, whom",
         "которую": "which, whom", "которой": "which, whom", "которым": "which, whom", "которых": "which, whom",
         "котором": "which, whom", "которому": "which, whom", "же": "(emphasis)", "ведь": "after all, you know",
         "разве": "really?", "неужели": "can it be?", "даже": "even", "о том, что": "about the fact that", "где": "where",
         "какой": "what, which", "какая": "what, which", "какое": "what, which", "какие": "what, which"}


for _c in FACETS.values():                 # labels were written with _ for spaces where they hold a colon
    for _k, _fs in _c.items():
        _c[_k] = [(l.replace("_", " "), w) for l, w in _fs]


def feats_full(e, prefer=()):
    f = P.feats(e, prefer)
    q = e.get("q") or ""
    ans = (e.get("answers") or [""])[0]
    hint = P.hint_of(q)
    # the sentence whole, with its answer in place
    f["sent"] = re.sub(r"\([^)]*\)", "", re.sub(r"___\s*\([^)]*\)", ans, q, count=1)).lower().replace("ё", "е")
    # a blank whose hint is English is a conjunction or particle blanked itself
    f["blank"] = ans.lower().replace("ё", "е") if hint and not re.search(r"[А-Яа-яЁё]", hint) else None
    # the dictionary forms of the words before the blank
    pre = re.sub(r"\([^)]*\)", " ", q.split("___")[0])
    ws = P.WORD.findall(pre.lower())[-4:]
    f["prevlem"] = " ".join(p.normal_form.replace("ё", "е") for w in ws for p in P.M.parse(w)[:2]) if P.M else ""
    return f


def ok(want, f):
    """pertinence.ok with the extra terms."""
    rest = []
    for term in want.split():
        neg = term.startswith("!")
        t = term[1:] if neg else term
        if t.startswith("blank:"):
            # for an existing exercise: the word is in the sentence (its blank
            # may be elsewhere); for a mined one: it is the blank itself
            alts = t[6:].replace("/", "|").replace("_", " ")
            rx = r"(?<![а-яё])(" + alts + r")(?![а-яё])"
            hit = bool(re.search(rx, f["sent"])) if not f.get("blank") else re.fullmatch(alts, f["blank"]) is not None
            if hit == neg:
                return False
            continue
        if t.startswith(("sent:", "end:", "prevlem:", "per:", "prevw:", "prevpos:")):
            kind, rx = t.split(":", 1)
            rx = rx.replace("/", "|").replace("_", " ")
            if kind == "sent":
                hit = bool(re.search(rx, f["sent"]))
            elif kind == "prevw":
                hit = bool(re.search(rx, f["prev"]))
            elif kind == "prevpos":
                hit = any(re.search(rx, str(x.tag.POS or "")) for x in (P.M.parse(f["prev"]) if f["prev"] else []))
            elif kind == "end":
                hit = bool(re.search(rx, f["ans"].lower().replace("ё", "е")))
            elif kind == "prevlem":
                hit = any(re.search(rx, w) for w in f["prevlem"].split())
            else:
                hit = (rx + "per") in f["tags"]
            if hit == neg:
                return False
        else:
            rest.append(term)
    return P.ok(" ".join(rest), f) if rest else True


def load_course(course):
    """{lesson id: [exercises of the lesson and its practice sets]}"""
    d = os.path.join(COURSES, course)
    out = defaultdict(list)
    for f in sorted(os.listdir(d)):
        if not f.endswith(".json") or f == "exam.json":
            continue
        base = re.sub(r"-practice(?:-\d+)?$", "", f[:-5])
        doc = json.load(io.open(os.path.join(d, f), encoding="utf-8"))
        out[base] += [e for e in doc.get("exercises") or [] if e.get("type") == "fill"]
    return out


def audit():
    """{(course, section): [(label, want, count)]}"""
    out = {}
    for course, secs in FACETS.items():
        have = load_course(course) if os.path.isdir(os.path.join(COURSES, course)) else {}
        for sec, facets in secs.items():
            prefer = re.findall(r"[a-z0-9]+", P.WANT.get(course, {}).get(sec, ""))
            fs = [feats_full(e, prefer) for e in have.get(sec, [])]
            out[(course, sec)] = [(label, want, sum(1 for f in fs if ok(want, f))) for label, want in facets]
    return out


def report(a):
    short = 0
    for (course, sec), rows in sorted(a.items()):
        gaps = [(l, w, n) for l, w, n in rows if n < MIN]
        tot = sum(n for _, _, n in rows)
        if gaps:
            print("%s/%s  (%d exercises)" % (course, sec, tot))
            for l, w, n in gaps:
                print("    %-45s %d" % (l, n))
            short += len(gaps)
    print("%d patterns with fewer than %d exercises" % (short, MIN))


# ── mining the library for the missing patterns ──
CITE_RE = re.compile(r"^(.+?), «(.+)»$")


def library():
    """(sentence, citation) from the library file, in a fixed shuffled order."""
    rows = []
    with io.open(LIB, encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            s, cite = parts[0].strip(), parts[2].strip()
            if not (28 <= len(s) <= 110) or re.search(r"[A-Za-z\d]", s) or s.count(",") > 3:
                continue
            if not CITE_RE.match(cite):
                continue
            rows.append((s, cite))
    random.Random(11).shuffle(rows)
    return rows


GRAMS = ("case", "number", "gender", "tense", "person", "mood", "voice", "aspect", "animacy")


ODD = re.compile(r"\b(Arch|Dist|Infr|Slng|Abbr|Erro|Litr|V-\w+)\b")


def standard(lemma, p, w):
    """Neither the word nor its dictionary form is a variant, archaic,
    colloquial or distorted spelling (вниманье, веселие, оне)."""
    if ODD.search(str(p.tag)):
        return False
    try:
        if ODD.search(str(p.normalized.tag)):
            return False
    except Exception:
        pass
    return True


def hypothetical(s, i, words, cite):
    """The sentence with its i-th word blanked, hinted with its dictionary form."""
    w = words[i]
    ps = P.M.parse(w.lower())
    if not ps:
        return None, None
    p = ps[0]
    if p.tag.POS not in P.POS_MAIN or "Name" in p.tag or "Surn" in p.tag or "Patr" in p.tag or "Geox" in p.tag:
        return None, None
    lemma = p.normal_form
    if lemma.lower() == w.lower() or "-" in w or not p.is_known:
        return None, None                    # nothing to change; a hyphenated or unknown word
    # the standard spelling only: the dictionary form, put into this form
    # again, must give the word (not вниманье, веселье from веселие, чорту)
    if not standard(lemma, p, w):
        return None, None
    k = 0
    q = None
    for m in re.finditer(r"[А-Яа-яЁё\-]+", s):
        if k == i:
            q = s[:m.start()] + "___ (" + lemma + ")" + s[m.end():]
            break
        k += 1
    if q is None:
        return None, None
    e = {"type": "fill", "q": q, "prompt": "*%s*" % cite, "answers": [w], "why": "From %s." % cite}
    return e, p


CONTEXT_TAGS = {"prep", "neg", "sya", "adj+", "samyi", "bolee", "eishiy", "Supr", "Fixd", "aspectchoice", "any", "afternum"}


def plain_tags(want):
    """The word's own tags a pattern requires — a cheap first check."""
    out = []
    for term in want.split():
        if term.startswith("!") or ":" in term or "|" in term or term in CONTEXT_TAGS or term.startswith("+"):
            continue
        out.append(term)
    return out


def mine(a, budget=400000):
    need = {}
    for (course, sec), rows in a.items():
        empty = sum(n for _, _, n in rows) == 0       # a lesson with no exercises at all gets more
        for label, want, n in rows:
            if n < MIN and " / " not in want:
                need[(course, sec, label)] = (want, (ADD + 2) if empty else ADD)
    if not need:
        return {}
    found = defaultdict(list)
    seen = set()
    if os.path.exists(FILL):            # go on from an earlier run
        for k, exs in json.load(io.open(FILL, encoding="utf-8")).items():
            course, sec = k.split("/")
            facets = dict(FACETS.get(course, {}).get(sec, []))
            prefer = re.findall(r"[a-z0-9]+", P.WANT.get(course, {}).get(sec, ""))
            for e in exs:
                want = facets.get(e.get("facet"))
                if want is None or ("blank:" in want) != (e["answers"][0].lower().replace("ё", "е") in GLOSS):
                    continue                # a pattern since redefined: mined again
                a0 = e["answers"][0]
                if "blank:" in want:
                    f = {"sent": re.sub(r"___ \([^)]*\)", a0, e["q"]).lower().replace("ё", "е"), "ans": a0, "prevlem": "", "tags": set(), "lemma": "", "hint": "", "blank": a0.lower().replace("ё", "е")}
                else:
                    f = feats_full(e, prefer)
                    s0 = re.sub(r"___ \([^)]*\)", a0, e["q"])
                    ws = re.findall(r"[А-Яа-яЁё\-]+", s0)
                    if a0 not in ws or hypothetical(s0, ws.index(a0), ws, "x")[0] is None:
                        continue            # would not pass today's checks
                if not ok(want, f):
                    continue
                found[k].append(e)
                seen.add((course, sec, re.sub(r"___ \([^)]*\)", e["answers"][0], e["q"])))
                key = (course, sec, e.get("facet"))
                if key in need:
                    want, left = need[key]
                    if left <= 1:
                        del need[key]
                    else:
                        need[key] = (want, left - 1)
    print("mining the library for %d patterns…" % len(need))
    rows = library()
    for si, (s, cite) in enumerate(rows[:budget]):
        if not need:
            break
        words = re.findall(r"[А-Яа-яЁё\-]+", s)
        if len(words) < 4:
            continue
        # a conjunction or particle, blanked itself
        low = s.lower().replace("ё", "е")
        for key in [k for k in need if "blank:" in need[k][0]]:
            course, sec, label = key
            want, left = need[key]
            term = next(t for t in want.split() if t.startswith("blank:"))
            m = re.search(r"(?<![а-яё])(" + term[6:].replace("/", "|").replace("_", " ") + r")(?![а-яё])", low)
            if not m or (course, sec, s) in seen:
                continue
            phrase = s[m.start(1):m.end(1)]
            gloss = GLOSS.get(phrase.lower().replace("ё", "е"))
            if not gloss:
                continue
            f = {"sent": low, "ans": phrase, "prevlem": "", "tags": set(), "lemma": "", "hint": gloss, "blank": phrase.lower().replace("ё", "е")}
            if not ok(want, f):
                continue
            q = s[:m.start(1)] + "___ (" + gloss + ")" + s[m.end(1):]
            seen.add((course, sec, s))
            found[course + "/" + sec].append({"type": "fill", "q": q, "prompt": "*%s*" % cite, "answers": [phrase],
                                              "why": "From %s." % cite, "keep": True, "facet": label})
            need[key] = (want, left - 1)
            if left - 1 <= 0:
                del need[key]
        if not any("blank:" not in v[0] for v in need.values()):
            continue
        for i, w in enumerate(words):
            if len(w) < 3:
                continue
            e, p = hypothetical(s, i, words, cite)
            if e is None:
                continue
            cheap = set(str(a) for a in (p.tag.POS, p.tag.case, p.tag.number, p.tag.gender, p.tag.tense, p.tag.aspect, p.tag.mood, p.tag.voice, p.tag.animacy, p.tag.person) if a)
            # a word may be read as other cases too: let the full check decide those
            cheap |= set(str(q.tag.case) for q in P.M.parse(w.lower())[:6] if q.tag.case)
            open_keys = [key for key in need if "blank:" not in need[key][0] and not any(t not in cheap for t in plain_tags(need[key][0]))]
            if not open_keys:
                continue
            # read once, as the case this word is taken to be
            f = feats_full(e, [str(p.tag.case)] if p.tag.case else ())
            for key in open_keys:
                if key not in need:
                    continue
                course, sec, label = key
                want, left = need[key]
                # a form that reads as two cases («урок»: nominative or
                # accusative): read it as the one the pattern wants
                cw = [c for c in P.CASES if c in plain_tags(want)]
                if cw and cw[0] not in f["tags"] and cw[0] in cheap:
                    f = feats_full(e, cw)
                sw = P.WANT.get(course, {}).get(sec)
                if sw and "sent:" not in want and not P.ok(sw, f):
                    continue                 # a pattern named by its sentence (пусть, если бы) is explicit enough
                if not ok(want, f):
                    continue
                if (course, sec, s) in seen:
                    continue
                seen.add((course, sec, s))
                found[course + "/" + sec].append(dict(e, keep=True, facet=label))
                need[key] = (want, left - 1)
                if left - 1 <= 0:
                    del need[key]
                break
        if si % 50000 == 0 and si:
            print("  %d sentences read, %d patterns still open" % (si, len(need)))
    for key, (want, left) in sorted(need.items()):
        print("  nothing found for %s/%s: %s" % key)
    return found


def apply_fill():
    if not os.path.exists(FILL):
        print("coverage: no coverage_fill.json, nothing to add")
        return
    fill = json.load(io.open(FILL, encoding="utf-8"))
    added = 0
    for key, exs in fill.items():
        course, sec = key.split("/")
        p = os.path.join(COURSES, course, sec + ".json")
        if not os.path.exists(p):
            continue
        doc = json.load(io.open(p, encoding="utf-8"))
        have = set(e.get("q") for e in doc.get("exercises") or [])
        new = [e for e in exs if e.get("q") not in have]
        if not new:
            continue
        exs0 = doc.get("exercises") or []
        for e in new:
            e = {k: v for k, v in e.items() if k != "facet"}
            e["id"] = "q%d" % (len(exs0) + 1)
            exs0.append(e)
        doc["exercises"] = exs0
        # the lesson says where the extra sentences come from
        blocks = doc.get("blocks") or []
        note = "Further sentences, so that every pattern above is practised: from Tatoeba (CC BY 2.0 FR), with their English."
        if not any(b.get("t") == "note" and b.get("text") == note for b in blocks):
            blocks.append({"t": "note", "text": note})
        doc["blocks"] = blocks
        io.open(p, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False))
        added += len(new)
    print("coverage: %d exercises added for patterns their lessons lacked" % added)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mine", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    if P.M is None:
        print("coverage skipped (pymorphy3 not installed)")
        return
    if a.apply:
        apply_fill()
        return
    au = audit()
    report(au)
    if a.mine:
        found = mine(au)
        io.open(FILL, "w", encoding="utf-8").write(json.dumps(found, ensure_ascii=False, indent=1))
        print("%d exercises -> %s" % (sum(len(v) for v in found.values()), FILL))


if __name__ == "__main__":
    main()
