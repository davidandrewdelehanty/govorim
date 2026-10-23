#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every exercise explained by the rule for its own construction.

attach_context.py gives each exercise the opening sentence of its lesson —
the lesson's subject, not necessarily the exercise's. A lesson on the
genitive prepositions opens with «из» and «с»; an exercise on «от» should
show the sentence about «от». A lesson on the perfective future opens with
how many tenses the imperfective has.

This pass runs after it. For every fill-in exercise it works out the
construction being tested — the blanked word's case, tense, aspect, mood,
degree, participle or gerund (pymorphy3, read with the hint's dictionary
form and the preposition before the blank) and what the hint adds («+ ли»,
«+ бы») — then:

  1. checks it against what the section teaches (WANT, by section id). An
     exercise testing something else is taken out of the section and
     logged to tools/courses/_dropped/pertinence.json;
  2. finds, among the lesson's own sentences, the one that states the rule
     for that construction — the sentence naming the preposition, the
     tense, the degree — and makes it the `context` shown above the
     question, with the sentence and its examples as the `why` shown after;
  3. where the lesson has no such sentence (a story's exercises; a lesson
     that teaches through a table), uses the rule the exercise already
     carried from its miner when that fits, else the matching rule from
     another lesson of the courses (BANK) — always a source's own sentence,
     never a line of ours.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/courses/pertinence.py            # report only
    python3 tools/courses/pertinence.py --apply
"""
import argparse, io, json, os, re, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
COURSES = os.path.join(ROOT, "public", "courses")
DROPPED = os.path.join(HERE, "_dropped", "pertinence.json")

try:
    import pymorphy3
    M = pymorphy3.MorphAnalyzer()
except ImportError:
    M = None

# Courses whose exercises explain themselves (one rule per kind of drill,
# given by their builders) or are not grammar drills at all.
SKIP = {"fast", "gramterms", "numerals", "clock", "time", "tables", "pronouns"}

NORM_PREP = {"во": "в", "со": "с", "ко": "к", "об": "о", "обо": "о", "надо": "над", "передо": "перед", "подо": "под", "изо": "из", "ото": "от"}
PREP_CASES = {
    "без": "gent", "для": "gent", "из": "gent", "от": "gent", "у": "gent", "около": "gent", "после": "gent", "до": "gent",
    "кроме": "gent", "мимо": "gent", "против": "gent", "вместо": "gent", "из-за": "gent", "из-под": "gent", "возле": "gent",
    "вокруг": "gent", "среди": "gent", "напротив": "gent", "вдоль": "gent", "ради": "gent",
    "к": "datv", "благодаря": "datv", "вопреки": "datv", "согласно": "datv", "навстречу": "datv",
    "через": "accs", "про": "accs", "сквозь": "accs",
    "над": "ablt", "перед": "ablt", "между": "ablt",
    "при": "loct",
    "с": "gent ablt", "в": "accs loct loc2", "на": "accs loct loc2", "о": "loct accs", "за": "accs ablt", "под": "accs ablt", "по": "datv loct",
}
WORD = re.compile(r"[А-Яа-яЁё\-]+")
QUANT = set("оба обе полтора полторы несколько много немного мало сколько столько пара пару десяток сотня тысяча тысячи тысяч миллион".split())
POS_MAIN = ("NOUN", "VERB", "INFN", "ADJF", "ADJS", "COMP", "NUMR", "PRTF", "PRTS", "GRND", "NPRO", "ADVB", "PRED")


def hint_of(q):
    m = re.search(r"___\s*\(([^)]*)\)", q)
    return m.group(1).strip() if m else ""


CASES = ("nomn", "gent", "datv", "accs", "ablt", "loct", "loc2", "gen2")


def feats(e, prefer=()):
    """What the exercise tests: a set of tags, the word before the blank,
    the hint's lemma and add-ons, the answer. A form that could be several
    cases («новой», «в груди») is read as the case its preposition allows
    and, among those, the one the section teaches (`prefer`)."""
    q = e.get("q") or ""
    ans = (e.get("answers") or [""])[0].replace("́", "").strip()
    hint = hint_of(q)
    extra = set(x.strip().lower() for x in re.findall(r"\+\s*([а-яё]+)", hint))
    base = re.sub(r"\+.*", "", hint).strip()
    lem = [w.lower() for w in WORD.findall(base.replace("ё", "е"))]
    if M:   # the hint may be a plural («чеки», «сыновья»): its dictionary forms too
        lem += [p.normal_form.replace("ё", "е") for w in list(lem) for p in M.parse(w)[:3]]
    lem = list(dict.fromkeys(lem))
    pre = re.sub(r"\([^)]*\)", " ", q.split("___")[0])
    prevs = WORD.findall(pre.lower().replace("ё", "е"))
    prev = NORM_PREP.get(prevs[-1], prevs[-1]) if prevs else ""
    prev2 = NORM_PREP.get(prevs[-2], prevs[-2]) if len(prevs) > 1 else ""
    words = WORD.findall(ans)
    first = NORM_PREP.get(words[0].lower(), words[0].lower()) if words else ""
    quantity = prev in QUANT or re.match(r"^\d", prev) or (M and any(p.tag.POS == "NUMR" for p in M.parse(prev)[:2]))
    tags_extra = {"afternum"} if quantity else set()
    if quantity:
        prep = ""                          # «на две части»: the number takes the case, the noun follows the number
    elif prev in PREP_CASES:
        prep = prev
    elif first in PREP_CASES:
        prep = first
    elif prev2 in PREP_CASES and prev not in ("не", "ни"):
        prep = prev2                       # «с фронтальной ___»: an adjective between
    else:
        prep = ""
    allowed = set(PREP_CASES.get(prep, "").split())
    prefer = set(prefer) & set(CASES)
    if allowed:
        prefer = prefer & allowed          # never a case the preposition cannot take
    tags = set(tags_extra)
    head = None
    parsed = []
    if M:
        for w in words:
            ps = M.parse(w.lower())
            pick = None
            # the hint's word, in a case the preposition (and the lesson) allows
            # first the case the lesson teaches, if the form can be read so
            for p in ps:
                if p.normal_form.replace("ё", "е") in lem and str(p.tag.case) in prefer:
                    pick = p; break
            for p in ps if pick is None else []:
                if p.normal_form.replace("ё", "е") in lem and (not allowed or str(p.tag.case) in allowed or p.tag.POS not in ("NOUN", "ADJF", "NPRO", "NUMR", "PRTF")):
                    pick = p; break
            if pick is None:
                for p in ps:
                    if p.normal_form.replace("ё", "е") in lem:
                        pick = p; break
            if pick is None and allowed:
                for p in ps:
                    if str(p.tag.case) in allowed:
                        pick = p; break
            parsed.append(pick or (ps[0] if ps else None))
        for p in parsed:
            if p and p.normal_form.replace("ё", "е") in lem and p.tag.POS in POS_MAIN:
                head = p
        if head is None:
            head = next((p for p in reversed(parsed) if p and p.tag.POS in POS_MAIN), None)
    if head is not None:
        t = head.tag
        for a in (t.POS, t.case, t.number, t.gender, t.tense, t.aspect, t.mood, t.voice, t.animacy, t.person):
            if a:
                tags.add(str(a))
        if "Supr" in t:
            tags.add("Supr")
        if "Fixd" in t:
            tags.add("Fixd")                 # indeclinable: фарси, оригами — any case
        if head.word.endswith(("ся", "сь")):
            tags.add("sya")
    for p in parsed:
        if p and p is not head and p.tag.POS in ("ADJF", "ADJS", "PRTF"):
            tags.add("adj+")
    low = ans.lower().replace("ё", "е")
    if re.match(r"сам(ый|ая|ое|ые|ого|ой|ых|ым|ыми|ому|ую)\b", low):
        tags.add("samyi")
    if re.search(r"(^|\s)(более|менее)\s", low):
        tags.add("bolee")
    if re.search(r"(ейш|айш)", low):
        tags.add("eishiy")
    if re.match(r"буд(у|ешь|ет|ем|ете|ут)\s", low):
        tags.add("futr"); tags.add("impf")
    for x in extra:
        tags.add("+" + x)
    if hint and not re.search(r"[А-Яа-яЁё]", hint):
        tags.add("gloss")                  # a conjunction or particle blanked itself, hinted in English
        tags.add("gloss:" + ans.lower().replace("ё", "е"))
    if " / " in hint:
        tags.add("aspectchoice")           # «делать / сделать»: which aspect
    if prev in ("не", "нет", "ни") or prev2 in ("не", "нет") and prev not in PREP_CASES:
        tags.add("neg")
    if prep:
        tags.add("prep"); tags.add("prep:" + prep)
    return {"tags": tags, "prev": prev, "prev2": prev2, "lemma": " ".join(lem), "ans": ans, "hint": hint, "prep": prep}


def ok(want, f):
    """want: terms separated by spaces, all must hold; alternatives in a
    term by |; a leading ! negates the term. A term is a tag (gent, futr,
    perf, COMP, PRTS, pssv, sya, neg, prep, prep:из, +ли …), ans:regex,
    lemma:regex, hint:regex, or any."""
    for term in want.split():
        neg = term.startswith("!")
        if neg:
            term = term[1:]
        hit = False
        for alt in term.split("|"):
            if alt == "any":
                hit = True
            elif alt.startswith("ans:"):          # in these regexes / stands for |
                hit = bool(re.search(alt[4:].replace("/", "|"), f["ans"].lower().replace("ё", "е")))
            elif alt.startswith("lemma:"):
                hit = bool(re.search(alt[6:].replace("/", "|"), f["lemma"]))
            elif alt.startswith("hint:"):
                hit = bool(re.search(alt[5:].replace("/", "|"), f["hint"].lower()))
            elif alt.startswith("prev:"):
                hit = alt[5:] in (f["prev"], f["prev2"])
            else:
                hit = alt in f["tags"] or (alt in CASES + ("sing", "plur") and "Fixd" in f["tags"])
            if hit:
                break
        if hit == neg:
            return False
    return True


# What each lesson teaches, as a test on the exercise (see ok()). A lesson
# not named here keeps every exercise. Practice sets go by their lesson.
WANT = {
    "case-nom": {"n1-subject": "nomn", "n2-eto": "nomn", "n3-adjectives": "ADJF|PRTF|adj+ nomn", "n4-pronouns": "nomn"},
    "case-gen": {"g1-possession": "gent", "g2-no": "gent", "g3-counting": "gent|NUMR", "g4-from": "gent prep:из|prep:с|prep:от",
                 "g5-u-dlya-bez": "gent prep:у|prep:для|prep:без", "g6-more-prepositions": "gent prep", "g7-verbs": "gent",
                 "g8-endings": "gent"},
    "case-dat": {"d1-to-whom": "datv", "d2-mne-nravitsya": "datv", "d3-verbs": "datv", "d4-k": "datv prep:к",
                 "d5-po": "datv prep:по|prep:благодаря|prep:вопреки|prep:согласно|prep:навстречу", "d6-endings": "datv"},
    "case-acc": {"a1-object": "accs", "a2-v-na": "accs prep:в|prep:на", "a3-za-pod": "accs prep:за|prep:под",
                 "a4-cherez-pro": "accs prep:через|prep:про|prep:сквозь", "a5-time": "accs|gent", "a6-endings": "accs"},
    "case-ins": {"i1-with": "ablt prep:с", "i2-means": "ablt", "i3-being": "ablt",
                 "i4-where": "ablt prep:над|prep:под|prep:за|prep:перед|prep:между", "i5-verbs": "ablt", "i6-time": "ablt", "i7-endings": "ablt"},
    "case-prp": {"p1-where": "loct|loc2 prep:в|prep:на", "p2-about": "loct prep:о", "p3-v-lesu": "loc2|ans:[ую]$ prep:в|prep:на",
                 "p4-pri-transport": "loct|loc2 prep:при|prep:на|prep:в", "p5-endings": "loct|loc2"},
    "cases": {"k1-nom-prep": "loct|loc2|nomn", "k2-accusative": "accs", "k3-genitive": "gent", "k4-dative": "datv", "k5-instrumental": "ablt",
              "k7-genitive-plural": "gent plur", "k8-plural-cases": "plur", "k9-adjectives-singular": "ADJF|adj+|NPRO sing",
              "k10-adjectives-plural": "ADJF|adj+|NPRO plur", "k11-prepositions": "prep"},
    "count": {"c2-genitive-plural": "gent plur", "c3-how-many": "gent", "c4-one-two-three-four": "NUMR|lemma:^(один|одна|одно|два|две|три|четыре)",
              "c5-five-and-up": "NUMR"},
    "aspect": {"a2-context": "impf", "a3-commands": "impr", "a4-future": "futr perf", "a5-po-s": "ans:^(по/с)"},
    "verbs": {"v1-present": "pres", "v2-past": "past", "v4-sya": "sya"},
    "compare": {"c1-comparative": "COMP", "c2-irregular": "COMP", "c3-than": "COMP|gent", "c4-bolee": "bolee|COMP",
                "c5-samyi": "samyi|Supr", "c6-eishiy": "eishiy|Supr|ans:всех", "c7-short": "ADJS"},
    "complex": {"x1-chtoby": "+чтобы|+что|ans:^(чтобы/что)", "x3-poka": "ans:пока|hint:пока|any", "x4-li": "+ли"},
    "inter2": {"i01-acc-or-gen": "accs|gent", "i02-adjectival-nouns": "ADJF", "i03-short-complement": "ADJS", "i05-compound-numerals": "NUMR|gent",
               "i07-sam-samyi": "samyi|lemma:^сам", "i08-aspect-past": "past", "i09-aspect-infinitive": "INFN", "i10-aspect-imperative": "impr",
               "i11-prefixed-motion": "VERB|INFN|GRND|PRTF", "i12-participles-active": "PRTF !pssv", "i13-participles-passive": "PRTF|PRTS pssv",
               "i14-gerunds": "GRND", "i15-passive": "pssv|sya", "i20-comparison": "COMP|bolee|samyi", "i22-negation": "neg|gent",
               "i26-imperative-types": "impr|VERB"},
    "adv3": {"v06-no-subject": "datv|gen2|!nomn", "v09-object-clauses": "+ли|+что|+чтобы",
             "v12-particles": "+же|+ведь|+разве|+неужели|+даже|ans:(^/\\s)(же/ведь/разве/неужели/даже)(\\s/$)"},
    "forms": {"f1-imperative": "impr", "f2-conditional": "past|+бы", "f3-short-passive": "PRTS pssv", "f4-long-passive": "PRTF pssv past",
              "f5-present-active": "PRTF pres !pssv", "f6-past-active": "PRTF past !pssv", "f7-passive-present": "PRTF|sya pres|sya",
              "f8-gerund-imperfective": "GRND impf", "f9-gerund-perfective": "GRND perf"},
    "tenses": {"x02-present": "pres", "x03-present-prog": "pres", "x04-pres-perf-prog": "pres", "x05-pres-perf": "past|pres",
               "x06-past": "past", "x07-past-prog": "past impf", "x08-past-perf": "past perf", "x09-used-to": "past impf",
               "x10-future": "futr", "x11-going-to": "futr|ans:^(буд|собира)", "x12-would": "past|+бы", "x13-passive": "pssv|sya"},
}

# What a sentence of a lesson must mention to explain a tag: (regex, weight).
CASE_WORDS = {"gent": "genitive", "datv": "dative", "accs": "accusative", "ablt": "instrumental", "loct": "prepositional|locative",
              "loc2": "prepositional|locative|-у\\b|stress", "nomn": "nominative", "gen2": "genitive|-у,? -ю"}
LEX = [
    ("past", r"\bpast\b", 2), ("futr", r"\bfuture\b", 2), ("pres", r"\bpresent\b", 2),
    ("impr", r"imperative|command", 3), ("perf", r"\bperfective\b(?! verb has)", 1), ("impf", r"\bimperfective\b", 1),
    ("COMP", r"comparative", 3), ("samyi", r"самый|superlative", 3), ("eishiy", r"ейш|айш|superlative", 3), ("Supr", r"superlative", 2),
    ("ADJS", r"short\b", 3), ("PRTF", r"participle", 3), ("PRTS", r"participle", 3), ("pssv", r"passive", 2), ("actv", r"active", 1),
    ("GRND", r"деепричаст|gerund|verbal adverb", 3), ("sya", r"-ся|reflexive", 2), ("neg", r"negat|\bне\b|\bнет\b|without", 2),
    ("NUMR", r"numeral|number", 2), ("plur", r"plural", 1), ("sing", r"singular", 0.5), ("NPRO", r"pronoun", 2), ("ADJF", r"adjective", 1),
    ("INFN", r"infinitive", 2), ("adj+", r"adjective|agree", 1), ("bolee", r"более|менее", 3), ("anim", r"animate", 0.5), ("inan", r"inanimate", 0.5),
    ("+ли", r"\bли\b", 4), ("+бы", r"\bбы\b|conditional", 4), ("+чтобы", r"чтобы", 4), ("+что", r"\bчто\b", 3), ("+же", r"\bже\b", 4),
    ("+ведь", r"\bведь\b", 4), ("+разве", r"\bразве\b", 4), ("+неужели", r"неужели", 4), ("+даже", r"\bдаже\b", 4),
    ("+ни", r"\bни\b", 3), ("+не", r"\bне\b", 2),
    ("femn", r"feminine", 1.5), ("masc", r"masculine", 1), ("neut", r"neuter", 1),
    ("aspectchoice", r"\baspect\b", 2), ("gen2", r"indefinite quantity|-у, -ю", 3),
]


PREP_WORD = re.compile(r"(?<![а-яё\-])(" + "|".join(sorted((re.escape(p) for p in PREP_CASES), key=len, reverse=True)) + r")(?![а-яё\-])")


def preps_named(sentence):
    """The prepositions a sentence talks about — named in its prose, not
    merely used inside its italic examples."""
    prose = re.sub(r"\*[^*]+\*", " ", sentence.replace("**", "")).lower().replace("ё", "е")
    return set(PREP_WORD.findall(prose))


def score(sentence, f):
    low = sentence.lower()
    s = 0.0
    # a sentence about other prepositions is not about this one: «под …
    # calls the accusative» explains nothing about «через»
    mine = [t[5:] for t in f["tags"] if t.startswith("prep:")]
    if mine:
        named = preps_named(sentence)
        if named and not (named & set(mine)):
            return 0
        # the sentence that introduces the preposition — «**Через**, 'through'…»,
        # «The preposition через + acc. denotes…» — over one that mentions it
        for p in mine:
            if re.match(r"^\W*(?:the\s+)?(?:prepositions?\s+)?(?:\*\*)?" + re.escape(p) + r"(?![а-яё])", low):
                s += 2
    for tag in f["tags"]:
        if tag in CASE_WORDS:
            if re.search(CASE_WORDS[tag], low):
                s += 2
        elif tag.startswith("prep:"):
            p = tag[5:]
            px = "об?о?" if p == "о" else re.escape(p)
            if re.search(r"(?<![а-яё\-])" + px + r"(?![а-яё\-])", low):
                s += 4
        elif tag.startswith("gloss:"):
            w = tag[6:]
            if re.search(r"(?<![а-яё\-])" + re.escape(w) + r"(?![а-яё\-])", low):
                s += 4
            elif len(w) > 5 and re.search(r"(?<![а-яё\-])" + re.escape(w[:-2]), low):
                s += 3                     # «которых» explained by a sentence about «который»
    for tag, rx, w in LEX:
        if tag in f["tags"] and re.search(rx, low):
            s += w + 0.1                   # the more of the construction's features named, the better
    # the sentence has the answer itself: «рано — раньше», «хороший — лучше»
    a = f["ans"].lower().replace("ё", "е")
    if len(a) >= 4 and re.search(r"(?<![а-яё])" + re.escape(a) + r"(?![а-яё])", low):
        s += 4
    # a present-tense verb: the sentence about its conjugation type
    if "pres" in f["tags"] and "VERB" in f["tags"]:
        plain = sentence.replace("**", "")
        if re.search(r"(ешь|ет|ем|ете|ут|ют|ю|у)(ся|сь)?$", a) and re.search(r"[\"“«]Е[\"”»]|first conjugation|Е type", plain):
            s += 2
        if re.search(r"(ишь|ит|им|ите|ат|ят)(ся|сь)?$", a) and re.search(r"[\"“«]И[\"”»]|second conjugation|И type", plain):
            s += 2
    # the sentence names the exercise's own word: «садиться — сесть: to sit down»
    for w in f.get("lemma", "").split():
        if len(w) >= 4 and re.search(r"(?<![а-яё])" + re.escape(w[:5 if len(w) > 5 else len(w)]), low):
            s += 3
            break
    if s:
        # a sentence that states a rule over one that introduces the topic
        if re.search(r"\b(is formed|are formed|is used|are used|takes|take the|requires|require|is followed|are followed|denotes|denote|expresses|express|agrees|agree|is in the|are in the|answers the question|belong to|belongs to|is rendered|are rendered|consists of|consist of)\b", low):
            s += 1
        # the sentence quotes the very ending the answer has: "-ее", -ами
        a = f["ans"].lower().replace("ё", "е")
        for n in (3, 2):
            if len(a) > n + 2 and re.search(r"[-‑]" + re.escape(a[-n:]) + r"(?![а-яё])", low):
                s += 1.5
                break
    if sentence.lstrip().startswith("*") and not re.search(r"[A-Za-z]{4}", sentence):
        s *= 0.5                      # an example alone, not a rule
    return s


def text_of(b):
    t = (b.get("text") or "").replace("\x27\x27\x27", "").replace("\x27\x27", "")
    t = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", t)      # wiki links, as their text
    return re.sub(r"\s+", " ", t).strip()


SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-ZА-Я«\"“*(])")


SRC_OF = {}      # a lesson sentence → the note that follows its block (the source it was quoted from)


def sentences(doc):
    """The lesson's sentences in order, and its source note."""
    out, src = [], ""
    blocks = doc.get("blocks") or []
    # the note after each block: a lesson quoting several sources cites each after the text it covers
    after = [""] * len(blocks)
    nxt = ""
    for i in range(len(blocks) - 1, -1, -1):
        if blocks[i].get("t") == "note":
            nxt = text_of(blocks[i])
        after[i] = nxt
    for bi, b in enumerate(blocks):
        t = b.get("t")
        if t == "note":
            if not src:
                src = text_of(b)
            continue
        texts = []
        if t in ("p", "lead", "formula"):
            texts.append(text_of(b))
        elif t == "table":
            # a table's rows, each as a line: «рано — раньше», «хороший — лучше — лучший»
            for r in b.get("rows") or []:
                cells = [text_of({"text": str(c)}) for c in r if str(c).strip()]
                if len(cells) >= 2:
                    texts.append(" — ".join(cells) + ".")
        elif t == "h":
            continue
        elif t == "rule":
            for it in b.get("items") or []:
                texts.append(re.sub(r"\s+", " ", it.get("text") or ""))
                texts += [re.sub(r"\s+", " ", p) for p in it.get("points") or []]
                if it.get("examples"):
                    texts.append("*" + " ".join(it["examples"]) + "*")
        elif t == "list":
            texts += [re.sub(r"\s+", " ", x) for x in b.get("items") or []]
        elif t == "ex":
            texts.append("*" + " ".join(x[0] for x in b.get("items") or []) + "*")
        for x in texts:
            x = text_of({"text": x})
            for s in SPLIT.split(x):
                s = s.strip()
                if len(s) >= 8:
                    out.append(s)
                    if after[bi]:
                        SRC_OF[s[:60]] = after[bi]
    return out, src


def unstar(s):
    """A wiki page's footnote mark — «обстановку**)» — is not bold markup;
    an unpaired ** is taken out."""
    if s.count("**") % 2 == 1:
        k = s.rfind("**")
        s = s[:k] + s[k + 2:]
    return s


def trim(s, n=260):
    s = unstar(re.sub(r"^\*+|\*+$", "", s).strip())
    if len(s) <= n:
        return s
    cut = s[:n]
    k = max(cut.rfind(". "), cut.rfind("; "), cut.rfind(", "))
    return (cut[:k + 1] if k > n * 0.5 else cut.rsplit(" ", 1)[0]) + "…"


def explain(sents, f):
    """(context, why, score) from the lesson's sentences: the best-matching
    sentence, then the examples and the sentence that follow it."""
    best, bi = 0, -1
    for i, s in enumerate(sents):
        sc = score(s, f)
        if sc > best:
            best, bi = sc, i
    if bi < 0:
        return None, None, 0
    ctx = trim(sents[bi])
    why = sents[bi]
    j = bi + 1
    while j < len(sents) and len(why) < 420:
        nxt = sents[j]
        # examples, and the sentence that goes on with the same point
        if nxt.lstrip().startswith("*") or re.match(r"^[а-яё(]", nxt) or score(nxt, f) >= best * 0.75 or why.count("*") % 2 == 1:
            why += " " + nxt
            j += 1
        else:
            break
    why = unstar(why.strip())
    if why.count("*") % 2 == 1:
        why += "*"
    return ctx, why, best


# Where another lesson states the rule, for an exercise whose own lesson
# has no sentence about its construction: (want, course, section, regex).
BANK = [
    ("+ли", "complex", "x4-li", r"ЛИ never begins"),
    ("aspectchoice impf", "aspect", "a1-process-result", r"imperfective aspect emphasizes"),
    ("aspectchoice perf", "aspect", "a1-process-result", r"perfective aspect places"),
    ("gen2", "cases", "k3-genitive", r"indefinite quantity"),
    ("+бы", "forms", "f2-conditional", r"бы"),
    ("GRND perf", "forms", "f9-gerund-perfective", r"perfective"),
    ("GRND", "forms", "f8-gerund-imperfective", r"деепричаст|gerund|adverb"),
    ("PRTS pssv", "forms", "f3-short-passive", r"short|passive"),
    ("PRTF pssv past", "forms", "f4-long-passive", r"passive"),
    ("PRTF pssv", "forms", "f7-passive-present", r"passive"),
    ("PRTF pres", "forms", "f5-present-active", r"present active|participle"),
    ("PRTF past", "forms", "f6-past-active", r"past active|participle"),
    ("impr", "forms", "f1-imperative", r"imperative"),
    ("COMP", "compare", "c1-comparative", r"comparative degree of Russian adjectives is formed"),
    ("samyi|Supr|eishiy", "compare", "c5-samyi", r"superlative|самый"),
    ("ADJS", "compare", "c7-short", r"short"),
    ("futr perf", "aspect", "a4-future", r"perfective future consists"),
    ("futr", "verbs", "v1-present", r"future|present"),
    ("past", "verbs", "v2-past", r"past tense is formed"),
    ("pres sya", "verbs", "v4-sya", r"-ся"),
    ("pres", "verbs", "v1-present", r"present tense"),
    ("INFN impf", "aspect", "a1-process-result", r"imperfective aspect emphasizes"),
    ("INFN perf", "aspect", "a1-process-result", r"perfective aspect places"),
    ("NUMR", "count", "c5-five-and-up", r"numeral"),
    ("ADJF|adj+", "cases", "k9-adjectives-singular", r"agree"),
    ("gent neg", "case-gen", "g2-no", r"negat|нет"),
    ("gent prep", "case-gen", "g4-from", r"genitive"),
    ("gent", "case-gen", "g1-possession", r"genitive"),
    ("datv prep:к", "case-dat", "d4-k", r"\bк\b"),
    ("datv prep:по", "case-dat", "d5-po", r"\bпо\b"),
    ("datv", "case-dat", "d1-to-whom", r"dative"),
    ("ablt prep", "case-ins", "i4-where", r"instrumental"),
    ("ablt", "case-ins", "i2-means", r"instrumental"),
    ("accs prep", "case-acc", "a2-v-na", r"accusative"),
    ("accs", "case-acc", "a1-object", r"accusative"),
    ("loct|loc2", "case-prp", "p1-where", r"prepositional|location"),
    ("nomn", "case-nom", "n1-subject", r"nominative"),
]
_bank_cache = {}


CASE_COURSE = {"gent": "case-gen", "gen2": "case-gen", "datv": "case-dat", "accs": "case-acc", "ablt": "case-ins",
               "loct": "case-prp", "loc2": "case-prp", "nomn": "case-nom"}
_course_cache = {}


def course_sentences(course):
    """Every lesson's sentences of a course, as (sentences, source note) pairs."""
    if course not in _course_cache:
        out = []
        d = os.path.join(COURSES, course)
        for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if fn.endswith(".json") and fn != "exam.json" and not re.search(r"-practice(?:-\d+)?\.json$", fn):
                out.append(sentences(json.load(io.open(os.path.join(d, fn), encoding="utf-8"))))
        _course_cache[course] = out
    return _course_cache[course]


def from_bank(f):
    # a preposition: the lesson of its case course that names it
    mine = [t[5:] for t in f["tags"] if t.startswith("prep:")]
    case = next((c for c in CASE_COURSE if c in f["tags"]), None)
    if mine and case:
        best = (None, None, "", 0)
        for sents, src in course_sentences(CASE_COURSE[case]):
            ctx, why, sc = explain(sents, f)
            if ctx and sc > best[3] and set(mine) & preps_named(why):
                best = (ctx, why, src, sc)
        if best[0]:
            return best[0], best[1], best[2]
    for want, course, sec, rx in BANK:
        if not ok(want, f):
            continue
        key = (course, sec)
        if key not in _bank_cache:
            p = os.path.join(COURSES, course, sec + ".json")
            _bank_cache[key] = sentences(json.load(io.open(p, encoding="utf-8"))) if os.path.exists(p) else ([], "")
        sents, src = _bank_cache[key]
        cands = [s for s in sents if re.search(rx, s, re.I)]
        if not cands:
            continue
        ctx, why, sc = explain(cands + [s for s in sents if s not in cands], f)
        if ctx:
            return ctx, why, src
    return None, None, ""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--course")
    a = ap.parse_args(argv)
    if M is None:
        print("pertinence skipped (pymorphy3 not installed)")
        return
    dropped = defaultdict(list)
    stats = Counter()
    for course in sorted(os.listdir(COURSES)):
        d = os.path.join(COURSES, course)
        if not os.path.isdir(d) or course in SKIP or (a.course and course != a.course):
            continue
        want_map = WANT.get(course, {})
        lessons = {}
        for f in sorted(os.listdir(d)):
            if not f.endswith(".json") or f == "exam.json":
                continue
            stem = f[:-5]
            base = re.sub(r"-practice(?:-\d+)?$", "", stem)
            if base not in lessons:
                p = os.path.join(d, base + ".json")
                lessons[base] = sentences(json.load(io.open(p, encoding="utf-8"))) if os.path.exists(p) else ([], "")
            sents, src = lessons[base]
            p = os.path.join(d, f)
            doc = json.load(io.open(p, encoding="utf-8"))
            if doc.get("stream"):
                continue
            keep = []
            changed = False
            for e in doc.get("exercises") or []:
                if e.get("type") != "fill":
                    keep.append(e); continue
                want = want_map.get(base)
                fe = feats(e, re.findall(r"[a-z0-9]+", want or ""))
                # a word that does not change («спасибо», «евро») shows no case
                same = fe["lemma"] and fe["lemma"] == fe["ans"].lower().replace("ё", "е") and "Fixd" in fe["tags"]
                if want and "gloss" not in fe["tags"] and (not ok(want, fe) or (same and any(c in want for c in CASES))):
                    dropped[course + "/" + stem].append({"q": e.get("q"), "answers": e.get("answers"), "tags": sorted(fe["tags"]), "want": want})
                    stats["dropped"] += 1
                    changed = True
                    continue
                keep.append(e)
                # the exercise's own citation, kept from its miner: after the
                # lesson prose attach_context put first
                why0 = e.get("why") or ""
                tail = why0.split("  ·  ")[-1].strip() if "  ·  " in why0 else ""
                ctx, why, sc = explain(sents, fe)
                if sc < 2:
                    # the rule the miner gave it, if it fits; else another lesson's
                    quote = re.search(r"«[^»]{20,}»(?:\s*«[^»]+»)*\s*—\s*[^.]*\.", tail)
                    if quote and score(quote.group(0), fe) >= 2:
                        ctx, why = trim(quote.group(0)), tail      # the rule, then its citation
                        tail = ""
                        stats["own rule"] += 1
                    else:
                        ctx, why, src2 = from_bank(fe)
                        if ctx:
                            why = why + (" — " + src2.rstrip(".") + "." if src2 else "")
                            stats["from bank"] += 1
                        else:
                            stats["unexplained"] += 1
                            continue
                else:
                    own = next((v for k, v in SRC_OF.items() if ctx.startswith(k[:40]) or k.startswith(ctx[:40])), "")
                    why = why + (" — " + (own or src) if (own or src) else "")
                    stats["from lesson"] += 1
                if tail and tail not in why:
                    why = why + "  ·  " + tail
                if e.get("context") != ctx or e.get("why") != why:
                    e["context"] = ctx
                    e["why"] = why
                    changed = True
            if changed:
                doc["exercises"] = keep
                if a.apply:
                    io.open(p, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False))
    if a.apply:
        os.makedirs(os.path.dirname(DROPPED), exist_ok=True)
        io.open(DROPPED, "w", encoding="utf-8").write(json.dumps(dropped, ensure_ascii=False, indent=1))
    for k, v in sorted(stats.items()):
        print("%-14s %6d" % (k, v))
    for k, v in sorted(dropped.items()):
        print("  dropped %3d from %s" % (len(v), k))
    if not a.apply:
        print("(report only; --apply to write)")


if __name__ == "__main__":
    main()
