#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""More practice for «в + accusative» and «на + accusative» time expressions:
в среду, во вторник, в эту минуту, в этот день, на следующий день, раз в
неделю. Real sentences only, from two places:

  * the library's public-domain books (tools/courses/library_sentences.tsv,
    built from the FB2s on the shelf) — always;
  * Tatoeba's Russian–English pairs (CC BY 2.0 FR), when the file is given —
    these come with a translation.

The sentence is the source's; the answer is the words the sentence has; the
hint is their dictionary form (pymorphy3). The rule shown with each drill is
DLI's, attached by explain_time.py in the build like every other time drill.

    python3 tools/courses/time_more.py                         # library only
    python3 tools/courses/time_more.py ~/tatoeba/rus.txt       # + Tatoeba (WSL)
    python3 tools/courses/build_courses.py

Writes tools/courses/time_more.json, which build_courses.py appends to the
time course as «On Wednesday, in that minute, the next day» and its practice
sets.
"""
import io, json, os, re, sys, random, collections

import pymorphy3

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
M = pymorphy3.MorphAnalyzer()
LIB = os.path.join(HERE, "library_sentences.tsv")
OUT = os.path.join(HERE, "time_more.json")
WORD = re.compile(r"[А-Яа-яЁё]+(?:-[а-яё]+)?")

DAYS = "понедельник|вторник|среду|четверг|пятницу|субботу|воскресенье"
MODS = r"(?:эту же|ту же|этот же|тот же|эту|ту|этот|тот|следующую|следующий|прошлую|прошлый|будущую|будущий|ближайшую|ближайший|первую|первый|последнюю|последний|каждую|каждый|одну|один|ту же|эту же|тот же|этот же|самую|самый|такую|такой|какую|какой|иную|иной|любую|любой|другую|другой|ту самую|эту самую|сию|сей|нынешнюю|нынешний|вчерашнюю|вчерашний|сегодняшнюю|сегодняшний|воскресную|воскресный|праздничную|праздничный|решающую|решающий|счастливую|счастливый|страшную|страшный|тяжёлую|тяжёлый|тяжелую|тяжелый|первые|последние|эти|те|все)"
# в/во + (modifier) + day of the week
RX_DAY = re.compile(r"(?<![\w-])([Вв]о?)\s+((?:%s\s+)?(?:%s))(?![\w-])" % (MODS, DAYS))
# в + modifier + minute / second / hour / night / day / time / раз
RX_UNIT = re.compile(r"(?<![\w-])([Вв]о?)\s+(%s\s+(?:минуту|секунду|ночь|день|час|раз|вечер|миг|мгновение))(?![\w-])" % MODS)
# на + следующий/другой/третий + день/утро/вечер/ночь
RX_NA = re.compile(r"(?<![\w-])([Нн]а)\s+((?:следующий|другой|другое|следующее|третий|второй|первый|четвёртый|четвертый|пятый|следующую|другую)\s+(?:день|утро|вечер|ночь))(?![\w-])")
# N раз(а) в день / неделю / месяц / год
RX_FREQ = re.compile(r"(?<![\w-])(раза?)\s+([Вв])\s+(день|неделю|месяц|год|час|минуту|сутки)(?![\w-])")

MIN_W, MAX_W = 4, 30


DAY_NOM = {"понедельник": "понедельник", "вторник": "вторник", "среду": "среда", "четверг": "четверг",
           "пятницу": "пятница", "субботу": "суббота", "воскресенье": "воскресенье"}


def noun_parse(w):
    """The reading of the noun that fits «в + accusative»: accusative singular
    first, so «раз» is not read as the genitive plural of «разы»."""
    ps = [p for p in M.parse(w) if "NOUN" in p.tag]
    for want in (("accs", "sing"), ("accs",), ()):
        for p in ps:
            if all(t in p.tag for t in want):
                return p
    return ps[0] if ps else None


def lemma_phrase(words):
    """The hint: each word's dictionary form, the adjective agreeing in gender
    with the noun's nominative (эту субботу → эта суббота)."""
    out = []
    noun = words[-1]
    np = noun_parse(noun)
    gender = np.tag.gender if np else None
    plural = bool(np) and np.tag.number == "plur"
    for w in words[:-1]:
        ps = [p for p in M.parse(w) if any(x in p.tag for x in ("ADJF", "NPRO", "NUMR"))]
        if not ps:
            out.append(w)
            continue
        p = ps[0]
        f = None
        if plural:
            f = p.inflect({"nomn", "plur"})
        elif gender:
            f = p.inflect({"nomn", "sing", gender})
        out.append(f.word if f else p.normal_form)
    # воскресенье: the dictionary's headword is воскресение, the resurrection
    out.append(DAY_NOM.get(noun.lower()) or (np.normal_form if np else noun))
    return " ".join(out)


def clean(s):
    s = s.replace(" ", " ").replace(" ", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def good_sentence(s):
    n = len(WORD.findall(s))
    if not MIN_W <= n <= MAX_W:
        return False
    if s.count("«") != s.count("»") or s.count("(") != s.count(")"):
        return False
    if re.search(r"[A-Za-z]{3,}", s):
        return False
    return True


def blank(s, m, phrase_group):
    """The sentence with the phrase blanked and its hint added."""
    phrase = m.group(phrase_group)
    words = phrase.split()
    hint = lemma_phrase(words)
    start = m.start(phrase_group)
    q = s[:start] + "___ (" + hint + ")" + s[start + len(phrase):]
    return q, phrase


def drills_from(sentences, limit_per_kind):
    """sentences: [(ru, en_or_cite, is_citation)]."""
    out, seen = collections.defaultdict(list), set()
    for ru, en, cite in sentences:
        ru = clean(ru)
        if not good_sentence(ru):
            continue
        key = re.sub(r"[^\w]+", " ", ru.lower()).strip()
        if key in seen:
            continue
        for kind, rx, grp in (("day", RX_DAY, 2), ("na", RX_NA, 2), ("unit", RX_UNIT, 2), ("freq", RX_FREQ, 3)):
            m = rx.search(ru)
            if not m:
                continue
            if kind == "freq":
                # blank the unit after раз в: «два раза в ___ (неделя)»
                phrase = m.group(3)
                hint = lemma_phrase([phrase])
                q = ru[:m.start(3)] + "___ (" + hint + ")" + ru[m.end(3):]
            else:
                q, phrase = blank(ru, m, grp)
            if len(out[kind]) >= limit_per_kind.get(kind, 10 ** 9):
                break
            seen.add(key)
            e = {"type": "fill", "q": q, "answers": [phrase],
                 "why": ("*%s*" % en) if cite else "Sentence and translation from Tatoeba (CC BY 2.0 FR)."}
            if not cite:
                e["prompt"] = en
            else:
                e["prompt"] = "*%s*" % en
            out[kind].append(e)
            break
    return out


def read_library(path):
    rows = []
    for line in io.open(path, encoding="utf-8", errors="replace"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 2:
            continue
        ru, cite = parts[0], parts[-1]
        if not cite.strip():
            continue
        rows.append((ru, cite.strip(), True))
    return rows


def read_tatoeba(path):
    from tense_examples import read
    return [(ru, en, False) for ru, en, _ in read(path)]


def main():
    rows = read_library(LIB)
    print("library sentences: %d" % len(rows))
    tat = []
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        tat = read_tatoeba(sys.argv[1])
        print("tatoeba pairs: %d" % len(tat))
    random.Random(11).shuffle(rows)
    # Tatoeba first: a sentence with a translation beats a bare citation.
    limits = {"day": 1500, "na": 200, "unit": 300, "freq": 100}
    found = drills_from(tat + rows, limits)
    kinds = {k: len(v) for k, v in found.items()}
    print("drills:", kinds)
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(found, ensure_ascii=False, indent=1))
    print("-> %s" % OUT)


if __name__ == "__main__":
    main()
