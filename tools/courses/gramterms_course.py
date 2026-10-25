# -*- coding: utf-8 -*-
"""Grammar in Russian — the terms: падеж, существительное, совершенный вид…

A student who knows what a genitive is still cannot read a Russian dictionary,
follow a Russian grammar, or ask a teacher a question until the Russian words
for these things are familiar. This course is a vocabulary: the fields of
linguistics, the parts of speech, the cases and the categories of the noun,
the verb and the adjective, the parts of the sentence, sounds and letters —
each term with its English and a one-sentence definition — and the drills
that make the words stick. No sentences from books, no Tatoeba: the terms,
their meanings, and the review.

Sources — and only these:
  * the English Wiktionary's sense for each term's English name (CC BY-SA
    4.0) — a dictionary's one-line gloss — and, for a few terms, the opening
    sentence of the English Wikipedia's article (CC BY-SA 4.0): fetched by
    tools/courses/gramterms_en.py into gramterms_en.json, which says which
    page and sense each definition is and where a long one was cut;
  * the OpenCorpora dictionary's own abbreviations for the categories (the
    ones pymorphy3 prints), for the table of how a dictionary writes them.
The list of terms, their English and the article each comes from (TERMS,
GROUPS below) is the course's only editorial content.
"""
import io, json, os, random, re

from kit import SEC, P, H, NOTE, T, FILL, MC

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
     "terms": ["часть речи", "имя существительное", "глагол", "наречие", "местоимение",
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
     "terms": ["имя прилагательное", "степень сравнения", "сравнительная степень", "превосходная степень", "краткая форма"]},
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
# The English definitions (tools/courses/gramterms_en.py): term → {def, source, page, url}
EN_P = os.path.join(HERE, "gramterms_en.json")
EN = json.load(io.open(EN_P, encoding="utf-8")) if os.path.exists(EN_P) else {}

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


# A parenthesis that gives the word's origin or pronunciation — Greek,
# Latin, an IPA transcription — rather than its meaning.
ETYM = re.compile(r"\s*\((?:[^()]*\([^()]*\))*[^()]*\)")


def is_etym(par):
    inner = par.strip()[1:-1]
    return bool(re.search(u"греч|лат[.]|латин|фр[.]|нем[.]|англ[.]|ср[.]-век|[\\[]|[A-Za-z\u0370-\u03ff\u1f00-\u1fff]", inner)) \
        or inner.startswith(u"от ")


def concise(text):
    """The article's first statement as a short definition: the opening
    paragraph (with the list it introduces, when it ends in a colon), its
    etymology in brackets taken out, the first sentence only."""
    lines = [l.strip() for l in text.split("\n")]
    lines = [l for l in lines if l and not l.startswith(("=", "*", "•"))]
    if not lines:
        return None
    # the article's title line, when the dump starts with it
    if len(lines) > 1 and len(lines[0]) < 40 and not lines[0].endswith((".", ":")):
        lines = lines[1:]
    first = lines[0]
    if len(first) >= 2 and first.endswith(":"):
        items = []
        for l in lines[1:6]:
            items.append(l.rstrip(";.").strip())
            if l.endswith("."):
                break
        first = first + " " + u"; ".join(items) + "."
    # etymologies, inside and outside the subject
    prev = None
    while prev != first:
        prev = first
        first = ETYM.sub(lambda m: "" if is_etym(m.group(0)) else m.group(0), first)
    first = re.sub(r"\s+", " ", first).replace(" ,", ",").strip()
    # the first sentence — a full stop or question mark inside «…» does not end it
    for m in re.finditer(r"(?<=[.!?»])\s+(?=[А-ЯЁ«])", first):
        head = first[:m.start()]
        if head.count(u"«") == head.count(u"»") and head.count("(") == head.count(")"):
            first = head
            break
    # a long one cut at a clause, so it reads as a definition and not an article
    if len(first) > 230:
        k = max(first.rfind(u"; ", 0, 230), first.rfind(u", ", 0, 230))
        if k > 90:
            cut = first[:k].rstrip(",;")
            if cut.count("(") > cut.count(")"):
                cut = cut[:cut.rfind("(")].rstrip(" ,;")
            first = cut + u"…"
    return first or None


def definition(term):
    """The term's definition in English — the Wiktionary's sense for its
    English name, or an English Wikipedia opening sentence — and the citation."""
    e = EN.get(term)
    if not e:
        return None, None
    if e["source"] == "wiktionary":
        cite = u"Wiktionary, \u00ab%s\u00bb (%s, CC BY-SA 4.0)" % (e["page"], e["url"])
    else:
        cite = u"Wikipedia, \u00ab%s\u00bb (%s, CC BY-SA 4.0)" % (e["page"], e["url"].replace("(", "%28").replace(")", "%29"))
    return e["def"], cite


def masked(term, d):
    """The definition with the term's own English name blanked, for the
    which-term quiz: «The … gender» for мужской род."""
    words = [w for w in re.split(r"[ ,:;]+", TERMS[term]["en"].lower()) if len(w) > 3 and w not in ("case", "tense", "mood", "voice", "gender", "form", "verb", "word")]
    out = d
    for w in words:
        out = re.sub(r"(?i)\b" + re.escape(w) + r"\w*", u"\u2026", out)
    return out


def ru_definition(term):
    """The Russian Wikipedia's opening statement — kept for reference, unused by the course."""
    key = TERMS[term]["articles"][0]
    a = SRC["articles"].get(key) if SRC else None
    if not a:
        return None, None
    first = concise(a["text"])
    if not first or len(first) < 30:
        first = next((s for s in sentences(a["text"]) if len(s) > 30), None)
    # the address with its brackets encoded, so the app's citation link can
    # take it apart: «Морфология (лингвистика)» has them in its title too
    url = a["url"].replace("(", "%28").replace(")", "%29")
    cite = u"Википедия, «%s» (%s, CC BY-SA 4.0)" % (a["title"], url)
    return first, cite


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
    # The cards the review drill deals: every term with its English, and the
    # dictionary's abbreviation where there is one (lib/kit: `terms` on a
    # section is passed through to the section's JSON).
    card = lambda t: {"ru": t, "en": TERMS[t]["en"], "abbr": cyr.get(t, ""), "def": (definition(t)[0] or "")}
    for g in GROUPS:
        for t in g["terms"]:
            rows.append([t, TERMS[t]["en"], cyr.get(t, "")])
    A(dict(SEC("gt0-all", "Every term at a glance", [
        P(u"The words a Russian grammar, a dictionary or a teacher uses for the things this site teaches — the "
          u"vocabulary you need to ask a question about Russian in Russian. Each lesson after this page takes a "
          u"group of them: the term, its English, and a one-line English definition from the dictionary; then "
          u"which term each definition is of. Review Terms drills the whole list \u2014 here, and from the Vocabulary tab."),
        T([u"Term", u"English", u"As the OpenCorpora dictionary abbreviates it"], rows),
        NOTE(u"Definitions: the English Wiktionary, and for a few terms the English Wikipedia (both CC BY-SA 4.0), "
             u"the page named with each. Abbreviations: the OpenCorpora dictionary (CC BY-SA 4.0), as pymorphy3 prints them."),
    ]), terms=[card(t) for g in GROUPS for t in g["terms"]]))

    for g in GROUPS:
        blocks = []
        vocab = []
        for t in g["terms"]:
            d, cite = definition(t)
            blocks.append(H(u"%s — %s" % (t, TERMS[t]["en"])))
            if d:
                blocks.append(P(d))
                blocks.append(NOTE(cite))
            vocab.append(t)
        # The exercises: which term does this definition describe — the
        # definition with the term's own name blanked, the group's terms to
        # choose from.
        rng = random.Random(g["id"])
        mcs = []
        for t in g["terms"]:
            d, cite = definition(t)
            if not d or len(g["terms"]) < 4:
                continue
            mask = masked(t, d)
            others = [x for x in g["terms"] if x != t]
            rng.shuffle(others)
            opts = [t] + others[:3]
            rng.shuffle(opts)
            mcs.append(dict(MC(u"Which term is this the definition of?", opts, opts.index(t),
                               why=u"%s \u2014 %s" % (d, cite), ru=mask), k=t, keep=True,
                            context=u"The definition is the dictionary's, in English, with the term's own name left out."))
        A(dict(SEC(g["id"], g["title"], blocks + [NOTE(u"Exercises: which term each definition is of. Review Terms, at the "
                                                        u"foot of the page, drills this module's terms.")],
                   mcs, sub="%d terms" % len(vocab)),
               terms=[card(t) for t in g["terms"]]))
