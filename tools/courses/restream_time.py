#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Time and Dates course, one chapter per construction.

The course is built as fourteen DLI lessons, each with practice sets after
it — which put the same construction in several places and the same answer
(«этой неделе») in front of the reader a hundred times. Here, after every
exercise has been given its construction by explain_time.py (`k`), the course
is dealt again:

  * one chapter per construction — «В + accusative: во вторник, в пять
    часов», «НА + prepositional: на этой неделе», … — opening with DLI's rule
    for it and then its exercises one at a time, in a new random order each
    time, with a Next button, finished once every one has been answered right
    (a finite stream, unlike the clock's endless one);
  * no more than a few exercises with the same answer in a chapter (a dozen
    for «в + accusative», where seven days of the week carry most of it and
    the reader asked for more of those), so the sentences vary;
  * the DLI lessons themselves kept after the chapters, as reading pages.

Run by build_courses.py after the explanations, the sense check and the
answer variants; it rewrites public/courses/time/ and returns the outline.
"""
import io, json, os, re, random

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TIME = os.path.join(ROOT, "public", "courses", "time")

# The chapters, in the order they are taught: construction key → title.
ORDER = [
    # key, the formula in big letters, the examples (Russian, English), the chapter title's tail
    ("clock", u"в + accusative · в + prepositional · без + genitive",
     [(u"в два часа", u"at two o'clock"), (u"в половине третьего", u"at half past two"), (u"без десяти три", u"at ten to three")],
     u"At two o'clock"),
    ("v-acc-day", u"В + accusative",
     [(u"в понедельник", u"on Monday"), (u"во вторник", u"on Tuesday"), (u"в среду", u"on Wednesday"), (u"в четверг", u"on Thursday"),
      (u"в пятницу", u"on Friday"), (u"в субботу", u"on Saturday"), (u"в воскресенье", u"on Sunday"), (u"в прошлую субботу", u"last Saturday")],
     u"On Tuesday, on Wednesday: the days of the week"),
    ("v-acc", u"В + accusative",
     [(u"в пять часов", u"at five o'clock"), (u"раз в неделю", u"once a week"), (u"в тот день", u"on that day"), (u"в эту минуту", u"at this moment"), (u"в первый раз", u"for the first time")],
     u"At five, once a week, that day, the first time"),
    ("instr", u"The instrumental, with no preposition",
     [(u"утром", u"in the morning"), (u"днём", u"in the afternoon"), (u"вечером", u"in the evening"), (u"ночью", u"at night"), (u"весной", u"in spring"), (u"летом", u"in summer")],
     u"In the morning, at night, in summer"),
    ("kazhdyy", u"каждый + accusative",
     [(u"каждый день", u"every day"), (u"каждую среду", u"every Wednesday"), (u"каждое утро", u"every morning")],
     u"Every day, every Wednesday"),
    ("ves", u"весь + accusative",
     [(u"весь день", u"all day"), (u"всю неделю", u"all week"), (u"всё утро", u"all morning")],
     u"All day, all week"),
    ("po-dat", u"ПО + dative plural",
     [(u"по вторникам", u"on Tuesdays"), (u"по утрам", u"in the mornings"), (u"по праздникам", u"on holidays")],
     u"On Tuesdays, in the mornings"),
    ("na-prep", u"НА + prepositional",
     [(u"на этой неделе", u"this week"), (u"на прошлой неделе", u"last week"), (u"на днях", u"the other day; within a few days")],
     u"This week, last week"),
    ("v-prep", u"В + prepositional",
     [(u"в мае", u"in May"), (u"в прошлом году", u"last year"), (u"в начале века", u"at the beginning of the century")],
     u"In May, last year"),
    ("date", u"The genitive for the date of an event",
     [(u"пятого мая", u"on the fifth of May"), (u"первого января", u"on the first of January")],
     u"On the fifth of May"),
    ("god-let", u"год · года · лет",
     [(u"один год", u"one year"), (u"два года", u"two years"), (u"пять лет", u"five years")],
     u"Two years, five years"),
    ("age", u"The dative for the person whose age it is",
     [(u"мне двадцать лет", u"I am twenty"), (u"ему было сорок", u"he was forty")],
     u"I am twenty"),
    ("how-long", u"The accusative alone",
     [(u"два часа", u"for two hours"), (u"всю ночь", u"all night"), (u"неделю", u"for a week")],
     u"For two hours, for a week"),
    ("na-acc", u"НА + accusative",
     [(u"на неделю", u"for a week (to stay)"), (u"на следующий день", u"the next day"), (u"опоздать на час", u"to be an hour late")],
     u"For a week, the next day"),
    ("za-acc", u"ЗА + accusative",
     [(u"за час", u"in an hour (it took an hour)"), (u"за два дня", u"in two days")],
     u"In an hour (it took)"),
    ("cherez", u"ЧЕРЕЗ + accusative",
     [(u"через час", u"in an hour (from now)"), (u"через неделю", u"in a week")],
     u"In an hour (from now)"),
    ("nazad", u"accusative + (тому) назад",
     [(u"час назад", u"an hour ago"), (u"два года тому назад", u"two years ago")],
     u"An hour ago"),
    ("s-gen", u"С + genitive",
     [(u"с утра", u"since morning"), (u"с понедельника", u"from Monday"), (u"с детства", u"since childhood")],
     u"Since morning, from Monday"),
    ("do-gen", u"ДО + genitive",
     [(u"до вечера", u"till evening"), (u"до обеда", u"before lunch")],
     u"Till evening, before lunch"),
    ("posle", u"ПОСЛЕ + genitive",
     [(u"после обеда", u"after lunch"), (u"после войны", u"after the war")],
     u"After lunch"),
    ("pered", u"ПЕРЕД + instrumental",
     [(u"перед обедом", u"just before lunch"), (u"перед сном", u"before going to sleep")],
     u"Just before lunch"),
    ("k-dat", u"К + dative",
     [(u"к вечеру", u"by evening"), (u"к пяти часам", u"by five o'clock")],
     u"By evening, by five"),
]
# How many exercises may share one answer in a chapter.
CAP = {"v-acc-day": 40, "v-acc": 12}
CAP_DEFAULT = 4
# A chapter needs this many exercises to be worth opening.
MIN_CHAPTER = 5
WEEKDAY = re.compile(u"(понедельник|вторник|сред[ау]|четверг|пятниц[ау]|суббот[ау]|воскресень[ея])")


def norm(a):
    return re.sub(r"[^а-яё ]+", " ", str(a or "").lower().replace("ё", "е")).strip()


def restream(rules):
    """`rules`: explain_time.R — key → (short, full, source)."""
    secs = {}
    for fn in sorted(os.listdir(TIME)):
        if fn.endswith(".json"):
            secs[fn[:-5]] = json.load(io.open(os.path.join(TIME, fn), encoding="utf-8"))
    # every exercise that has its construction, by construction
    pool = {}
    seen = set()
    for sid, sec in secs.items():
        for e in sec.get("exercises") or []:
            k = e.get("k")
            if not k:
                continue
            sig = (k, norm(e.get("q")), norm((e.get("answers") or [""])[0]))
            if sig in seen:
                continue
            seen.add(sig)
            # the days of the week get a chapter of their own
            if k == "v-acc" and WEEKDAY.search(norm((e.get("answers") or [""])[0])):
                k = "v-acc-day"
            pool.setdefault(k, []).append(e)
    # fewer of the same answer; a fixed shuffle so the cap keeps a spread of sources
    out_secs = []
    for k, formula, examples, tail in ORDER:
        title = u"%s: %s" % (formula, tail) if not formula.startswith("The ") and " · " not in formula else tail
        xs = list(pool.get(k) or [])
        if not xs:
            continue
        random.Random(hash(k) & 0xffff).shuffle(xs)
        per, keep = {}, []
        cap = CAP.get(k, CAP_DEFAULT)
        for e in xs:
            a = norm((e.get("answers") or [""])[0])
            if per.get(a, 0) >= cap:
                continue
            per[a] = per.get(a, 0) + 1
            keep.append(e)
        if len(keep) < MIN_CHAPTER:
            continue
        keep = [dict(e, id="q%d" % (i + 1)) for i, e in enumerate(keep)]
        short, full, src = rules.get(k.replace("-day", ""), ("", "", ""))
        # The explanation first, set large: the formula, the one idea to
        # take away, the examples, then DLI's rule in full.
        blocks = [{"t": "formula", "text": formula},
                  {"t": "lead", "text": short},
                  {"t": "ex", "items": [list(x) for x in examples]}]
        if full:
            blocks.append({"t": "p", "text": full})
        blocks.append({"t": "note", "text": (src + ". " if src else "") +
                       u"One sentence at a time, in a new order each time you open this chapter; it is finished "
                       u"when every one has been answered right. The sentences are real: the source of each is shown with it."})
        sid = "ts-" + k
        data = {"id": sid, "title": title, "blocks": blocks, "exercises": keep, "stream": True, "finite": True}
        io.open(os.path.join(TIME, sid + ".json"), "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        out_secs.append({"id": sid, "title": title, "n": len(keep), "stream": True, "finite": True})
    # the DLI lessons, as reading pages after the chapters
    lessons = []
    for sid in sorted(secs, key=lambda s: int(re.match(r"t(\d+)", s).group(1)) if re.match(r"t(\d+)-", s) else 999):
        if not re.match(r"t\d+-", sid) or re.search(r"-practice(-\d+)?$", sid):
            continue
        sec = secs[sid]
        sec["exercises"] = []
        io.open(os.path.join(TIME, sid + ".json"), "w", encoding="utf-8").write(json.dumps(sec, ensure_ascii=False, separators=(",", ":")))
        lessons.append({"id": sid, "title": u"DLI: " + sec["title"], "n": 0})
    # the practice files are no longer part of the course
    gone = 0
    for sid in secs:
        if re.search(r"-practice(-\d+)?$", sid):
            try:
                os.remove(os.path.join(TIME, sid + ".json")); gone += 1
            except OSError:
                pass
    print("time course dealt again: %d chapters (%d exercises), %d lesson pages, %d practice files removed" % (
        len(out_secs), sum(s["n"] for s in out_secs), len(lessons), gone))
    for s in out_secs:
        print("   %-9s %4d  %s" % (s["id"][3:], s["n"], s["title"]))
    return out_secs + lessons


if __name__ == "__main__":
    import sys
    sys.path.insert(0, HERE)
    from explain_time import R
    restream(R)
