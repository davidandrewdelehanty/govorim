#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The grammar terms' English definitions, for the Terms course.

Each Russian term gets one short English definition: the English Wiktionary's
sense for the term's English name (CC BY-SA 4.0) — a dictionary's one-line
gloss, not an encyclopedia's paragraph — and, for the few terms whose
Wiktionary sense is a stub or a thicket, the opening sentence of the English
Wikipedia's article (CC BY-SA 4.0). MAP below is the editorial content: which
headword, which sense, and where a long sense is cut (a cut inside a sentence
is marked with …). Nothing is written here; every definition is quoted, and
the lesson cites its page.

    python3 tools/courses/gramterms_en.py            # fetch and write gramterms_en.json
    python3 tools/courses/gramterms_en.py --raw f    # from a saved dump of the senses
"""
import io, json, os, re, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "gramterms_en.json")
WIKT = "https://en.wiktionary.org/w/api.php"
WP = "https://en.wikipedia.org/api/rest_v1/page/summary/"
UA = "govorim-courses/1.0 (https://govorim.dev; grammar-terms course)"

# term → (source, page, sense, cut)
#   source "wikt": the English Wiktionary page; `sense` is the 0-based index
#   among the page's English senses labelled grammar/linguistics/phonetics
#   (or, with no such label, the first senses); `cut` is a regex at which the
#   sentence is cut, or None for the first sentence whole.
#   source "wp": the English Wikipedia article's first sentence.
MAP = {
    "грамматика": ("wikt", "grammar", 0, None),
    "морфология": ("wikt", "morphology", 0, None),
    "синтаксис": ("wikt", "syntax", 0, None),
    "орфография": ("wikt", "orthography", 0, r";"),
    "пунктуация": ("wikt", "punctuation", 0, r";"),
    "лексика": ("wikt", "lexis", 0, None),
    "ударение": ("wp", "Stress (linguistics)", 0, None),
    "часть речи": ("wikt", "part of speech", 0, None),
    "имя существительное": ("wikt", "noun", 0, r":"),
    "имя прилагательное": ("wikt", "adjective", 0, None),
    "глагол": ("wikt", "verb", 0, None),
    "наречие": ("wikt", "adverb", 0, None),
    "местоимение": ("wp", "Pronoun", 0, None),
    "имя числительное": ("wikt", "numeral", 0, None),
    "предлог": ("wikt", "preposition", 0, r":"),
    "союз": ("wikt", "conjunction", 0, None),
    "частица": ("wikt", "particle", 0, r":"),
    "междометие": ("wikt", "interjection", 0, r";"),
    "причастие": ("wikt", "participle", 0, None),
    "деепричастие": ("wikt", "adverbial participle", 0, None),
    "падеж": ("wikt", "case", 0, None),
    "именительный падеж": ("wikt", "nominative case", 0, None),
    "родительный падеж": ("wikt", "genitive case", 0, None),
    "дательный падеж": ("wikt", "dative case", 0, r", and is generally"),
    "винительный падеж": ("wikt", "accusative case", 0, None),
    "творительный падеж": ("wikt", "instrumental case", 0, r"—and is"),
    "предложный падеж": ("wikt", "prepositional case", 0, None),
    "склонение": ("wikt", "declension", 2, None),
    "род": ("wikt", "gender", 0, None),
    "мужской род": ("wikt", "masculine", 0, None),
    "женский род": ("wikt", "feminine", 0, None),
    "средний род": ("wikt", "neuter", 0, r";"),
    "число": ("wikt", "number", 0, None),
    "единственное число": ("wikt", "singular", 1, None),
    "множественное число": ("wikt", "plural", 2, r";"),
    "одушевлённость": ("wikt", "animacy", 0, r" \(it can"),
    "окончание": ("wikt", "ending", 0, None),
    "основа": ("wikt", "stem", 0, None),
    "корень": ("wikt", "root", 0, None),
    "приставка": ("wikt", "prefix", 0, r", for example"),
    "суффикс": ("wikt", "suffix", 0, None),
    "вид": ("wp", "Grammatical aspect", 0, None),
    "совершенный вид": ("wp", "Perfective aspect", 0, r", i\.e\."),
    "несовершенный вид": ("wp", "Imperfective aspect", 0, None),
    "время": ("wikt", "tense", 0, None),
    "настоящее время": ("wikt", "present tense", 0, None),
    "прошедшее время": ("wp", "Past tense", 0, None),
    "будущее время": ("wikt", "future tense", 0, None),
    "лицо": ("wikt", "person", 0, None),
    "наклонение": ("wikt", "mood", 0, None),
    "изъявительное наклонение": ("wikt", "indicative mood", 0, None),
    "повелительное наклонение": ("wikt", "imperative mood", 0, None),
    "сослагательное наклонение": ("wikt", "subjunctive mood", 0, None),
    "залог": ("wikt", "voice", 1, None),
    "действительный залог": ("wikt", "active voice", 0, None),
    "страдательный залог": ("wikt", "passive voice", 0, None),
    "спряжение": ("wikt", "conjugation", 1, None),
    "инфинитив": ("wikt", "infinitive", 1, None),
    "возвратный глагол": ("wikt", "reflexive verb", 0, None),
    "переходный глагол": ("wikt", "transitive verb", 0, None),
    "степень сравнения": ("wikt", "degree of comparison", 0, None),
    "сравнительная степень": ("wikt", "comparative", 0, None),
    "превосходная степень": ("wikt", "superlative", 1, None),
    "краткая форма": ("wikt", "short form", 1, None),
    "предложение": ("wikt", "sentence", 0, None),
    "словосочетание": ("wikt", "phrase", 0, r", always containing"),
    "подлежащее": ("wikt", "subject", 0, None),
    "сказуемое": ("wikt", "predicate", 0, None),
    "дополнение": ("wikt", "object", 0, None),
    "определение": ("wikt", "attribute", 0, None),
    "обстоятельство": ("wp", "Adverbial", 0, None),
    "гласный": ("wikt", "vowel", 0, None),
    "согласный": ("wikt", "consonant", 0, r";"),
    "слог": ("wikt", "syllable", 0, None),
    "буква": ("wikt", "letter", 0, None),
    "алфавит": ("wikt", "alphabet", 0, None),
    "твёрдый знак": ("wikt", "hard sign", 0, None),
    "мягкий знак": ("wikt", "soft sign", 0, None),
}
# the second sentence is the plain one: kept with the first
TWO_SENTENCES = {"дополнение"}
# an aside inside the sentence, taken out
DROP = {"мягкий знак": r" \(transliterated.*?\)\)"}

LABEL = re.compile(r"\{\{lb\|en\|[^}]*\b(grammar|grammatical case|linguistics|phonetics|phonology|orthography|linguistic morphology)\b", re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def wikt_senses(page):
    """The page's English senses: (part of speech, wikitext of the sense)."""
    q = urllib.parse.urlencode({"action": "query", "format": "json", "formatversion": "2", "prop": "revisions",
                                "rvprop": "content", "rvslots": "main", "titles": page})
    d = fetch(WIKT + "?" + q)
    pg = d["query"]["pages"][0]
    if pg.get("missing"):
        return []
    text = pg["revisions"][0]["slots"]["main"]["content"]
    m = re.search(r"==English==([\s\S]*?)(?:\n==[^=]|$)", text)
    out, pos = [], ""
    for ln in (m.group(1) if m else "").split("\n"):
        h = re.match(r"^===+\s*([^=]+?)\s*===+$", ln)
        if h:
            pos = h.group(1)
            continue
        if re.match(r"^#+ ", ln):
            out.append(pos + "\t" + re.sub(r"^#+ ", "", ln))
    return out


def labelled(senses):
    g = [s for s in senses if LABEL.search(s) and clean(s)]
    return g if g else [s for s in senses if clean(s)][:3]


def tmpl_word(inner):
    """{{l|en|inflection|inflections}} → inflections; {{m|en|-'s}} → -'s;
    {{l|mul|sc=Cyrl|Ъ}} → Ъ: the last positional parameter."""
    parts = [p for p in inner.split("|")[1:] if "=" not in p]
    return parts[-1] if parts else ""


def clean(wt):
    s = wt.split("\t", 1)[1] if "\t" in wt else wt
    s = re.sub(r"<!--[\s\S]*?-->", "", s)
    s = re.sub(r"\{\{(?:lb|senseid|sid|defdate|qualifier|1)\|[^{}]*\}\}", "", s)
    s = re.sub(r"\{\{(?:n-g|ng)\|([^{}]*)\}\}", r"\1", s)
    s = re.sub(r"\{\{,\}\}", ",", s)
    s = re.sub(r"\{\{(?:l|m|w)\|([^{}]*)\}\}", lambda m: tmpl_word("x|" + m.group(1)) if not m.group(0).startswith("{{w|") else m.group(1).split("|")[-1], s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    s = s.replace("'''", "").replace("''", "")
    s = re.sub(r"^\s*:\s*", "", s)
    s = re.sub(r"\s+", " ", s).replace(" ,", ",").replace("( ", "(").replace(" )", ")").strip()
    return s


def first_sentences(s, n=1):
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", s)
    return " ".join(parts[:n]).strip()


def shape(s, cut, n=1, drop=None, subject=False):
    if drop:
        s = re.sub(drop, "", s)
    s = first_sentences(s, n)
    # an encyclopedia's "A pronoun is a word…": the definition is what follows "is"
    if subject:
        s = re.sub(r"^(?:In [^,]+(?:, and particularly [^,]+)?, )?(?:the |an? )?[A-Za-z][\w\- ]*?(?:, sometimes called [^,]+,)? (?:is|are) (?=an? |the )", "", s, count=1)
    if cut:
        m = re.search(cut, s)
        if m:
            head = s[:m.start()].rstrip(" ,;:")
            # a bracket opened before the cut is closed by it
            if head.count("(") > head.count(")"):
                head = head[:head.rfind("(")].rstrip(" ,;:")
            s = head + "."
    # an opening that says only where the term is used, not what it is
    s = re.sub(r"^(?:In (?:English and other modern languages|some languages|linguistics, and particularly phonology|linguistics and grammar|linguistics|English grammar|grammar)),\s*", "", s)
    s = s[0].upper() + s[1:] if s else s
    if not s.endswith((".", "!", "?")):
        s += "."
    return s


def build(raw):
    out = {}
    for term, (src, page, idx, cut) in MAP.items():
        n = 2 if term in TWO_SENTENCES else 1
        if src == "wikt":
            senses = raw[page] if raw and page in raw else wikt_senses(page)
            pick = labelled(senses)
            if idx >= len(pick):
                print("no sense %d for %s" % (idx, page), file=sys.stderr)
                continue
            d = shape(clean(pick[idx]), cut, n, DROP.get(term))
            out[term] = {"def": d, "source": "wiktionary", "page": page,
                         "url": "https://en.wiktionary.org/wiki/" + urllib.parse.quote(page.replace(" ", "_"))}
        else:
            if raw and page in raw.get("_wikipedia", {}):
                j = raw["_wikipedia"][page]
                extract, url, rev = j["extract"], j["url"], j.get("rev", "")
            else:
                j = fetch(WP + urllib.parse.quote(page.replace(" ", "_")) + "?redirect=true")
                extract, url, rev = j["extract"], j["content_urls"]["desktop"]["page"], j.get("revision", "")
            d = shape(re.sub(r"\s+", " ", extract).strip(), cut, n, DROP.get(term), subject=True)
            out[term] = {"def": d, "source": "wikipedia", "page": page, "url": url, "rev": rev}
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    raw = None
    if "--raw" in argv:
        raw = json.load(io.open(argv[argv.index("--raw") + 1], encoding="utf-8"))
    out = build(raw)
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print("%d definitions → %s" % (len(out), OUT))
    for t, e in out.items():
        print("%-26s %s" % (t, e["def"]))


if __name__ == "__main__":
    main()
