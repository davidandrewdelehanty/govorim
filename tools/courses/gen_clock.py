# -*- coding: utf-8 -*-
"""Telling the Time: generate the clock drills.

Each drill is a clock time. One kind shows the time in Russian words and asks
for it on a 24-hour digital clock; the other shows the clock and asks for the
words. The words are built from dictionary forms by the rules the DLI Grammar
Reference Book states for telling the time (Lessons 40, 73 and 74, quoted on
the course pages):

  * on the hour: «два часа» — a cardinal and the hour word;
  * past the hour, up to the half: minutes, then the NEXT hour as an ordinal
    in the genitive — «пять минут третьего»; a quarter is «четверть»;
  * the half: «половина третьего»;
  * before the hour: «без» + the minutes in the genitive, then the next hour
    as a cardinal — «без десяти три»; «минут» may be left out;
  * the part of the day instead of AM/PM: утра, дня, вечера, ночи;
  * the 24-hour system: «четырнадцать ноль ноль», «семнадцать тридцать».

Every Russian word comes out of OpenCorpora through pymorphy3; nothing here
writes an ending.  python3 tools/courses/gen_clock.py -> clock_data.json
"""
import io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paradigms as P

UNITS = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
TEENS = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать",
         "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
TENS = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят"]
ORD = ["", "первый", "второй", "третий", "четвёртый", "пятый", "шестой", "седьмой", "восьмой",
       "девятый", "десятый", "одиннадцатый", "двенадцатый"]

_lex = {}


def form(word, pos, *tags):
    k = (word, pos, tags)
    if k not in _lex:
        got = P._pick(P._lemma(word, pos).lexeme, *tags, drop=P.ADJ_DROP)
        if not got:
            raise ValueError("%s %s %s" % (word, pos, tags))
        _lex[k] = got[0]
    return _lex[k]


def card(n, case="nomn", gender="masc"):
    """A cardinal 0-59 in one case; feminine for один/два where asked."""
    if n == 0:
        return form("ноль", "NOUN", case, "sing")
    words = []
    t, u = divmod(n, 10)
    if 10 <= n <= 19:
        words.append((TEENS[n - 10], "masc"))
    else:
        if t:
            words.append((TENS[t], "masc"))
        if u:
            words.append((UNITS[u], gender))
    out = []
    for w, g in words:
        if w in ("один", "два"):
            if case == "nomn":
                out.append(form(w, "NUMR", "nomn", g) if w == "два" else form(w, "ADJF", "nomn", g, "sing"))
            else:
                out.append(form(w, "NUMR", case) if w == "два" else form(w, "ADJF", case, g, "sing"))
        else:
            out.append(form(w, "NUMR", case))
    return " ".join(out)


def minutes_word(n, case="nomn"):
    """минута agreeing with n: одна минута, две минуты, пять минут."""
    last2, last = n % 100, n % 10
    if last == 1 and last2 != 11:
        return form("минута", "NOUN", case, "sing")
    if 2 <= last <= 4 and not 12 <= last2 <= 14:
        return form("минута", "NOUN", "gent" if case == "nomn" else case, "sing" if case == "nomn" else "plur")
    return form("минута", "NOUN", "gent" if case == "nomn" else case, "plur")


def hour_word(n):
    """час agreeing with n: час, два часа, пять часов; 21 час, 22 часа, 23 часа."""
    last2, last = n % 100, n % 10
    if last == 1 and last2 != 11:
        return form("час", "NOUN", "nomn", "sing")
    if 2 <= last <= 4 and not 12 <= last2 <= 14:
        return form("час", "NOUN", "gent", "sing")
    return form("час", "NOUN", "gent", "plur")


def ord_gen(h12):
    return form(ORD[h12], "ADJF", "gent", "masc", "sing")


def part_of_day(h):
    if h < 4:
        return form("ночь", "NOUN", "gent", "sing")
    if h < 12:
        return form("утро", "NOUN", "gent", "sing")
    if h < 17:
        return form("день", "NOUN", "gent", "sing")
    return form("вечер", "NOUN", "gent", "sing")


def say(h, m):
    """What a time is called.

    Returns a dict:
      main  - the way it is said, part of the day included
      tw    - every accepted 12-hour wording, WITHOUT the part of the day
      pods  - the parts of the day that may follow it (the right one first; the
              next hour's too, for «без пяти три» at the turn of a band)
      t24   - the 24-hour readings that are also accepted
      sets  - the wordings shown when the reader has to set the clock
    """
    h12 = h % 12 or 12
    nxt = (h % 12) + 1
    pod = part_of_day(h)
    pod_next = part_of_day((h + 1) % 24)
    alts = []
    if m == 0:
        hw = hour_word(h12)
        base = ("%s %s" % (card(h12), hw)) if h12 != 1 else hw
        alts += ["%s %s" % (card(h12), hw)]
        if h12 == 1:
            alts.append("один час")
    elif m < 30:
        if m == 15:
            base = "четверть %s" % ord_gen(nxt)
            alts.append("пятнадцать минут %s" % ord_gen(nxt))
        else:
            base = "%s %s %s" % (card(m, "nomn", "femn"), minutes_word(m), ord_gen(nxt))
    elif m == 30:
        base = "половина %s" % ord_gen(nxt)
        alts.append("пол" + ord_gen(nxt))
    else:
        left = 60 - m
        if left == 15:
            base = "без четверти %s" % card(nxt)
            alts.append("без пятнадцати %s" % card(nxt))
            alts.append("без пятнадцати минут %s" % card(nxt))
        else:
            short = "без %s %s" % (card(left, "gent", "femn"), card(nxt))
            full = "без %s %s %s" % (card(left, "gent", "femn"), minutes_word(left, "gent"), card(nxt))
            # «минут» is often omitted — on the five-minute marks; nobody says
            # «без одной три»
            base = short if left % 5 == 0 else full
            alts.append(full if base is short else short)
    tw = [base]
    for a in alts:
        if a not in tw:
            tw.append(a)
    pods = [pod] if pod == pod_next else [pod, pod_next]
    main = "%s %s" % (base, pod)
    # the 24-hour system
    h24 = card(h) if h else form("ноль", "NOUN", "nomn", "sing")
    hw24 = hour_word(h) if h else "часов"
    t24 = []
    if m == 0:
        t24 += ["%s ноль ноль" % h24, "%s %s" % (h24, hw24), "%s %s ровно" % (h24, hw24), "ровно %s %s" % (h24, hw24)]
        show24 = "%s ноль ноль" % h24
    else:
        mm = card(m, "nomn", "femn")
        mw = minutes_word(m)
        for mid in (["%s" % mm, "ноль %s" % mm] if m < 10 else ["%s" % mm]):
            t24 += ["%s %s" % (h24, mid), "%s %s %s" % (h24, hw24, mid),
                    "%s %s %s %s" % (h24, hw24, mid, mw), "%s %s %s" % (h24, mid, mw)]
        show24 = "%s %s" % (h24, ("ноль " + mm) if m < 10 else mm)
    out24 = []
    for a in t24:
        if a not in out24:
            out24.append(a)
    # shown when the reader sets the clock: the 12-hour wordings always carry
    # the part of the day (without it «пять минут третьего» is 2:05 or 14:05);
    # the 24-hour reading needs none, and is only given for the hours that only
    # that system uses.
    sets = [main] + [a + " " + pod for a in tw[1:] if not a.startswith("пол") and a != "один час"]
    if h >= 13:
        sets.append(show24)
    return {"main": main, "tw": tw, "pods": pods, "t24": out24, "sets": sets}


def kind(m):
    return "on" if m == 0 else "past" if m < 30 else "half" if m == 30 else "to"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    drills = []
    for h in range(24):
        for m in range(60):
            d = say(h, m)
            e = {"hhmm": "%02d:%02d" % (h, m), "k": kind(m), "q": d["main"], "sets": d["sets"],
                 "a": d["tw"], "pods": d["pods"], "a24": d["t24"],
                 "clock": "%d:%02d" % (h % 12 or 12, m), "pod": d["pods"][0]}
            # 00:25 on a twelve-hour face is «12:25», which reads as just after
            # noon; after midnight is only ever asked the other way round.
            if h == 0:
                e["noSay"] = 1
            drills.append(e)
    table = []
    for h, m in [(14, 0), (14, 5), (14, 15), (14, 21), (14, 30), (14, 40), (14, 45), (14, 59), (1, 0), (0, 10), (12, 30), (23, 55)]:
        d = say(h, m)
        t24 = [a for a in d["t24"] if a.startswith(card(h) if h else "ноль")][0]
        table.append(["%02d:%02d" % (h, m), d["main"], t24])
    io.open(os.path.join(here, "clock_data.json"), "w", encoding="utf-8").write(
        json.dumps({"drills": drills, "table": table}, ensure_ascii=False, separators=(",", ":")))
    # every Russian word must be a dictionary word
    import re
    bad = set()
    for d in drills:
        for a in d["a"] + d["a24"] + d["sets"]:
            for w in re.findall(r"[а-яё]+", a):
                if not [p for p in P.M.parse(w) if "UNKN" not in str(p.tag)]:
                    bad.add(w)
    print("%d times; words not in the dictionary: %s" % (len(drills), sorted(bad) or "none"))
    for row in table:
        print("   ", row)


if __name__ == "__main__":
    main()
