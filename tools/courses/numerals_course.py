# -*- coding: utf-8 -*-
"""Declined Numerals — the chart of every declined numeral form, then a drill
for every form: type двух for 2 in the genitive, ста сорока пяти for 145.

Two sources, and nothing else:
  * every Russian form is the OpenCorpora dictionary's own, put together only
    by the DLI rules quoted below (tools/courses/gen_numerals.py ->
    numerals_data.json);
  * every sentence of explanation is quoted from the Defense Language
    Institute Russian Basic Course, Grammar Reference Book (US Government
    work, public domain), checked against the page images, with lesson and
    page.
"""
import io, json, os, random

from kit import SEC, P, H, NOTE, T, FILL

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(io.open(os.path.join(HERE, "numerals_data.json"), encoding="utf-8"))
TB_ = D["tables"]
DR = D["drills"]


def TB(key):
    t = TB_[key]
    return T(t["head"], t["rows"])


FORMS = ("Every form on this page is the OpenCorpora dictionary's own (CC BY-SA 4.0), "
         "put together by the rules quoted above.")


def src(where):
    return NOTE("DLI Grammar Reference Book, %s. · %s" % (where, FORMS))


# The rule each topic's drills practise: (one line above the question, the
# fuller rule shown once answered). Quoted, never paraphrased.
Q = {
 "one": (u"«The number “ОДИН” acts as an adjective. It agrees with the nouns to which it refers in gender, number and case.»",
         u"«The number “ОДИН” acts as an adjective. It agrees with the nouns to which it refers in gender, number and case. "
         u"ОДИН (ОДНА, ОДНО) declines like ЭТОТ (ЭТА, ЭТО).» «Note that with masculine inanimate nouns the Accusative "
         u"of “ОДИН” is the same as the Nominative. With animate nouns it is the same as the Genitive… "
         u"The feminine Accusative is always “ОДНУ”.» — DLI Grammar Reference Book, Lesson 70, p. 24."),
 "two": (u"«In oblique cases the numbers always agree in case with the noun to which they refer.»",
         u"«In oblique cases the numbers always agree in case with the noun to which they refer (двум студентам; "
         u"с тремя книгами; на четырёх грузовиках). Note also the “Ь” and the stress in the Instrumental case "
         u"of “ЧЕТЫРЕ” — “ЧЕТЫРЬМЯ”.» The accusative: «два, две or двух» — the genitive form with an "
         u"animate noun. — DLI Grammar Reference Book, Lessons 70–71, pp. 26 and 35."),
 "five": (u"«Numerals ending in soft sign (5–20 and 30) are declined like feminine nouns ending in soft sign (ночь, площадь etc.)»",
          u"«Numerals ending in soft sign (5–20 and 30) are declined like feminine nouns ending in soft sign (ночь, "
          u"площадь etc.)» «Note that the Accusative of both animate and inanimate is always the same as the "
          u"Nominative.» — DLI Grammar Reference Book, Lesson 71, p. 32."),
 "forty": (u"«Note that both parts of these four numerals (50, 60, 70, 80) are declined separately but are written together.»",
           u"«Note that both parts of these four numerals (50, 60, 70, 80) are declined separately but are written "
           u"together.» For 40, 90 and 100: «Note that there are only two forms: 1) N. & A. сорок, девяносто, сто; "
           u"2) In all other cases — сорока, девяноста, ста.» — DLI Grammar Reference Book, Lesson 71, p. 33."),
 "hund": (u"«Both parts of these numerals are declined separately but are written together.»",
          u"«Both parts of these numerals are declined separately but are written together. Note that the second "
          u"part has plural endings (-стам, -стами, -стах).» — DLI Grammar Reference Book, Lesson 72, p. 37."),
 "comp": (u"«Note that each component of a compound numeral is declined separately.»",
          u"«Note that each component of a compound numeral is declined separately.» On the accusative: "
          u"«The word один follows this rule even when it appears at the end of a compound numeral: Я вижу "
          u"двадцать одного студента.» «However, два (две), три, четыре etc. appearing at the end of the "
          u"compound numerals do not follow the above pattern in the Accusative case. Their Accusative (both animate "
          u"and inanimate) is usually the same as the Nominative.» — DLI Grammar Reference Book, Lesson 71, "
          u"pp. 32–34."),
 "thou": (u"«Тысяча (fem.) and миллион (masc.) are used and declined as nouns and have both singular and plural forms.»",
          u"«Тысяча (fem.) and миллион (masc.) are used and declined as nouns and have both singular and plural "
          u"forms: одна тысяча, две тысячи, пять тысяч; один миллион, два миллиона, пять "
          u"миллионов.» «Note that each component of a compound numeral is declined separately.» "
          u"— DLI Grammar Reference Book, Lessons 69 and 71."),
 "coll": (u"«Collective numerals are declined like adjectives in the plural.»",
          u"«Collective numerals are declined like adjectives in the plural, however in oblique cases they are "
          u"usually replaced by the corresponding form of the cardinal numerals.» (L.98, p. 188) For полтора: "
          u"«These forms are used for Nominative-Accusative only. For all other cases the form “полутора” is "
          u"used for all genders.» (L.99, p. 193) — DLI Grammar Reference Book."),
 "ord": (u"«Ordinal numerals are used and declined as Adjectives in both Singular and Plural.»",
         u"«Ordinal numerals are used and declined as Adjectives in both Singular and Plural. In compound "
         u"ordinal numerals only the last element is actually an ordinal, and only this element is declined.» "
         u"«The first part is in the Genitive case: пятидесятый, двухсотый. This part does not change in "
         u"declension.» — DLI Grammar Reference Book, Lesson 72, pp. 37–38."),
 "date": (u"«In a date the day is rendered by an ordinal number.»",
          u"«In a statement of a date the day is in the nominative and the month is in the genitive: Какое "
          u"сегодня число? — Сегодня пятое февраля.» «To state the date of the event both the day and "
          u"the month are in the genitive: Какого числа вы уезжаете? — Десятого августа.» «In a compound "
          u"ordinal number only the last word is declined.» — DLI Grammar Reference Book, Lesson 50, "
          u"pp. 153–154."),
 "year": (u"«The preposition В + Prepositional is used to indicate the year or the month in which an event takes place.»",
          u"«The preposition В + Prepositional is used: (a) to indicate the year or the month (but never the week) "
          u"in which an event takes place… Я был там в 1958-ом году.» (L.73, p. 43) «In compound ordinal "
          u"numerals only the last element is actually an ordinal, and only this element is declined.» (L.72, "
          u"p. 37) — DLI Grammar Reference Book."),
}


def drills(key, rule):
    ctx, why = Q[rule]
    return [dict(FILL(u"___ (%s)" % hint, answers, why=why, prompt=task), context=ctx)
            for hint, task, answers in DR[key]]


def practice(sid, title, key, rule, size=50, seed=0):
    """The topic's drills, in a fixed shuffled order, as sets of `size`."""
    xs = drills(key, rule)
    random.Random(seed).shuffle(xs)
    cut = [xs[i:i + size] for i in range(0, len(xs), size)]
    out = []
    for n, part in enumerate(cut, 1):
        out.append(SEC(sid + "-practice" + ("" if n == 1 else "-%d" % n),
                       "Practice%s: %s" % ("" if len(cut) == 1 else " %d" % n, title),
                       [NOTE(FORMS)], part, sub="%d forms to write" % len(part)))
    return out


SECTIONS = []
A = SECTIONS.append

A(SEC("n0-chart", "The chart: every numeral, every case", [
    P(u"«Numerals are declined in Russian. They have their own pattern of declension.»"),
    H(u"1 — один, одна, одно"), TB("one"),
    H(u"2, 3, 4"), TB("two-four"),
    H(u"оба, обе"), TB("oba"),
    H(u"5 to 10"), TB("five-ten"),
    H(u"11 to 20"), TB("eleven-twenty"),
    H(u"30 to 100"), TB("tens"),
    H(u"200 to 900"), TB("hundreds"),
    H(u"Thousands and millions"), TB("thousand"),
    H(u"Compound numerals — DLI's own two examples"), TB("dli-compound"),
    H(u"полтора, полтораста"), TB("poltora"),
    H(u"Collective numerals"), TB("collective"),
    H(u"Ordinals 1st to 10th"), TB("ord-units"),
    H(u"Ordinals 20th to 100th"), TB("ord-tens"),
    H(u"Ordinals 200th to 2000th"), TB("ord-hundreds"),
    H(u"An ordinal in every gender — третий"), TB("ord-feminine"),
    H(u"Dates"), TB("dates"),
    H(u"Years"), TB("years"),
    src("Lessons 50 and 69–73, 98–99; the appendix table on p. 35"),
]))

# ── Real sentences: the numeral blanked, the figure as the hint ──
# tools/courses/numeral_decl.py finds them in the library's public-domain
# books and in Tatoeba (those come with a translation). One endless practice
# screen per group: a new order every time it is opened, Next after each.
SENT_P = os.path.join(HERE, "numeral_decl.json")
SENT = json.load(io.open(SENT_P, encoding="utf-8")) if os.path.exists(SENT_P) else {}
SENT_NOTE = (u"Real sentences: from the library's public-domain books (author and title above each), and from "
             u"Tatoeba (tatoeba.org, CC BY 2.0 FR), shown with their translation. The numeral is blanked; type it "
             u"in the form the sentence needs. ё and е are both accepted.")


def sentences(key, rule):
    out = []
    for x in SENT.get(key, []):
        e = dict(FILL(x["q"], [x["a"]], why=Q[rule][1], prompt=(u"*%s*" % x["src"]) if x["src"] else (u"*%s*" % x["en"]) if x["en"] else None),
                 context=Q[rule][0], k=rule)
        out.append(e)
    return out


SENT_GROUPS = [
    ("s1-one", u"In sentences: 1 — одного, одной, одним…", "one", "one", "Lesson 70, p. 24"),
    ("s2-two-four", u"In sentences: 2, 3, 4 — двух, трём, четырьмя…", "two", "two", "Lessons 70–71, pp. 26 and 35"),
    ("s3-five-thirty", u"In sentences: 5 to 20 and 30 — пяти, десятью…", "five", "five", "Lesson 71, p. 32"),
    ("s4-forty-hundred", u"In sentences: 40 to 100 — сорока, пятидесяти, ста…", "forty", "forty", "Lesson 71, p. 33"),
    ("s5-compound", u"In sentences: 21 to 104 — двадцати двух…", "comp", "comp", "Lesson 71, pp. 32–34"),
    ("s6-ordinals", u"In sentences: ordinals — третьего, двадцать пятом…", "ord", "ord", "Lesson 72, pp. 37–38"),
]
for sid, title, key, rule, where in SENT_GROUPS:
    xs = sentences(key, rule)
    if not xs:
        continue
    # the builder keeps the one explanation once, under `k`, not on each of the sentences
    A(dict(SEC(sid, title, [P(Q[rule][1].rsplit(u" — ", 1)[0]), src(where), NOTE(SENT_NOTE)], xs,
                sub="%d real sentences, as many as you like" % len(xs)), stream=True))

A(SEC("n1-one", u"1 — один, одна, одно", [
    P(Q["one"][1].rsplit(u" — ", 1)[0]), TB("one"), src("Lesson 70, p. 24"),
], drills("n1-one", "one")))

A(SEC("n2-two-four", u"2, 3, 4 and оба", [
    P(Q["two"][1].rsplit(u" — ", 1)[0]), TB("two-four"), TB("oba"), src("Lessons 70–71, pp. 26 and 35"),
], drills("n2-two-four", "two")))

A(SEC("n3-five-thirty", u"5 to 20, and 30", [
    P(Q["five"][1].rsplit(u" — ", 1)[0]), TB("five-ten"), TB("eleven-twenty"), src("Lesson 71, p. 32"),
], drills("n3-five-thirty", "five")))

A(SEC("n4-forty-hundred", u"40 to 100", [
    P(Q["forty"][1].rsplit(u" — ", 1)[0]), TB("tens"), src("Lesson 71, p. 33"),
], drills("n4-forty-hundred", "forty")))

A(SEC("n5-hundreds", u"200 to 900", [
    P(Q["hund"][1].rsplit(u" — ", 1)[0]), TB("hundreds"), src("Lesson 72, p. 37"),
], drills("n5-hundreds", "hund")))

A(SEC("n6-compound", u"21 to 99", [
    P(Q["comp"][1].rsplit(u" — ", 1)[0]), TB("dli-compound"), src("Lesson 71, pp. 32–34"),
]))
SECTIONS.extend(practice("n6-compound", u"21 to 99", "n6-compound", "comp", seed=6))

A(SEC("n7-three-digit", u"101 to 999", [
    P(Q["comp"][1].rsplit(u" — ", 1)[0]), TB("dli-compound"), TB("hundreds"),
    src("Lessons 71–72, pp. 32–37"),
]))
SECTIONS.extend(practice("n7-three-digit", u"101 to 999", "n7-three-digit", "comp", seed=7))

A(SEC("n8-thousands", u"Thousands and millions", [
    P(Q["thou"][1].rsplit(u" — ", 1)[0]), TB("thousand"), src("Lessons 69 and 71"),
]))
SECTIONS.extend(practice("n8-thousands", u"thousands and millions", "n8-thousands", "thou", seed=8))

A(SEC("n9-collective", u"двое, трое … and полтора", [
    P(Q["coll"][1].rsplit(u" — ", 1)[0]), TB("collective"), TB("poltora"), src("Lessons 98–99, pp. 188 and 193"),
], drills("n9-collective", "coll")))

A(SEC("n10-ordinals", u"Ordinals: первый to двухтысячный", [
    P(Q["ord"][1].rsplit(u" — ", 1)[0]), TB("ord-units"), TB("ord-tens"), TB("ord-hundreds"), TB("ord-feminine"),
    src("Lesson 72, pp. 37–38"),
]))
SECTIONS.extend(practice("n10-ordinals", u"ordinals", "n10-ordinals", "ord", seed=10))

A(SEC("n11-dates", u"Dates: двадцать пятое, двадцать пятого", [
    P(Q["date"][1].rsplit(u" — ", 1)[0]), TB("dates"), src("Lesson 50, pp. 153–154"),
]))
SECTIONS.extend(practice("n11-dates", u"dates", "n11-dates", "date", seed=11))

A(SEC("n12-years", u"Years: в тысяча девятьсот сорок пятом году", [
    P(Q["year"][1].rsplit(u" — ", 1)[0]), TB("years"), src("Lessons 72–73, pp. 37 and 43"),
]))
SECTIONS.extend(practice("n12-years", u"years, 1700 to 2030", "n12-years", "year", seed=12))
