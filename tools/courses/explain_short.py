# -*- coding: utf-8 -*-
"""A short explanation for every gap exercise outside the case courses and Counting Things:
«**hint → answer** (what form it is) — the one rule that makes it», worked out from the answer itself.

The lessons attach whole rule paragraphs to a few hundred exercise types; many of those paragraphs do not explain the
particular word (the dative rule for «логический субъект» under «с голоду»).  Here the form is analysed with pymorphy3 /
OpenCorpora (CC BY-SA 4.0): verbs (past, present, perfective future, imperative), participles, gerunds, short forms and degrees of
adjectives, conjunctions and particles, and nouns/adjectives/pronouns in a case (through case_explain, with the word that
governs the case).  A rule is stated only when the form itself shows it (the past ends in -л/-ла/-ло/-ли, the gerund is the
present stem + -я …); otherwise just what the form is.  Nothing is written for an exercise it cannot read.
Usage: explain_short.py [--apply] [--course ID ...]
"""
import io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
COURSES = os.path.join(ROOT, "public", "courses")
import case_explain as CE
M = CE.M

SKIP = {"count", "cases", "case-nom", "case-gen", "case-dat", "case-acc", "case-ins", "case-prp"}
HINT = re.compile(r"___ \(((?:[^()]|\([^()]*\))*)\)")
WORD = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)?")


def n(w):
    return w.lower().replace("ё", "е")


# ---- conjunctions, particles and other function words, by the English hint --------------------------------------------
FW = {
    "while": "«while»: opens a clause about something happening at the same time.",
    "until": "«until»: пока не is one unit that opens a time clause; the не is not translated.",
    "before": "«before» + a clause: прежде чем (the same verb form as in the main clause, or an infinitive).",
    "after": "«after» + a clause: после того как (после takes the genitive того).",
    "as soon as": "«as soon as»: opens a time clause.",
    "when": "«when»: opens a time clause.",
    "if (unreal)": "«if» in an unreal condition (improbable or contrary to fact): если бы, with the verb in the past tense.",
    "if": "«if» in a real condition: если.",
    "because": "«because»: потому что introduces the reason.",
    "since, as": "«since, as»: так как introduces the reason.",
    "although": "«although»: хотя introduces a concession.",
    "in spite of": "«in spite of»: несмотря на, followed by the accusative.",
    "or else": "«or else»: а то warns what happens otherwise.",
    "but then": "«but then»: зато sets a gain against a loss.",
    "or": "«or»: joins alternatives.",
    "(emphasis)": "an emphatic particle, placed right after the word it stresses.",
    "after all, you know": "a particle meaning «after all»: it reminds the listener of something known.",
    "can it be?": "«can it be?»: a question of surprise or doubt.",
    "really?": "«really?»: a question of doubt.",
    "even": "«even».",
    "than": "«than»: чем follows a comparative.",
    "less": "«less»: менее + adjective gives a compound comparative.",
    "more": "«more»: более + adjective gives a compound comparative.",
    "that": "«that»: что opens a subordinate clause.",
    "so that, in order to": "«so that, in order to»: чтобы introduces a purpose.",
    "about the fact that": "«about the fact that»: о (+ prepositional) том, что.",
    "let him, her, them": "«let him, her, them»: пусть + a third-person verb.",
    "let’s": "«let's»: давайте (давай to one person) + a verb.",
    "no time to": "«no time to»: некогда + infinitive.",
    "nothing to": "«nothing to»: нечего + infinitive.",
    "nowhere to": "«nowhere to»: негде (place) or некуда (direction) + infinitive.",
    "where": "«where»: где asks about place.",
}


def pairs_hint(q, ans):
    """(hint lemma, answer word, parse) for the blank, or None."""
    m = HINT.search(q or "")
    if not m or not ans:
        return None
    hw = WORD.findall(m.group(1))
    aw = WORD.findall(ans)
    if not hw or not aw:
        return None
    for h0 in (hw if "/" in m.group(1) else hw[:1]):
        hl = {n(h0)} | {n(p.normal_form) for p in M.parse(h0)}
        for a in aw:
            for p in M.parse(a):
                if n(p.normal_form) in hl:
                    return h0, a, p, aw
    return None


GEN_EN = {"masc": "masc.", "femn": "fem.", "neut": "neut."}
CASE_EN = {"nomn": "nom.", "gent": "gen.", "datv": "dat.", "accs": "acc.", "ablt": "instr.", "loct": "prep.", "gen2": "gen.", "loc2": "prep.", "acc2": "acc."}
NUM_EN = {"sing": "sg.", "plur": "pl."}
PERS = {"1per": "1st", "2per": "2nd", "3per": "3rd"}


def who_(d):
    return "%s person %s" % (PERS.get(d["person"], ""), "singular" if d["number"] == "sing" else "plural")


def tg(p):
    t = p.tag
    return {k: (str(getattr(t, k)) if getattr(t, k) else None) for k in ("POS", "case", "number", "gender", "tense", "person", "mood", "aspect", "voice", "animacy")}


def head(h, a):
    return "**%s → %s**" % (h, a)


# ---- verbs --------------------------------------------------------------------------------------------------------------
FIRST = {"ешь", "ёшь", "ет", "ёт", "ем", "ём", "ете", "ёте", "ут", "ют"}
SECOND = {"ишь", "ит", "им", "ите", "ат", "ят"}
PAST_SUF = {"masc": "л", "femn": "ла", "neut": "ло", "plur": "ли"}


def past_expl(hint, a, d):
    inf = n(hint)
    refl = inf.endswith("ся")
    core = inf[:-2] if refl else inf
    g = d["gender"] if d["number"] != "plur" else "plur"
    base = None
    if core.endswith("ть"):
        base = core[:-2]
    if base is not None and g in PAST_SUF:
        reg = base + PAST_SUF[g] + (("ся" if g in ("masc",) else "сь") if refl else "")
        if n(a) == n(reg):
            suf = PAST_SUF[g]
            drop = "-ться" if refl else "-ть"
            add = "-" + suf + (("ся" if g == "masc" else "сь") if refl else "")
            return "past tense, %s: drop %s, add %s." % (GEN_EN.get(g, "plural"), drop, add)
    if g == "masc" and (core.endswith("ти") or core.endswith("чь")) and not n(a).rstrip("ся").endswith("л"):
        return "past tense, masc.: verbs in -ти / -чь have no -л in the masculine (the other forms do)."
    return "past tense, %s (irregular stem)." % GEN_EN.get(g, "plural")


def pres_expl(hint, a, d):
    w = n(a)
    refl = w.endswith(("ся", "сь"))
    core = w[:-2] if refl else w
    who = who_(d)
    for e in sorted(FIRST, key=len, reverse=True):
        if core.endswith(e):
            return "present tense, %s: ending -%s belongs to the first (е) conjugation." % (who, e)
    for e in sorted(SECOND, key=len, reverse=True):
        if core.endswith(e):
            return "present tense, %s: ending -%s belongs to the second (и) conjugation." % (who, e)
    return "present tense, %s." % who


def hint_aspect(hint):
    asp = {str(p.tag.aspect) for p in M.parse(hint) if p.tag.POS in ("INFN", "VERB") and p.tag.aspect}
    return next(iter(asp)) if len(asp) == 1 else None


def finite_expl(hint, a, d):
    """Present / perfective future / future of быть for a finite non-past form, by the aspect of the hint verb."""
    if n(hint) == "быть":
        return "future of быть: %s." % who_(d)
    asp = hint_aspect(hint)
    if asp == "impf":
        return pres_expl(hint, a, d)
    if asp == "perf":
        return futr_expl(hint, a, dict(d, aspect="perf"))
    r = pres_expl(hint, a, d)
    return r.replace("present tense,", "present-type form,", 1)


def futr_expl(hint, a, d):
    who = who_(d)
    if d["aspect"] == "perf":
        return "perfective verb, %s: it has no present tense; the present-type ending gives the future." % who
    return "future, %s." % who


def imp_expl(hint, a, d):
    w = n(a)
    if w.endswith("тесь"):
        return "imperative, polite / plural of a reflexive verb: the singular + -те, with -сь at the end."
    if w.endswith(("ся", "сь")):
        return "imperative, singular (to «ты») of a reflexive verb: -ся after a consonant, -сь after a vowel."
    pl = w.endswith("те")
    core = w[:-2] if pl else w
    if core.endswith("й"):
        e = "-й (stem ends in a vowel)"
    elif core.endswith("и"):
        e = "-и"
    elif core.endswith("ь"):
        e = "-ь"
    else:
        e = None
    if pl:
        return "imperative, polite / plural: the singular %s + -те." % core
    return "imperative, singular (to «ты»)" + (": ending %s." % e if e else ".")


def gerund_expl(hint, a, d):
    w = n(a)
    inf = n(hint)
    asp = None
    if w.endswith(("вшись", "ав", "яв", "в", "ши", "вши")) and not w.endswith(("ая", "яя")):
        pass
    refl = inf.endswith("ся")
    if w.endswith(("я", "а", "ясь", "ась")):
        s = "gerund (деепричастие) of an imperfective verb: present stem + -%s; the action goes on at the same time as the main verb." % ("сь" if refl and w.endswith("сь") else ("я" if w.endswith(("я", "ясь")) else "а, after ж, ч, ш, щ"))
        if w.endswith(("я", "ясь")):
            s = "gerund (деепричастие) of an imperfective verb: present stem + -я%s; the action goes on at the same time as the main verb." % ("сь" if refl else "")
        elif w.endswith(("а", "ась")):
            s = "gerund (деепричастие) of an imperfective verb: present stem + -а%s (after ж, ч, ш, щ); the action goes on at the same time as the main verb." % ("сь" if refl else "")
        return s
    if w.endswith(("в", "вшись", "ши", "вши")):
        return "gerund (деепричастие) of a perfective verb: past masculine without -л + -в%s; the action is finished before the main verb." % ("шись" if refl else "")
    return "gerund (деепричастие)."


def part_expl(a, d, short):
    w = n(a)
    v, t = d["voice"], d["tense"]
    form = "short form" if short else "long form"
    if v == "actv" and t == "pres":
        ok = re.search(r"(ущ|ющ|ащ|ящ)", w)
        return "present active participle%s: 3rd person plural without -т + -щ- + adjective ending." % ("" if ok else "")
    if v == "actv" and t == "past":
        return "past active participle: past stem + -вш- (after a vowel) or -ш- (after a consonant) + adjective ending."
    if v == "pssv" and t == "pres":
        return "present passive participle: first person plural + adjective ending (-емый / -имый)."
    if v == "pssv" and t == "past":
        return "past passive participle%s: from a perfective verb, with -нн-, -енн- or -т-%s." % ("", "; the short form drops one н" if short else "")
    return "participle."


# ---- adjectives -------------------------------------------------------------------------------------------------------------
CUR_Q = [""]


def top_is_adverb(a):
    ps = M.parse(a)
    return bool(ps) and str(ps[0].tag.POS) in ("ADVB", "PRED")


def before_is_verb(q):
    toks = WORD.findall(q.split("___")[0])
    if not toks:
        return False
    ps = M.parse(toks[-1])
    return bool(ps) and str(ps[0].tag.POS) in ("VERB", "INFN")


def adj_expl(hint, a, d, p):
    pos = d["POS"]
    lemma = n(hint)
    w = n(a)
    if pos == "ADJS":
        g = d["gender"] if d["number"] != "plur" else "plur"
        if g == "neut" and top_is_adverb(a):
            return "adverb: the adjective stem + -о (here it is not the neuter short form)." if before_is_verb(CUR_Q[0]) else None
        end = {"masc": "no ending", "femn": "-а", "neut": "-е" if w.endswith("е") else "-о", "plur": "-и" if w.endswith("и") else "-ы"}.get(g, "")
        return "short form (%s): %s." % (GEN_EN.get(g, "plural"), end)
    if pos == "COMP":
        stem = lemma[:-2] if lemma.endswith(("ый", "ий", "ой")) else None
        if stem and (w == stem + "ее" or w == stem + "ей"):
            return "comparative: stem + -ее (-ей)."
        if stem and w.startswith("по") and (w[2:] == stem + "ее" or w[2:] == stem + "ей"):
            return "comparative: stem + -ее (-ей); по- adds «a little»."
        return "irregular comparative: the stem changes."
    return None


PREP_USE = {
    "в": {"accs": "into / a point in time or a day of the week", "loct": "inside / a month or a year"},
    "во": {"accs": "into / a point in time or a day of the week", "loct": "inside / a month or a year"},
    "на": {"accs": "onto / for a length of time", "loct": "on / the week"},
    "за": {"accs": "in exchange for / the time an action takes", "ablt": "behind, beyond"},
    "под": {"accs": "motion to a place under", "ablt": "location under"},
    "с": {"gent": "from, since", "ablt": "with"},
    "со": {"gent": "from, since", "ablt": "with"},
    "по": {"datv": "along / on regular days"},
    "через": {"accs": "in (time) / across"},
    "к": {"datv": "towards / by (a time)"},
}
CASE_NAME = {"nomn": "nominative", "gent": "genitive", "datv": "dative", "accs": "accusative", "ablt": "instrumental", "loct": "prepositional"}
SG_PL = {"sing": "singular", "plur": "plural"}


def find_prep(before):
    """The preposition that governs the blank (up to two modifiers between), as CE.governing_cases finds it; else None."""
    toks = CE.TOKEN.findall(before)
    gaps = 0
    for i in range(len(toks) - 1, max(len(toks) - 5, -1), -1):
        t = toks[i].lower()
        if not CE.WORD.fullmatch(toks[i]):
            return None
        if t in CE.PREP_ALL:
            return t
        if gaps >= 2:
            return None
        if t not in ("один", "одна", "одно", "одни") and any(x.tag.POS == "NUMR" for x in M.parse(t)) and not any(x.tag.POS in CE.MODIFIER_POS for x in M.parse(t)):
            return None
        if not any(x.tag.POS in CE.MODIFIER_POS for x in M.parse(t)):
            return None
        gaps += 1
    return None


NEG = ("не", "нет", "ни", "нельзя", "никогда", "некого", "нечего", "нету")


def governor_reason(q, case_tag, number):
    """«after семь» / «в + prepositional» / «нет + genitive» for the blank in q, or ''."""
    m = HINT.search(q)
    if not m:
        return ""
    before = q[:m.start()]
    g = CE.governed(before)
    if g:
        toks = [t.lower() for t in CE.TOKEN.findall(before)][-3:]
        w = next((t for t in reversed(toks) if t in CE.QUANT_SG or t in CE.QUANT_PL or t in CE.QUANT_Q), None)
        if w:
            return "after %s" % w
    pw = find_prep(before)
    if pw:
        return "%s + %s" % (pw, CASE_NAME.get(case_tag, ""))
    words = [t.lower() for t in CE.TOKEN.findall(before) if CE.WORD.fullmatch(t)]
    if case_tag == "gent" and words:
        tail = words[-4:]
        for w in reversed(tail):
            if w in NEG:
                return "нет + genitive" if w in ("нет", "нету") else "genitive after the negation «%s»" % w
            if w in ("было", "будет", "был", "была", "были"):
                continue
            break
    return ""


TIME_NOUNS = {"день", "неделя", "месяц", "год", "утро", "вечер", "ночь", "час", "минута", "секунда", "сутки", "полдень", "полночь", "понедельник", "вторник",
              "среда", "четверг", "пятница", "суббота", "воскресенье", "январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь",
              "октябрь", "ноябрь", "декабрь", "лето", "зима", "весна", "осень", "будни", "выходные", "конец", "начало", "середина", "день рождения"}
MONTHS = {"январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"}
DAYS = {"понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"}
TIME_RULE = {
    ("в", "accs"): ("the time of day, the day of the week, or how often", lambda L: L & (DAYS | {"утро", "вечер", "ночь", "час", "минута", "секунда", "день", "неделя"})),
    ("во", "accs"): ("the day of the week", lambda L: L & DAYS),
    ("в", "loct"): ("the year or the month in which something happens", lambda L: L & (MONTHS | {"год"})),
    ("на", "loct"): ("the week in which something happens", lambda L: "неделя" in L),
    ("на", "accs"): ("how long something is expected to last", lambda L: L & {"день", "неделя", "месяц", "год", "ночь", "час", "минута", "утро", "вечер", "лето", "зима"}),
    ("за", "accs"): ("the time an action takes", lambda L: L & {"день", "неделя", "месяц", "год", "ночь", "час", "минута", "секунда", "сутки"}),
    ("через", "accs"): ("«in», «after» a period of time", lambda L: L & {"день", "неделя", "месяц", "год", "ночь", "час", "минута", "секунда", "сутки"}),
    ("к", "datv"): ("the time by which something happens", lambda L: L & TIME_NOUNS),
    ("до", "gent"): ("«till», «before»", lambda L: L & TIME_NOUNS),
    ("после", "gent"): ("«after»", lambda L: L & TIME_NOUNS),
    ("с", "gent"): ("«from», «since»", lambda L: L & TIME_NOUNS),
    ("перед", "ablt"): ("«immediately before»", lambda L: L & TIME_NOUNS),
    ("по", "datv"): ("something that happens regularly (по утрам, по вторникам)", lambda L: L & TIME_NOUNS),
}


def bare_time_rule(q, case_tag, lemmas):
    """Time expressions with no preposition: the date, «how long ago», «every», «all»."""
    m = HINT.search(q)
    before, after = q[:m.start()], q[m.end():]
    words = [w.lower() for w in WORD.findall(before)]
    if case_tag == "gent" and lemmas & MONTHS and words and re.search(r"(ого|его)$", words[-1]):
        return "in a date, the day is an ordinal and the month is in the genitive"
    if case_tag == "accs" and lemmas & TIME_NOUNS and re.match(r"\s*(тому\s+)?назад\b", after):
        return "«how long ago?»: the accusative, followed by назад"
    if case_tag == "accs" and lemmas & TIME_NOUNS and lemmas & {"каждый", "весь"}:
        return "«every», «all» in a time expression take the accusative"
    return None


def time_rule(prep, case_tag, lemmas, number):
    r = TIME_RULE.get((prep, case_tag))
    if not r:
        return None
    if prep == "по" and number != "plur":
        return None
    if r[1](lemmas):
        return "%s + %s: %s" % (prep, CASE_NAME[case_tag], r[0])
    return None


CASE_TAGS = {"nom.": "nomn", "gen.": "gent", "dat.": "datv", "acc.": "accs", "instr.": "ablt", "prep.": "loct"}


def lemmatise_hint(e):
    """The exercise with its hint words in dictionary form («расходы» → «расход»): the case engine wants lemmas."""
    q = e.get("q") or ""
    m = HINT.search(q)
    if not m:
        return e
    hw, aw = WORD.findall(m.group(1)), WORD.findall((e.get("answers") or [""])[0])
    if len(hw) != len(aw):
        return e
    out = m.group(1)
    for h, a in zip(hw, aw):
        hl = {n(h)} | {n(x.normal_form) for x in M.parse(h)}
        for pa in M.parse(a):
            lem = n(pa.normal_form)
            if lem in hl and pa.tag.POS in ("NOUN", "ADJF", "PRTF", "NPRO", "NUMR"):
                nf = pa.normal_form
                if pa.tag.POS == "PRTF":
                    nf = CE.adj_lemma(pa)
                nf = (nf[:1].upper() + nf[1:]) if h[:1].isupper() else nf
                if "Pltm" in CE.tags(pa) and not pa.tag.number == "sing":
                    nf = h
                out = out.replace(h, nf, 1)
                break
    e2 = dict(e)
    e2["q"] = q[:m.start(1)] + out + q[m.end(1):]
    return e2


def case_expl(course, e):
    keep = {k: CE.PREP_ALL.get(k) for k in ("с", "со")}
    CE.PREP_ALL["с"] = {"gent", "ablt"}          # «с утра»: the accusative of с only follows a rough number («с километр»)
    CE.PREP_ALL["со"] = {"gent", "ablt"}
    try:
        return _case_expl(course, e)
    finally:
        for k, v in keep.items():
            if v is not None:
                CE.PREP_ALL[k] = v


def _case_expl(course, e):
    e = lemmatise_hint(e)
    try:
        r = CE.rewrite(dict(e), set(), True)
        if r is None:
            m0 = HINT.search(e["q"])
            words = [t.lower() for t in CE.TOKEN.findall(e["q"][:m0.start()]) if CE.WORD.fullmatch(t)] if m0 else []
            if words and any(w in NEG for w in words[-4:]) and not CE.governing_cases(e["q"][:m0.start()]):
                e2 = dict(e)
                e2["q"] = e["q"][:m0.start()] + "без " + e["q"][m0.start():] if False else e["q"][:m0.start()].rstrip() + " без ___ (" + m0.group(1) + ")" + e["q"][m0.end():]
                r = CE.rewrite(e2, set(), True)
    except Exception:
        return None
    if r is None or r is CE.DROP:
        return None
    why = r[1]
    why = re.sub(r"\s*[—–]\s*(?:DLI|forms from).*$", "", why, flags=re.S).strip()
    parts = re.split(r"\s{2,}", why)
    keep = []
    for part in parts:
        if part.startswith("«") or part.startswith("After a preposition"):
            continue
        part = re.sub(r"\s*Its forms \(.*$", "", part)
        part = re.sub(r"\s*Declension[^:]*:[^.]*\.", "", part)
        keep.append(part.strip())
    keep = [k for k in keep if k]
    if not keep:
        return None
    # the case tag in the first part: (gen. pl.)  ->  (gen. pl.: after семь)
    first = keep[0]
    mt = re.search(r"\((nom|gen|dat|acc|instr|prep)\. (sg|pl)\.([^)]*)\)", first)
    if mt:
        case_tag = CASE_TAGS.get(mt.group(1) + ".")
        num = "sing" if mt.group(2) == "sg" else "plur"
        gr = governor_reason(e["q"], case_tag, num)
        m0 = HINT.search(e["q"])
        lem = {n(w) for w in WORD.findall(m0.group(1))} if m0 else set()
        pw = find_prep(e["q"][:m0.start()]) if m0 else None
        tr = time_rule(pw, case_tag, lem, num) if pw else bare_time_rule(e["q"], case_tag, lem)
        if tr:
            first = first.replace(mt.group(0), "(%s. %s.%s)" % (mt.group(1), mt.group(2), mt.group(3)), 1)
            tr = tr[:1].upper() + tr[1:]
            first = re.sub(r"(\)\.)", lambda mm: mm.group(1) + " " + tr + ".", first, count=1)
        elif gr:
            first = first.replace(mt.group(0), "(%s. %s.%s: %s)" % (mt.group(1), mt.group(2), mt.group(3), gr), 1)
    keep[0] = first
    return "  ".join(keep)


def num_expl(e, hint, a):
    q = e["q"]
    m = HINT.search(q)
    before = q[:m.start()]
    cases = {CE._cn(p.tag.case) for p in M.parse(a) if p.tag.POS == "NUMR" and n(p.normal_form) == n(hint) and p.tag.case}
    cases &= set(CE.CASES)
    gc = CE.governing_cases(before)
    if gc:
        cases &= gc
    c = None
    why = ""
    if len(cases) == 1:
        c = next(iter(cases))
        why = governor_reason(q, c, None)
    if not why:
        after = WORD.findall(q[m.end():])[:1]
        if after:
            nc = {CE._cn(p.tag.case) for p in M.parse(after[0]) if p.tag.POS == "NOUN" and p.tag.number == "plur" and p.tag.case}
            nc &= set(CE.CASES)
            both = cases & nc
            if len(both) == 1 and "nomn" not in both and "accs" not in both:
                c = next(iter(both))
                why = "agrees with %s (%s plural)" % (after[0], CASE_NAME[c])
    if not why or c is None:
        return None
    return "**%s → %s** (%s: %s). Numerals decline like adjectives in the plural; every part of a compound numeral declines." % (
        hint, a, {"nomn": "nom.", "gent": "gen.", "datv": "dat.", "accs": "acc.", "ablt": "instr.", "loct": "prep."}[c], why)


def superlative(hint, a, p):
    lemma = n(hint)
    stem = lemma[:-2] if lemma.endswith(("ый", "ий", "ой")) else None
    w = n(a)
    if not stem:
        return None
    if re.match(re.escape(stem) + r"ейш", w):
        return "superlative: stem + -ейш- + the adjective ending."
    mut = {"к": "ч", "г": "ж", "х": "ш"}
    if stem[-1] in mut and re.match(re.escape(stem[:-1] + mut[stem[-1]]) + r"айш", w):
        return "superlative: stem (%s → %s) + -айш- + the adjective ending." % (stem[-1], mut[stem[-1]])
    if re.match(re.escape(stem) + r"айш", w):
        return "superlative: stem + -айш- (after ж, ч, ш, щ) + the adjective ending."
    return None


def rel_expl(ans, h):
    lem = "который" if h.startswith(("which")) else "какой"
    forms = set()
    for p in M.parse(ans.split()[-1]):
        if n(p.normal_form) == lem and p.tag.case:
            c = CE._cn(p.tag.case)
            if c not in CE.CASES:
                continue
            g = {"masc": "m.", "femn": "f.", "neut": "n."}.get(p.tag.gender or "", "")
            num = "pl." if p.tag.number == "plur" else "sg."
            forms.add("%s %s%s" % (CE.CASE_EN[c], num, (" " + g) if g and num == "sg." else ""))
    if not forms or len(forms) > 3:
        return None
    if lem == "который":
        return "**%s** — «который» takes its gender and number from the noun it refers to and its case from its own clause (here: %s)." % (ans, " or ".join(sorted(forms)))
    return "**%s** — «какой» agrees with the noun it asks about (here: %s)." % (ans, " or ".join(sorted(forms)))


def li_expl(hint, ans):
    if n(hint) in ("вряд", "едва"):
        return "**%s** — a set phrase: «hardly, unlikely»." % ans
    return "**%s** — ли comes right after the word the question is about (%s): a yes/no question." % (ans, hint)


def bare_time_first(e, h):
    q, ans = e["q"], e["answers"][0]
    m = HINT.search(q)
    after = q[m.end():]
    hw = [n(w) for w in WORD.findall(h)]
    aw = WORD.findall(ans)
    if not aw:
        return None
    lem = set()
    for w in hw:
        lem |= {w} | {n(x.normal_form) for x in M.parse(w)}
    acc = any(p.tag.case in ("accs", "nomn") and n(p.normal_form) in lem for p in M.parse(aw[-1]))
    if acc and lem & TIME_NOUNS and re.match(r"\s*(тому\s+)?назад\b", after):
        return "**%s назад** — «how long ago?»: the accusative, followed by назад." % ans
    if acc and lem & TIME_NOUNS and lem & {"каждый", "весь"} and len(aw) == 2 and not find_prep(q[:m.start()]):
        return "**%s** — «every», «all» in a time expression take the accusative." % ans
    return None


def digits_to_lemmas(e):
    """«___ (3-му)» / «___ (1)» → «___ (третий)» / «___ (один)»: the numeral exercises hint with digits; the dictionary form of the answer stands in."""
    q = e.get("q") or ""
    m = HINT.search(q)
    if not m or not re.fullmatch(r"\s*\d+(?:-[а-я]+)?\s*", m.group(1)):
        return e
    aw = WORD.findall((e.get("answers") or [""])[0])
    if not aw:
        return e
    lem = []
    for w in aw:
        ps = [p for p in M.parse(w) if p.tag.POS in ("NUMR", "ADJF", "NPRO") or (str(p.tag.POS) == "NOUN" and n(p.normal_form) in ("сорок", "сто", "тысяча", "миллион"))]
        ordinal = "-" in m.group(1)
        if ordinal:
            ps2 = [p for p in ps if p.tag.POS == "ADJF"]
            ps = ps2 or ps
        if not ps:
            return e
        lem.append(ps[0].normal_form)
    e2 = dict(e)
    e2["q"] = q[:m.start(1)] + " ".join(lem) + q[m.end(1):]
    return e2


def classify_and_explain(course, e):
    e = digits_to_lemmas(e)
    q = e.get("q") or ""
    CUR_Q[0] = q
    ans = (e.get("answers") or [""])[0]
    m = HINT.search(q)
    if not m or not ans:
        return None
    h = m.group(1).strip()
    if not re.search(r"[A-Za-zА-Яа-яЁё]", h):
        return None                       # digits: the numeral drills
    if not re.search(r"[А-Яа-яЁё]", h):
        txt = FW.get(h.strip())
        if txt:
            return "**%s** — %s" % (ans, txt)
        if re.match(r"(which|what)", h.strip()):
            return rel_expl(ans, h.strip())
        return None
    ли = bool(re.search(r"\+\s*ли\b", h))
    pr = pairs_hint(q, ans)
    if re.search(r"[А-Яа-яЁё]+\s+___", q):
        import count_explain as CX
        try:
            cx = CX.counted(lemmatise_hint(e))
        except Exception:
            cx = None
        if cx:
            return cx
    bt = bare_time_first(e, h)
    if bt:
        return bt
    if not pr:
        if ли:
            return li_expl(WORD.findall(h)[0], ans)
        return case_expl(course, e)
    hint, a, p, aw = pr
    d = tg(p)
    pos = d["POS"]
    hd = head(hint, " ".join(aw))
    if "/" in h and pos in ("VERB", "INFN", "GRND", "PRTF", "PRTS"):
        hs = [w for w in WORD.findall(h) if n(w) != n(hint)]
        asp = {"perf": "perfective", "impf": "imperfective"}.get(hint_aspect(hint) or "", "")
        base = "infinitive" if pos == "INFN" else ""
        out = None
        if pos == "VERB":
            if d["mood"] == "impr": out = imp_expl(hint, a, d)
            elif d["tense"] == "past": out = past_expl(hint, a, d)
            elif d["tense"] in ("pres", "futr"): out = finite_expl(hint, a, d)
        elif pos == "GRND": out = gerund_expl(hint, a, d)
        if asp:
            what = out if out else ("infinitive." if pos == "INFN" else "")
            if what:
                return "%s — %s (%s; its partner: %s)" % (hd, what.rstrip("."), asp, ", ".join(hs)) + "."
    if pos == "NUMR":
        return num_expl(e, hint, a)
    tail = " The particle ли follows the verb: a yes/no question." if ли else ""
    out = None
    if pos == "VERB":
        if d["mood"] == "impr":
            out = imp_expl(hint, a, d)
        elif d["tense"] == "past":
            out = past_expl(hint, a, d)
        elif d["tense"] in ("pres", "futr"):
            out = finite_expl(hint, a, d)
    elif pos == "GRND":
        out = gerund_expl(hint, a, d)
    elif pos in ("PRTF", "PRTS"):
        out = part_expl(a, d, pos == "PRTS")
    elif pos in ("ADJS", "COMP"):
        out = adj_expl(hint, a, d, p)
    if out is None and pos in ("ADJF", "COMP", "ADJS"):
        sup = superlative(hint, a, p)
        if sup:
            out = sup
    if out:
        return "%s — %s%s" % (hd, out, tail)
    if ли:
        return li_expl(hint, " ".join(aw))
    return case_expl(course, e)


PROMPT_CASE = {"nominative": "nomn", "genitive": "gent", "dative": "datv", "accusative": "accs", "instrumental": "ablt", "prepositional": "loct"}
SPECIFIC_TABLE_RULE = {"g1-spelling", "g4-noun-irregular", "g5-noun-awkward", "g15-irregular-verbs", "g13-mutation"}


def unquote(t):
    t = (t or "").strip()
    t = re.sub(r"^«|»$", "", t).strip()
    return t


def drill_expl(course, fn, e):
    """The form drills (numerals n-sets, tables): «**студент → студенту** (dat. sg.) …» from the answer and the case the prompt names."""
    q = e.get("q") or ""
    m = HINT.search(q)
    ans = (e.get("answers") or [""])[0]
    if not m or not ans:
        return None
    h = m.group(1).strip()
    prompt = (e.get("prompt") or "").strip()
    rule = unquote(e.get("context"))
    if course == "numerals" and re.match(r"\d+\s*·", h):
        words = h.split("·", 1)[1].strip()
        what = prompt[:1].lower() + prompt[1:] if prompt else ""
        return "**%s → %s** — %s. %s" % (words, ans, what, rule.rstrip(".") + "." if rule else "") if what else None
    if course == "numerals" and re.fullmatch(r"[А-Яа-яЁё]+", h):
        what = prompt[:1].lower() + prompt[1:] if prompt else ""
        return "**%s → %s** — %s. %s" % (h, ans, what, rule.rstrip(".") + "." if rule else "") if what else None
    if course == "tables":
        out = classify_and_explain(course, e)
        if out and not out.startswith("**" + ans):
            return out
        # a noun, adjective or pronoun in the case(s) the prompt names
        wc = {c for w, c in PROMPT_CASE.items() if w in prompt.lower()}
        if wc:
            e2 = dict(e)
            try:
                r = CE.rewrite(e2, wc, False)
            except Exception:
                r = None
            if r is not None and r is not CE.DROP:
                why = r[1]
                why = re.sub(r"\s*[—–]\s*(?:DLI|forms from).*$", "", why, flags=re.S).strip()
                parts = [re.sub(r"\s*Its forms \(.*$", "", p_).strip() for p_ in re.split(r"\s{2,}", why) if not p_.startswith(("«", "After a preposition"))]
                parts = [re.sub(r"\s*Declension[^:]*:[^.]*\.", "", p_).strip() for p_ in parts]
                parts = [p_ for p_ in parts if p_]
                if parts:
                    return "  ".join(parts) + ((" " + rule.rstrip(".") + ".") if rule and fn[:-5] in SPECIFIC_TABLE_RULE else "")
        if fn[:-5] in SPECIFIC_TABLE_RULE and rule:
            hl = WORD.findall(h)
            return "**%s → %s** — %s. %s" % (hl[0] if hl else h, ans, prompt[:1].lower() + prompt[1:], rule.rstrip(".") + ".")
    return None


def iter_files(only):
    for cid in sorted(os.listdir(COURSES)):
        if cid in SKIP or (only and cid not in only):
            continue
        d = os.path.join(COURSES, cid)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json") and fn != "exam.json":
                yield cid, os.path.join(d, fn)


DONE = {"aspect", "verbs", "tenses", "forms", "compare", "complex", "adv3", "inter2", "stories", "time", "tables", "numerals", "gramterms"}      # courses this explains


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    apply = "--apply" in argv
    only = set()
    if "--course" in argv:
        i = argv.index("--course")
        only = set(a for a in argv[i + 1:] if not a.startswith("--"))
    only = (only & DONE) if only else DONE
    stats = {}
    for cid, p in iter_files(only):
        try:
            j = json.load(io.open(p, encoding="utf-8"))
        except ValueError:
            continue
        ex = j.get("exercises") or []
        if not ex:
            continue
        if cid == "gramterms":
            tm = {t["ru"]: t for t in j.get("terms") or []}
            for e in ex:
                t = tm.get(e.get("k"))
                if t:
                    e["why"] = "**%s** — %s%s." % (t["ru"], t["en"], " (abbreviated %s)" % t["abbr"] if t.get("abbr") else "")
                    e["context"] = ""
                    stats.setdefault(cid, [0, 0])[0] += 1
            if apply:
                io.open(p, "w", encoding="utf-8").write(json.dumps(j, ensure_ascii=False))
            continue
        kept = []
        for e in ex:
            if not isinstance(e, dict) or not e.get("answers"):
                kept.append(e)
                continue
            try:
                w = None
                if cid in ("tables", "numerals"):
                    if not e.get("context") and e.get("why"):
                        w = e["why"]                                # already done in an earlier run
                    else:
                        w = drill_expl(cid, os.path.basename(p), e)
                if not w and not (cid in ("tables",) and False):
                    w = classify_and_explain(cid, e)
            except Exception as x:                                  # an exercise this cannot read gets no explanation
                w = None
            if w:
                import tidy_explanations as TE
                w = TE.trim_case(w)
            st = stats.setdefault(cid, [0, 0])
            st[0 if w else 1] += 1
            if not w:
                continue                                            # no explanation, no exercise
            e["why"] = w
            e["context"] = ""
            kept.append(e)
        j["exercises"] = kept
        if apply:
            io.open(p, "w", encoding="utf-8").write(json.dumps(j, ensure_ascii=False))
    print("explain_short (explained, without):", {k: tuple(v) for k, v in stats.items()}, "" if apply else "(dry run)")


if __name__ == "__main__":
    main()
