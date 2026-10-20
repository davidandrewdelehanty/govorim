#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find exercises whose sentence does not exercise the section it sits in.

The practice sentences were mined by matching Russian words, so a word with
two senses could drag in a sentence about something else: «я забочусь об
окружающей среде́» (the environment) landed in a lesson on среда́, Wednesday,
and in a section on за + Accusative though its answer is prepositional.

Two checks, both mechanical:

  case      the section says which case it teaches; the answer is parsed and
            must be able to be that case
  governor  if a preposition stands in front of the blank, the answer must be
            in a case that preposition governs

    python3 tools/courses/sense_check.py                 # report
    python3 tools/courses/sense_check.py --drop          # quarantine the bad ones
"""
import argparse, io, json, os, re, collections

import pymorphy3

M = pymorphy3.MorphAnalyzer()
ROOT = "public/courses"
DROPPED = "tools/courses/_dropped"

CASE_WORD = {
    "nominative": "nomn", "genitive": "gent", "dative": "datv",
    "accusative": "accs", "instrumental": "ablt", "prepositional": "loct",
    "locative": "loct",
}
CASE_ABBR = {"nom": "nomn", "gen": "gent", "dat": "datv", "acc": "accs",
             "instr": "ablt", "inst": "ablt", "prep": "loct", "loc": "loct"}
BY_COURSE = {"case-nom": "nomn", "case-gen": "gent", "case-dat": "datv",
             "case-acc": "accs", "case-ins": "ablt", "case-prp": "loct"}

# Which case each preposition governs. Prepositions that take more than one
# are listed with all of them, so they can never make a false accusation.
PREP = {
    "без": {"gent"}, "для": {"gent"}, "до": {"gent"}, "из": {"gent"}, "из-за": {"gent"},
    "из-под": {"gent"}, "кроме": {"gent"}, "мимо": {"gent"}, "около": {"gent"}, "от": {"gent"},
    "после": {"gent"}, "против": {"gent"}, "у": {"gent"}, "вдоль": {"gent"}, "вокруг": {"gent"},
    "вместо": {"gent"}, "впереди": {"gent"}, "позади": {"gent"}, "среди": {"gent"},
    "накануне": {"gent"}, "ради": {"gent"},
    "к": {"datv"}, "ко": {"datv"}, "благодаря": {"datv"}, "согласно": {"datv"},
    "вопреки": {"datv"},
    "про": {"accs"}, "сквозь": {"accs"}, "через": {"accs"},
    "над": {"ablt"}, "надо": {"ablt"}, "перед": {"ablt"}, "передо": {"ablt"},
    "между": {"ablt"},
    "при": {"loct"}, "о": {"loct"}, "об": {"loct"}, "обо": {"loct"},
    # two cases, both allowed
    "в": {"accs", "loct"}, "во": {"accs", "loct"},
    "на": {"accs", "loct"}, "за": {"accs", "ablt"},
    "под": {"accs", "ablt"}, "подо": {"accs", "ablt"},
    "с": {"gent", "accs", "ablt"}, "со": {"gent", "accs", "ablt"},
    "по": {"datv", "accs", "loct"},
}

# В углу́, с голоду: the dictionary calls these the second locative and the
# second genitive. They ARE the prepositional and the genitive, so they count.
SAME = {"loc2": "loct", "gen2": "gent", "acc2": "accs"}

# A numeral in front of the blank decides the noun's case, not the section:
# «три дня назад» is an accusative time phrase whose noun is genitive.
NUMERAL = re.compile(
    u"^(\\d+|од(ин|на|но)|дв[аеух]|тр[иеёхём]|четыр|пят|шест|сем|восем|девят|десят"
    u"|сколько|несколько|много|мало|пол|полтор|об[аеои]|дво|тро|четвер|сот|ст[аоы]|тысяч|миллион|миллиард|пар[аыу])")


# A word can have two senses, and the sentences were mined by matching the
# Russian. «Я забочусь об окружающей среде́» is about the environment, not
# about среда́, Wednesday, so it does not belong in a lesson on time. Where
# the sentence carries an English translation, that translation has to mention
# the thing the course is about.
TOPIC_EN = {
 "time": """hour minute second day week month year morning evening night noon midnight
    today tomorrow yesterday o'clock time date monday tuesday wednesday thursday friday
    saturday sunday january february march april may june july august september october
    november december season spring summer autumn fall winter ago soon late later lately
    early always never often rarely seldom long when while century decade weekend birthday
    anniversary clock watch calendar moment period during until till since deadline age aged
    old young now then before after past future present daily weekly monthly yearly annual
    annually hourly nightly schedule holiday vacation christmas easter anytime awhile
    overnight weekday weeknight breakfast lunch dinner supper brunch bedtime lifetime
    afternoon tonight midnight millennium millennia once twice again still yet already
    forever meantime nowadays recently shortly presently whenever ancient modern birthday
    lifespan era epoch instant whenever meanwhile duration eve midday daybreak dawn dusk
    sunrise sunset term semester quarter anniversary curfew timetable""",
}
# Plurals, possessives and the figures count too: "300 years", "two hours".
TOPIC_RX = {k: re.compile(
    r"(?:\d|\b(?:%s)(?:s|es|'s|th|ly)?\b)" % "|".join(
        re.escape(w) for w in v.split()), re.I)
    for k, v in TOPIC_EN.items()}
# A prompt that is a book citation (*Author, «Title»*) is not a translation.
CITATION = re.compile(r"^\s*\*")

# с голоду, без спросу, с размаху — the masculine partitive in -у.
PARTITIVE_U = re.compile(u"^[а-яё]+[ую]$")

WORD = re.compile(r"[а-яёА-ЯЁ]+(?:-[а-яё]+)?")
Y = lambda s: (s or "").lower().replace("ё", "е")


def lemmas(w):
    return {Y(p.normal_form) for p in M.parse(w)} | {Y(w)}


def cases_of(word, hint):
    """Every case this written form could be, restricted to parses that share
    a lemma with the bracket hint so a homograph of another word cannot vouch
    for it."""
    want = lemmas(hint) if hint else None
    out = set()
    for p in M.parse(word):
        if want and not (lemmas(p.word) | {Y(p.normal_form)}) & want:
            continue
        c = p.tag.case
        if c:
            out.add(SAME.get(c, c))
    if not out:                      # unknown word, or no case (verb, adverb)
        for p in M.parse(word):
            if p.tag.case:
                out.add(SAME.get(p.tag.case, p.tag.case))
    return out


def expected_case(course, sec, ctx):
    """The case this section says it is teaching, or None.

    Only evidence that names one case on purpose counts: the course itself,
    an explicit «+ Acc.» in the heading or rule, or a title that names exactly
    one case. A case mentioned in passing in the lesson's prose does not —
    «Which case after which preposition» is not a genitive lesson."""
    title = Y(sec.get("title") or "")
    if re.search(r"\bwhich case|\bprepositions?\b.*\bcase|\bcase\b.*\bprepositions?\b", title):
        return None
    # «ДО + Gen.» and «К + Dat.» in one lesson means the lesson covers both:
    # only an unambiguous naming counts.
    got = {CASE_ABBR[x] for x in re.findall(
        r"\+\s*(nom|gen|dat|acc|instr?|prep|loc)\b", title + " " + Y(ctx or ""))}
    if len(got) == 1:
        return got.pop()
    if got:
        return None
    if course in BY_COURSE:
        return BY_COURSE[course]
    hits = {CASE_WORD[k] for k in CASE_WORD if re.search(r"\b" + k + r"\b", title)}
    return hits.pop() if len(hits) == 1 else None


def governor(q, blank_at):
    """The preposition standing immediately in front of this blank, if any."""
    before = q[:blank_at]
    ws = WORD.findall(before)
    return Y(ws[-1]) if ws and Y(ws[-1]) in PREP else None


def counted(q, blank_at):
    """True if a numeral or quantity word stands in front of the blank."""
    ws = re.findall(r"[\u0430-\u044f\u0451\u0410-\u042f\u04010-9]+", q[:blank_at])
    return bool(ws) and bool(NUMERAL.match(Y(ws[-1])))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--drop", action="store_true", help="quarantine the mismatches")
    ap.add_argument("--course")
    ap.add_argument("--show", type=int, default=25)
    args = ap.parse_args(argv)

    bad = collections.defaultdict(list)
    seen = kept = 0
    for course in sorted(os.listdir(ROOT)):
        d = os.path.join(ROOT, course)
        if not os.path.isdir(d) or (args.course and course != args.course):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json"):
                continue
            p = os.path.join(d, fn)
            sec = json.load(io.open(p, encoding="utf-8"))
            keep, drop = [], []
            for e in sec.get("exercises") or []:
                seen += 1
                why = reason(course, sec, e)
                if why:
                    drop.append((e, why))
                else:
                    keep.append(e)
            kept += len(keep)
            if not drop:
                continue
            bad[course].append((sec["id"], drop))
            if args.drop:
                sec["exercises"] = [dict(x, id="q%d" % (i + 1)) for i, x in enumerate(keep)]
                io.open(p, "w", encoding="utf-8").write(json.dumps(sec, ensure_ascii=False))

    n = sum(len(dr) for c in bad.values() for _, dr in c)
    print("%d exercises checked, %d flagged, %d kept" % (seen, n, seen - n))
    for course in sorted(bad):
        cn = sum(len(dr) for _, dr in bad[course])
        print("\n--- %s: %d" % (course, cn))
        shown = 0
        for sid, dr in bad[course]:
            for e, why in dr:
                if shown >= args.show:
                    break
                print("   [%s] %s" % (sid, why))
                print("       %s" % re.sub(r"\s+", " ", e.get("q") or "")[:110])
                print("       -> %s   |  %s" % (", ".join(e.get("answers") or []),
                                                re.sub(r"\s+", " ", e.get("prompt") or "")[:70]))
                shown += 1
    if args.drop:
        os.makedirs(DROPPED, exist_ok=True)
        out = {c: [{"section": s, "dropped": [x for x, _ in dr],
                    "why": [w for _, w in dr]} for s, dr in v] for c, v in bad.items()}
        io.open(os.path.join(DROPPED, "sense.json"), "w", encoding="utf-8").write(
            json.dumps(out, ensure_ascii=False, indent=1))
        print("\nquarantined to %s/sense.json" % DROPPED)
    else:
        print("\nreport only — add --drop to remove them")


def reason(course, sec, e):
    """Why this exercise does not belong here, or '' if it does."""
    if e.get("type") != "fill":
        return ""
    q = e.get("q") or ""
    blanks = [m.start() for m in re.finditer(r"___", q)]
    if len(blanks) != 1:
        return ""
    ans = (e.get("answers") or [""])[0]
    aw = WORD.findall(ans)
    if len(aw) != 1:
        return ""              # compound answers (буду писать) are not case-checked
    hint = re.findall(r"___ \(([^)]*)\)", q)
    hint = WORD.findall(hint[0])[-1] if hint and WORD.findall(hint[0]) else ""
    got = cases_of(aw[0], hint)
    if not got:
        return ""              # not a case-bearing word: nothing to check

    g = governor(q, blanks[0])
    if g:
        if got & PREP[g]:
            return ""          # a preposition stands in front and the answer
                               # agrees with it: the sentence is sound Russian,
                               # whatever case the section happens to name
        if PARTITIVE_U.match(ans) and "gent" in PREP[g]:
            return ""          # с голоду, без спросу: the partitive in -у,
                               # which the dictionary files under the dative
        return "after «%s» the answer should be %s, but %s can only be %s" % (
            g, "/".join(sorted(PREP[g])), ans, "/".join(sorted(got)))

    # Only the time course gets this check: its words have other senses
    # (среда is Wednesday and also the environment), and its sentences all
    # carry an English translation that shows which sense is meant. Elsewhere
    # the translation often hides the point, so the test would misfire.
    rx = TOPIC_RX.get(course)
    prompt = (e.get("prompt") or "").strip()
    if rx and prompt and not CITATION.match(prompt) and not rx.search(prompt):
        return "the %s course, but the sentence is not about %s" % (course, course)

    if counted(q, blanks[0]):
        return ""              # the numeral in front decides the case

    want = expected_case(course, sec, e.get("context"))
    if want and want not in got:
        return "section teaches %s, but %s can only be %s" % (
            want, ans, "/".join(sorted(got)))
    return ""


if __name__ == "__main__":
    main()
