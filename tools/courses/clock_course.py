# -*- coding: utf-8 -*-
"""Telling the Time — one page of DLI's rules, then a drill for every minute up to the half and every
five minutes after it, asked in random order, alternating: the time in Russian words, set it on a 24-hour digital clock; the
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


PROMPT_SET = "Set the clock to this time."
PROMPT_SAY = ("Write this time in words, the way it is said (пять минут третьего). You may leave off утра / дня / "
              "вечера / ночи. The 24-hour way (четырнадцать ноль пять) counts too.")


def drill(d):
    """One time of the day. The page makes a question of it, at random: the
    words to be set on the clock (one of the wordings in `sets`), or the clock
    to be put into words. `a` are the accepted twelve-hour wordings (the part
    of the day in `pods` may follow, or be left off); `a24` the 24-hour ones.
    All of it is built by gen_clock.py from dictionary forms."""
    k = d["k"]
    pod = d["pod"]
    show = d["a"][0] + " (" + pod + ")"
    e = {"type": "clock", "k": k, "q": d["q"], "hhmm": d["hhmm"], "answers": d["a"], "pods": d["pods"],
         "a24": d["a24"], "sets": d["sets"], "clock": d["clock"], "pod": pod, "show": show,
         "context": CTX[k], "why": WHY[k] + " " + H24}
    if d.get("noSay"):
        e["noSay"] = 1
    return e


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

# One practice screen: every time of the day in one section, shown one at a
# time with a Next button (the app renders a section marked `stream` that way).
# The page shuffles them anew each time the section is opened and alternates
# the two kinds of question; the prompts are the same for all of them, so they
# are kept once, in the section (`prompts`).
drills = [drill(d) for d in D["drills"]]
SECTIONS.append(dict(SEC("ck-practice", "Clock practice",
                         [NOTE(u"One time at a time: set the clock, then say the next one, as long as you like. "
                               u"There is a question for every minute up to the half hour and for every five minutes after it, in a new order each time you open this page. "
                               u"Every time here is made from dictionary forms by the rules on the first page.")],
                         drills, sub="as many as you like"), stream=True,
                    prompts={"set": PROMPT_SET, "say": PROMPT_SAY}))
