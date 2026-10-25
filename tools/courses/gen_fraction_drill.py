# -*- coding: utf-8 -*-
"""Data for the Exercises tab's fractions practice: a fraction in digits → the words.  Every word is the OpenCorpora dictionary's own form
(through gen_numerals.py / paradigms.py), put together by the rule the DLI Grammar Reference Book gives for fractions (Lesson 98, quoted on the
Grammar in Depth course page «Fractions»): numerators are cardinal and denominators ordinal, in the feminine, because the word «часть» is
implied; the conjunction «и» links a fraction to a whole number; half, third and quarter are feminine nouns (пять с половиной).
    python3 tools/courses/gen_fraction_drill.py   (from the repo root)   →   public/vocab/fractions.json
Item: [digits, [accepted wordings], the wording shown after the answer]"""
import io, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
import gen_numerals as G
DEN = [2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 20, 100, 1000]
SPECIAL = {(1, 2): ["половина"], (1, 3): ["треть"], (1, 4): ["четверть"], (2, 3): ["две трети"], (3, 4): ["три четверти"]}
def one(x):
    return x[0] if isinstance(x, (list, tuple)) else x
def frac(n, d):
    num = one(G.cardinal(n, "nomn", "femn"))
    den = one(G.ordinal(d, "nomn", "femn", "sing")) if n == 1 else one(G.ordinal(d, "gent", "femn", "plur"))
    return "%s %s" % (num, den)
items = []
for d in DEN:
    for n in range(1, 10):
        if n >= d: continue
        w = frac(n, d)
        items.append(["%d/%d" % (n, d), [w] + SPECIAL.get((n, d), []), w])
for whole in range(3, 10):
    for n, d in ((1, 2), (1, 4), (3, 4), (2, 5), (3, 8), (7, 8), (1, 3), (2, 3), (5, 6), (1, 10)):
        w = frac(n, d); a = one(G.cardinal(whole, "nomn", "masc"))
        shown = "%s и %s" % (a, w)
        alts = [shown]
        if (n, d) == (1, 2): alts = ["%s с половиной" % a, shown]; shown = alts[0]
        elif (n, d) == (1, 4): alts = ["%s с четвертью" % a, shown]; shown = alts[0]
        else: alts += ["%s и %s" % (a, x) for x in SPECIAL.get((n, d), [])]
        items.append(["%d %d/%d" % (whole, n, d), alts, shown])
out = {"rule": "In Russian, as in English, numerators are cardinal and denominators are ordinal numbers. Note that the feminine gender is used: одна вторая, две седьмых, etc. This is because the word «часть» (part) is implied. The conjunction «и» is used to link the fraction to a whole number: 3 7/8 — три и семь восьмых. «Половина», «треть» and «четверть» are feminine nouns: 5 1/2 — пять с половиной. — DLI Grammar Reference Book, Lesson 98.",
       "t": items}
p = os.path.join(ROOT, "public", "vocab", "fractions.json")
io.open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
print(len(items), "fractions;", [x for x in items if x[0] in ("1/2", "3/8", "2/5", "1/100", "5/1000", "7 1/2", "4 3/4", "3 7/8")])
