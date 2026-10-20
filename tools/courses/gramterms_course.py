# -*- coding: utf-8 -*-
"""Grammar in Russian — the terms: падеж, существительное, совершенный вид…

A student who knows what a genitive is still cannot read a Russian dictionary
or a Russian grammar until the words for these things are familiar. This
course teaches the terms through real Russian text that uses them.

Sources — and only these:
  * the Russian Wikipedia's article on each term (CC BY-SA 4.0), fetched by
    tools/courses/gramterms_fetch.py into gramterms_src.json: every lesson
    quotes the article's own opening sentence as the term's definition, and
    every sentence exercise is a sentence of an article with the term blanked;
  * sentences from the library's public-domain books that use a term;
  * the OpenCorpora dictionary's own abbreviations for the categories (the
    ones pymorphy3 prints), for the table of how a dictionary writes them.
The list of terms, their English and the article each comes from (TERMS,
GROUPS below) is the course's only editorial content.
"""
import io, json, os, random, re

from kit import SEC, P, H, NOTE, T, FILL

HERE = os.path.dirname(os.path.abspath(__file__))

# term → English; the Wikipedia article(s) to try, first that exists wins;
# `also`: shorter or other spellings of the term accepted as the answer.
TERMS = {
    # the field itself
    "грамматика": {"en": "grammar", "articles": ["Грамматика"]},
    "морфология": {"en": "morphology", "articles": ["Морфология (лингвистика)"]},
    "синтаксис": {"en": "syntax", "articles": ["Синтаксис"]},
    "орфография": {"en": "spelling, orthography", "articles": ["Орфография"]},
    "пунктуация": {"en": "punctuation", "articles": ["Пунктуация"]},
    "лексика": {"en": "vocabulary, lexis", "articles": ["Лексика"]},
    "ударение": {"en": "stress", "articles": ["Ударение"]},
    # parts of speech
    "часть речи": {"en": "part of speech", "articles": ["Часть речи", "Части речи"]},
    "имя существительное": {"en": "noun", "articles": ["Имя существительное"], "also": ["существительное"]},
    "имя прилагательное": {"en": "adjective", "articles": ["Имя прилагательное"], "also": ["прилагательное"]},
    "глагол": {"en": "verb", "articles": ["Глагол"]},
    "наречие": {"en": "adverb", "articles": ["Наречие"]},
    "местоимение": {"en": "pronoun", "articles": ["Местоимение"]},
    "имя числительное": {"en": "numeral", "articles": ["Имя числительное"], "also": ["числительное"]},
    "предлог": {"en": "preposition", "articles": ["Предлог"]},
    "союз": {"en": "conjunction", "articles": ["Союз (часть речи)", "Союз (лингвистика)"]},
    "частица": {"en": "particle", "articles": ["Частица (часть речи)", "Частица (лингвистика)"]},
    "междометие": {"en": "interjection", "articles": ["Междометие"]},
    "причастие": {"en": "participle", "articles": ["Причастие (лингвистика)"]},
    "деепричастие": {"en": "verbal adverb, gerund", "articles": ["Деепричастие"]},
    # the cases
    "падеж": {"en": "case", "articles": ["Падеж"]},
    "именительный падеж": {"en": "nominative case", "articles": ["Именительный падеж"], "also": ["именительный"]},
    "родительный падеж": {"en": "genitive case", "articles": ["Родительный падеж"], "also": ["родительный"]},
    "дательный падеж": {"en": "dative case", "articles": ["Дательный падеж"], "also": ["дательный"]},
    "винительный падеж": {"en": "accusative case", "articles": ["Винительный падеж"], "also": ["винительный"]},
    "творительный падеж": {"en": "instrumental case", "articles": ["Творительный падеж"], "also": ["творительный"]},
    "предложный падеж": {"en": "prepositional case", "articles": ["Предложный падеж"], "also": ["предложный"]},
    "склонение": {"en": "declension", "articles": ["Склонение (лингвистика)", "Склонение"]},
    # the noun's categories
    "род": {"en": "gender", "articles": ["Род (лингвистика)"]},
    "мужской род": {"en": "masculine gender", "articles": ["Род (лингвистика)"], "also": ["мужской"]},
    "женский род": {"en": "feminine gender", "articles": ["Род (лингвистика)"], "also": ["женский"]},
    "средний род": {"en": "neuter gender", "articles": ["Род (лингвистика)"], "also": ["средний"]},
    "число": {"en": "number: singular or plural", "articles": ["Число (лингвистика)", "Грамматическое число"]},
    "единственное число": {"en": "singular", "articles": ["Единственное число"], "also": ["единственное"]},
    "множественное число": {"en": "plural", "articles": ["Множественное число"], "also": ["множественное"]},
    "одушевлённость": {"en": "animacy", "articles": ["Одушевлённость"], "also": ["одушевленность"]},
    "окончание": {"en": "ending", "articles": ["Окончание (лингвистика)", "Флексия"]},
    "основа": {"en": "stem", "articles": ["Основа (лингвистика)", "Основа слова"]},
    "корень": {"en": "root", "articles": ["Корень (лингвистика)", "Корень слова"]},
    "приставка": {"en": "prefix", "articles": ["Приставка (лингвистика)", "Префикс"]},
    "суффикс": {"en": "suffix", "articles": ["Суффикс"]},
    # the verb's categories
    "вид": {"en": "aspect", "articles": ["Вид (лингвистика)", "Глагольный вид"]},
    "совершенный вид": {"en": "perfective aspect", "articles": ["Вид (лингвистика)", "Глагольный вид"], "also": ["совершенный"]},
    "несовершенный вид": {"en": "imperfective aspect", "articles": ["Вид (лингвистика)", "Глагольный вид"], "also": ["несовершенный"]},
    "время": {"en": "tense", "articles": ["Время (лингвистика)", "Грамматическое время"]},
    "настоящее время": {"en": "present tense", "articles": ["Настоящее время"], "also": ["настоящее"]},
    "прошедшее время": {"en": "past tense", "articles": ["Прошедшее время"], "also": ["прошедшее"]},
    "будущее время": {"en": "future tense", "articles": ["Будущее время"], "also": ["будущее"]},
    "лицо": {"en": "person: 1st, 2nd, 3rd", "articles": ["Лицо (лингвистика)", "Грамматическое лицо"]},
    "наклонение": {"en": "mood", "articles": ["Наклонение (лингвистика)", "Наклонение"]},
    "изъявительное наклонение": {"en": "indicative mood", "articles": ["Изъявительное наклонение"], "also": ["изъявительное"]},
    "повелительное наклонение": {"en": "imperative mood", "articles": ["Повелительное наклонение"], "also": ["повелительное"]},
    "сослагательное наклонение": {"en": "subjunctive or conditional mood", "articles": ["Сослагательное наклонение"], "also": ["сослагательное", "условное наклонение", "условное"]},
    "залог": {"en": "voice: active or passive", "articles": ["Залог (лингвистика)"]},
    "действительный залог": {"en": "active voice", "articles": ["Действительный залог"], "also": ["действительный"]},
    "страдательный залог": {"en": "passive voice", "articles": ["Страдательный залог"], "also": ["страдательный"]},
    "спряжение": {"en": "conjugation", "articles": ["Спряжение"]},
    "инфинитив": {"en": "infinitive", "articles": ["Инфинитив"], "also": ["неопределённая форма", "неопределенная форма"]},
    "возвратный глагол": {"en": "reflexive verb", "articles": ["Возвратный глагол"], "also": ["возвратный"]},
    "переходный глагол": {"en": "transitive verb", "articles": ["Переходность", "Переходный глагол"], "also": ["переходный"]},
    # the adjective
    "степень сравнения": {"en": "degree of comparison", "articles": ["Степени сравнения"], "also": ["степени сравнения"]},
    "сравнительная степень": {"en": "comparative", "articles": ["Сравнительная степень"], "also": ["сравнительная"]},
    "превосходная степень": {"en": "superlative", "articles": ["Превосходная степень"], "also": ["превосходная"]},
    "краткая форма": {"en": "short form of an adjective", "articles": ["Краткое прилагательное", "Краткая форма прилагательного"], "also": ["краткая"]},
    # the sentence
    "предложение": {"en": "sentence", "articles": ["Предложение (лингвистика)"]},
    "словосочетание": {"en": "word group, phrase", "articles": ["Словосочетание"]},
    "подлежащее": {"en": "subject", "articles": ["Подлежащее"]},
    "сказуемое": {"en": "predicate", "articles": ["Сказуемое"]},
    "дополнение": {"en": "object", "articles": ["Дополнение (лингвистика)", "Дополнение (синтаксис)"]},
    "определение": {"en": "attribute, modifier", "articles": ["Определение (лингвистика)", "Определение (синтаксис)"]},
    "обстоятельство": {"en": "adverbial", "articles": ["Обстоятельство (лингвистика)", "Обстоятельство (синтаксис)"]},
    # sounds and letters
    "гласный": {"en": "vowel", "articles": ["Гласные"], "also": ["гласный звук", "гласная"]},
    "согласный": {"en": "consonant", "articles": ["Согласные"], "also": ["согласный звук", "согласная"]},
    "слог": {"en": "syllable", "articles": ["Слог"]},
    "буква": {"en": "letter", "articles": ["Буква"]},
    "алфавит": {"en": "alphabet", "articles": ["Русский алфавит", "Алфавит"]},
    "твёрдый знак": {"en": "hard sign, ъ", "articles": ["Ъ (кириллица)", "Ъ"], "also": ["твердый знак"]},
    "мягкий знак": {"en": "soft sign, ь", "articles": ["Ь (кириллица)", "Ь"]},
}

GROUPS = [
    {"id": "gt1-field", "title": "Grammar, morphology, syntax",
     "terms": ["грамматика", "морфология", "синтаксис", "орфография", "пунктуация", "лексика", "ударение"]},
    {"id": "gt2-parts", "title": "The parts of speech",
     "terms": ["часть речи", "имя существительное", "имя прилагательное", "глагол", "наречие", "местоимение",
               "имя числительное", "предлог", "союз", "частица", "междометие", "причастие", "деепричастие"]},
    {"id": "gt3-cases", "title": "The cases",
     "terms": ["падеж", "именительный падеж", "родительный падеж", "дательный падеж", "винительный падеж",
               "творительный падеж", "предложный падеж", "склонение"]},
    {"id": "gt4-noun", "title": "Gender, number, animacy; the parts of a word",
     "terms": ["род", "мужской род", "женский род", "средний род", "число", "единственное число", "множественное число",
               "одушевлённость", "окончание", "основа", "корень", "приставка", "суффикс"]},
    {"id": "gt5-verb", "title": "The verb: aspect, tense, person, mood, voice",
     "terms": ["вид", "совершенный вид", "несовершенный вид", "время", "настоящее время", "прошедшее время", "будущее время",
               "лицо", "наклонение", "изъявительное наклонение", "повелительное наклонение", "сослагательное наклонение",
               "залог", "действительный залог", "страдательный залог", "спряжение", "инфинитив", "возвратный глагол",
               "переходный глагол"]},
    {"id": "gt6-adj", "title": "The adjective: degrees of comparison, the short form",
     "terms": ["степень сравнения", "сравнительная степень", "превосходная степень", "краткая форма"]},
    {"id": "gt7-sentence", "title": "The sentence and its parts",
     "terms": ["предложение", "словосочетание", "подлежащее", "сказуемое", "дополнение", "определение", "обстоятельство"]},
    {"id": "gt8-letters", "title": "Sounds and letters",
     "terms": ["гласный", "согласный", "слог", "буква", "алфавит", "твёрдый знак", "мягкий знак"]},
]

# Terms that mean nothing but the grammatical thing, so a sentence from any
# article — or from a novel — that uses them is about grammar. «время»,
# «лицо», «род», «число», «вид», «союз», «предлог», «корень», «окончание»… are
# not: those are taken only from their own article, where every «время» is a
# tense.
# In a grammar article — any article the course fetched — these can mean
# nothing else. Not the tenses: «в настоящее время» is "at present" on any
# page; not «наречие» (a dialect) or «подлежащее» (the participle: «не
# подлежащее склонению»).
SAFE_IN_WIKI = {
    "грамматика", "морфология", "синтаксис", "орфография", "пунктуация", "имя существительное", "имя прилагательное",
    "местоимение", "имя числительное", "междометие", "причастие", "деепричастие", "падеж",
    "именительный падеж", "родительный падеж", "дательный падеж", "винительный падеж", "творительный падеж",
    "предложный падеж", "склонение", "спряжение", "инфинитив", "суффикс", "сказуемое",
    "совершенный вид", "несовершенный вид",
    "изъявительное наклонение", "повелительное наклонение", "сослагательное наклонение", "страдательный залог",
    "действительный залог", "возвратный глагол", "переходный глагол", "сравнительная степень", "превосходная степень",
    "степень сравнения", "мужской род", "женский род", "средний род", "единственное число", "множественное число",
    "одушевлённость", "словосочетание", "твёрдый знак", "мягкий знак", "алфавит", "существительное", "прилагательное",
    "числительное",
}
# In a novel, fewer still: there «причастие» is Communion, «склонение» a
# slope, and «падеж» without its ё can be a cattle plague.
SAFE_IN_PROSE = SAFE_IN_WIKI - {"причастие", "склонение", "падеж"}
TENSES = {"настоящее время", "прошедшее время", "будущее время"}


def adverbial_time(s, a, b, term):
    """«в настоящее время», «до настоящего времени»: the phrase "at present",
    not the tense — the tense is «в настоящем времени» or «форма настоящего
    времени». Judged on the whole phrase in the text, whichever part of it
    was matched."""
    if term not in TENSES:
        return False
    m = re.match(r"(настоящ|прошедш|будущ)\S*\s+врем\S*", s[a:].lower().replace("\u0301", ""))
    if not m:
        return False
    phrase = m.group(0).rstrip(".,;:!?»)")
    before = s[:a].rstrip().lower()
    if phrase.endswith("время") and re.search(r"(^|[\s(«„])(в|во)$", before):
        return True
    if re.search(r"(^|[\s(«„])(до|с|со|по|к|ко)$", before):
        return True
    return False


# OpenCorpora's own abbreviations (the ones pymorphy3 prints), for the table
# of how a dictionary writes the categories.
ABBR = [("NOUN", "имя существительное"), ("ADJF", "имя прилагательное"), ("ADJS", "краткая форма"), ("COMP", "сравнительная степень"),
        ("VERB", "глагол"), ("INFN", "инфинитив"), ("PRTF", "причастие"), ("GRND", "деепричастие"), ("NUMR", "имя числительное"),
        ("ADVB", "наречие"), ("NPRO", "местоимение"), ("PREP", "предлог"), ("CONJ", "союз"), ("PRCL", "частица"), ("INTJ", "междометие"),
        ("anim", "одушевлённость"), ("masc", "мужской род"), ("femn", "женский род"), ("neut", "средний род"),
        ("sing", "единственное число"), ("plur", "множественное число"),
        ("nomn", "именительный падеж"), ("gent", "родительный падеж"), ("datv", "дательный падеж"), ("accs", "винительный падеж"),
        ("ablt", "творительный падеж"), ("loct", "предложный падеж"),
        ("perf", "совершенный вид"), ("impf", "несовершенный вид"), ("tran", "переходный глагол"),
        ("pres", "настоящее время"), ("past", "прошедшее время"), ("futr", "будущее время"),
        ("indc", "изъявительное наклонение"), ("impr", "повелительное наклонение"),
        ("actv", "действительный залог"), ("pssv", "страдательный залог")]

SRC_P = os.path.join(HERE, "gramterms_src.json")
SRC = json.load(io.open(SRC_P, encoding="utf-8")) if os.path.exists(SRC_P) else None

try:
    import pymorphy3
    M = pymorphy3.MorphAnalyzer()
except ImportError:
    M = None

_lem = {}


def lemmas(w):
    w = w.lower().replace("ё", "е")
    if w not in _lem:
        _lem[w] = {p.normal_form.replace("ё", "е") for p in M.parse(w) if p.score > 0.03} | {w} if M else {w}
    return _lem[w]


def term_lemmas(term):
    return [M.parse(w)[0].normal_form.replace("ё", "е") for w in term.split()]


WORD = re.compile(r"[А-Яа-яЁё́]+(?:-[А-Яа-яЁё́]+)?")
ABBREV = {"лат", "греч", "англ", "нем", "фр", "др", "т", "е", "см", "напр", "ср", "букв", "устар", "им", "тж", "сокр",
          "г", "гг", "н", "э", "ст", "рус", "ед", "мн", "ч", "п", "р", "л", "в", "вв", "тыс", "санскр", "ит", "исп", "яз"}


def sentences(text):
    """The prose sentences of an article's plain text: no headings, no lists."""
    out = []
    for para in text.split("\n"):
        para = para.strip()
        if len(para) < 40 or para[-1] not in ".!?»" or para.startswith(("=", "*", "—", "•")):
            continue
        # split on . ! ? before a space and a capital — unless the dot ends an abbreviation
        buf, i = "", 0
        parts = re.split(r"(?<=[.!?»])\s+(?=[А-ЯЁ«])", para)
        for s in parts:
            if buf:
                s = buf + " " + s
                buf = ""
            last = re.findall(r"([А-Яа-яЁё]+)\.$", s)
            if last and last[0].lower() in ABBREV:
                buf = s
                continue
            out.append(s)
        if buf:
            out.append(buf)
    return out


def clean(s):
    return (40 <= len(s) <= 180 and not re.search(r"[\[\]{}|→←≈†<>]|\bсм\. \b|\d{4}", s)
            and s[0].isupper() and s.count("(") == s.count(")") and s.count("«") == s.count("»"))


def find_term(s, term, strict=False):
    """(start, end) of `term` (or one of its shorter spellings) inflected in
    sentence s, or None. `strict`: outside the term's own article only the
    spellings that can mean nothing else («совершенный» alone is "perfect")."""
    ws = list(WORD.finditer(s))
    words = [w.group().replace("́", "") for w in ws]
    spellings = [term] + [a for a in (TERMS.get(term, {}).get("also") or []) if not strict or a in SAFE_IN_WIKI]
    for t in spellings:
        lem = term_lemmas(t)
        for i in range(len(words) - len(lem) + 1):
            if all(lem[k] in lemmas(words[i + k]) for k in range(len(lem))):
                a, b = ws[i].start(), ws[i + len(lem) - 1].end()
                if adverbial_time(s, a, b, term):
                    continue
                return a, b
    return None


def definition(term):
    """The opening sentence of the term's article, and the citation."""
    key = TERMS[term]["articles"][0]
    a = SRC["articles"].get(key) if SRC else None
    if not a:
        return None, None
    first = next((s for s in sentences(a["text"]) if len(s) > 30), None)
    cite = u"Википедия, «%s» (%s, CC BY-SA 4.0)" % (a["title"], a["url"])
    return first, cite


def drill(s, span, term, cite):
    a, b = span
    ans = s[a:b].replace("́", "")
    q = s[:a].replace("́", "") + "___ (%s)" % TERMS[term]["en"] + s[b:].replace("́", "")
    d, dcite = definition(term)
    why = (u"%s — %s" % (d, dcite)) if d else dcite
    return dict(FILL(q, [ans], why=why or "", prompt=u"*%s*" % cite),
                context=u"The term in English is in the brackets. Type it in Russian, in the form the sentence needs.",
                k=term)


SECTIONS = []
if SRC and M:
    A = SECTIONS.append
    rows = []
    cyr = {}
    for lat, term in ABBR:
        try:
            cyr[term] = M.lat2cyr(lat)
        except Exception:
            pass
    for g in GROUPS:
        for t in g["terms"]:
            rows.append([t, TERMS[t]["en"], cyr.get(t, "")])
    A(SEC("gt0-all", "Every term at a glance", [
        P(u"The words a Russian grammar, dictionary or teacher uses for the things this site teaches. Each lesson "
          u"after this page takes a group of them: the definition the Russian Wikipedia gives, then real sentences "
          u"that use the term, with the term left out for you to type."),
        T([u"Term", u"English", u"As the OpenCorpora dictionary abbreviates it"], rows),
        NOTE(u"Definitions and sentences: the Russian Wikipedia (CC BY-SA 4.0), article and revision named with each. "
             u"Abbreviations: the OpenCorpora dictionary (CC BY-SA 4.0), as pymorphy3 prints them. Further sentences from "
             u"the library's public-domain books, with author and title."),
    ]))

    used = set()
    lib = {}
    for x in (SRC.get("library") or []):
        lib.setdefault(x["term"], []).append(x)
    for g in GROUPS:
        blocks = []
        vocab = []
        sent = []
        for t in g["terms"]:
            d, cite = definition(t)
            blocks.append(H(u"%s — %s" % (t, TERMS[t]["en"])))
            if d:
                blocks.append(P(d))
                blocks.append(NOTE(cite))
            vocab.append(dict(FILL(u"___ (%s)" % TERMS[t]["en"], [t] + list(TERMS[t].get("also") or []),
                                   why=(u"%s — %s" % (d, cite)) if d else u"", prompt=u"Write the Russian term."),
                              context=u"The term in English is in the brackets. Type it in Russian.", k=t))
        # sentences: from the term's own article always; from every article, and from the
        # library, when the term can mean nothing else
        pool = []
        for t in g["terms"]:
            own = TERMS[t]["articles"][0]
            arts = SRC["articles"].items() if (t in SAFE_IN_WIKI) else [(own, SRC["articles"][own])] if own in SRC["articles"] else []
            for key, a in arts:
                for s in sentences(a["text"]):
                    if not clean(s) or (s, t) in used:
                        continue
                    span = find_term(s, t, strict=(key != own))
                    if not span:
                        continue
                    used.add((s, t))
                    pool.append(drill(s, span, t, u"Википедия, «%s»" % a["title"]))
            for x in (lib.get(t, []) if t in SAFE_IN_PROSE else []):
                s = x["ru"]
                if (s, t) in used:
                    continue
                span = find_term(s, t, strict=True)
                if not span:
                    continue
                used.add((s, t))
                pool.append(drill(s, span, t, x["src"]))
        random.Random(len(pool)).shuffle(pool)
        A(SEC(g["id"], g["title"], blocks + [NOTE(u"Exercises: first the terms themselves, then sentences from the "
                                                   u"Wikipedia articles named above and from the library's books.")],
              vocab, sub="%d terms" % len(vocab)))
        size = 20
        cut = [pool[i:i + size] for i in range(0, len(pool), size)]
        for n, part in enumerate(cut, 1):
            if len(part) < 5:
                continue
            A(SEC(g["id"] + "-practice" + ("" if n == 1 else "-%d" % n),
                  "Practice%s: %s" % ("" if len(cut) == 1 else " %d" % n, g["title"]),
                  [NOTE(u"Real sentences that use these terms; the source of each is above it. The term is given in "
                        u"English — type it in Russian, in the form the sentence needs.")],
                  part, sub="%d real sentences" % len(part)))
