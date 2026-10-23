#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The case courses' exercises, explained by the word itself.

Above a case exercise the lesson's sentence about the case used to be
repeated; now the exercise stands alone, its hint naming the word in its
dictionary form with the form wanted in English — «___ (книга, gen. pl.)» —
and once answered, right or wrong, it shows how that word's ending is
spelled and how the word declines into that case:

  * the change of ending, from the nominative singular to the form asked
    (both are the OpenCorpora dictionary's own forms, through pymorphy3);
  * the DLI model noun or adjective the word declines like, with the DLI
    form in the same case beside it, and the whole declension of the word;
  * the DLI spelling rule or peculiarity that applies (ы after gutturals and
    sibilants, -ем/-ом after sibilants, the fleeting vowel, -ии, the animate
    accusative, the genitive plural's four types and its inserted vowel …),
    quoted from the Grammar Reference Book with its lesson.

Nothing is composed: the forms are the dictionary's and the rules are DLI's;
the lines between them only name the ending that changed.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/courses/case_explain.py            # report
    python3 tools/courses/case_explain.py --apply
"""
import argparse, io, json, os, re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
COURSES = os.path.join(ROOT, "public", "courses")
CASE_COURSES = ["cases", "case-nom", "case-gen", "case-dat", "case-acc", "case-ins", "case-prp"]

try:
    import pymorphy3
    M = pymorphy3.MorphAnalyzer()
except ImportError:
    M = None

CASE_EN = {"nomn": "nom.", "gent": "gen.", "gen2": "gen.", "datv": "dat.", "accs": "acc.", "acc2": "acc.", "ablt": "instr.", "loct": "prep.", "loc2": "prep."}
CASE_FULL = {"nomn": "nominative", "gent": "genitive", "datv": "dative", "accs": "accusative", "ablt": "instrumental", "loct": "prepositional"}
CASE_ROW = {"nomn": "N.", "gent": "G.", "datv": "D.", "accs": "A.", "ablt": "I.", "loct": "P."}
CASES = ["nomn", "gent", "datv", "accs", "ablt", "loct"]
GUTT, SIB = "гкх", "жчшщ"
WORD = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)?")

DICT = "forms from the OpenCorpora dictionary (CC BY-SA 4.0)"

# The DLI model words (Grammar Reference Book, Lessons 32–33 for the singular,
# 42–45 for the plural, 46–48 for adjectives), with their full declension.
MODELS_SG = {
    "hard": ("студент", ["студент", "студента", "студенту", "студента", "студентом", "о студенте"], "a hard consonant"),
    "hard-inan": ("дом", ["дом", "дома", "дому", "дом", "домом", "о доме"], "a hard consonant"),
    "soft": ("учитель", ["учитель", "учителя", "учителю", "учителя", "учителем", "об учителе"], "-ь"),
    "soft-inan": ("автомобиль", ["автомобиль", "автомобиля", "автомобилю", "автомобиль", "автомобилем", "об автомобиле"], "-ь"),
    "j": ("трамвай", ["трамвай", "трамвая", "трамваю", "трамвай", "трамваем", "о трамвае"], "-й"),
    "j-anim": ("Андрей", ["Андрей", "Андрея", "Андрею", "Андрея", "Андреем", "об Андрее"], "-й"),
    "n-o": ("окно", ["окно", "окна", "окну", "окно", "окном", "об окне"], "-о"),
    "n-e": ("поле", ["поле", "поля", "полю", "поле", "полем", "о поле"], "-е"),
    "n-ie": ("здание", ["здание", "здания", "зданию", "здание", "зданием", "о здании"], "-ие"),
    "f-a": ("сестра", ["сестра", "сестры", "сестре", "сестру", "сестрой", "о сестре"], "-а"),
    "f-ya": ("тётя", ["тётя", "тёти", "тёте", "тётю", "тётей", "о тёте"], "-я"),
    "f-iya": ("армия", ["армия", "армии", "армии", "армию", "армией", "об армии"], "-ия"),
    "f-soft": ("часть", ["часть", "части", "части", "часть", "частью", "о части"], "-ь"),
    "mya": ("имя", ["имя", "имени", "имени", "имя", "именем", "об имени"], "-мя"),
}
MODELS_PL = {
    "hard": ("слова", ["слова", "слов", "словам", "слова", "словами", "о словах"]),
    "sibilant": ("ключи", ["ключи", "ключей", "ключам", "ключи", "ключами", "о ключах"]),
    "guttural": ("книги", ["книги", "книг", "книгам", "книги", "книгами", "о книгах"]),
    "soft": ("словари", ["словари", "словарей", "словарям", "словари", "словарями", "о словарях"]),
    "-ь-": ("семьи", ["семьи", "семей", "семьям", "семьи", "семьями", "о семьях"]),
    "vowel": ("батареи", ["батареи", "батарей", "батареям", "батареи", "батареями", "о батареях"]),
}
ADJ_SG_M = {"hard": ("новый", ["новый", "нового", "новому", "—", "новым", "о новом"]), "soft": ("синий", ["синий", "синего", "синему", "—", "синим", "о синем"]),
            "guttural": ("русский", ["русский", "русского", "русскому", "—", "русским", "о русском"]), "sibilant": ("хороший", ["хороший", "хорошего", "хорошему", "—", "хорошим", "о хорошем"])}
ADJ_SG_F = {"hard": ("новая", ["новая", "новой", "новой", "новую", "новой", "о новой"]), "soft": ("синяя", ["синяя", "синей", "синей", "синюю", "синей", "о синей"]),
            "guttural": ("русская", ["русская", "русской", "русской", "русскую", "русской", "о русской"]), "sibilant": ("хорошая", ["хорошая", "хорошей", "хорошей", "хорошую", "хорошей", "о хорошей"])}
ADJ_PL = {"hard": ("новые", ["новые", "новых", "новым", "—", "новыми", "о новых"]), "soft": ("синие", ["синие", "синих", "синим", "—", "синими", "о синих"]),
          "guttural": ("русские", ["русские", "русских", "русским", "—", "русскими", "о русских"]), "sibilant": ("хорошие", ["хорошие", "хороших", "хорошим", "—", "хорошими", "о хороших"])}
ADJ_TYPE_EN = {"hard": "I, hard", "soft": "II, soft", "guttural": "III, guttural (after г, к, х)", "sibilant": "IV, sibilant (after ж, ч, ш, щ)"}

# DLI's own words, from the lessons the case courses quote.
R = {
 "y": "«The letter ы never follows г, к, х, ж, ч, ш, щ; therefore: книга — книги, река — реки, госпожа — госпожи.» — DLI, Lesson 23.",
 "ins-sib": "«After ж, ч, ш, щ and ц the stressed ending is -ом, the unstressed ending is -ем: карандашом, багажом, ключом, отцом; but: мужем, товарищем, американцем. The same for feminine nouns: госпожой, but учительницей.» — DLI, Lesson 30.",
 "ins-soft": "«The \"soft\" ending is -ём if stressed: словарём, дождём, днём. These endings are easily remembered when associated with the adverbs утром, вечером and днём, which are nothing but the instrumental case of the nouns утро, вечер and день. Likewise деревней, армией, but семьёй.» — DLI, Lesson 30.",
 "ins-f": "Instrumental endings: masculine and neuter -ом, -ем (доктором, учителем, молоком, полем); feminine (and masculine) in -а, -я: -ой, -ей (сестрой, армией); feminine in -ь: -ью (частью). — DLI, Lesson 30.",
 "fleet": "«Certain masculine nouns have the vowels е or о only in the nominative singular (and in the accusative if inanimate): отец — отца, американец — американца, кусок — куска, звонок — звонка.» — DLI, Lesson 32.",
 "prep-i": "«If the stem of the noun ends in и-, the prepositional case singular has another -и as the ending (instead of -е): Россия — в России, здание — в здании.» — DLI, Lessons 16–17.",
 "prep-f": "«Feminine nouns ending in -ь in the nominative singular have -и in the prepositional singular: тетрадь — в тетради, часть — о части, дверь — на двери.» — DLI, Lessons 16–17.",
 "prep-e": "«The prepositional case is always used with a preposition. … The basic ending of the prepositional case singular is -е.» — DLI, Lessons 16–17.",
 "loc-u": "«Some masculine nouns take the ending -у (always with a stress) in the prepositional-locative case, i.e. after the prepositions в or на. The same nouns have the regular ending -е after о, об. Я был в лесу, в саду, в аэропорту, на берегу. Also: на мосту, в полку, в or на снегу. However: Я говорю о лесе, об аэропорте.» — DLI, Lesson 27.",
 "acc-anim": "«The accusative of masculine animate nouns is the same as the genitive. The accusative of masculine inanimate nouns and of all neuter nouns is the same as the nominative.» — DLI, Lesson 32.",
 "acc-f": "«The accusative singular of all feminine nouns ending in -ь is the same as nominative. The accusative singular of all other feminine nouns ends in -у or -ю.» — DLI, Lesson 33.",
 "acc-stress": "«Some feminine nouns with stressed endings in the nominative case have the stress on the 1st syllable in the accusative: доска — до́ску, стена — сте́ну, рука — ру́ку, гора — го́ру. However: жена — жену́, сестра — сестру́, река — ре́ку.» — DLI, Lesson 18.",
 "acc-pl": "«The accusative plural of inanimate nouns is the same as the nominative plural. The accusative plural of animate nouns is the same as the genitive plural.» — DLI, Lesson 42.",
 "masc-a": "«There are some masculine nouns ending in -а, -я which are declined like feminine nouns: мужчина, старшина, дедушка, дядя. The modifiers of these nouns remain in masculine forms: Мой старый дедушка.» — DLI, Lesson 33.",
 "mat": "«The nouns мать and дочь take -ер- before the ending in all cases except the nom. and the acc. sing.: матерью, дочерью.» — DLI, Lesson 30.",
 "gen-sg": "Genitive endings: masculine -а, -я (книга студента, книга учителя); neuter -а, -я (стакан вина, часть здания); feminine -ы, -и (стакан воды, часть семьи, часть тетради). — DLI, Lesson 23.",
 "gen-u": "«Several masculine nouns may take the ending -у, -ю (instead of -а, -я) in the genitive case when a quantity is expressed: Дайте, пожалуйста, супу, сахару, чаю. Хотите стакан чаю?» — DLI, Lesson 33.",
 "dat-sg": "Dative: 1. Masculine and neuter (except masculine in -а, -я): студенту, учителю, озеру, полю. 2. All feminine, and masculine in -а, -я: сестре, дяде, Марии, двери. — DLI, Lesson 28.",
 "genpl": "Genitive plural, the four basic types: I — nom. sing. in a consonant (стол, нож): -ов, столов; II — in -ь or a sibilant (словарь, тетрадь): -ей, словарей, тетрадей, ножей; III — in -а, -о (газета, слово): no ending, газет, слов; IV — in -(и)я, -(и)е (лекция, здание): -й, лекций, зданий. — DLI, Lessons 38–41.",
 "genpl-I": "«Type I. a) After ц the stressed ending is -ов, the unstressed is -ев: отцов, продавцов, but: американцев, немцев, месяцев. b) Masculine nouns in -й have -ев in the genitive plural: трамвай — трамваев.» — DLI, Lessons 38–41.",
 "genpl-II": "«Type II. a) The nouns мать and дочь keep -ер- throughout the plural: матерей, дочерей. b) The noun соседи, also the nouns люди, дети, and родители belong to type II: соседей, людей, родителей, детей.» — DLI, Lessons 38–41.",
 "genpl-III": "«Type III. a) The genitive plural of feminine and neuter nouns of this type often has an inserted -е- or -о- between any two consonants at the end of the word. 1. They always take -е- between a sibilant and к: чашка — чашек, девочка — девочек. 2. They take -о- between any other consonant and к: ошибка — ошибок, машинка — машинок. 3. Memorize: число — чисел, письмо — писем, окно — окон; also деньги — денег. Remember: сестра — сёстры — сестёр; but: место — мест, лампа — ламп, буква — букв, карта — карт. b) неделя — недель, деревня — деревень, туфля — туфель.» — DLI, Lessons 38–41.",
 "genpl-IV": "«Type IV. The neuter nouns поле and море: полей, морей. семья has the genitive plural семей.» — DLI, Lessons 38–41.",
 "genpl-irr": "«Some masculine and neuter nouns with the irregular nom. plural ending -ья: стулья — стульев, братья — братьев, перья — перьев; and друзья — друзей, сыновья — сыновей, мужья — мужей. The genitive plural of раз, человек, солдат is the same as the nominative singular: пять раз, пять человек, пять солдат. For the genitive plural of the noun год the word лет is used: один год, два года, пять лет.» — DLI, Lessons 38–41.",
 "pl-dip": "«For the dative and the prepositional plural there are two kinds of endings for each case: -ам, -ами, -ах after a hard, a sibilant or a guttural consonant; -ям, -ями, -ях after a soft consonant, a «ь» or a vowel. The formation of these cases does not depend upon the gender of the noun, but only upon the sound preceding the ending.» — DLI, Lessons 42–45.",
 "pl-mi": "«Three nouns: люди, дети and дочери have the instrumental case ending -ьми instead of -ями: людьми, детьми, дочерьми.» «Masculine and neuter nouns with the irregular plural ending in -ья (стулья, перья, etc.) retain the «ь»: стульям, стульями, о стульях.» — DLI, Lessons 42–45.",
 "pl-nom": "«The basic endings of masculine and feminine nouns in the nominative plural are ы (\"hard\") and и (\"soft\").» — DLI, Lesson 36.",
 "pl-nom-a": "«Masculine nouns with the irregular nominative plural in -а or -я have the regular declension in all other cases: дома — домов — домам; учителя — учителей — учителям.» — DLI, Lessons 42–45.",
 "adj": "«All adjectives agree in gender, number and case with the noun they modify.» — DLI, Lesson 47.",
 "adj-oy": "«Masculine adjectives of the \"hard\" and \"guttural\" types have in the nominative the ending -ой if stressed: новый — молодой; русский — плохой, and retain the stress on the ending throughout the declension.» «The adjective «большой» belongs to the guttural type, in spite of its -ш-: большого, большому, большим, о большом.» — DLI, Lesson 47.",
 "adj-f": "«Notice that the feminine adjectives have the same ending -ой (-ей) for all cases except for the nominative and accusative. In spite of -ш-, «большая» belongs to the guttural type: большой, большую.» — DLI, Lesson 47.",
 "adj-pl": "«Notice that the adjectives of the \"soft\", \"guttural\" and \"sibilant\" types are declined in the plural in the very same way.» — DLI, Lesson 48.",
 "adj-acc": "Adjectives in the accusative: animate = genitive, inanimate = nominative (masculine and plural); feminine -ую, -юю. — DLI, Lessons 46–47.",
 "poss": "«Notice the similarity of the endings of the possessives to the form of «они».» мой · моё — моего — моему — моим — о моём; моя — моей — мою; мои — моих — моим — моими — о моих. — DLI, Lessons 47–48.",
 "surname": "«Russian masculine surnames in -ов, -ев, -ин take the ending -ым in the instrumental: с господином Ивановым, с Гусевым, с Рудиным.» «Russian feminine surnames in -ова, -ева, -ина have the usual ending -у in the accusative; in other cases they take the ending -ой.» — DLI, Lessons 32–33.",
 "pron": "After a preposition the third-person pronouns take н-: у него, к ней, с ними. — DLI, Lessons 32 and 35.",
 "adj-noun": "«Больной, раненый and знакомый are often used as adjectival nouns.» — DLI, Lesson 57.",
 "num234": "«After 2, 3, 4 (also after compounds ending in 2, 3, 4) the adjective or possessive is in the genitive plural, while the noun is in the genitive singular: два наших самолёта; двадцать четыре новых самолёта.» — DLI, Lesson 50.",
}


def tags(p):
    return set(str(p.tag).replace(" ", ",").split(","))


def norm(w):
    return w.lower().replace("ё", "е")


def paradigm(p):
    """{(case, number): form} for a noun or adjective parse, the dictionary's first form of each."""
    out = {}
    for f in p.lexeme:
        t = tags(f)
        c = f.tag.case
        n = f.tag.number
        if not c or not n or c in ("voct", "gen2", "acc2", "loc2") or "Infr" in t or "V-ey" in t or "V-oy" in t or "V-be" in t:
            continue
        if p.tag.POS in ("ADJF", "PRTF", "NPRO", "NUMR"):
            key = (c, n, f.tag.gender, f.tag.animacy if c == "accs" else None)
        else:
            key = (c, n)
        out.setdefault(key, f.word)
    return out


def noun_class(nom, gender, anim):
    """The DLI model (singular) a noun declines like, from its nominative singular."""
    w = norm(nom)
    if w in ("мать", "дочь"):
        return "f-soft"
    if gender == "neut":
        if w.endswith("мя"): return "mya"
        if w.endswith("ие") or w.endswith("ье"): return "n-ie"
        if w.endswith("е") or w.endswith("ё"): return "n-e"
        return "n-o"
    if w.endswith("ия"): return "f-iya"
    if w.endswith("а"): return "f-a"
    if w.endswith("я"): return "f-ya"
    if gender == "femn":
        return "f-soft"
    if w.endswith("ь"): return "soft" if anim == "anim" else "soft-inan"
    if w.endswith("й"): return "j-anim" if anim == "anim" else "j"
    return "hard" if anim == "anim" else "hard-inan"


def plural_class(nom_sg, nom_pl):
    w = norm(nom_sg)
    stem = re.sub(r"[аяоеьй]$", "", w)
    if w.endswith(("ья", "ье")): return "-ь-"
    if w.endswith(("ий", "ия", "ие", "й", "ей")): return "vowel"
    if stem and stem[-1] in SIB: return "sibilant"
    if stem and stem[-1] in GUTT: return "guttural"
    if w.endswith("ь") or w.endswith("я") or w.endswith("е"): return "soft"
    return "hard"


def genpl_type(nom_sg, gender):
    w = norm(nom_sg)
    if w.endswith(("ия", "ие")): return "IV"
    if w.endswith(("а", "о", "я", "е")): return "III"
    if w.endswith("ь") or (w and w[-1] in SIB): return "II"
    return "I"


def adj_class(lemma):
    w = norm(lemma)
    stem = re.sub(r"(ый|ий|ой)$", "", w)
    last = stem[-1:] if stem else ""
    if w == "большой" or last in GUTT: return "guttural"
    if last in SIB: return "sibilant"
    if w.endswith("ий"): return "soft"
    return "hard"


def ending_change(nom, form, stem=None):
    """«-а → -и»: the endings of the two forms after the stem (the nominative
    without its final vowel, -ь or -й); «отец → отца (stem отц-)» when the stem itself changes."""
    a, b = norm(nom), norm(form)
    if stem is None:
        stem = re.sub(r"(ый|ий|ой|ая|яя|ое|ее|ые|ие)$", "", a) if re.search(r"(ый|ий|ой)$", a) else re.sub(r"[аяоеёьй]$", "", a)
    stem = norm(stem)
    ea = a[len(stem):] if a.startswith(stem) else a
    if b.startswith(stem):
        eb = b[len(stem):]
        return ("-" + ea if ea else "— (no ending)"), ("-" + eb if eb else "— (no ending)"), False
    # the fleeting vowel: отец → отца, кусок → куска
    if len(stem) >= 3 and stem[-2] in "оеё" and b.startswith(stem[:-2] + stem[-1]) and not b.startswith(stem):
        eb = b[len(stem) - 1:]
        return ("-" + ea if ea else "— (no ending)"), ("-%s, with the fleeting -%s- of the stem dropped: %s- + -%s" % (eb, stem[-2], stem[:-2] + stem[-1], eb)), True
    # the genitive plural's inserted vowel: ремарка → ремарок, окно → окон
    if len(stem) >= 2 and len(b) == len(stem) + 1 and b[:-2] == stem[:-1] and b[-1] == stem[-1] and b[-2] in "оеё":
        return ("-" + ea if ea else "— (no ending)"), ("— (no ending; -%s- is inserted before the final %s: %s)" % (b[-2], stem[-1], b)), True
    k = 0
    while k < min(len(a), len(b)) and a[k] == b[k]:
        k += 1
    return ("-" + ea if ea else "— (no ending)"), ("-" + b[k:] + " (the stem changes: " + b[:max(k, 1)] + "-)"), True


def decl_line(par, number):
    return " · ".join(par.get((c, number), "—") for c in CASES)


def explain_noun(p, form, case, number, prep_before):
    nom_sg = p.normal_form if p.tag.number != "plur" or ("Pltm" not in tags(p)) else None
    par = paradigm(p)
    nom = par.get(("nomn", "sing")) or p.normal_form
    nom_pl = par.get(("nomn", "plur")) or ""
    gender, anim = p.tag.gender, p.tag.animacy
    bits, rules = [], []
    c_en, n_en = CASE_EN[case], ("sg." if number == "sing" else "pl.")
    cls = noun_class(nom, gender, anim)
    model, mforms, nom_end = MODELS_SG[cls]
    stem_nom = re.sub(r"[аяоеёьй]$", "", norm(nom))
    ea, eb, changed = ending_change(nom, form, stem_nom)
    head = "**%s → %s** (%s %s)." % (nom, form.lower(), c_en, n_en)
    gen_en = {"masc": "masculine", "femn": "feminine", "neut": "neuter"}.get(gender, "plural-only")
    an_en = (", animate" if anim == "anim" else ", inanimate") if (gender == "masc" or number == "plur") and anim else ""
    if number == "sing":
        bits.append("%s%s, nominative singular in %s — declines like DLI's %s: %s %s. Ending %s → %s." % (
            gen_en.capitalize(), an_en, nom_end, model, CASE_ROW[case], mforms[CASES.index(case)], ea, eb))
    else:
        pcls = plural_class(nom, nom_pl)
        pm, pforms = MODELS_PL[pcls]
        bits.append("%s%s; nominative plural %s; declines like DLI's %s (%s stem): %s %s. Ending %s → %s." % (
            gen_en.capitalize(), an_en, nom_pl or "—", pm, pcls, CASE_ROW[case], pforms[CASES.index(case)], ea, eb))
    f = norm(form)
    k = len(stem_nom) if not changed else 0
    # the rules that apply
    if number == "sing":
        if case == "gent":
            rules.append(R["gen-sg"])
            if f.endswith("и") and stem_nom[-1:] in GUTT + SIB and gender != "masc" and norm(nom).endswith("а"):
                rules.append(R["y"])
            if f.endswith(("у", "ю")) and gender == "masc":
                rules.append(R["gen-u"])
        elif case == "datv":
            rules.append(R["dat-sg"])
        elif case == "ablt":
            rules.append(R["ins-f"])
            if (f.endswith("ем") or f.endswith("ей")) and stem_nom[-1:] in SIB + "ц":
                rules.append(R["ins-sib"])
            if "ё" in form.lower() and form.lower().endswith(("ём", "ёй")):
                rules.append(R["ins-soft"])
        elif case == "loct":
            if f.endswith("ии"):
                rules.append(R["prep-i"])
            elif cls == "f-soft":
                rules.append(R["prep-f"])
            elif f.endswith(("у", "ю")) and gender == "masc":
                rules.append(R["loc-u"])
            else:
                rules.append(R["prep-e"])
        elif case == "accs":
            if gender == "masc" and cls not in ("f-a", "f-ya", "f-iya"):
                rules.append(R["acc-anim"])
            elif gender == "femn" or cls in ("f-a", "f-ya", "f-iya"):
                rules.append(R["acc-f"])
            else:
                rules.append(R["acc-anim"])
        elif case == "nomn":
            pass
        if cls in ("f-a", "f-ya", "f-iya") and gender == "masc":
            rules.append(R["masc-a"])
        if norm(nom) in ("мать", "дочь") and case != "nomn":
            rules.append(R["mat"])
        if gender == "masc" and case != "nomn" and re.search(r"(ец|ок|ёк|ек|ел|ень|ень)$", norm(nom)) and k < len(stem_nom) and not norm(form).startswith(stem_nom):
            rules.append(R["fleet"])
    else:
        if case == "nomn":
            rules.append(R["pl-nom"])
            if f.endswith("и") and stem_nom[-1:] in GUTT + SIB:
                rules.append(R["y"])
            if gender == "masc" and f.endswith(("а", "я")):
                rules.append(R["pl-nom-a"])
        elif case == "gent":
            t = genpl_type(nom, gender)
            rules.append(R["genpl"])
            rules.append(R["genpl-" + t])
            if norm(nom_pl).endswith("ья") or norm(nom) in ("раз", "человек", "солдат", "год"):
                rules.append(R["genpl-irr"])
        elif case == "accs":
            rules.append(R["acc-pl"])
            if f.endswith("и") and stem_nom[-1:] in GUTT + SIB and anim != "anim":
                rules.append(R["y"])
        else:
            rules.append(R["pl-dip"])
            if f.endswith("ьми") or norm(nom_pl).endswith("ья"):
                rules.append(R["pl-mi"])
    decl = "Declension: sg. %s; pl. %s." % (decl_line(par, "sing"), decl_line(par, "plur"))
    return head, bits, rules, decl


POSS = {"мой", "твой", "свой", "наш", "ваш", "чей"}


def explain_adj(p, form, case, number, gender, anim, noun_word):
    lemma = p.normal_form
    par = paradigm(p)
    c_en, n_en = CASE_EN[case], ("sg." if number == "sing" else "pl.")
    if norm(lemma) in POSS:
        stem = norm(lemma)[:-1] if norm(lemma).endswith("й") else norm(lemma)
        nomf = par.get(("nomn", number, gender if number == "sing" else None, None)) or lemma
        ea, eb, _ = ending_change(nomf, form, stem)
        head = "**%s → %s** (%s %s%s, agreeing with %s)." % (lemma, form.lower(), c_en, n_en, (" " + {"masc": "m.", "femn": "f.", "neut": "n."}.get(gender, "")) if number == "sing" and gender else "", noun_word)
        return head, ["A possessive — declines like DLI's мой / наш. Ending %s → %s." % (ea, eb)], [R["poss"]]
    cls = adj_class(lemma)
    head = "**%s → %s** (%s %s%s, agreeing with %s)." % (lemma, form.lower(), c_en, n_en, (" " + {"masc": "m.", "femn": "f.", "neut": "n."}.get(gender, "")) if number == "sing" and gender else "", noun_word)
    bits, rules = [], []
    if number == "plur":
        model, forms = ADJ_PL[cls]
    elif gender == "femn":
        model, forms = ADJ_SG_F[cls]
    else:
        model, forms = ADJ_SG_M[cls]
    mf = forms[CASES.index(case)]
    if mf == "—":
        mf = "anim. = G., inan. = N."
    stem = re.sub(r"(ый|ий|ой)$", "", norm(lemma))
    nomf = par.get(("nomn", number, gender if number == "sing" else None, None)) or lemma
    ea, eb, _ = ending_change(nomf, form, stem)
    bits.append("Adjective type %s — declines like DLI's %s: %s %s. Ending %s → %s." % (ADJ_TYPE_EN[cls], model, CASE_ROW[case], mf, ea, eb))
    rules.append(R["adj"])
    if norm(lemma).endswith("ой"):
        rules.append(R["adj-oy"])
    if number == "sing" and gender == "femn" and case not in ("nomn", "accs"):
        rules.append(R["adj-f"])
    if number == "plur":
        rules.append(R["adj-pl"])
    if case == "accs":
        rules.append(R["adj-acc"])
    return head, bits, rules


PREP_CASE = {"без": "gent", "для": "gent", "из": "gent", "от": "gent", "у": "gent", "около": "gent", "после": "gent", "до": "gent", "кроме": "gent", "мимо": "gent",
             "против": "gent", "вместо": "gent", "из-за": "gent", "из-под": "gent", "возле": "gent", "вокруг": "gent", "среди": "gent", "вдоль": "gent", "ради": "gent", "напротив": "gent",
             "к": "datv", "ко": "datv", "по": "datv", "благодаря": "datv", "навстречу": "datv",
             "через": "accs", "про": "accs", "сквозь": "accs",
             "над": "ablt", "надо": "ablt", "перед": "ablt", "передо": "ablt", "между": "ablt",
             "при": "loct", "о": "loct", "об": "loct", "обо": "loct"}
COURSE_CASE = {"case-nom": {"nomn"}, "case-gen": {"gent"}, "case-dat": {"datv"}, "case-acc": {"accs"}, "case-ins": {"ablt"}, "case-prp": {"loct"}}
SECTION_CASE = {"k1": {"nomn", "loct"}, "k2": {"accs"}, "k3": {"gent"}, "k4": {"datv"}, "k5": {"ablt"}, "k7": {"gent"}}


def best_parse(word, want_lemma, pos_set, want_cases=()):
    ps = [p for p in M.parse(word) if p.tag.POS in pos_set]
    if want_lemma:
        hit = [p for p in ps if norm(p.normal_form) == norm(want_lemma)]
        if hit:
            ps = hit
    if want_cases:
        c = [p for p in ps if (("loct" if p.tag.case == "loc2" else "gent" if p.tag.case == "gen2" else "accs" if p.tag.case == "acc2" else p.tag.case) in want_cases)]
        if c:
            return c[0]
    return ps[0] if ps else None


def rewrite(e, want_cases=()):
    """(new q, new why) for a case exercise, or None when the word is not a noun phrase we can read."""
    q = e.get("q") or ""
    m = re.search(r"___ \(([^)]*)\)", q)
    if not m:
        return None
    hint = re.sub(r",\s*(nom|gen|dat|acc|instr|prep)\.\s*(sg|pl)\.(\s*[mfn]\.)?\s*$", "", m.group(1).strip())   # a label given earlier
    if re.search(r"\d|[A-Za-z]", hint):
        return None
    ans = (e.get("answers") or [""])[0]
    hw = WORD.findall(hint)
    aw = WORD.findall(ans)
    if not aw or len(hw) != len(aw) or len(aw) > 3:
        return None
    before = q[:m.start()]
    prep = (re.findall(r"([А-Яа-яЁё-]+)\s*$", before) or [""])[0].lower()
    want = set(want_cases)
    pc = PREP_CASE.get(prep)
    if pc and (not want or pc in want):
        want = {pc}
    # the noun of the phrase (the last noun), then its modifiers in the noun's case
    parses = []
    for h, a in zip(hw, aw):
        p = best_parse(a, h, {"NOUN", "ADJF", "PRTF", "NPRO", "NUMR"}, want)
        if not p:
            return None
        parses.append(p)
    nouns = [i for i, p in enumerate(parses) if p.tag.POS == "NOUN"]
    if not nouns and len(parses) == 1 and parses[0].tag.POS == "NPRO":
        # a pronoun on its own: its declension, and the н- after a preposition
        p0 = parses[0]
        case, number = p0.tag.case, p0.tag.number or "sing"
        case = {"gen2": "gent", "loc2": "loct", "acc2": "accs"}.get(case, case)
        if case not in CASES:
            return None
        label = "%s %s" % (CASE_EN[case], "sg." if number == "sing" else "pl.")
        par = paradigm(p0)
        g = p0.tag.gender
        decl = " · ".join(par.get((c, number, g, None)) or par.get((c, number, None, None)) or "—" for c in CASES)
        newq = q[:m.start()] + "___ (" + p0.normal_form + ", " + label + ")" + q[m.end():]
        why = "**%s → %s** (%s). Declension: %s.  %s  — %s." % (p0.normal_form, aw[0].lower(), label, decl, R["pron"], DICT)
        return newq, why
    if not nouns and len(parses) == 1 and parses[0].tag.POS in ("ADJF", "PRTF"):
        # an adjective on its own: it agrees with the noun that follows it in the sentence
        after = q[m.end():]
        nxt = WORD.findall(after)[:2]
        pnoun = None
        for w in nxt:
            cand = [x for x in M.parse(w) if x.tag.POS == "NOUN"]
            if cand:
                pnoun = cand[0]
                for x in cand:
                    if x.tag.case in want or not want:
                        pnoun = x
                        break
                break
        pa = parses[0]
        if pnoun is not None:
            alt = [x for x in M.parse(aw[0]) if x.tag.POS in ("ADJF", "PRTF") and x.tag.case == pnoun.tag.case and x.tag.number == pnoun.tag.number
                   and (pnoun.tag.number == "plur" or x.tag.gender == pnoun.tag.gender)]
            if alt:
                pa = alt[0]
        case, number, gender = pa.tag.case, pa.tag.number or "sing", pa.tag.gender
        case = {"gen2": "gent", "loc2": "loct", "acc2": "accs"}.get(case, case)
        if case not in CASES:
            return None
        g_en = (" " + {"masc": "m.", "femn": "f.", "neut": "n."}.get(gender, "")) if number == "sing" and gender else ""
        label = "%s %s%s" % (CASE_EN[case], "sg." if number == "sing" else "pl.", g_en)
        newq = q[:m.start()] + "___ (" + pa.normal_form + ", " + label + ")" + q[m.end():]
        head, bits, rules = explain_adj(pa, aw[0], case, number, gender, pnoun.tag.animacy if pnoun else None, pnoun.word if pnoun else "its noun")
        par = paradigm(pa)
        pl_line = " · ".join(par.get((c, "plur", None, None)) or par.get((c, "plur", None, "inan")) or "—" for c in CASES)
        if number == "plur" or not gender:
            decl = "Declension (plural): %s." % pl_line
        else:
            decl = "Declension (%s): %s; plural: %s." % ({"masc": "m.", "femn": "f.", "neut": "n."}[gender],
                   " · ".join(par.get((c, "sing", gender, None)) or par.get((c, "sing", gender, "inan")) or "—" for c in CASES), pl_line)
        why = head + " " + " ".join(bits) + "  " + decl + "  " + "  ".join(rules) + "  — Model words and rules from the DLI Grammar Reference Book; " + DICT + "."
        return newq, why
    if not nouns:
        return None
    ni = nouns[-1]
    pn = parses[ni]
    case, number = pn.tag.case, pn.tag.number
    for i, p in enumerate(parses):
        if i != ni and p.tag.case != case:
            alt = best_parse(aw[i], hw[i], {p.tag.POS}, {case})
            if alt and alt.tag.case == case:
                parses[i] = alt
    if case in ("gen2",): case = "gent"
    if case in ("loc2",): case = "loct"
    if case in ("acc2",): case = "accs"
    if case not in CASES or not number:
        return None
    label = "%s %s" % (CASE_EN[case], "sg." if number == "sing" else "pl.")
    # the hint: every word in its dictionary form
    dict_forms = []
    par_n = paradigm(pn)
    pl_only = "Pltm" in tags(pn) or not par_n.get(("nomn", "sing"))
    for i, p in enumerate(parses):
        if p.tag.POS == "NOUN":
            par = paradigm(p)
            dict_forms.append((par.get(("nomn", "plur")) if pl_only else par.get(("nomn", "sing"))) or p.normal_form)
        elif p.tag.POS in ("ADJF", "PRTF", "NPRO", "NUMR"):
            par = paradigm(p)
            dict_forms.append((par.get(("nomn", "plur", None, None)) if pl_only else par.get(("nomn", "sing", pn.tag.gender, None))) or p.normal_form)
        else:
            dict_forms.append(p.normal_form)
    dict_forms = [(d[:1].upper() + d[1:]) if h[:1].isupper() else d for d, h in zip(dict_forms, hw)]
    newq = q[:m.start()] + "___ (" + " ".join(dict_forms) + ", " + label + ")" + q[m.end():]
    adjectival = norm(par_n.get(("gent", "sing"), "")).endswith(("ого", "его")) or (number == "plur" and norm(par_n.get(("gent", "plur"), "")).endswith(("ых", "их")))
    pa = None
    if adjectival:
        pa = best_parse(aw[ni], None, {"ADJF", "PRTF"}, {case})
    if pa is not None and pa.tag.case == case:
        head, bits, rules = explain_adj(pa, aw[ni], case, number, pn.tag.gender or pa.tag.gender, pn.tag.animacy, "the noun it stands for")
        head = head.replace(", agreeing with the noun it stands for", "; an adjective used as a noun")
        rules = [R["adj-noun"]] + rules
        decl = "Declension: sg. %s; pl. %s." % (decl_line(par_n, "sing"), decl_line(par_n, "plur"))
    else:
        head, bits, rules, decl = explain_noun(pn, aw[ni], case, number, prep)
    parts = [head + " " + " ".join(bits)]
    for i, p in enumerate(parses):
        if i == ni:
            continue
        if p.tag.POS in ("ADJF", "PRTF"):
            h2, b2, r2 = explain_adj(p, aw[i], case, number, pn.tag.gender, pn.tag.animacy, aw[ni])
            parts.append(h2 + " " + " ".join(b2))
            for r in r2:
                if r not in rules:
                    rules.append(r)
        elif p.tag.POS == "NPRO" and norm(p.normal_form) in ("мой", "твой", "наш", "ваш", "свой", "его", "её", "их"):
            parts.append("**%s → %s** — %s" % (p.normal_form, aw[i].lower(), label))
            if R["poss"] not in rules:
                rules.append(R["poss"])
    why = "  ".join(parts) + "  " + decl + "  " + "  ".join(rules) + "  — Model words and rules from the DLI Grammar Reference Book; " + DICT + "."
    if hw[ni][:1].isupper():
        nf = parses[ni].normal_form
        why = why.replace("**" + nf + " →", "**" + nf[:1].upper() + nf[1:] + " →")
    return newq, why


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--course")
    a = ap.parse_args(argv)
    if M is None:
        print("case_explain skipped (pymorphy3 not installed)")
        return
    st = Counter()
    samples = []
    for cid in CASE_COURSES:
        if a.course and cid != a.course:
            continue
        d = os.path.join(COURSES, cid)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json") or fn == "exam.json":
                continue
            p = os.path.join(d, fn)
            doc = json.load(io.open(p, encoding="utf-8"))
            want0 = COURSE_CASE.get(cid) or SECTION_CASE.get(fn[:2], set())
            changed = False
            for e in doc.get("exercises") or []:
                if e.get("type") != "fill":
                    continue
                st["fill"] += 1
                if e.get("context"):
                    e["context"] = ""
                    changed = True
                want = want0
                if not want:
                    old = (e.get("context") or "") + " " + (e.get("why") or "")
                    mm = re.search(r"\b(nominative|genitive|dative|accusative|instrumental|prepositional)\b", old, re.I)
                    if mm:
                        want = {{"nominative": "nomn", "genitive": "gent", "dative": "datv", "accusative": "accs", "instrumental": "ablt", "prepositional": "loct"}[mm.group(1).lower()]}
                r = rewrite(e, want)
                if not r:
                    st["left"] += 1
                    continue
                newq, why = r
                if e.get("q") != newq or e.get("why") != why:
                    e["q"], e["why"] = newq, why
                    changed = True
                st["explained"] += 1
                if len(samples) < 6 and st["explained"] % 400 == 1:
                    samples.append((cid, newq, e["answers"][0], why[:420]))
            if changed and a.apply:
                io.open(p, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False))
    print("case_explain:", dict(st))
    for s in samples:
        print(" ", s[0], "|", s[1], "→", s[2]); print("    ", s[3]); print()


if __name__ == "__main__":
    main()
