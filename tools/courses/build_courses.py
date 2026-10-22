#!/usr/bin/env python3
"""Build the Courses tab: each course's sections → public/courses/<course>/<section>.json,
and the outline (titles, section lists, exercise counts) → src/courses-outline.js,
which the app and the server's badge code both read.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/courses/build_courses.py
"""
import importlib, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

COURSES = [
    {
        "id": "wikibook", "title": "Russian Grammar from the Wikibook", "short": "Wikibook", "mark": "W",
        "blurb": "Twenty short lessons, from your first «Привет!» to the six cases, verbs of motion and numbers — "
                 "a guided tour of everyday Russian grammar.",
        "credit": "Adapted from the Wikibooks Russian textbook and its contributors",
        "creditUrl": "https://en.wikibooks.org/wiki/Russian",
        "license": "CC BY-SA 4.0", "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/",
        "modules": ["wikibook_a", "wikibook_b", "wikibook_c"],
        "order": ["greetings", "no-the-no-is", "gender", "plurals", "pronouns", "adjectives",
                  "present", "past", "future", "aspect",
                  "cases", "accusative", "prepositional", "genitive", "dative", "instrumental",
                  "reflexive", "going", "questions", "numbers"],
    },
]
COURSES.append({
    "id": "motion", "title": "Verbs of Motion", "short": "Motion", "mark": "→",
    "blurb": "Going, carrying, leading and driving — the unprefixed pairs, then every prefix from при- to с-, "
             "with drills: a course of its own, also in the Grammar tab.",
    "credit": "Based on the Defense Language Institute Russian Basic Course, Grammar Reference Book and Student Workbooks (US Government work, public domain)",
    "creditUrl": "https://www.fsi-language-courses.org/russian/courses/dli-russian-basic-course",
    "license": "Public domain", "licenseUrl": "",
    "modules": ["motion_a", "motion_b", "motion_c"], "order": None,
})
DLI_CREDIT = "Transcribed from the Defense Language Institute Russian Basic Course, Grammar Reference Books I (1970) and II (1965) — a US Government work in the public domain"
DLI_URL = "https://www.fsi-language-courses.org/russian/courses/dli-russian-basic-course"
COURSES.append({
    "id": "time", "title": "Time and Dates", "short": "Time", "mark": "◷",
    "blurb": "Который час? Past and to the hour, the 12- and 24-hour clocks, days, weeks, months, years, full dates, "
             "and every preposition of time — in DLI's own words, with its sentences as exercises.",
    "credit": DLI_CREDIT + "; word lists from the Wikibooks Russian textbook (CC BY-SA 4.0)", "creditUrl": DLI_URL,
    "license": "Public domain · CC BY-SA 4.0", "licenseUrl": "",
    "modules": ["time_a", "time_b"], "order": None,
})
COURSES.append({
    "id": "count", "title": "Counting Things", "short": "Counting", "mark": "№",
    "blurb": "Numbers and the nouns after them, numbers in every case, thousands and millions, ordinals, fractions, "
             "approximate amounts — in DLI's own words, with its sentences as exercises.",
    "credit": DLI_CREDIT, "creditUrl": DLI_URL, "license": "Public domain", "licenseUrl": "",
    "modules": sorted(m[:-3] for m in os.listdir(HERE) if m.startswith("count_") and m.endswith(".py")), "order": None,
})
COURSES.append({
    "id": "cases", "title": "Nouns and Adjectives in Cases", "short": "Cases", "mark": "Пп",
    "blurb": "All six cases, singular and plural: what each case does, every ending, the exceptions, adjectives, "
             "possessives, surnames and which preposition takes which case — in DLI's own words, with its sentences as exercises.",
    "credit": DLI_CREDIT, "creditUrl": DLI_URL, "license": "Public domain", "licenseUrl": "",
    "modules": ["cases_a", "cases_b"], "order": None,
})
COURSES.append({
    "id": "forms", "title": "Verb Forms and Participles", "short": "Verb forms", "mark": "щ",
    "blurb": "The imperative, пусть and давайте, the conditional with бы, all four participles, the -ся passive and both "
             "деепричастия — how each is formed and used, in DLI's own words, with its sentences as exercises.",
    "credit": DLI_CREDIT, "creditUrl": DLI_URL, "license": "Public domain", "licenseUrl": "",
    "modules": ["forms_a", "forms_b"], "order": None,
})
import case_courses
for _meta, _secs in case_courses.COURSE_DEFS:
    COURSES.append(dict(_meta, modules=[], order=None, sections=_secs))
import adv_courses
for _meta, _secs in adv_courses.COURSE_DEFS:
    COURSES.append(dict(_meta, modules=[], order=None, sections=_secs))
import topic_courses
for _meta, _secs in topic_courses.COURSE_DEFS:
    COURSES.append(dict(_meta, modules=[], order=None, sections=_secs))
import story_course
for _meta, _secs in story_course.COURSE_DEFS:
    COURSES.append(dict(_meta, modules=[], order=None, sections=_secs))
for _c in COURSES:
    if _c["id"] == "time":
        _c["sections"] = case_courses.TIME_MORE
        # More «в / на + accusative» practice — real sentences found by
        # tools/courses/time_more.py (the library's books, and Tatoeba when it
        # was given the pair file). One lesson, DLI's words, then the sets.
        _tm = os.path.join(HERE, "time_more.json")
        if os.path.exists(_tm):
            _d = json.load(io.open(_tm, encoding="utf-8"))
            from kit import SEC, P, H, NOTE, EX
            _more = _d.get("day", []) + _d.get("na", []) + _d.get("unit", []) + _d.get("freq", [])
            _c["sections"].append(SEC("t14-on-wednesday", "On Wednesday, in that minute, the next day: в and на + accusative", [
                H("Days of the week"),
                P("To indicate the day of the week when something happened or will happen, the preposition в + Acc. is used:"),
                EX(["Какой сегодня день? — Сегодня пятница.", ""], ["Когда вы были там? — Я был там в пятницу.", ""],
                   ["В какой день он был там? — Он был там во вторник.", ""]),
                P("The days of the week are not capitalized. «Во» before «вт» for euphony."),
                NOTE("DLI, Lesson 19."),
                H("The preposition «в» + accusative"),
                P("**В + Accusative** is used: (a) to indicate the time of the day; (b) to indicate the day of the week; "
                  "(c) to indicate how frequently something occurs."),
                EX(["Собрание начинается в три часа.", ""], ["Я приехал туда в пять часов.", ""],
                   ["В какой день вы были там? Я был там в пятницу.", ""], ["Я хожу в штаб два раза в день.", ""],
                   ["Он приезжает сюда раз в месяц.", ""]),
                P("Note also the following expressions: В минуту опасности. В годы войны. Во время войны. В первый раз. "
                  "В следующий раз. В последний раз."),
                P("Note that a week takes \"НА + Loc.\"; units larger than a week (month, year) take \"В + Loc.\"; units "
                  "smaller than a week (day, hour etc.) take \"В + Acc.\" Exception: НА следующий день — the next day, "
                  "the following day."),
                NOTE("DLI, Lesson 73. Exercises: sentences from the library's public-domain books, and from Tatoeba "
                     "(tatoeba.org, CC BY 2.0 FR) where a translation is given."),
            ], more=_more))
if os.path.exists(os.path.join(HERE, "tense_pairs.json")):
    COURSES.append({
        "id": "tenses", "title": "English Tenses in Russian", "short": "Tenses", "mark": "⇄",
        "blurb": "How each English tense comes out in Russian: DLI's rules, and real translated sentence pairs from Tatoeba "
                 "for the commonest verbs in the library.",
        "credit": DLI_CREDIT + "; example sentences from Tatoeba (tatoeba.org), CC BY 2.0 FR", "creditUrl": DLI_URL,
        "license": "Public domain · CC BY 2.0 FR", "licenseUrl": "https://creativecommons.org/licenses/by/2.0/fr/",
        "modules": ["tense_course"], "order": None,
    })
if os.path.exists(os.path.join(HERE, "dli_a.py")):
    COURSES.append({
        "id": "dli", "title": "DLI Basic Russian Grammar", "short": "DLI", "mark": "D",
        "blurb": "The grammar of the US Defense Language Institute's Basic Russian course — thorough, systematic, "
                 "with drills — rewritten as lessons and exercises.",
        "credit": "Based on the Defense Language Institute Russian Basic Course (US Government work, public domain)",
        "creditUrl": "https://www.fsi-language-courses.org/russian/courses/dli-russian-basic-course",
        "license": "Public domain", "licenseUrl": "",
        "modules": sorted(m[:-3] for m in os.listdir(HERE) if m.startswith("dli_") and m.endswith(".py")),
        "order": None,
    })


import tables_course
COURSES.append({
    "id": "tables", "title": "Grammar Tables", "short": "Tables", "mark": "\u2630",
    "blurb": "",
    "credit": "Rules quoted from the Defense Language Institute Russian Basic Course, Grammar Reference Book "
              "(a US Government work in the public domain); every Russian form generated from the OpenCorpora "
              "dictionary (CC BY-SA 4.0) by tools/courses/gen_tables.py; the sixteen conjugation classes follow "
              "the scheme in Wiktionary's Appendix:Russian verbs (CC BY-SA 4.0), after Zaliznyak",
    "creditUrl": DLI_URL,
    "license": "Public domain \u00b7 CC BY-SA 4.0", "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/",
    "modules": ["tables_course"], "order": None,
})


import numerals_course
COURSES.append({
    "id": "numerals", "title": "Declined Numerals", "short": "Numerals", "mark": "123",
    "blurb": "",
    "credit": "Rules quoted from the Defense Language Institute Russian Basic Course, Grammar Reference Books I and II "
              "(a US Government work in the public domain); every Russian form from the OpenCorpora dictionary "
              "(CC BY-SA 4.0), put together by those rules in tools/courses/gen_numerals.py",
    "creditUrl": DLI_URL,
    "license": "Public domain \u00b7 CC BY-SA 4.0", "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/",
    "modules": ["numerals_course"], "order": None,
})


import clock_course
COURSES.append({
    "id": "clock", "title": "Telling the Time", "short": "Clock", "mark": "\u25f7",
    "blurb": "",
    "credit": "Rules from the Defense Language Institute Russian Basic Course, Grammar Reference Book, Lessons 40, 73 "
              "and 74 (a US Government work in the public domain); every time in words is dictionary forms (OpenCorpora, "
              "CC BY-SA 4.0) put together by those rules in tools/courses/gen_clock.py",
    "creditUrl": DLI_URL,
    "license": "Public domain \u00b7 CC BY-SA 4.0", "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/",
    "modules": ["clock_course"], "order": None,
    "repeat": True,     # practice to repeat as often as you like: no sections "finished", no ticks
})


# Grammar in Russian — the terms. Needs tools/courses/gramterms_src.json
# (python3 tools/courses/gramterms_fetch.py, where Wikipedia is reachable).
import gramterms_course
if gramterms_course.SECTIONS:
    COURSES.append({
        "id": "gramterms", "title": "Grammar in Russian: the Terms", "short": "Terms", "mark": "\u00a7",
        "blurb": "",
        "credit": "Definitions from the Russian Wikipedia (CC BY-SA 4.0), each article named where it is quoted; "
                  "dictionary abbreviations from OpenCorpora (CC BY-SA 4.0)",
        "creditUrl": "https://ru.wikipedia.org/",
        "license": "CC BY-SA 4.0", "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/",
        "modules": ["gramterms_course"], "order": None,
    })


# Practice drills from Tatoeba (tools/courses/tatoeba_drills.py): a section
# of real sentences after each section they belong to.
DRILLS_P = os.path.join(HERE, "drills.json")
DRILLS = json.load(io.open(DRILLS_P, encoding="utf-8")) if os.path.exists(DRILLS_P) else {}
TATOEBA_NOTE = "Exercises: sentences and translations from Tatoeba (tatoeba.org, CC BY 2.0 FR)."


PRACTICE_SIZE = 20
REAL_NOTE = "Exercises: sentences from Tatoeba (tatoeba.org, CC BY 2.0 FR) and from the library's public-domain books."


def with_practice(cid, secs):
    """Each section, then its practice sets: the Tatoeba drills (drills.json) and a
    case-course section's further sentences ("more"), PRACTICE_SIZE at a time."""
    out = []
    for s in secs:
        more = list(s.pop("more", None) or [])
        out.append(s)
        exs = (DRILLS.get(cid) or {}).get(s["id"]) or []
        sets = [exs] if len(exs) >= 4 else []
        sets += [more[k:k + PRACTICE_SIZE] for k in range(0, len(more), PRACTICE_SIZE) if len(more[k:k + PRACTICE_SIZE]) >= 5]
        for n, xs in enumerate(sets, 1):
            note = TATOEBA_NOTE if xs is exs else (s.get("moreNote") or REAL_NOTE)
            out.append({"id": s["id"] + "-practice" + ("" if n == 1 else "-%d" % n),
                        "title": "Practice%s: %s" % ("" if len(sets) == 1 else " %d" % n, s["title"]),
                        "sub": "%d real sentences" % len(xs),
                        "blocks": [{"t": "note", "text": note}],
                        "exercises": xs})
    return out


# Courses written by us rather than taken from a source: not built.
NOT_BUILT = {"wikibook", "dli", "motion"}
# Courses transcribed from the DLI book: keep the exercises that are its own
# sentences and forms to type; drop multiple-choice ones (their wrong options
# were ours) and keep only the source line of each explanation.
DLI_MODULE_COURSES = {"time", "count", "cases", "forms"}


def clean_dli_exercises(exs):
    out = []
    for e in exs:
        if e.get("type") != "fill":
            continue
        why = e.get("why") or ""
        k = why.find("From the DLI")
        e = dict(e, why=why[k:] if k >= 0 else "")
        out.append(e)
    return out


def trusted(e):
    why = e.get("why") or ""
    if not why or why.startswith("From the DLI"):
        return False
    return HINTS is None or HINTS.good(e) is not False


try:
    import hint_check as HINTS
except ImportError:
    HINTS = None


# The Courses tab opens on these groups. A course not named here is Intermediate.
LEVELS = {
    "cases": "Beginner", "case-nom": "Beginner", "case-gen": "Beginner", "case-dat": "Beginner",
    "case-acc": "Beginner", "case-ins": "Beginner", "case-prp": "Beginner",
    "verbs": "Beginner", "count": "Beginner", "tables": "Beginner",
    "aspect": "Intermediate", "forms": "Intermediate", "compare": "Intermediate", "pronouns": "Intermediate",
    "complex": "Intermediate", "inter2": "Intermediate", "numerals": "Intermediate", "tenses": "Intermediate",
    "adv3": "Advanced", "stories": "Advanced", "gramterms": "Advanced",
    "time": "Dates and Times", "clock": "Dates and Times",
}
LEVEL_ORDER = ["Beginner", "Intermediate", "Advanced", "Dates and Times"]


def main():
    outline = []
    for c in [x for x in COURSES if x["id"] not in NOT_BUILT]:
        secs = []
        for m in c["modules"]:
            for x in importlib.import_module(m).SECTIONS:
                x = dict(x)
                if c["id"] in DLI_MODULE_COURSES:
                    x["exercises"] = clean_dli_exercises(x.get("exercises") or [])
                secs.append(x)
        secs += [dict(x) for x in (c.get("sections") or [])]
        secs = with_practice(c["id"], secs)
        by = {s["id"]: s for s in secs}
        if len(by) != len(secs):
            raise SystemExit("duplicate section id in " + c["id"])
        order = c["order"] or [s["id"] for s in secs]
        missing = [i for i in order if i not in by]
        if missing:
            raise SystemExit("missing sections: %s" % missing)
        out_dir = os.path.join(ROOT, "public", "courses", c["id"])
        os.makedirs(out_dir, exist_ok=True)
        osecs = []
        for sid in order:
            s = by[sid]
            exs = []
            # Only fill-in exercises: the multiple-choice distractors were ours.
            # and not the DLI-based items whose blank-and-hint format we made, nor any
            # item whose bracket hint is not a form of the answer's own word.
            # An exercise marked `keep` is the course's own material whatever its
            # kind: the grammar terms matched to their English, the definition quiz.
            for e in [x for x in s["exercises"] if x.get("keep") or (x["type"] != "mc" and trusted(x))]:
                exs.append(dict(e, id="q%d" % (len(exs) + 1)))
            data = {"id": sid, "title": s["title"], "blocks": s["blocks"], "exercises": exs}
            if s.get("terms"):
                data["terms"] = s["terms"]       # the cards a section's review drill deals (the grammar terms)
            if s.get("stream"):
                data["stream"] = True      # one drill at a time, with a Next button
                if s.get("prompts"):
                    data["prompts"] = s["prompts"]
                # The explanation is the same for every drill of a kind: kept
                # once, under the kind, instead of on each of 1,440 drills.
                whys, ctxs = {}, {}
                for x in exs:
                    if x.get("k") and x.get("why"):
                        whys.setdefault(x["k"], x["why"])
                        del x["why"]
                    if x.get("k") and x.get("context"):
                        ctxs.setdefault(x["k"], x["context"])
                        del x["context"]
                if whys:
                    data["whys"] = whys
                if ctxs:
                    data["ctxs"] = ctxs
            io.open(os.path.join(out_dir, sid + ".json"), "w", encoding="utf-8").write(
                json.dumps(data, ensure_ascii=False, separators=(",", ":")))
            o = {"id": sid, "title": s["title"], "n": len(exs)}
            if s.get("stream"):
                o["stream"] = True
            osecs.append(o)
        meta = {k: v for k, v in c.items() if k not in ("modules", "order", "sections")}
        meta["blurb"] = ""          # descriptions were ours; the credit line says where the course comes from
        meta["sections"] = osecs
        meta["level"] = LEVELS.get(meta["id"], "Intermediate")
        outline.append(meta)
        print("%-10s %2d sections, %3d exercises" % (c["id"], len(osecs), sum(s["n"] for s in osecs)))
    # Writing the section JSONs drops the `context` field that
    # attach_context.py puts on every exercise, so it is re-applied here:
    # building and explaining are one step, and a rebuild can never ship
    # exercises with nothing but a citation for an explanation.
    # The time course: each exercise gets the DLI rule for the construction
    # its own sentence uses, and a sentence using none the course teaches is
    # taken out (tools/courses/_dropped/time-unexplained.json). Runs before
    # attach_context, which leaves an exercise with a context alone.
    try:
        import explain_time
    except ImportError:
        print("explain_time skipped (pymorphy3 not installed)")
    else:
        explain_time.main(["--apply"])

    import attach_context
    attach_context.main(["--apply"])

    # And drop any practice sentence that does not actually exercise the
    # section it was mined into: «я забочусь об окружающей среде» matched среда,
    # Wednesday, but is about the environment. Needs pymorphy3; without it the
    # build still works and the check is simply skipped.
    try:
        import sense_check
    except ImportError:
        print("sense_check skipped (pymorphy3 not installed)")
    else:
        sense_check.main(["--drop"])

    # «весною» in a sentence from the library: «весной» is right too.
    try:
        import answer_variants
    except ImportError:
        print("answer_variants skipped (pymorphy3 not installed)")
    else:
        answer_variants.main(["--apply"])

    # The time course is dealt again as one chapter per construction, each a
    # finite stream, now that every exercise carries its construction (`k`).
    try:
        import restream_time
        from explain_time import R as TIME_RULES
    except ImportError:
        print("restream_time skipped (pymorphy3 not installed)")
    else:
        for meta in outline:
            if meta["id"] == "time":
                meta["sections"] = restream_time.restream(TIME_RULES)

    # attach_context and sense_check rewrote the section files, and
    # sense_check removed some exercises, so the counts in the outline are
    # read back off disk rather than trusted from before.
    for meta in outline:
        for o in meta["sections"]:
            p = os.path.join(ROOT, "public", "courses", meta["id"], o["id"] + ".json")
            j = json.load(io.open(p, encoding="utf-8"))
            # An endless stream has no end to reach: it counts as a lesson, finished
            # when opened. A finite one is finished when every exercise is right.
            o["n"] = 0 if (j.get("stream") and not j.get("finite")) else len(j.get("exercises") or [])
            if j.get("stream"):
                o["stream"] = True
            if j.get("finite"):
                o["finite"] = True

    # Translated sentences first; the untranslated go where there are enough.
    import prefer_translated
    prefer_translated.run()
    for meta in outline:
        for o in meta["sections"]:
            p = os.path.join(ROOT, "public", "courses", meta["id"], o["id"] + ".json")
            j = json.load(io.open(p, encoding="utf-8"))
            if not (j.get("stream") and not j.get("finite")):
                o["n"] = len(j.get("exercises") or [])

    # Every exercise explained by the rule for its own construction — the
    # lesson's sentence about that preposition, tense or degree — and an
    # exercise testing something its section does not teach taken out
    # (tools/courses/_dropped/pertinence.json). Needs pymorphy3.
    # Every pattern a lesson shows, practised: sentences found for the
    # patterns its exercises lacked (tools/courses/coverage_fill.json, from
    # coverage.py --mine) are added to the lesson first.
    import coverage
    coverage.main(["--apply"])
    # The prose set for reading: lists out of "a. … b. …", paragraphs of two
    # sentences, the constructions in bold (tools/courses/prose.py).
    import prose
    prose.main(["--apply"])
    import pertinence
    pertinence.main(["--apply"])
    for meta in outline:
        kept = []
        for o in meta["sections"]:
            p = os.path.join(ROOT, "public", "courses", meta["id"], o["id"] + ".json")
            j = json.load(io.open(p, encoding="utf-8"))
            if not (j.get("stream") and not j.get("finite")):
                o["n"] = len(j.get("exercises") or [])
            # a practice set left with nothing to practise is no section
            if o["n"] == 0 and re.search(r"-practice(?:-\d+)?$", o["id"]):
                os.remove(p)
                continue
            kept.append(o)
        meta["sections"] = kept

    # The exam at the end of each course, from the chapters' own exercises.
    import make_exams
    make_exams.add_exams(outline)

    js = ("// Written by tools/courses/build_courses.py — the courses, their sections and\n"
          "// how many exercises each has. The lessons themselves are in public/courses/.\n"
          "export default " + json.dumps(outline, ensure_ascii=False, indent=1) + ";\n")
    io.open(os.path.join(ROOT, "src", "courses-outline.js"), "w", encoding="utf-8").write(js)


if __name__ == "__main__":
    main()
