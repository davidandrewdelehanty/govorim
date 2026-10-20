# -*- coding: utf-8 -*-
"""Telling the Time — one page of DLI's rules, then 400 clock drills that
alternate: the time in Russian words, set it on a 24-hour digital clock; the
clock, write the time in words.

The words are dictionary forms put together by the rules quoted below
(tools/courses/gen_clock.py -> clock_data.json). The rules are the course's
own transcription of the DLI Grammar Reference Book, Lessons 40, 73 and 74.
"""
import io, json, os

from kit import SEC, P, H, NOTE, T, EX

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(io.open(os.path.join(HERE, "clock_data.json"), encoding="utf-8"))

ON = (u"«Time on the hour: Сейчас два часа. Я приехал туда в два часа. (в + Acc.)» Instead of AM or PM "
      u"Russians say «of the morning» (утра), «of the day» (дня), «of the evening» (вечера), «of the "
      u"night» (ночи). — DLI Grammar Reference Book, Lessons 40 and 73.")
PAST = (u"«The moment the minute hand moves beyond the full hour, it begins to denote time in terms of some "
        u"fraction of the following hour. Thus, “five minutes past two” is rendered in Russian by «пять минут "
        u"третьего» (lit. “five minutes of the third”). Note that “the following hour” is always denoted by "
        u"an ORDINAL numeral in the Genitive case.» «пятнадцать минут десятого — or — четверть десятого». "
        u"— DLI Grammar Reference Book, Lesson 74.")
HALF = (u"«Half past the hour: Сейчас половина третьего. Я пришёл туда в половине третьего. (в + Prep.)» "
        u"«This process continues until the half-hour mark only.» — DLI Grammar Reference Book, Lessons 40 "
        u"and 74.")
TO = (u"«The moment the minute hand crosses the half-hour mark, it begins to denote time in terms of some "
      u"fraction lacking for the completion of the next full hour. Thus, “five (minutes) to three” is "
      u"rendered in Russian by «без пяти (минут) три». Note that the preposition «без» takes the Genitive "
      u"case. The hour is rendered as a CARDINAL numeral and the word “minutes” is often omitted.» «без "
      u"пятнадцати двенадцать — or — без четверти двенадцать». — DLI Grammar Reference Book, Lesson 74.")
H24 = (u"«The 24-hour system. Transportation, radio and military installations use the 24-hour system: "
       u"Самолёт вылетел в 14.00 (четырнадцать ноль ноль). Командир будет здесь в 17.30 (семнадцать "
       u"тридцать).» — DLI Grammar Reference Book, Lesson 73.")
CTX = {"on": u"On the hour: «два часа»; and утра / дня / вечера / ночи instead of AM and PM.",
       "past": u"Past the hour: the minutes, then the NEXT hour as an ordinal in the genitive — «пять минут третьего».",
       "half": u"Half past: «половина третьего».",
       "to": u"Before the hour: «без» + the minutes in the genitive, then the next hour — «без пяти три»."}
WHY = {"on": ON, "past": PAST, "half": HALF, "to": TO}


def kind(hhmm):
    m = int(hhmm[3:])
    return "on" if m == 0 else "past" if m < 30 else "half" if m == 30 else "to"


def drill(d):
    k = kind(d["hhmm"])
    if d["type"] == "clockset":
        return {"type": "clockset", "q": d["say"], "hhmm": d["hhmm"], "answers": [d["hhmm"]],
                "prompt": "Set the clock to this time.",
                "context": CTX[k], "why": WHY[k]}
    # The clock to be put into words shows the time as it is said: twelve
    # hours, and the part of the day beside it. A 24-hour display would ask
    # for «двадцать тридцать пять» while the answer waited for «без двадцати
    # пяти девять»; setting the 24-hour clock from the words is the other
    # drill, where that mapping is the point.
    h, m = int(d["hhmm"][:2]), int(d["hhmm"][3:])
    return {"type": "fill", "q": "___", "clock": "%d:%02d" % (h % 12 or 12, m), "pod": d["say"].split()[-1],
            "answers": d["accept"],
            "prompt": "Write this time in words — the way it is said (пять минут третьего), with or without утра / дня / вечера / ночи; or the 24-hour way (четырнадцать ноль пять).",
            "context": CTX[k], "why": WHY[k] + " " + H24}


SECTIONS = [SEC("ck0-rules", "How the time is told", [
    P(u"*Memorize the following expressions:*"),
    EX([u"Который час?", u"What time is it?"], [u"В котором часу?", u"At what time?"]),
    H(u"Time expressions in hours and minutes"),
    T(["", u"Который час?", u"В котором часу?"], [
        ["Time on the hour", u"Сейчас два часа.", u"Я приехал туда в два часа. (в + Acc.)"],
        ["Time after the hour", u"Уже пять минут третьего.", u"Я позвоню вам в пять минут третьего. (в + Acc.)"],
        ["Half past the hour", u"Сейчас половина третьего.", u"Я пришёл туда в половине третьего. (в + Prep.)"],
        ["Time before the hour", u"Сейчас без десяти (минут) три.", u"Я буду там без десяти три. (без + Gen.; the prep. «в» is not used)"]]),
    P(u"In order to grasp the “mechanics of time expression” in Russian remember the following:"),
    P(u"1. The moment the minute hand moves beyond the full hour, it begins to denote time in terms of some fraction of the following hour. Thus, “five minutes past two” is rendered in Russian by «пять минут третьего» (lit. “five minutes of the third”). Note that “the following hour” is always denoted by an ORDINAL numeral in the Genitive case."),
    EX([u"десять минут первого", u"10 min. past twelve"], [u"пятнадцать минут десятого — or — четверть десятого", u"a quarter past nine"]),
    P(u"IMPORTANT: This process continues until the half-hour mark only."),
    P(u"2. The moment the minute hand crosses the half-hour mark, it begins to denote time in terms of some fraction lacking for the completion of the next full hour. Thus, “five (minutes) to three” is rendered in Russian by «без пяти (минут) три» (Lit. without 5 min. 3). Note that the preposition «без» takes the Genitive case. The hour is rendered as a CARDINAL numeral and the word “minutes” is often omitted. The preposition «в» is not used when some event occurs at the time mentioned."),
    EX([u"без двадцати (минут) пять", u"twenty to five"], [u"без пятнадцати двенадцать — or — без четверти двенадцать", u"a quarter to twelve"]),
    H(u"Time systems"),
    P(u"(a) The 12-hour system"),
    EX([u"семь часов утра", u"7:00 AM"], [u"два часа дня", u"2:00 PM"], [u"шесть часов вечера", u"6:00 PM"], [u"два часа ночи", u"2:00 AM"]),
    P(u"Instead of AM or PM Russians say: “of the morning” (from 3:00 or 4:00 AM to 12:00); “of the day” (after 12:00 noon to 4:00 PM); “of the evening” (from 5:00 PM to 11:00 PM); “of the night” (from midnight to 3:00 or 4:00 AM)."),
    P(u"(b) The 24-hour system. Transportation, radio and military installations use the 24-hour system. Thus:"),
    EX([u"Самолёт вылетел в 14.00 (четырнадцать ноль ноль).", ""], [u"Командир будет здесь в 17.30 (семнадцать тридцать).", ""]),
    H(u"The same clock, said both ways"),
    T(["", u"Который час?", u"24-hour"], D["table"]),
    NOTE(u"DLI Grammar Reference Book, Lessons 40, 73 and 74. The table and every drill after this page: dictionary forms (OpenCorpora, CC BY-SA 4.0) put together by these rules, tools/courses/gen_clock.py."),
])]

SIZE = 20
drills = D["drills"]
for n, i in enumerate(range(0, len(drills), SIZE), 1):
    part = [drill(d) for d in drills[i:i + SIZE]]
    SECTIONS.append(SEC("ck%d" % n, "Clock practice %d" % n,
                        [NOTE(u"Set the clock, then say the next one. Every time here is made from dictionary forms by the rules on the first page.")],
                        part, sub="%d times" % len(part)))
