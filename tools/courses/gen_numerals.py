# -*- coding: utf-8 -*-
"""Generate the Declined Numerals course data: the chart, and a drill for every
declined form of every number it covers.

Nothing here writes a Russian ending. Each word of each answer is the
OpenCorpora dictionary's own form (through pymorphy3, via paradigms.py), and
words are put together only by the rules the DLI Grammar Reference Book
states, quoted on the course pages beside the drills:

  * «Note that each component of a compound numeral is declined separately.»
    (Lesson 71, p. 34)
  * «In compound ordinal numerals only the last element is actually an
    ordinal, and only this element is declined.»  (Lesson 72, p. 37)
  * the accusative: «with masculine inanimate nouns the Accusative of ОДИН is
    the same as the Nominative. With animate nouns it is the same as the
    Genitive» (L.70 p.24); 2, 3, 4 «два, две or двух» (L.71 p.35); 5 and up
    «the Accusative of both animate and inanimate is always the same as the
    Nominative» (L.71 p.32); at the end of a compound, один keeps the rule but
    два, три, четыре are «usually the same as the Nominative» (L.71 pp.32-33).
  * тысяча, миллион «are used and declined as nouns» (L.69), and in oblique
    cases «the numbers always agree in case with the noun» (L.70 p.26).

    pip install pymorphy3 pymorphy3-dicts-ru
    python3 tools/courses/gen_numerals.py      ->  tools/courses/numerals_data.json
"""
import io, itertools, json, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paradigms as P

CASES = [c for c, _ in P.CASES]
CASE_EN = {"nomn": "nominative", "gent": "genitive", "datv": "dative",
           "accs": "accusative", "ablt": "instrumental", "loct": "prepositional"}
OBLIQUE = ["gent", "datv", "ablt", "loct"]

UNITS = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
TEENS = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать",
         "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
TENS = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят",
        "восемьдесят", "девяносто"]
HUNDS = ["", "сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот", "семьсот",
         "восемьсот", "девятьсот"]

UNIT_ORD = ["", "первый", "второй", "третий", "четвёртый", "пятый", "шестой", "седьмой",
            "восьмой", "девятый"]
TEEN_ORD = ["десятый", "одиннадцатый", "двенадцатый", "тринадцатый", "четырнадцатый",
            "пятнадцатый", "шестнадцатый", "семнадцатый", "восемнадцатый", "девятнадцатый"]
TENS_ORD = ["", "", "двадцатый", "тридцатый", "сороковой", "пятидесятый", "шестидесятый",
            "семидесятый", "восьмидесятый", "девяностый"]
HUND_ORD = ["", "сотый", "двухсотый", "трёхсотый", "четырёхсотый", "пятисотый", "шестисотый",
            "семисотый", "восьмисотый", "девятисотый"]


# ----------------------------------------------------------- dictionary access

_LEX = {}


def lex(word):
    if word not in _LEX:
        for pos in ("NUMR", "ADJF", "NOUN", "NPRO"):
            try:
                _LEX[word] = P._lemma(word, pos).lexeme
                break
            except P.NotInDict:
                continue
        else:
            raise P.NotInDict(word)
    return _LEX[word]


def forms(word, *tags):
    got = P._pick(lex(word), *tags, drop=P.ADJ_DROP)
    if not got:
        raise ValueError("%s: no form for %s" % (word, tags))
    return got


def numword(word, case, gender="masc", anim=False):
    """One numeral word in one case, as the dictionary gives it."""
    if word == "один":
        if case == "accs":
            if gender == "femn":
                return forms(word, "accs", "femn", "sing")
            return forms(word, "accs", "anim" if anim else "inan", gender, "sing") \
                if gender == "masc" else forms(word, "accs", "neut", "sing")
        return forms(word, case, gender, "sing")
    if word == "два" and case in ("nomn", "accs") and not (case == "accs" and anim):
        g = "femn" if gender == "femn" else "masc"
        got = [f for f in forms(word, "nomn") if (f == "две") == (g == "femn")]
        return got
    if case == "accs":
        return forms(word, "gent") if anim else forms(word, "nomn")
    return forms(word, case)


def noun_after(word, count, case):
    """тысяча / миллион after a count, in this case. Nominative and
    accusative follow the count (1 тысяча, 2-4 тысячи, 5+ тысяч); in the
    oblique cases the noun agrees in case — singular after a count ending in
    one, plural otherwise."""
    last2 = count % 100
    last = count % 10
    one = last == 1 and last2 != 11
    if case in ("nomn", "accs"):
        if one:
            return forms(word, case, "sing")
        if last in (2, 3, 4) and not 12 <= last2 <= 14:
            return forms(word, "gent", "sing")
        return forms(word, "gent", "plur")
    return forms(word, case, "sing" if one else "plur")


# ------------------------------------------------------------ number to words

def under1000(n, gender):
    out = []
    h, r = divmod(n, 100)
    if h:
        out.append((HUNDS[h], "masc"))
    if 10 <= r <= 19:
        out.append((TEENS[r - 10], "masc"))
    else:
        t, u = divmod(r, 10)
        if t:
            out.append((TENS[t], "masc"))
        if u:
            out.append((UNITS[u], gender))
    return out


def parts(n, gender="masc"):
    """[(word, gender, kind, count)] — kind is 'num' or 'noun'."""
    out = []
    m, n = divmod(n, 1000000)
    if m:
        if m != 1:
            out += [(w, g, "num", None) for w, g in under1000(m, "masc")]
        out.append(("миллион", None, "noun", m))
    k, n = divmod(n, 1000)
    if k:
        if k != 1:
            out += [(w, g, "num", None) for w, g in under1000(k, "femn")]
        out.append(("тысяча", None, "noun", k))
    out += [(w, g, "num", None) for w, g in under1000(n, gender)]
    return out


def cardinal_nom(n, gender="masc"):
    return " ".join(numword(w, "nomn", g)[0] if k == "num" else noun_after(w, c, "nomn")[0]
                    for w, g, k, c in parts(n, gender))


def cardinal(n, case, gender="masc", anim=False):
    """Every accepted spelling of n in this case."""
    ps = parts(n, gender)
    simple = len(ps) == 1
    alts = []
    for i, (w, g, kind, cnt) in enumerate(ps):
        last = i == len(ps) - 1
        if kind == "noun":
            alts.append(noun_after(w, cnt, case))
            continue
        if case == "accs":
            if w == "один" and last:
                alts.append(numword(w, "accs", g, anim))
            elif anim and simple and w in ("два", "три", "четыре"):
                alts.append(numword(w, "accs", g, True))
            elif w == "один":
                alts.append(numword(w, "accs", g, False))
            else:
                alts.append(numword(w, "nomn", g))
        else:
            alts.append(numword(w, case, g))
    return [" ".join(x) for x in itertools.product(*alts)][:6]


def ordinal_split(n):
    """(cardinal prefix value, ordinal lemma)."""
    if n >= 1000 and n % 1000 == 0:
        k = n // 1000
        if k == 1:
            return 0, "тысячный"
        word = "".join(numword(w, "gent", g)[0] for w, g in under1000(k, "masc")) + "тысячный"
        return 0, word
    if n % 100 == 0:
        return n - n % 1000, HUND_ORD[(n % 1000) // 100]
    r = n % 100
    if 10 <= r <= 19:
        return n - r, TEEN_ORD[r - 10]
    if r % 10 == 0:
        return n - r, TENS_ORD[r // 10]
    return n - r % 10, UNIT_ORD[r % 10]


def ordinal(n, case, gender="masc", number="sing", anim=False):
    pre, word = ordinal_split(n)
    head = cardinal_nom(pre) + " " if pre else ""
    lx = P._lemma(word, "ADJF").lexeme
    if case == "accs" and gender == "masc" and number == "sing":
        got = P._pick(lx, "ADJF", "accs", "anim" if anim else "inan", "masc", "sing", drop=P.ADJ_DROP)
    elif number == "plur":
        got = P._pick(lx, "ADJF", case, "plur", drop=P.ADJ_DROP) if case != "accs" else \
            P._pick(lx, "ADJF", "accs", "anim" if anim else "inan", "plur", drop=P.ADJ_DROP)
    else:
        got = P._pick(lx, "ADJF", case, gender, "sing", drop=P.ADJ_DROP)
    if not got:
        raise ValueError("%s %s %s" % (word, case, gender))
    return [head + g for g in got]


def ordinal_nom(n, gender="masc"):
    return ordinal(n, "nomn", gender)[0]


# ------------------------------------------------------------------- drills

def label(tasks):
    """'genitive', 'dative', 'prepositional' -> 'Genitive, dative and prepositional'."""
    tasks = list(dict.fromkeys(tasks))
    if len(tasks) == 1:
        s = tasks[0]
    else:
        # share a common tail ("… feminine") when there is one
        tails = [t.split(" ", 1)[1] if " " in t else "" for t in tasks]
        if tails[0] and all(x == tails[0] for x in tails):
            heads = [t.split(" ", 1)[0] for t in tasks]
            s = ", ".join(heads[:-1]) + " and " + heads[-1] + " " + tails[0]
        else:
            s = ", ".join(tasks[:-1]) + " and " + tasks[-1]
    return s[0].upper() + s[1:]


def merge(items):
    """[(hint, task, answers)] -> one drill per (hint, answers)."""
    order, by = [], {}
    for hint, task, ans in items:
        k = (hint, tuple(ans))
        if k not in by:
            by[k] = []
            order.append(k)
        by[k].append(task)
    return [[h, label(by[(h, a)]), list(a)] for h, a in order]


def card_drills(n, gender="masc", with_anim=True):
    nom = cardinal_nom(n, gender)
    hint = "%d · %s" % (n, nom) if n < 10 ** 6 else nom
    items = []
    for c in OBLIQUE:
        g_en = {"femn": " feminine", "neut": " neuter"}.get(gender, "")
        items.append((hint, CASE_EN[c] + g_en, cardinal(n, c, gender)))
    # accusative only where it differs from the nominative
    inan = cardinal(n, "accs", gender, False)
    if inan[0] != nom:
        items.append((hint, "accusative" + {"femn": " feminine"}.get(gender, ""), inan))
    if with_anim:
        an = cardinal(n, "accs", gender, True)
        if an[0] != nom and an != inan:
            items.append((hint, "accusative, with an animate noun", an))
    return items


def ord_drills(n, genders=("masc", "femn"), plural=True, cases=OBLIQUE, hint_word=None):
    items = []
    for g in genders:
        hint = "%d \u00b7 %s" % (n, ordinal_nom(n, g))   # the word itself says it is an ordinal
        g_en = {"masc": "masculine", "femn": "feminine", "neut": "neuter"}[g]
        for c in cases:
            items.append((hint, CASE_EN[c] + " " + g_en, ordinal(n, c, g)))
        if g == "femn":
            items.append((hint, "accusative feminine", ordinal(n, "accs", "femn")))
    if plural:
        hint = "%d \u00b7 %s" % (n, ordinal(n, "nomn", number="plur")[0])
        for c in cases:
            items.append((hint, CASE_EN[c] + " plural", ordinal(n, c, number="plur")))
    return items


def sets(items, size=40, seed=0):
    """Shuffle one topic's drills (a fixed order, so a rebuild changes nothing)
    and cut them into practice sets."""
    xs = list(items)
    random.Random(seed).shuffle(xs)
    return [xs[i:i + size] for i in range(0, len(xs), size)]


# ------------------------------------------------------------------- tables

def card_table(nums, cases=CASES, gender="masc"):
    head = [""] + [str(n) for n in nums]
    rows = []
    for c in cases:
        label_ = {"nomn": "N.", "gent": "G.", "datv": "D.", "accs": "A.", "ablt": "I.", "loct": "P."}[c]
        rows.append([label_] + [" / ".join(cardinal(n, c, gender)) for n in nums])
    return head, rows


def card_table_anim(nums):
    head = [""] + [str(n) for n in nums]
    lab = {"nomn": "N.", "gent": "G.", "datv": "D.", "ablt": "I.", "loct": "P."}
    rows = []
    for c in ("nomn", "gent", "datv"):
        rows.append([lab[c]] + [" / ".join(cardinal(n, c)) for n in nums])
    rows.append(["A. inan."] + [" / ".join(cardinal(n, "accs")) for n in nums])
    rows.append(["A. anim."] + [" / ".join(cardinal(n, "accs", anim=True)) for n in nums])
    for c in ("ablt", "loct"):
        rows.append([lab[c]] + [" / ".join(cardinal(n, c)) for n in nums])
    return head, rows


def words_row(nums, f):
    return [[str(n), f(n)] for n in nums]


def build():
    OUT = {"tables": {}, "drills": {}}
    T, DR = OUT["tables"], OUT["drills"]

    def put(k, hr):
        T[k] = {"head": hr[0], "rows": hr[1]}

    # -------- the chart
    put("one", P.pron_full("один"))
    put("two-four", card_table_anim([2, 3, 4]))
    T["two-four"]["head"] = ["", "2 · два, две", "3 · три", "4 · четыре"]
    oba = lex("оба")
    put("oba", (["", "Masc. & Neut. · оба", "Fem. · обе"],
                [[{"nomn": "N.", "gent": "G.", "datv": "D.", "accs": "A.", "ablt": "I.", "loct": "P."}[c]] +
                 [", ".join(P._pick(oba, c, g, drop=P.ADJ_DROP) or ["\u2014"]) for g in ("masc", "femn")]
                 for c in CASES]))
    put("five-ten", card_table(range(5, 11)))
    put("eleven-twenty", card_table(range(11, 21)))
    put("tens", card_table([30, 40, 50, 60, 70, 80, 90, 100]))
    put("hundreds", card_table([200, 300, 400, 500, 600, 700, 800, 900]))
    put("thousand", card_table([1000, 2000, 5000, 1000000, 2000000, 5000000]))
    put("dli-compound", card_table_anim([21, 145]))
    put("collective", P.numr_table(["двое", "трое", "четверо", "пятеро", "шестеро", "семеро"]))
    put("poltora", P.numr_table(["полтора", "полтораста"]))
    put("ord-units", ([""] + ["%d-й" % n for n in range(1, 11)],
                      [["N."] + [ordinal_nom(n) for n in range(1, 11)]] +
                      [[l] + [ordinal(n, c)[0] for n in range(1, 11)]
                       for c, l in (("gent", "G."), ("datv", "D."), ("ablt", "I."), ("loct", "P."))]))
    put("ord-tens", ([""] + ["%d-й" % n for n in (20, 30, 40, 50, 60, 70, 80, 90, 100)],
                     [["N."] + [ordinal_nom(n) for n in (20, 30, 40, 50, 60, 70, 80, 90, 100)]] +
                     [[l] + [ordinal(n, c)[0] for n in (20, 30, 40, 50, 60, 70, 80, 90, 100)]
                      for c, l in (("gent", "G."), ("loct", "P."))]))
    put("ord-hundreds", ([""] + ["%d-й" % n for n in (200, 300, 500, 900, 1000, 2000)],
                         [["N."] + [ordinal_nom(n) for n in (200, 300, 500, 900, 1000, 2000)]] +
                         [[l] + [ordinal(n, c)[0] for n in (200, 300, 500, 900, 1000, 2000)]
                          for c, l in (("gent", "G."), ("loct", "P."))]))
    put("ord-feminine", P.pron_full("третий"))
    put("dates", ([""] + ["%d" % d for d in (1, 2, 3, 10, 21, 25, 31)],
                  [["Какое число? (N.)"] + [ordinal_nom(d, "neut") for d in (1, 2, 3, 10, 21, 25, 31)],
                   ["Какого числа? (G.)"] + [ordinal(d, "gent", "neut")[0] for d in (1, 2, 3, 10, 21, 25, 31)]]))
    put("years", ([""] + ["%d" % y for y in (1812, 1917, 1945, 1961, 2000, 2014)],
                  [["N."] + [ordinal_nom(y) for y in (1812, 1917, 1945, 1961, 2000, 2014)],
                   ["G. (… года)"] + [ordinal(y, "gent")[0] for y in (1812, 1917, 1945, 1961, 2000, 2014)],
                   ["P. (в … году)"] + [ordinal(y, "loct")[0] for y in (1812, 1917, 1945, 1961, 2000, 2014)]]))

    # -------- drills, by topic
    one = []
    for g in ("masc", "femn", "neut"):
        hint = "1 · " + numword("один", "nomn", g)[0]
        g_en = {"masc": "masculine", "femn": "feminine", "neut": "neuter"}[g]
        for c in OBLIQUE:
            one.append((hint, CASE_EN[c] + " " + g_en, numword("один", c, g)))
        if g == "masc":
            one.append((hint, "accusative masculine, with an animate noun", numword("один", "accs", g, True)))
        if g == "femn":
            one.append((hint, "accusative feminine", numword("один", "accs", g)))
    DR["n1-one"] = merge(one)

    two = []
    for n in (2, 3, 4):
        two += card_drills(n)
    two += card_drills(2, "femn", with_anim=False)
    for g, nom in (("masc", "оба"), ("femn", "обе")):
        hint = nom
        g_en = {"masc": "masculine/neuter", "femn": "feminine"}[g]
        for c in OBLIQUE:
            two.append((hint, CASE_EN[c] + " " + g_en, P._pick(lex("оба"), c, g, drop=P.ADJ_DROP) or
                        P._pick(lex("оба"), c, drop=P.ADJ_DROP)))
    DR["n2-two-four"] = merge(two)

    DR["n3-five-thirty"] = merge(sum([card_drills(n) for n in list(range(5, 21)) + [30]], []))
    DR["n4-forty-hundred"] = merge(sum([card_drills(n) for n in (40, 50, 60, 70, 80, 90, 100)], []))
    DR["n5-hundreds"] = merge(sum([card_drills(n) for n in range(200, 1000, 100)], []))
    DR["n6-compound"] = merge(sum([card_drills(n) for n in range(21, 100) if n % 10], []))
    DR["n7-three-digit"] = merge(sum([card_drills(n) for n in range(101, 1000) if n % 100], []))
    thou = [n for n in range(1000, 10000, 100)] + [n * 1000 for n in (10, 11, 12, 15, 20, 21, 22, 25, 30,
                                                                      40, 50, 100, 200, 500)] + \
           [10 ** 6, 2 * 10 ** 6, 5 * 10 ** 6, 21 * 10 ** 6]
    DR["n8-thousands"] = merge(sum([card_drills(n) for n in thou], []))

    coll = []
    for w in ("двое", "трое", "четверо", "пятеро", "шестеро", "семеро"):
        for c in OBLIQUE:
            coll.append((w, CASE_EN[c], P._pick(lex(w), c, drop=P.ADJ_DROP)))
    for w, g in (("полтора", "masc"), ("полторы", "femn")):
        for c in OBLIQUE:
            coll.append(("1,5 · " + w, CASE_EN[c], P._pick(lex("полтора"), c, drop=P.ADJ_DROP)))
    for c in OBLIQUE:
        coll.append(("150 · полтораста", CASE_EN[c], P._pick(lex("полтораста"), c, drop=P.ADJ_DROP)))
    DR["n9-collective"] = merge(coll)

    ords = []
    for n in list(range(1, 101)) + list(range(200, 1000, 100)) + [1000, 2000]:
        ords += ord_drills(n, plural=(n <= 20))
    DR["n10-ordinals"] = merge(ords)

    dates = []
    for d in range(1, 32):
        hint = "%d · %s" % (d, ordinal_nom(d, "neut"))
        dates.append((hint, "genitive neuter (какого числа?)", ordinal(d, "gent", "neut")))
        dates.append(("%d · %s" % (d, ordinal_nom(d)), "nominative neuter (какое число?)",
                      [ordinal_nom(d, "neut")]))
        dates.append((hint, "prepositional masculine/neuter", ordinal(d, "loct", "neut")))
    DR["n11-dates"] = merge(dates)

    years = []
    for y in range(1700, 2031):
        hint = "%d · %s" % (y, ordinal_nom(y))
        years.append((hint, "prepositional (в … году)", ordinal(y, "loct")))
        years.append((hint, "genitive (… года)", ordinal(y, "gent")))
    DR["n12-years"] = merge(years)
    return OUT


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = build()
    p = os.path.join(here, "numerals_data.json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    n = sum(len(v) for v in out["drills"].values())
    print("%d tables, %d drills -> %s" % (len(out["tables"]), n, p))
    for k, v in out["drills"].items():
        print("   %-18s %5d" % (k, len(v)))


if __name__ == "__main__":
    main()
