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
import argparse, io, json, os, re, sys
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
sys.path.insert(0, HERE)

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
 "genpl-none": "This genitive plural does not follow one of the four basic types in DLI's table above; learn the form from the declension given here.",
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
    RARE = {"Litr", "Arch", "Slng", "Erro", "Dist", "Infr", "Abbr"}
    forms = [f for f in p.lexeme if not (tags(f) & RARE)] + [f for f in p.lexeme if tags(f) & RARE]   # archaic variants only as a last resort
    for f in forms:
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
    """(from, to, kind): the endings of the two forms after their common stem, «-а → -и»;
    kind is 'plain', 'fleet' (отец → отца), 'inserted' (окно → окон), 'soft' (семья → семей) or
    'irregular' — the form changes by more than its ending (ребёнок → детей, этот → этому), and no ending is claimed."""
    a, b = norm(nom), norm(form)
    if stem is None:
        stem = re.sub(r"(ый|ий|ой|ая|яя|ое|ее|ые|ие)$", "", a) if re.search(r"(ый|ий|ой)$", a) else re.sub(r"[аяоеёьй]$", "", a)
    stem = norm(stem)
    if not a.startswith(stem) or len(stem) < 1:
        return None, None, "irregular"

    def lab(x):
        return ("-" + x) if x else "— (no ending)"
    ea = a[len(stem):]
    if b.startswith(stem):
        return lab(ea), lab(b[len(stem):]), "plain"
    # the fleeting vowel: отец → отца, кусок → куска
    if len(stem) >= 3 and stem[-2] in "оеё" and b.startswith(stem[:-2] + stem[-1]):
        eb = b[len(stem) - 1:]
        return lab(ea), ("-%s, with the fleeting -%s- of the stem dropped: %s- + -%s" % (eb, stem[-2], stem[:-2] + stem[-1], eb)), "fleet"
    # the genitive plural's inserted vowel: ремарка → ремарок, окно → окон, сестра → сестёр, письмо → писем
    if len(stem) >= 2:
        for cut in (1, 2):
            if len(stem) > cut and (cut == 1 or stem[-2] == "ь") and b == stem[:-cut] + b[len(stem) - cut:len(stem) - cut + 1] + stem[-cut:] and b[len(stem) - cut] in "оеё":
                return lab(ea), ("— (no ending; -%s- is inserted before the final %s: %s)" % (b[len(stem) - cut], stem[-1], b)), "inserted"
    # семья → семей: the soft sign of the stem gives way to -е-
    if stem.endswith("ь") and b.startswith(stem[:-1]) and b[len(stem) - 1:] in ("ей", "ёй"):
        return lab(ea), "-%s (the soft sign of the stem drops: %s- → %s-)" % (b[len(stem) - 1:], stem, stem[:-1]), "soft"
    return None, None, "irregular"


IRR_TXT = "The form changes by more than its ending, so no single ending is given — see the declension below."


def ending_txt(ea, eb, kind, case=None):
    if kind == "irregular":
        return IRR_TXT
    if kind == "plain" and ea == eb:
        if case == "nomn":
            return "Nominative: the ending is %s." % eb
        return "No change of ending: here the accusative is the same as the nominative."
    return "Ending %s → %s." % (ea, eb)


def nom_end_label(nom):
    w = norm(nom)
    for suf, lab in (("ие", "-ие"), ("ия", "-ия"), ("мя", "-мя"), ("а", "-а"), ("я", "-я"), ("о", "-о"), ("е", "-е"), ("ь", "-ь"), ("й", "-й")):
        if w.endswith(suf):
            return lab
    return "a consonant"


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
    pl_only = "Pltm" in tags(p)
    adjn = (not pl_only) and bool(re.search(r"(ый|ий|ой|ое|ее|ая|яя)$", norm(nom))) and norm(par.get(("gent", "sing"), "")).endswith(("ого", "его", "ой", "ей"))
    if adjn:
        stem_nom = re.sub(r"(ый|ий|ой|ое|ее|ая|яя)$", "", norm(nom))     # насекомое, рабочий, дежурная: the endings of an adjective
    else:
        stem_nom = re.sub(r"[ыиаяь]$", "", norm(nom)) if pl_only else re.sub(r"[аяоеёьй]$", "", norm(nom))
    ea, eb, kind = ending_change(nom, form, stem_nom)
    head = "**%s → %s** (%s %s)." % (nom, form.lower(), c_en, n_en)
    gen_en = {"masc": "masculine", "femn": "feminine", "neut": "neuter"}.get(gender, "plural-only")
    an_en = (", animate" if anim == "anim" else ", inanimate") if (gender == "masc" or number == "plur") and anim else ""
    import case_models as CM
    mm = {} if (pl_only or adjn) else CM.match_noun(M, par, nom, gender, anim, number, case)
    claim = ""
    if adjn:
        claim = " A noun that declines like an adjective (an adjective used as a noun): it takes adjective endings, not noun endings."
        rules.append(R["adj-noun"])
    if mm.get("level") == "full":
        claim = " Declines like DLI's %s — every %s form has the same endings (%s %s %s)." % (
            mm["model"], "singular" if number == "sing" else "plural", CASE_ROW[case], n_en, mm["form"])
        if not mm.get("same_anim"):
            claim = claim[:-1] + ", except the accusative, which follows the animacy rule."
    et = ending_txt(ea, eb, kind, case)
    if pl_only:
        bits.append("A plural-only noun (it has no singular); nominative plural %s.%s" % (nom, " " + et if kind != "irregular" else " " + et))
    elif number == "sing":
        bits.append("%s%s, nominative singular in %s.%s %s" % (gen_en.capitalize(), an_en, nom_end_label(nom), claim, et))
    else:
        bits.append("%s%s; nominative plural %s.%s %s" % (gen_en.capitalize(), an_en, nom_pl or "—", claim, et))
    if adjn:
        rules.append(R["adj"])
        return head, bits, rules, "Declension: sg. %s; pl. %s." % (decl_line(par, "sing"), decl_line(par, "plur"))
    f = norm(form)
    k = len(stem_nom) if kind == "plain" else 0
    # the rules that apply
    if number == "sing":
        if case == "gent":
            rules.append(R["gen-sg"])
            if re.search("[" + GUTT + SIB + "]и$", f) and gender != "masc" and norm(nom).endswith("а"):
                rules.append(R["y"])
            if f.endswith(("у", "ю")) and gender == "masc":
                rules.append(R["gen-u"])
        elif case == "datv":
            rules.append(R["dat-sg"])
        elif case == "ablt":
            rules.append(R["ins-f"])
            if f.endswith(("ем", "ей", "ом", "ой")) and stem_nom[-1:] in SIB + "ц":
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
            if re.search("[" + GUTT + SIB + "]и$", f):
                rules.append(R["y"])
            if gender == "masc" and f.endswith(("а", "я")):
                rules.append(R["pl-nom-a"])
        elif case == "gent":
            t = CM.genpl_type(nom, form, gender, nom_pl)
            if t in ("I", "II", "III", "IV"):
                rules.append(R["genpl"])
                nn = norm(nom)
                relevant = {"I": nn[-1:] in ("ц", "й"),                                       # the notes under each type, only when they concern this word
                            "II": nn in ("мать", "дочь", "сосед", "человек", "ребенок", "дитя", "родитель"),
                            "III": kind in ("inserted", "soft") or bool(re.search(r"(ня|ля|ье|ья)$", nn)),
                            "IV": nn in ("поле", "море", "семья")}[t]
                if relevant:
                    rules.append(R["genpl-" + t])
            elif t == "irr":
                rules.append(R["genpl-irr"])
            else:
                rules.append(R["genpl-none"])
        elif case == "accs":
            rules.append(R["acc-pl"])
            if re.search("[" + GUTT + SIB + "]и$", f) and anim != "anim":
                rules.append(R["y"])
        else:
            rules.append(R["pl-dip"])
            if f.endswith("ьми") or norm(nom_pl).endswith("ья"):
                rules.append(R["pl-mi"])
    if pl_only:
        decl = "Declension (plural only): %s." % decl_line(par, "plur")
    else:
        decl = "Declension: sg. %s; pl. %s." % (decl_line(par, "sing"), decl_line(par, "plur"))
    return head, bits, rules, decl


_DERIVED = False
POSS = {"мой", "твой", "свой", "наш", "ваш", "чей"}


def adj_forms(par, number, gender):
    g = gender if number == "sing" else None
    out = []
    for c in CASES:
        if c == "accs":
            ai, an, pl = par.get((c, number, g, "inan")), par.get((c, number, g, "anim")), par.get((c, number, g, None))
            if ai and an and norm(ai) != norm(an):
                out.append("%s (inan.) / %s (anim.)" % (ai, an))
            else:
                out.append(pl or ai or an or "—")
        else:
            out.append(par.get((c, number, g, None)) or "—")
    return " · ".join(out)


def explain_adj(p, form, case, number, gender, anim, noun_word):
    global _DERIVED
    _DERIVED = False
    lemma = p.normal_form
    par = paradigm(p)
    c_en, n_en = CASE_EN[case], ("sg." if number == "sing" else "pl.")
    import case_models as CM
    gtxt = (" " + {"masc": "m.", "femn": "f.", "neut": "n."}.get(gender, "")) if number == "sing" and gender else ""
    head = "**%s → %s** (%s %s%s, agreeing with %s)." % (lemma, form.lower(), c_en, n_en, gtxt, noun_word)
    nomf = par.get(("nomn", number, gender if number == "sing" else None, None)) or lemma
    if norm(lemma) in POSS:
        stem = norm(lemma)[:-1] if norm(lemma).endswith("й") else norm(lemma)
        ea, eb, kind = ending_change(nomf, form, stem)
        pw = CM.poss_match(M, par, lemma)
        return head, ["A possessive%s. %s" % (" — declines like DLI's %s" % pw if pw else "", ending_txt(ea, eb, kind, case))], [R["poss"]]
    bits, rules = [], []
    same = [v for k, v in par.items() if k[0] == case and k[1] == number and (number == "plur" or k[2] == gender)]
    if same and norm(form) not in [norm(v) for v in same]:
        # the answer is not a form of the plain adjective (a superlative or comparative: малый → малейшую)
        _DERIVED = True
        ft = [x for x in M.parse(form) if norm(x.normal_form) == norm(lemma)]
        tg = tags(ft[0]) if ft else set()
        kind_en = "a degree form (comparative / superlative)" if (tg & {"Supr", "COMP", "Cmp2"}) else "a derived form"
        return head, ["«%s» is %s of %s, not its plain form, so no ending is compared with the plain declension." % (form.lower(), kind_en, lemma)], [R["adj"]]
    stem = re.sub(r"(ый|ий|ой)$", "", norm(lemma))
    ea, eb, kind = ending_change(nomf, form, stem)
    regular_adj = bool(re.search(r"(ый|ий|ой)$", norm(lemma)))
    if not regular_adj:
        kind = "irregular"
        bits.append("«%s» is a pronoun-type word with its own declension, not the regular adjective pattern, so no ending rule is claimed. Its forms (%s): %s." % (
            lemma, ("%s sg." % {"masc": "m.", "femn": "f.", "neut": "n."}.get(gender, "")) if number == "sing" else "pl.", adj_forms(par, number, gender)))
        return head, bits, [R["adj"]]
    am = CM.match_adj(M, par, lemma) if regular_adj else None
    if am:
        model, cls, mpar = am
        mf = CM.model_form(mpar, case, number, gender)
        exc = ""
        if norm(lemma)[-2:] != norm(model)[-2:]:
            exc = " apart from the masculine nominative singular (and the inanimate accusative equal to it), which ends in -%s here, not -%s" % (norm(lemma)[-2:], norm(model)[-2:])
        bits.append("Adjective type %s — declines like DLI's %s (every form has the same endings,%s): %s %s. %s" % (ADJ_TYPE_EN[cls], model, exc or "", CASE_ROW[case], mf.rstrip("."), ending_txt(ea, eb, kind, case)) if exc else
                    "Adjective type %s — declines like DLI's %s (every form has the same endings): %s %s. %s" % (ADJ_TYPE_EN[cls], model, CASE_ROW[case], mf.rstrip("."), ending_txt(ea, eb, kind, case)))
    else:
        bits.append(ending_txt(ea, eb, kind, case))
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


PREP_ALL = {"в": {"accs", "loct"}, "во": {"accs", "loct"}, "на": {"accs", "loct"}, "за": {"accs", "ablt"}, "под": {"accs", "ablt"},
            "с": {"gent", "accs", "ablt"}, "со": {"gent", "accs", "ablt"}, "о": {"loct", "accs"}, "об": {"loct", "accs"}, "обо": {"loct", "accs"},
            "по": {"datv", "loct", "accs"}, "между": {"ablt", "gent"}, "перед": {"ablt"}, "передо": {"ablt"}, "над": {"ablt"}, "надо": {"ablt"},
            "вне": {"gent"}, "внутри": {"gent"}, "согласно": {"datv"}, "вопреки": {"datv"}, "подобно": {"datv"}}
for _k, _v in PREP_CASE.items():
    PREP_ALL.setdefault(_k, {_v})
TOKEN = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)?|[^\sА-Яа-яЁё]")
MODIFIER_POS = {"ADJF", "PRTF", "NPRO"}   # words that can stand between a preposition and its noun
INVARIANT = {"его", "её", "ее", "их"}


def _cn(c):
    return {"gen2": "gent", "loc2": "loct", "acc2": "accs"}.get(c, c)


def pairs_of(word, lemma=None, pos=None):
    """{(case, number)} the word can be (by lemma and part of speech when given)."""
    out = set()
    for p in M.parse(word):
        if pos and p.tag.POS not in pos:
            continue
        if lemma and not lemma_ok(p, lemma):
            continue
        c, n = _cn(p.tag.case), p.tag.number
        if c in CASES and n:
            out.add((c, n))
    return out


def governing_cases(before):
    """The cases a preposition just before the blank (up to two modifiers away) allows; None when there is none."""
    toks = TOKEN.findall(before)
    gaps = 0
    for i in range(len(toks) - 1, max(len(toks) - 5, -1), -1):
        t = toks[i].lower()
        if not WORD.fullmatch(toks[i]):
            return None                                   # punctuation ends the phrase
        if t in PREP_ALL:
            if t == "за" and i > 0 and toks[i - 1].lower() == "что":
                return {"nomn"}                           # «что за уродливые волосы»
            return set(PREP_ALL[t])
        if gaps >= 2:
            return None
        if t not in ("один", "одна", "одно", "одни") and any(x.tag.POS == "NUMR" for x in M.parse(t)) and not any(x.tag.POS in MODIFIER_POS for x in M.parse(t)):
            return None                                   # a numeral governs the genitive: the preposition no longer fixes the case
        if not any(x.tag.POS in MODIFIER_POS for x in M.parse(t)):
            return None                                   # a verb or noun: not part of the preposition's phrase
        gaps += 1
    return None


def resolve_pair(q, m, aw, hw):
    """The one (case, number) the blank can be in its sentence — from the preposition, the words that agree with it
    and the form itself — or None when the sentence does not settle it."""
    before, after = q[:m.start()], q[m.end():]
    last_w, last_h = aw[-1], hw[-1]
    if norm(last_w) in INVARIANT:
        return "invariant"
    P = pairs_of(last_w, last_h)
    if not P:
        return None
    gc = governing_cases(before)
    if gc:
        P = {x for x in P if x[0] in gc}
    if not P:
        return None
    for w, h in zip(aw[:-1], hw[:-1]):
        Q = P & pairs_of(w, h)
        if Q:
            P = Q
    last_pos = {p.tag.POS for p in M.parse(last_w) if not last_h or norm(p.normal_form) == norm(last_h)}
    if len(P) > 1 and "NOUN" in last_pos:
        pt = [t for t in TOKEN.findall(before)[-1:] if WORD.fullmatch(t)]
        if pt:     # an adjective or pronoun just before the noun agrees with it (a numeral does not: it governs the genitive)
            Q = P & {x for p in M.parse(pt[0]) if (p.tag.POS in ("ADJF", "PRTF") or (p.tag.POS == "NPRO" and not p.tag.person)) for x in pairs_of(pt[0], p.normal_form, {p.tag.POS})}
            if Q:
                P = Q
    if len(P) > 1 and not ("NOUN" in last_pos):
        # an adjective or pronoun on its own agrees with a noun beside it
        for side in (WORD.findall(after)[:2], WORD.findall(before)[-2:][::-1]):
            for w in side:
                npairs = {x for p in M.parse(w) if p.tag.POS == "NOUN" for x in pairs_of(w, p.normal_form, {"NOUN"})}
                Q = P & npairs
                if npairs and Q:
                    P = Q
                    break
            if len(P) == 1:
                break
    return next(iter(P)) if len(P) == 1 else None


def best_parse(word, want_lemma, pos_set, want_cases=(), num=None):
    allp = [p for p in M.parse(word) if p.tag.POS in pos_set]
    PROPER = {"Name", "Surn", "Patr", "Geox", "Orgn", "Trad"}
    common = [p for p in allp if not (tags(p) & PROPER)] or allp            # a word is not a first name unless nothing else fits
    for pool in (common, allp):
        ps = pool
        if want_lemma:
            hit = [p for p in ps if norm(p.normal_form) == norm(want_lemma)]
            if hit:
                ps = hit
        if num:
            hit = [p for p in ps if p.tag.number == num and (not want_cases or _cn(p.tag.case) in want_cases)]
            if hit:
                ps = hit
        if want_cases:
            c = [p for p in ps if _cn(p.tag.case) in want_cases]
            if c:
                return c[0]
            if want_lemma and pool is common:
                # the hint may be the inflected form itself (прекрасные цвета): then the lemma cannot pick the parse
                c = [p for p in pool if _cn(p.tag.case) in want_cases and (not num or p.tag.number == num)]
                if c:
                    return c[0]
        elif ps:
            return ps[0]
    return allp[0] if allp else None


CONFLICTS = []
NOT_MOD = object()


def lemma_ok(p, h):
    if norm(p.normal_form) == norm(h):
        return True
    return p.tag.POS in ("ADJF", "PRTF", "NPRO", "NUMR") and norm(h) in {norm(f.word) for f in p.lexeme if f.tag.case == "nomn"}


def modifier_path(e, q, m, aw, hw, want, num, pair):
    """A blank holding only adjectives / pronouns / participles (мой старший, своя маленькая) whose noun stands right after it:
    every word agrees with that noun. NOT_MOD when the blank is not like that; None when the sentence does not settle the form."""
    mt = re.match(r"\s*([А-Яа-яЁё-]+)", q[m.end():])
    if not mt:
        return NOT_MOD
    tw = mt.group(1)
    tn = [x for x in M.parse(tw) if x.tag.POS == "NOUN" and _cn(x.tag.case) in CASES and x.tag.number]
    if not tn:
        return NOT_MOD
    # an adjective in the sentence's own word order: a noun beside the blank that the words can agree with
    cands = []
    for x in tn:
        c, n = _cn(x.tag.case), x.tag.number
        if want and c not in want:
            continue
        if num and n != num:
            continue
        reads = []
        for a, h in zip(aw, hw):
            rs = [p for p in M.parse(a) if p.tag.POS in ("ADJF", "PRTF", "NPRO", "NUMR") and lemma_ok(p, h) and _cn(p.tag.case) == c and p.tag.number == n
                  and (n == "plur" or not x.tag.gender or p.tag.gender == x.tag.gender)]
            if not rs:
                break
            reads.append(rs[0])
        else:
            cands.append((c, n, x, reads))
    if not cands:
        return NOT_MOD
    keys = {(c, n) for c, n, _, _ in cands}
    if len(keys) > 1:
        if pair and pair in keys:
            cands = [t for t in cands if (t[0], t[1]) == pair]
        else:
            return None
    case, number, x, reads = cands[0]
    gender = x.tag.gender if number == "sing" else None
    g_en = (" " + {"masc": "m.", "femn": "f.", "neut": "n."}.get(gender, "")) if gender else ""
    label = "%s %s%s" % (CASE_EN[case], "sg." if number == "sing" else "pl.", g_en)
    hintw = [(p.normal_form[:1].upper() + p.normal_form[1:]) if h[:1].isupper() else p.normal_form for p, h in zip(reads, hw)]
    newq = q[:m.start()] + "___ (" + " ".join(hintw) + ", " + label + ")" + q[m.end():]
    parts, rules, decls = [], [], []
    for p, a in zip(reads, aw):
        head, bits, rl = explain_adj(p, a, case, number, gender, x.tag.animacy, tw)
        parts.append(head + " " + " ".join(bits))
        for r in rl:
            if r not in rules:
                rules.append(r)
        if not _DERIVED and not bits[0].startswith("«") and "pronoun-type" not in bits[0]:
            par = paradigm(p)
            pl_line = adj_forms(par, "plur", None)
            if number == "plur" or not gender:
                decls.append("Declension of %s (plural): %s." % (p.normal_form, pl_line))
            else:
                decls.append("Declension of %s (%s): %s; plural: %s." % (p.normal_form, {"masc": "m.", "femn": "f.", "neut": "n."}[gender], adj_forms(par, "sing", gender), pl_line))
    why = "  ".join(parts) + "  " + "  ".join(decls) + "  " + "  ".join(rules) + "  — Model words and rules from the DLI Grammar Reference Book; " + DICT + "."
    _check(e, pair, case, number)
    return newq, why


def _check(e, pair, case, number):
    """Independent cross-check of the course's case against the sentence (preposition, agreeing words)."""
    if pair and pair != "invariant" and pair != (case, number):
        e["_conflict"] = True
        CONFLICTS.append((e.get("q"), (e.get("answers") or [""])[0], (case, number), pair))


def strip_label(q):
    return re.sub(r"(___ \([^)]*?),\s*(?:nom|gen|dat|acc|instr|prep)\.\s*(?:sg|pl)\.(?:\s*[mfn]\.)?\)", r"\1)", q)


def rewrite(e, want_cases=(), mixed=False):
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
    num = None
    pair = resolve_pair(q, m, aw, hw)
    if pair == "invariant":
        newq = q[:m.start()] + "___ (" + hint + ")" + q[m.end():]
        why = ("**%s** (and «его», «их») is the same in every case and number: it does not agree with the noun it belongs to, unlike «мой», «наш». "
               "Only the noun changes with its case." % aw[-1].lower())
        return newq, why
    if mixed:
        # the course does not fix the case: it must come from the sentence, or no case is claimed at all
        if pair is None:
            mod = modifier_path(e, q, m, aw, hw, want, None, None)
            if mod is NOT_MOD or mod is None:
                return None
            return mod
        want, num = {pair[0]}, pair[1]
    pc = PREP_CASE.get(prep)
    if pc and (not want or pc in want):
        want = {pc}
    mod = modifier_path(e, q, m, aw, hw, want, num, pair)
    if mod is not NOT_MOD:
        return mod
    # the noun of the phrase (the last noun), then its modifiers in the noun's case
    parses = []
    for h, a in zip(hw, aw):
        p = best_parse(a, h, {"NOUN", "ADJF", "PRTF", "NPRO", "NUMR"}, want, num)
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
        _check(e, pair, case, number)
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
                    if (x.tag.case in want or not want) and (not num or x.tag.number == num):
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
        if _DERIVED:
            return newq, head + " " + " ".join(bits) + "  " + "  ".join(rules) + "  — Rules from the DLI Grammar Reference Book; " + DICT + "."
        pl_line = adj_forms(par, "plur", None)
        if number == "plur" or not gender:
            decl = "Declension (plural): %s." % pl_line
        else:
            decl = "Declension (%s): %s; plural: %s." % ({"masc": "m.", "femn": "f.", "neut": "n."}[gender],
                   adj_forms(par, "sing", gender), pl_line)
        why = head + " " + " ".join(bits) + "  " + decl + "  " + "  ".join(rules) + "  — Model words and rules from the DLI Grammar Reference Book; " + DICT + "."
        _check(e, pair, case, number)
        return newq, why
    if not nouns:
        return None
    ni = nouns[-1]
    pn = parses[ni]
    case, number = pn.tag.case, pn.tag.number
    for i, p in enumerate(parses):
        if i != ni and p.tag.case != case:
            alt = best_parse(aw[i], hw[i], {p.tag.POS}, {case}, number)
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
        head = head.replace("**" + pa.normal_form + " →", "**" + dict_forms[ni] + " →", 1)   # the word as the hint shows it (мороженое, not мороженый)
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
    _check(e, pair, case, number)
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
            dropped = []
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
                mixed = cid == "cases" and re.match(r"k(1|6|8|9|10|11)-", fn) is not None
                r = rewrite(e, set() if mixed else want, mixed)
                if not r:
                    st["left"] += 1
                    if not mixed:
                        print("  left:", cid, e.get("q"), e.get("answers"))
                        if e.get("why"):
                            e["why"] = ""          # an explanation nobody has verified is worse than none
                            changed = True
                    if mixed:
                        # no case can be read from the sentence: no label, no explanation, rather than a guess
                        nq = strip_label(e.get("q") or "")
                        if nq != e.get("q") or e.get("why"):
                            e["q"], e["why"] = nq, ""
                            changed = True
                        st["unlabelled"] += 1
                    continue
                newq, why = r
                if e.pop("_conflict", False) and not mixed:
                    # the sentence puts the word in another case than the course: «Что за вздор…» is nominative, not accusative
                    dropped.append(e)
                    st["dropped"] += 1
                    continue
                if e.get("q") != newq or e.get("why") != why:
                    e["q"], e["why"] = newq, why
                    changed = True
                st["explained"] += 1
                if len(samples) < 6 and st["explained"] % 400 == 1:
                    samples.append((cid, newq, e["answers"][0], why[:420]))
            if dropped:
                doc["exercises"] = [x for x in doc["exercises"] if not any(x is d_ for d_ in dropped)]
                changed = True
            if changed and a.apply:
                io.open(p, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False))
    print("case_explain:", dict(st))
    print("conflicts between the course's case and the sentence:", len(CONFLICTS))
    for c in CONFLICTS[:40]:
        print("   ", c)
    for s in samples:
        print(" ", s[0], "|", s[1], "→", s[2]); print("    ", s[3]); print()


if __name__ == "__main__":
    main()
