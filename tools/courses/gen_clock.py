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
import io, json, os, random, sys

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


def hour_word(h12):
    if h12 == 1:
        return form("час", "NOUN", "nomn", "sing")
    if 2 <= h12 <= 4:
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
    """(the main 12-hour phrase with its part of day, [every accepted answer])."""
    h12 = h % 12 or 12
    nxt = (h % 12) + 1
    pod = part_of_day(h)
    pod_next = part_of_day((h + 1) % 24)
    main, alts = "", []
    if m == 0:
        hw = hour_word(h12)
        base = ("%s %s" % (card(h12), hw)) if h12 != 1 else hw
        main = "%s %s" % (base, pod)
        alts += [base, "один час" if h12 == 1 else base, "%s %s" % (card(h12), hw)]
    elif m < 30:
        if m == 15:
            base = "четверть %s" % ord_gen(nxt)
            alts.append("пятнадцать минут %s" % ord_gen(nxt))
        else:
            base = "%s %s %s" % (card(m, "nomn", "femn"), minutes_word(m), ord_gen(nxt))
        main = "%s %s" % (base, pod)
        alts.append(base)
    elif m == 30:
        base = "половина %s" % ord_gen(nxt)
        main = "%s %s" % (base, pod)
        alts += [base, "пол" + ord_gen(nxt)]
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
        main = "%s %s" % (base, pod)
        alts.append(base)
    pods = {pod, pod_next}
    acc = [main]
    for a in alts:
        for x in [a] + ["%s %s" % (a, p) for p in pods]:
            if x not in acc:
                acc.append(x)
    # the 24-hour system
    h24 = card(h) if h else form("ноль", "NOUN", "nomn", "sing")
    hw24 = hour_word(h) if h else "часов"
    if m == 0:
        acc += ["%s ноль ноль" % h24, "%s %s" % (h24, hw24), "%s %s ровно" % (h24, hw24), "ровно %s %s" % (h24, hw24)]
    else:
        mm = card(m, "nomn", "femn")
        mw = minutes_word(m)
        for mid in (["%s" % mm, "ноль %s" % mm] if m < 10 else ["%s" % mm]):
            acc += ["%s %s" % (h24, mid), "%s %s %s" % (h24, hw24, mid),
                    "%s %s %s %s" % (h24, hw24, mid, mw), "%s %s %s" % (h24, mid, mw)]
    out = []
    for a in acc:
        if a not in out:
            out.append(a)
    return main, out


def times(n, seed=7):
    """A spread of times: half on the five-minute marks, the rest anywhere,
    every hour of the day and every kind of phrase in fair measure."""
    r = random.Random(seed)
    out, seen = [], set()
    while len(out) < n:
        h = r.randrange(24)
        m = r.choice([0, 15, 30, 45, 5, 10, 20, 25, 35, 40, 50, 55]) if r.random() < 0.55 else r.randrange(60)
        if (h, m) in seen:
            continue
        seen.add((h, m))
        out.append((h, m))
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    drills = []
    for i, (h, m) in enumerate(times(400)):
        main_phrase, acc = say(h, m)
        hhmm = "%02d:%02d" % (h, m)
        if i % 2 == 0:
            drills.append({"type": "clockset", "hhmm": hhmm, "say": main_phrase, "accept": acc})
        else:
            drills.append({"type": "clocksay", "hhmm": hhmm, "say": main_phrase, "accept": acc})
    table = []
    for h, m in [(14, 0), (14, 5), (14, 15), (14, 21), (14, 30), (14, 40), (14, 45), (14, 59), (1, 0), (0, 10), (12, 30), (23, 55)]:
        mp, acc = say(h, m)
        t24 = [a for a in acc if a.startswith(card(h) if h else "ноль")][0]
        table.append(["%02d:%02d" % (h, m), mp, t24])
    io.open(os.path.join(here, "clock_data.json"), "w", encoding="utf-8").write(
        json.dumps({"drills": drills, "table": table}, ensure_ascii=False, indent=1))
    # every Russian word must be a dictionary word
    import re
    bad = set()
    for d in drills:
        for a in d["accept"]:
            for w in re.findall(r"[а-яё]+", a):
                if not [p for p in P.M.parse(w) if "UNKN" not in str(p.tag)]:
                    bad.add(w)
    print("%d drills; words not in the dictionary: %s" % (len(drills), sorted(bad) or "none"))
    for row in table:
        print("   ", row)


if __name__ == "__main__":
    main()
